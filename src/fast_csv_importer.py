#!/usr/bin/env python3
"""
Fast CSV Importer with batch processing and optimized database operations.
Supports both CLI and real-time UI progress callbacks.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any
import threading
from queue import Queue
import sys
import os

# Add src directory to path if needed
BASE_DIR = Path(__file__).parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database_connection import DatabaseConnection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ImportCancelledError(Exception):
    """Raised when the import process is cancelled by the user."""
    pass


class FastCSVImporter:
    """High-performance CSV importer with batch processing and progress tracking."""
    
    def __init__(self):
        """Initialize the CSV importer."""
        self.db_connection = DatabaseConnection()
        self.batch_size = 2000  # Increased batch size for better throughput
        self.grouping_batch_size = 1000
        
        # Statistics
        self.total_records = 0
        self.processed_records = 0
        self.inserted_records = 0
        self.matched_records = 0
        self.unmatched_records = 0
        self.skipped_records = 0
        
        # State
        self.cancel_requested = False
        self.progress_callback: Optional[Callable[[str, Optional[float]], None]] = None
        self.progress_stage_start = 0.0
        self.progress_stage_span = 100.0
        
        # Cache for grouping lookups
        self.grouping_lookup_cache = {}
        self.grouping_missing_values = set()
        self.grouping_updates = []
        
        # Control tag for tracking
        self.test_control_value = None
        
        # Timing
        self.start_time = None
    
    def set_progress_callback(self, callback: Optional[Callable[[str, Optional[float]], None]]):
        """Register a callback to receive progress updates."""
        self.progress_callback = callback
    
    def emit_progress(self, message: str, progress: Optional[float] = None):
        """Send progress updates to the registered callback and log."""
        logger.info(message)
        scaled_progress = None
        if progress is not None:
            normalized = max(0.0, min(100.0, float(progress)))
            scaled_progress = self.progress_stage_start + (
                self.progress_stage_span * (normalized / 100.0)
            )
            scaled_progress = max(0.0, min(100.0, scaled_progress))
        
        if self.progress_callback:
            try:
                self.progress_callback(message, scaled_progress)
            except Exception as callback_error:
                logger.warning("Progress callback error: %s", str(callback_error))
    
    def set_progress_stage(self, start: float, span: float) -> None:
        """Define the progress range used for subsequent progress updates."""
        safe_start = max(0.0, min(100.0, start))
        safe_span = max(0.0, min(100.0 - safe_start, span))
        self.progress_stage_start = safe_start
        self.progress_stage_span = safe_span if safe_span > 0 else 0.0001
    
    def request_cancel(self):
        """Signal that the import should cancel at the next opportunity."""
        self.cancel_requested = True
        self.emit_progress("Cancellation requested by user.")
    
    def clean_mlsf_no(self, mlsf_no: str) -> str:
        """Clean mlsfNo for matching by removing 'AND EXTENSION' and '(TEMP)'."""
        if not mlsf_no:
            return mlsf_no
        
        cleaned = str(mlsf_no).strip()
        cleaned = cleaned.replace('AND EXTENSION', '').replace('and extension', '')
        cleaned = cleaned.replace('(TEMP)', '').replace('(temp)', '')
        cleaned = ' '.join(cleaned.split())
        return cleaned.strip()
    
    def prefetch_grouping_lookup(self, cleaned_values: List[str]) -> None:
        """Bulk load grouping matches using indexed lookups."""
        values_to_lookup = [
            value.strip()
            for value in cleaned_values
            if value
            and value.strip() not in self.grouping_lookup_cache
            and value.strip() not in self.grouping_missing_values
        ]
        
        if not values_to_lookup:
            logger.info("Grouping cache already primed; skipping prefetch")
            return
        
        total_candidates = len(values_to_lookup)
        logger.info("Prefetching grouping matches for %d unique MLS numbers", total_candidates)
        self.emit_progress(f"Prefetching grouping data ({total_candidates} unique values)...")
        
        chunk_size = 1000
        total_matched = 0
        total_processed = 0
        
        try:
            conn = self.db_connection.get_connection()
            if conn is None:
                raise RuntimeError("Database connection failed")
            
            cursor = conn.cursor()
            
            for start in range(0, total_candidates, chunk_size):
                if self.cancel_requested:
                    raise ImportCancelledError()
                
                chunk = values_to_lookup[start:start + chunk_size]
                placeholders = ",".join(["?"] * len(chunk))
                
                # Use indexed lookup on awaiting_fileno
                query = f"""
                    SELECT LTRIM(RTRIM(awaiting_fileno)) AS awaiting_trim, tracking_id
                    FROM [dbo].[grouping]
                    WHERE LTRIM(RTRIM(awaiting_fileno)) IN ({placeholders})
                """
                
                cursor.execute(query, tuple(chunk))
                rows = cursor.fetchall()
                chunk_matched_keys = set()
                
                for awaiting_trim, tracking_id in rows:
                    if awaiting_trim and awaiting_trim not in self.grouping_lookup_cache:
                        self.grouping_lookup_cache[awaiting_trim] = tracking_id
                        chunk_matched_keys.add(awaiting_trim)
                
                total_matched += len(chunk_matched_keys)
                unreturned = set(chunk) - chunk_matched_keys
                self.grouping_missing_values.update(unreturned)
                
                total_processed += len(chunk)
                progress_percent = (total_processed / total_candidates) * 100
                self.emit_progress(
                    f"Prefetch progress: {total_processed}/{total_candidates} ({progress_percent:.1f}%)",
                    progress_percent
                )
            
            logger.info(
                "Grouping prefetch completed: %d matched, %d unmatched",
                total_matched,
                total_candidates - total_matched
            )
            self.emit_progress("Grouping prefetch completed.", 100.0)
            
        except ImportCancelledError:
            raise
        except Exception as e:
            logger.error("Error during grouping prefetch: %s", str(e))
            raise
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    def lookup_tracking_id(self, cleaned_mlsf_no: str) -> Optional[str]:
        """Get cached tracking ID or return None."""
        if not cleaned_mlsf_no:
            return None
        
        cleaned_value = cleaned_mlsf_no.strip()
        if cleaned_value in self.grouping_lookup_cache:
            return self.grouping_lookup_cache[cleaned_value]
        if cleaned_value in self.grouping_missing_values:
            return None
        
        return None
    
    def stage_grouping_update(self, tracking_id: str, original_mlsf_no: str) -> None:
        """Queue grouping update for batched execution."""
        if not tracking_id:
            return
        self.grouping_updates.append((original_mlsf_no, self.test_control_value, tracking_id))
        if len(self.grouping_updates) >= self.grouping_batch_size:
            self._flush_grouping_updates()
    
    def _flush_grouping_updates(self) -> None:
        """Flush staged grouping updates to the database in bulk."""
        if not self.grouping_updates:
            return
        
        update_query = """
            UPDATE [dbo].[grouping]
            SET mapping = 1,
                mls_fileno = ?,
                test_control = ?
            WHERE tracking_id = ?
        """
        
        try:
            conn = self.db_connection.get_connection()
            if conn is None:
                raise RuntimeError("Database connection failed")
            
            cursor = conn.cursor()
            cursor.executemany(update_query, self.grouping_updates)
            conn.commit()
            logger.info("Flushed %d grouping updates", len(self.grouping_updates))
            
        except Exception as exc:
            logger.error("Bulk grouping update failed: %s", str(exc))
            raise
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
            self.grouping_updates.clear()
    
    def read_csv_file(self, csv_path: Path) -> Optional[List[Dict[str, Any]]]:
        """Read and parse CSV file with proper encoding detection."""
        try:
            logger.info(f"Reading CSV file: {csv_path}")
            
            if not csv_path.exists():
                raise FileNotFoundError(f"CSV file not found: {csv_path}")
            
            records = []
            
            # Try multiple encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            csv_data = None
            
            for encoding in encodings:
                try:
                    with open(csv_path, 'r', encoding=encoding) as f:
                        reader = csv.DictReader(f)
                        csv_data = list(reader)
                    logger.info(f"Successfully read CSV with {encoding} encoding")
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if csv_data is None:
                raise RuntimeError("Could not read CSV file with any supported encoding")
            
            records = csv_data
            self.total_records = len(records)
            logger.info(f"Successfully read CSV file with {self.total_records} records")
            self.emit_progress(f"CSV file loaded: {self.total_records} records", 100.0)
            
            return records
            
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}")
            self.emit_progress(f"Error reading CSV: {str(e)}")
            return None
    
    def prepare_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare records for insertion with grouping lookups."""
        logger.info("Preparing records for database insertion...")
        self.emit_progress("Preparing records...")
        self.set_progress_stage(5.0, 20.0)
        
        prepared_data = []
        current_time = datetime.now()
        unique_cleaned_values = set()
        
        # First pass: collect unique cleaned values for prefetch
        rows_to_process = []
        for index, row in enumerate(records):
            try:
                original_mlsf_no = str(row.get('mlsfNo', '')).strip()
                if not original_mlsf_no:
                    logger.warning(f"Row {index}: No mlsfNo found, skipping")
                    self.skipped_records += 1
                    continue
                
                cleaned_mlsf_no = self.clean_mlsf_no(original_mlsf_no)
                rows_to_process.append((index, row, original_mlsf_no, cleaned_mlsf_no))
                if cleaned_mlsf_no:
                    unique_cleaned_values.add(cleaned_mlsf_no.strip())
                    
            except Exception as e:
                logger.error(f"Error preprocessing record at index {index}: {str(e)}")
                self.skipped_records += 1
                continue
        
        total_to_process = len(rows_to_process)
        if total_to_process == 0:
            logger.warning("No valid rows found in CSV file after preprocessing")
            return prepared_data
        
        if self.cancel_requested:
            raise ImportCancelledError()
        
        # Prefetch grouping data
        self.set_progress_stage(5.0, 20.0)
        self.prefetch_grouping_lookup(list(unique_cleaned_values))
        
        if self.cancel_requested:
            raise ImportCancelledError()
        
        # Second pass: prepare records with tracking IDs
        self.set_progress_stage(25.0, 20.0)
        progress_interval = max(1, total_to_process // 20)
        processed_count = 0
        
        try:
            for index, row, original_mlsf_no, cleaned_mlsf_no in rows_to_process:
                try:
                    if self.cancel_requested:
                        raise ImportCancelledError()
                    
                    tracking_id = self.lookup_tracking_id(cleaned_mlsf_no)
                    
                    if tracking_id:
                        logger.debug(f"Row {index}: Found tracking_id: {tracking_id}")
                        self.stage_grouping_update(tracking_id, original_mlsf_no)
                        self.matched_records += 1
                    else:
                        logger.debug(f"Row {index}: No matching tracking_id for '{cleaned_mlsf_no}'")
                        self.unmatched_records += 1
                    
                    # Build location string
                    layout_name = str(row.get('layoutName', '')).strip()
                    lga_name = str(row.get('lgaName', '')).strip()
                    district_name = str(row.get('districtName', '')).strip()
                    
                    location = f"{lga_name}, {district_name}"
                    if layout_name:
                        location = f"{layout_name}, {location}"
                    
                    record = {
                        'kangisFileNo': str(row.get('kangisFileNo', '')).strip() or None,
                        'mlsfNo': original_mlsf_no,
                        'NewKANGISFileNo': None,
                        'FileName': str(row.get('currentAllottee', '')).strip() or None,
                        'created_at': current_time,
                        'location': location,
                        'created_by': 'CSV Bulk Importer',
                        'type': 'KANGIS',
                        'is_deleted': 0,
                        'SOURCE': 'KANGIS GIS',
                        'plot_no': str(row.get('plotNo', '')).strip() or None,
                        'tp_no': str(row.get('tpPlanNo', '')).strip() or None,
                        'tracking_id': tracking_id,
                        'date_migrated': str(current_time),
                        'migrated_by': '1',
                        'migration_source': 'KANGIS GIS',
                        'test_control': self.test_control_value
                    }
                    
                    prepared_data.append(record)
                    processed_count += 1
                    
                    if (processed_count % progress_interval == 0) or processed_count == total_to_process:
                        progress_percent = (processed_count / total_to_process) * 100
                        self.emit_progress(
                            f"Preparing records: {processed_count}/{total_to_process} ({progress_percent:.1f}%)",
                            progress_percent
                        )
                    
                except ImportCancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error preparing record at index {index}: {str(e)}")
                    self.skipped_records += 1
                    continue
                    
        finally:
            if self.grouping_updates:
                self._flush_grouping_updates()
        
        logger.info(f"Prepared {len(prepared_data)} records for insertion")
        logger.info(f"Matched records: {self.matched_records}")
        logger.info(f"Unmatched records: {self.unmatched_records}")
        logger.info(f"Skipped records: {self.skipped_records}")
        
        self.emit_progress(
            f"Prepared {len(prepared_data)} records (matched: {self.matched_records}, unmatched: {self.unmatched_records}, skipped: {self.skipped_records})",
            100.0
        )
        
        return prepared_data
    
    def insert_batch(self, batch_data: List[Dict[str, Any]], batch_num: int = 0, total_batches: int = 0) -> int:
        """Insert a batch of records into the database with per-row progress."""
        insert_sql = """
        INSERT INTO [dbo].[fileNumber] (
            [kangisFileNo], [mlsfNo], [NewKANGISFileNo], [FileName], [created_at],
            [location], [created_by], [type], [is_deleted],
            [SOURCE], [plot_no], [tp_no], [tracking_id], [date_migrated],
            [migrated_by], [migration_source], [test_control]
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            conn = self.db_connection.get_connection()
            if conn is None:
                raise RuntimeError("Database connection failed")
            
            cursor = conn.cursor()
            
            # Insert each record individually to provide per-row progress
            inserted_count = 0
            for idx, record in enumerate(batch_data):
                if self.cancel_requested:
                    raise ImportCancelledError()
                
                values = (
                    record['kangisFileNo'],
                    record['mlsfNo'],
                    record['NewKANGISFileNo'],
                    record['FileName'],
                    record['created_at'],
                    record['location'],
                    record['created_by'],
                    record['type'],
                    record['is_deleted'],
                    record['SOURCE'],
                    record['plot_no'],
                    record['tp_no'],
                    record['tracking_id'],
                    record['date_migrated'],
                    record['migrated_by'],
                    record['migration_source'],
                    record['test_control']
                )
                
                try:
                    cursor.execute(insert_sql, values)
                    inserted_count += 1
                    self.processed_records += 1
                    
                    # Commit every 10 records for better performance
                    if inserted_count % 10 == 0:
                        conn.commit()
                    
                    # Emit per-row progress every 5 records
                    if inserted_count % 5 == 0:
                        progress_in_batch = (inserted_count / len(batch_data)) * 100
                        current_progress = ((self.processed_records / self.total_records) * 100) if self.total_records > 0 else 0
                        
                        mlsf_no = record.get('mlsfNo', 'N/A')
                        allottee = record.get('FileName', '')[:30]
                        
                        msg = f"Inserting: {mlsf_no} - {allottee} | Batch {batch_num}/{total_batches} ({progress_in_batch:.0f}%) | Total: {self.processed_records}/{self.total_records}"
                        self.emit_progress(msg, current_progress)
                    
                except Exception as row_error:
                    logger.warning(f"Error inserting row {idx}: {str(row_error)}")
                    continue
            
            # Final commit
            if inserted_count % 10 != 0:
                conn.commit()
            
            return inserted_count
            
        except ImportCancelledError:
            raise
        except Exception as e:
            logger.error(f"Error inserting batch: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
            raise
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    def run_import(self, csv_path: Path, control_tag: str = "PROD") -> bool:
        """Run the complete CSV import process."""
        self.test_control_value = control_tag if control_tag else None
        self.start_time = datetime.now()
        self.cancel_requested = False
        
        logger.info("="*70)
        logger.info("Starting CSV import process...")
        logger.info("="*70)
        self.emit_progress("Starting CSV import process...")
        self.set_progress_stage(0.0, 5.0)
        
        try:
            # Test database connection
            logger.info("Testing database connection...")
            conn = self.db_connection.get_connection()
            if conn is None:
                raise RuntimeError("Database connection failed. Check .env settings.")
            conn.close()
            self.emit_progress("Database connection successful", 100.0)
            
            # Read CSV file
            self.set_progress_stage(0.0, 5.0)
            records = self.read_csv_file(csv_path)
            if records is None or len(records) == 0:
                logger.error("Failed to read CSV file or file is empty")
                return False
            
            # Prepare records with grouping lookups
            self.set_progress_stage(5.0, 40.0)
            prepared_data = self.prepare_records(records)
            if not prepared_data:
                logger.warning("No data prepared for insertion")
                return False
            
            # Insert records in batches
            logger.info(f"Inserting {len(prepared_data)} records in batches of {self.batch_size}...")
            self.set_progress_stage(45.0, 50.0)
            
            total_inserted = 0
            for i in range(0, len(prepared_data), self.batch_size):
                if self.cancel_requested:
                    raise ImportCancelledError()
                
                batch = prepared_data[i:i + self.batch_size]
                batch_number = (i // self.batch_size) + 1
                total_batches = (len(prepared_data) + self.batch_size - 1) // self.batch_size
                
                logger.info(f"Processing batch {batch_number}/{total_batches} ({len(batch)} records)...")
                self.emit_progress(
                    f"Processing batch {batch_number}/{total_batches} ({len(batch)} records)...",
                    (i / len(prepared_data)) * 100
                )
                
                try:
                    inserted_count = self.insert_batch(batch, batch_number, total_batches)
                    total_inserted += inserted_count
                    
                    progress_percent = (total_inserted / len(prepared_data)) * 100
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    rate = total_inserted / elapsed if elapsed > 0 else 0
                    
                    self.emit_progress(
                        f"Batch {batch_number} complete: {total_inserted}/{len(prepared_data)} records - {rate:.0f} rec/sec",
                        progress_percent
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to insert batch {batch_number}: {str(e)}")
                    return False
            
            self.inserted_records = total_inserted
            
            # Summary
            elapsed = (datetime.now() - self.start_time).total_seconds()
            rate = total_inserted / elapsed if elapsed > 0 else 0
            
            logger.info("="*70)
            logger.info("CSV Import Completed Successfully!")
            logger.info("="*70)
            logger.info(f"Total records read: {self.total_records}")
            logger.info(f"Skipped records: {self.skipped_records}")
            logger.info(f"Records inserted: {total_inserted}")
            logger.info(f"Matched groupings: {self.matched_records}")
            logger.info(f"Unmatched groupings: {self.unmatched_records}")
            logger.info(f"Elapsed time: {elapsed:.2f} seconds")
            logger.info(f"Import rate: {rate:.0f} records/second")
            logger.info("="*70)
            
            self.emit_progress(
                f"✓ Import complete! {total_inserted} records inserted at {rate:.0f} rec/sec",
                100.0
            )
            
            return True
            
        except ImportCancelledError:
            logger.info("Import cancelled by user.")
            self.emit_progress("Import cancelled by user.")
            return False
        except Exception as e:
            logger.error(f"Import process failed: {str(e)}")
            self.emit_progress(f"Error: {str(e)}")
            return False


def main():
    """CLI entry point for CSV import."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fast CSV importer for file numbers")
    parser.add_argument("--csv", default="FileNos_PRO.csv", help="Path to CSV file")
    parser.add_argument("--control-tag", default="PROD", help="Control tag for tracking")
    args = parser.parse_args()
    
    csv_path = Path(args.csv).expanduser().resolve()
    
    importer = FastCSVImporter()
    importer.set_progress_callback(lambda msg, pct: print(f"{msg} ({pct:.1f}%)" if pct else msg))
    
    success = importer.run_import(csv_path, args.control_tag)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
