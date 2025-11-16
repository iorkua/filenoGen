#!/usr/bin/env python3
"""
Excel File Importer for FileNos_Updated.xlsx
Imports data from Excel file into the fileNumber table with proper field mapping.
"""

import pandas as pd
from datetime import datetime
import logging
from pathlib import Path
from typing import Callable, Optional
from database_connection import DatabaseConnection
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('excel_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


READ_STAGE = (0.0, 5.0)
PREFETCH_STAGE = (5.0, 30.0)
PREPARATION_STAGE = (35.0, 35.0)
INSERT_STAGE = (70.0, 25.0)
VALIDATION_STAGE = (95.0, 5.0)


class ImportCancelledError(Exception):
    """Raised when the import process is cancelled by the user."""
    pass

class ExcelImporter:
    def __init__(self):
        """Initialize the Excel importer."""
        self.db_connection = DatabaseConnection()
        base_dir = Path(__file__).parent.parent
        excel_name = os.getenv("EXCEL_IMPORT_FILE", "FileNos_TEST.xlsx")
        excel_path = Path(excel_name)
        if not excel_path.is_absolute():
            excel_path = base_dir / excel_path
        self.excel_file_path = excel_path

        rows_env = os.getenv("EXCEL_IMPORT_NROWS")
        if rows_env is None:
            self.max_rows = None if excel_name.lower().endswith("_pro.xlsx") else 10
        else:
            try:
                rows_value = int(rows_env)
                self.max_rows = None if rows_value <= 0 else rows_value
            except ValueError:
                logger.warning(
                    "Invalid EXCEL_IMPORT_NROWS value '%s'. Falling back to default.",
                    rows_env
                )
                self.max_rows = None if excel_name.lower().endswith("_pro.xlsx") else 10

        self.batch_size = 1000
        self.total_records = 0
        self.processed_records = 0
        self.matched_records = 0
        self.unmatched_records = 0
        control_value = os.getenv("EXCEL_IMPORT_CONTROL", "TEST")
        self.test_control_value = control_value if control_value != "" else None
        self.grouping_lookup_cache = {}
        self.grouping_missing_values = set()
        self.grouping_updates = []
        self.grouping_update_batch_size = int(os.getenv("GROUPING_UPDATE_BATCH", "500"))
        self.progress_callback: Optional[Callable[[str, Optional[float]], None]] = None
        self.cancel_requested = False
        self.progress_stage_start = 0.0
        self.progress_stage_span = 100.0
        
    def clean_mlsf_no_for_matching(self, mlsf_no):
        """
        Clean mlsfNo for matching purposes by removing 'AND EXTENSION' and '(TEMP)'.
        
        Args:
            mlsf_no (str): Original mlsfNo from Excel
            
        Returns:
            str: Cleaned mlsfNo for matching with awaiting_fileno
        """
        if not mlsf_no:
            return mlsf_no
            
        cleaned = str(mlsf_no).strip()
        
        # Remove 'AND EXTENSION' (case insensitive)
        cleaned = cleaned.replace('AND EXTENSION', '').replace('and extension', '')
        
        # Remove '(TEMP)' (case insensitive)
        cleaned = cleaned.replace('(TEMP)', '').replace('(temp)', '')
        
        # Clean up extra spaces
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()

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
    
    def _fetch_tracking_id_from_db(self, cleaned_mlsf_no):
        """Fetch a single tracking ID directly from the database."""
        try:
            conn = self.db_connection.get_connection()
            cursor = conn.cursor()
            query = """
                SELECT TOP 1 tracking_id 
                FROM [dbo].[grouping]
                WHERE LTRIM(RTRIM(awaiting_fileno)) = ?
                ORDER BY id
            """
            cursor.execute(query, (cleaned_mlsf_no.strip(),))
            result = cursor.fetchone()
            if result:
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Error looking up tracking ID for {cleaned_mlsf_no}: {str(e)}")
            return None
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def prefetch_grouping_lookup(self, cleaned_values):
        """Bulk load grouping matches in manageable chunks to reduce lookup queries."""
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

        chunk_size = 500
        total_matched = 0
        total_processed = 0

        try:
            conn = self.db_connection.get_connection()
            cursor = conn.cursor()

            for start in range(0, total_candidates, chunk_size):
                if self.cancel_requested:
                    raise ImportCancelledError()
                chunk = values_to_lookup[start:start + chunk_size]
                placeholders = ",".join(["?"] * len(chunk))
                query = f"""
                    SELECT LTRIM(RTRIM(awaiting_fileno)) AS awaiting_trim, tracking_id
                    FROM [dbo].[grouping]
                    WHERE LTRIM(RTRIM(awaiting_fileno)) IN ({placeholders})
                    ORDER BY id
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
                logger.debug(
                    "Prefetch progress: %d/%d candidates processed (%d matched in chunk)",
                    total_processed,
                    total_candidates,
                    len(chunk_matched_keys)
                )

            logger.info(
                "Grouping prefetch completed: %d matched, %d unmatched",
                total_matched,
                total_candidates - total_matched
            )
            self.emit_progress(
                "Grouping prefetch completed.",
                100.0
            )

        except ImportCancelledError:
            raise
        except Exception as e:
            logger.error("Error during grouping prefetch: %s", str(e))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def lookup_tracking_id_from_grouping(self, cleaned_mlsf_no):
        """Return cached tracking ID or fall back to a direct lookup if needed."""
        if not cleaned_mlsf_no:
            return None

        cleaned_value = cleaned_mlsf_no.strip()
        if cleaned_value in self.grouping_lookup_cache:
            return self.grouping_lookup_cache[cleaned_value]
        if cleaned_value in self.grouping_missing_values:
            return None

        tracking_id = self._fetch_tracking_id_from_db(cleaned_value)
        if tracking_id:
            self.grouping_lookup_cache[cleaned_value] = tracking_id
        else:
            self.grouping_missing_values.add(cleaned_value)
        return tracking_id
    
    def _flush_grouping_updates(self):
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
            cursor = conn.cursor()
            if hasattr(cursor, "fast_executemany"):
                cursor.fast_executemany = True
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

    def stage_grouping_update(self, tracking_id, original_mlsf_no):
        """Queue grouping update for batched execution."""
        if not tracking_id:
            return
        self.grouping_updates.append((original_mlsf_no, self.test_control_value, tracking_id))
        if len(self.grouping_updates) >= self.grouping_update_batch_size:
            self._flush_grouping_updates()
    
    def read_excel_file(self):
        """Read and validate the Excel file. Limit to first 10 records for testing."""
        try:
            logger.info(f"Reading Excel file: {self.excel_file_path}")
            
            if not self.excel_file_path.exists():
                raise FileNotFoundError(f"Excel file not found: {self.excel_file_path}")
            
            read_kwargs = {}
            if self.max_rows is not None:
                read_kwargs["nrows"] = self.max_rows
            df = pd.read_excel(self.excel_file_path, **read_kwargs)
            
            # Expected columns from Excel
            expected_columns = [
                'mlsfNo', 'kangisFileNo', 'plotNo', 'tpPlanNo', 
                'currentAllottee', 'layoutName', 'districtName', 'lgaName'
            ]
            
            # Check if all required columns exist
            missing_columns = [col for col in expected_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing columns in Excel file: {missing_columns}")
                logger.info(f"Available columns: {list(df.columns)}")
                return None
            
            limit_note = (
                f"limited to first {self.max_rows} records"
                if self.max_rows is not None
                else "full dataset"
            )
            logger.info(
                "Successfully read Excel file with %s records (%s)",
                len(df),
                limit_note
            )
            logger.info(f"Columns: {list(df.columns)}")
            self.emit_progress(
                f"Excel file loaded: {len(df)} records ({limit_note})",
                100.0
            )
            
            return df
            
        except Exception as e:
            logger.error(f"Error reading Excel file: {str(e)}")
            return None
    
    def prepare_data_for_insertion(self, df):
        """
        Prepare DataFrame for database insertion with tracking ID lookup from grouping table.
        
        New Logic:
        1. Clean mlsfNo for matching (remove AND EXTENSION and TEMP)
        2. Lookup tracking_id from grouping table where awaiting_fileno matches
        3. If found: use existing tracking_id and update grouping table
        4. If not found: skip record and log as unmatched
        """
        logger.info("Preparing data for database insertion with grouping table lookup...")
        self.emit_progress("Preparing data for database insertion...")
        self.set_progress_stage(*PREFETCH_STAGE)

        prepared_data = []
        current_time = datetime.now()
        rows_to_process = []
        unique_cleaned_values = set()

        for index, row in df.iterrows():
            try:
                original_mlsf_no = str(row['mlsfNo']) if pd.notna(row['mlsfNo']) else None
                if not original_mlsf_no:
                    logger.warning(f"Row {index}: No mlsfNo found, skipping record")
                    continue

                cleaned_mlsf_no = self.clean_mlsf_no_for_matching(original_mlsf_no)
                rows_to_process.append((index, row, original_mlsf_no, cleaned_mlsf_no))
                if cleaned_mlsf_no:
                    unique_cleaned_values.add(cleaned_mlsf_no.strip())

            except Exception as e:
                logger.error(f"Error preprocessing record at index {index}: {str(e)}")
                continue

        total_to_process = len(rows_to_process)
        if total_to_process == 0:
            logger.warning("No valid rows found in Excel file after preprocessing")
            return prepared_data

        if self.cancel_requested:
            raise ImportCancelledError()

        self.prefetch_grouping_lookup(unique_cleaned_values)

        if self.cancel_requested:
            raise ImportCancelledError()

        self.set_progress_stage(*PREPARATION_STAGE)

        progress_interval = max(1, total_to_process // 20)
        processed_count = 0

        try:
            for index, row, original_mlsf_no, cleaned_mlsf_no in rows_to_process:
                try:
                    if self.cancel_requested:
                        raise ImportCancelledError()
                    tracking_id = self.lookup_tracking_id_from_grouping(cleaned_mlsf_no)
                    if tracking_id:
                        logger.debug(f"Row {index}: Found tracking_id: {tracking_id}")
                        self.stage_grouping_update(tracking_id, original_mlsf_no)
                    else:
                        logger.debug(
                            "Row %s: No matching tracking_id found for '%s'",
                            index,
                            cleaned_mlsf_no
                        )
                        self.unmatched_records += 1

                    layout_name = str(row['layoutName']) if pd.notna(row['layoutName']) else ''
                    location = f"{row['lgaName']}, {row['districtName']}"
                    if layout_name:
                        location = f"{layout_name}, {location}"

                    record = {
                        'kangisFileNo': str(row['kangisFileNo']) if pd.notna(row['kangisFileNo']) else None,
                        'mlsfNo': original_mlsf_no,
                        'NewKANGISFileNo': None,
                        'FileName': str(row['currentAllottee']) if pd.notna(row['currentAllottee']) else None,
                        'created_at': current_time,
                        'location': location,
                        'created_by': 'Excel Reimport',
                        'type': 'KANGIS',
                        'is_deleted': 0,
                        'SOURCE': 'KANGIS GIS',
                        'plot_no': str(row['plotNo']) if pd.notna(row['plotNo']) else None,
                        'tp_no': str(row['tpPlanNo']) if pd.notna(row['tpPlanNo']) else None,
                        'tracking_id': tracking_id,
                        'date_migrated': str(current_time),
                        'migrated_by': '1',
                        'migration_source': 'KANGIS GIS',
                        'test_control': self.test_control_value
                    }

                    prepared_data.append(record)
                    if tracking_id:
                        self.matched_records += 1

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
                    continue
        finally:
            if self.grouping_updates:
                self._flush_grouping_updates()

        self.total_records = total_to_process
        logger.info(f"Prepared {len(prepared_data)} records for insertion")
        logger.info(f"Matched records: {self.matched_records}")
        logger.info(f"Unmatched records: {self.unmatched_records}")
        self.emit_progress(
            f"Prepared {len(prepared_data)} records (matched: {self.matched_records}, unmatched: {self.unmatched_records})",
            100.0
        )
        return prepared_data
    
    def verify_table_exists(self):
        """Verify the fileNumber table exists and has required columns."""
        try:
            conn = self.db_connection.get_connection()
            cursor = conn.cursor()
            if hasattr(cursor, "fast_executemany"):
                cursor.fast_executemany = True
            
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'fileNumber'
            """)
            table_exists = cursor.fetchone()[0] > 0
            
            if not table_exists:
                logger.error("fileNumber table does not exist!")
                return False
            
            logger.info("fileNumber table verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying table: {str(e)}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    def insert_batch(self, batch_data):
        """Insert a batch of records into the database with test_control field."""
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
            cursor = conn.cursor()
            
            # Prepare batch values
            batch_values = []
            for record in batch_data:
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
                batch_values.append(values)
            
            cursor.executemany(insert_sql, batch_values)
            conn.commit()
            
            return len(batch_values)
            
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
    
    def validate_import(self):
        """Validate the imported data with test_control filtering."""
        if self.test_control_value is None:
            control_filter = "[test_control] IS NULL"
            control_params = ()
        else:
            control_filter = "[test_control] = ?"
            control_params = (self.test_control_value,)

        validation_queries = [
            ("Total records in table", "SELECT COUNT(*) FROM [dbo].[fileNumber]", ()),
            (
                "Tagged records in fileNumber",
                f"SELECT COUNT(*) FROM [dbo].[fileNumber] WHERE {control_filter}",
                control_params
            ),
            (
                "Tagged records with tracking IDs",
                f"SELECT COUNT(*) FROM [dbo].[fileNumber] WHERE [tracking_id] IS NOT NULL AND {control_filter}",
                control_params
            ),
            (
                "Tagged records from KANGIS GIS source",
                f"SELECT COUNT(*) FROM [dbo].[fileNumber] WHERE [SOURCE] = 'KANGIS GIS' AND {control_filter}",
                control_params
            ),
            (
                "Sample tagged records",
                f"SELECT TOP 5 [tracking_id], [mlsfNo], [FileName], [location] FROM [dbo].[fileNumber] WHERE {control_filter} ORDER BY [id] DESC",
                control_params
            ),
            (
                "Grouping table mappings",
                f"SELECT COUNT(*) FROM [dbo].[grouping] WHERE [mapping] = 1 AND {control_filter}",
                control_params
            ),
            (
                "Sample grouping mappings",
                f"SELECT TOP 5 [tracking_id], [awaiting_fileno], [mls_fileno] FROM [dbo].[grouping] WHERE {control_filter} ORDER BY [id] DESC",
                control_params
            )
        ]
        
        try:
            conn = self.db_connection.get_connection()
            cursor = conn.cursor()
            
            logger.info("\n" + "="*60)
            logger.info("REIMPORT VALIDATION RESULTS")
            logger.info("="*60)
            
            for description, query, params in validation_queries:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                if "Sample" in description:
                    results = cursor.fetchall()
                    logger.info(f"\n{description}:")
                    for row in results:
                        if len(row) == 4:  # fileNumber table samples
                            logger.info(f"  {row[0]} - {row[1]} - {row[2]}")
                            logger.info(f"    Location: {row[3]}")
                        else:  # grouping table samples
                            logger.info(f"  {row[0]} - Awaiting: {row[1]} -> MLS: {row[2]}")
                else:
                    result = cursor.fetchone()[0]
                    logger.info(f"{description}: {result:,}")
            
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    def cleanup_test_records(self):
        """Delete all test records from both tables."""
        try:
            conn = self.db_connection.get_connection()
            cursor = conn.cursor()
            
            if self.test_control_value is None:
                cursor.execute("DELETE FROM [dbo].[fileNumber] WHERE [test_control] IS NULL")
                fileno_deleted = cursor.rowcount
                cursor.execute("""
                    UPDATE [dbo].[grouping] 
                    SET mapping = NULL, mls_fileno = NULL, test_control = NULL 
                    WHERE [test_control] IS NULL
                """)
                grouping_updated = cursor.rowcount
            else:
                cursor.execute(
                    "DELETE FROM [dbo].[fileNumber] WHERE [test_control] = ?",
                    (self.test_control_value,)
                )
                fileno_deleted = cursor.rowcount
                cursor.execute("""
                    UPDATE [dbo].[grouping] 
                    SET mapping = NULL, mls_fileno = NULL, test_control = NULL 
                    WHERE [test_control] = ?
                """, (self.test_control_value,))
                grouping_updated = cursor.rowcount
            
            conn.commit()
            
            logger.info(f"Cleanup completed:")
            logger.info(f"  - Deleted {fileno_deleted} records from fileNumber table")
            logger.info(f"  - Reset {grouping_updated} records in grouping table")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    def run_import(self):
        """Run the complete import process."""
        logger.info("Starting Excel import process...")
        self.emit_progress("Starting Excel import process...")
        self.set_progress_stage(*READ_STAGE)
        
        try:
            # Step 1: Test database connection
            if not self.db_connection.test_connection():
                logger.error("Database connection failed. Aborting import.")
                return False
            
            # Step 2: Verify table exists
            if not self.verify_table_exists():
                logger.error("Failed to verify table. Aborting import.")
                return False
            
            # Step 3: Read Excel file
            df = self.read_excel_file()
            if df is None:
                logger.error("Failed to read Excel file. Aborting import.")
                return False
            
            self.total_records = len(df)
            logger.info(f"Total records to import: {self.total_records:,}")
            self.emit_progress(f"Total records to import: {self.total_records:,}")
            
            # Step 4: Prepare data
            self.set_progress_stage(*PREFETCH_STAGE)
            prepared_data = self.prepare_data_for_insertion(df)
            if not prepared_data:
                logger.error("No data prepared for insertion. Aborting import.")
                return False
            
            # Step 5: Process in batches
            logger.info(f"Processing in batches of {self.batch_size}...")
            self.emit_progress(f"Processing in batches of {self.batch_size}...")
            self.set_progress_stage(*INSERT_STAGE)
            
            for i in range(0, len(prepared_data), self.batch_size):
                if self.cancel_requested:
                    raise ImportCancelledError()
                batch = prepared_data[i:i + self.batch_size]
                batch_number = (i // self.batch_size) + 1
                total_batches = (len(prepared_data) + self.batch_size - 1) // self.batch_size
                
                logger.info(f"Processing batch {batch_number}/{total_batches} ({len(batch)} records)...")
                self.emit_progress(
                    f"Processing batch {batch_number}/{total_batches} ({len(batch)} records)..."
                )
                
                try:
                    inserted_count = self.insert_batch(batch)
                    self.processed_records += inserted_count
                    
                    progress_percent = (self.processed_records / self.total_records) * 100
                    logger.info(f"Progress: {self.processed_records:,}/{self.total_records:,} ({progress_percent:.1f}%)")
                    self.emit_progress(
                        f"Inserted records: {self.processed_records:,}/{self.total_records:,} ({progress_percent:.1f}%)",
                        progress_percent
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to insert batch {batch_number}: {str(e)}")
                    return False
            
            # Step 6: Validate results
            logger.info("Import completed successfully! Running validation...")
            self.emit_progress("Running validation...")
            self.set_progress_stage(*VALIDATION_STAGE)
            self.validate_import()
            
            logger.info("Excel import process completed successfully!")
            self.emit_progress("Excel import process completed successfully!", 100.0)
            return True
            
        except ImportCancelledError:
            logger.info("Import cancelled by user.")
            self.emit_progress("Import cancelled by user.")
            return False
        except Exception as e:
            logger.error(f"Import process failed: {str(e)}")
            return False

def main():
    """Main function to run the reimport."""
    importer = ExcelImporter()
    importer.set_progress_callback(lambda message, progress=None: print(message))
    file_name = importer.excel_file_path.name
    row_limit_label = (
        str(importer.max_rows)
        if importer.max_rows is not None
        else "ALL"
    )
    test_control_label = importer.test_control_value or "None"
    is_production = (importer.test_control_value or "").upper() == "PROD"
    run_label = "production import" if is_production else "reimport test"
    run_option_text = "Run production import" if is_production else "Run reimport test"
    cleanup_option_text = "Cleanup production-tagged records" if is_production else "Cleanup test records"

    print("="*70)
    print(f"🚀 EXCEL REIMPORTER - {file_name}")
    print("="*70)
    
    # Show current configuration
    print(f"📁 Excel file: {importer.excel_file_path}")
    print("🎯 Target tables: fileNumber, grouping")
    print(f"📊 Row limit: {row_limit_label}")
    print(f"🏷️  Test control: {test_control_label}")
    print("\nREIMPORT LOGIC:")
    print(f"1. Read {'first ' + row_limit_label if row_limit_label != 'ALL' else 'all'} records from Excel")
    print("2. Clean mlsfNo (remove 'AND EXTENSION' and '(TEMP)')")
    print("3. Lookup tracking_id from grouping table")
    print("4. Update grouping table with mapping info")
    print("5. Insert into fileNumber table with existing tracking_id")
    
    # Ask what to do
    print("\nOptions:")
    print(f"1. {run_option_text}")
    print(f"2. {cleanup_option_text}")
    print("3. Cancel")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == '1':
        response = input(f"\nProceed with {run_label}? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Reimport cancelled by user.")
            return
            
        success = importer.run_import()
        
        if success:
            print(f"\n🎉 {run_label.capitalize()} completed successfully!")
            print(f"Matched records: {importer.matched_records}")
            print(f"Unmatched records: {importer.unmatched_records}")
        else:
            print(f"\n❌ {run_label.capitalize()} failed. Check the logs for details.")
            sys.exit(1)
            
    elif choice == '2':
        response = input(f"\nThis will delete ALL {run_label.split()[0]} records. Proceed? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Cleanup cancelled by user.")
            return
            
        success = importer.cleanup_test_records()
        if success:
            print("\n🧹 Tagged records cleanup completed!")
        else:
            print("\n❌ Cleanup failed. Check the logs for details.")
            
    else:
        print("Operation cancelled.")
        return

if __name__ == "__main__":
    main()