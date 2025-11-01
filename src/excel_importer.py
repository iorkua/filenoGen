#!/usr/bin/env python3
"""
Excel File Importer for FileNos_Updated.xlsx
Imports data from Excel file into the fileNumber table with proper field mapping.
"""

import pandas as pd
import random
import string
from datetime import datetime
import logging
from pathlib import Path
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

class ExcelImporter:
    def __init__(self):
        """Initialize the Excel importer."""
        self.db_connection = DatabaseConnection()
        self.excel_file_path = Path(__file__).parent.parent / "FileNos_Updated.xlsx"
        self.batch_size = 1000
        self.total_records = 0
        self.processed_records = 0
        
    def generate_tracking_id(self):
        """
        Generate a unique tracking ID in format: TRK-B9010697-C2474
        Pattern: TRK-[B + 7 digits]-[C + 4 digits]
        """
        # Generate 7 random digits for first part
        first_part = ''.join(random.choices(string.digits, k=7))
        # Generate 4 random digits for second part  
        second_part = ''.join(random.choices(string.digits, k=4))
        
        tracking_id = f"TRK-B{first_part}-C{second_part}"
        return tracking_id
    
    def read_excel_file(self):
        """Read and validate the Excel file."""
        try:
            logger.info(f"Reading Excel file: {self.excel_file_path}")
            
            if not self.excel_file_path.exists():
                raise FileNotFoundError(f"Excel file not found: {self.excel_file_path}")
            
            # Read Excel file
            df = pd.read_excel(self.excel_file_path)
            
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
            
            logger.info(f"Successfully read Excel file with {len(df)} records")
            logger.info(f"Columns: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error reading Excel file: {str(e)}")
            return None
    
    def prepare_data_for_insertion(self, df):
        """
        Prepare DataFrame for database insertion with proper field mapping.
        
        Excel Columns -> Database Columns:
        - mlsfNo -> mlsfNo
        - kangisFileNo -> kangisFileNo  
        - plotNo -> plot_no
        - tpPlanNo -> tp_no
        - currentAllottee -> FileName
        - layoutName -> layoutName
        - districtName, lgaName -> location (combined)
        - Generated tracking_id -> tracking_id
        """
        logger.info("Preparing data for database insertion...")
        
        prepared_data = []
        current_time = datetime.now()
        
        for index, row in df.iterrows():
            try:
                # Combine location info including layout name
                layout_name = str(row['layoutName']) if pd.notna(row['layoutName']) else ''
                location = f"{row['lgaName']}, {row['districtName']}"
                if layout_name:
                    location = f"{layout_name}, {location}"
                
                # Generate unique tracking ID
                tracking_id = self.generate_tracking_id()
                
                record = {
                    'kangisFileNo': str(row['kangisFileNo']) if pd.notna(row['kangisFileNo']) else None,
                    'mlsfNo': str(row['mlsfNo']) if pd.notna(row['mlsfNo']) else None,
                    'NewKANGISFileNo': None,  # Not provided in Excel
                    'FileName': str(row['currentAllottee']) if pd.notna(row['currentAllottee']) else None,
                    'created_at': current_time,
                    'location': location,
                    'created_by': 'Excel Import',
                    'type': 'KANGIS',  # Set type to indicate source
                    'is_deleted': 0,  # Default to not deleted
                    'SOURCE': 'KANGIS GIS',
                    'plot_no': str(row['plotNo']) if pd.notna(row['plotNo']) else None,
                    'tp_no': str(row['tpPlanNo']) if pd.notna(row['tpPlanNo']) else None,
                    'tracking_id': tracking_id,
                    'date_migrated': str(current_time),
                    'migrated_by': '1',
                    'migration_source': 'KANGIS GIS'
                }
                
                prepared_data.append(record)
                
            except Exception as e:
                logger.error(f"Error preparing record at index {index}: {str(e)}")
                continue
        
        logger.info(f"Prepared {len(prepared_data)} records for insertion")
        return prepared_data
    
    def verify_table_exists(self):
        """Verify the fileNumber table exists and has required columns."""
        try:
            conn = self.db_connection.get_connection()
            cursor = conn.cursor()
            
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
        """Insert a batch of records into the database."""
        insert_sql = """
        INSERT INTO [dbo].[fileNumber] (
            [kangisFileNo], [mlsfNo], [NewKANGISFileNo], [FileName], [created_at],
            [location], [created_by], [type], [is_deleted],
            [SOURCE], [plot_no], [tp_no], [tracking_id], [date_migrated],
            [migrated_by], [migration_source]
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    record['migration_source']
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
        """Validate the imported data."""
        validation_queries = [
            ("Total records in table", "SELECT COUNT(*) FROM [dbo].[fileNumber]"),
            ("Records from Excel Import", "SELECT COUNT(*) FROM [dbo].[fileNumber] WHERE [created_by] = 'Excel Import'"),
            ("Records with tracking IDs", "SELECT COUNT(*) FROM [dbo].[fileNumber] WHERE [tracking_id] IS NOT NULL AND [created_by] = 'Excel Import'"),
            ("Records from KANGIS GIS source", "SELECT COUNT(*) FROM [dbo].[fileNumber] WHERE [SOURCE] = 'KANGIS GIS' AND [created_by] = 'Excel Import'"),
            ("Sample tracking IDs", "SELECT TOP 5 [tracking_id], [FileName], [location] FROM [dbo].[fileNumber] WHERE [created_by] = 'Excel Import' ORDER BY [id] DESC")
        ]
        
        try:
            conn = self.db_connection.get_connection()
            cursor = conn.cursor()
            
            logger.info("\n" + "="*60)
            logger.info("IMPORT VALIDATION RESULTS")
            logger.info("="*60)
            
            for description, query in validation_queries:
                cursor.execute(query)
                if "Sample" in description:
                    results = cursor.fetchall()
                    logger.info(f"\n{description}:")
                    for row in results:
                        logger.info(f"  {row[0]} - {row[1]}")
                        logger.info(f"    Location: {row[2]}")
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
    
    def run_import(self):
        """Run the complete import process."""
        logger.info("Starting Excel import process...")
        
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
            
            # Step 4: Prepare data
            prepared_data = self.prepare_data_for_insertion(df)
            if not prepared_data:
                logger.error("No data prepared for insertion. Aborting import.")
                return False
            
            # Step 5: Process in batches
            logger.info(f"Processing in batches of {self.batch_size}...")
            
            for i in range(0, len(prepared_data), self.batch_size):
                batch = prepared_data[i:i + self.batch_size]
                batch_number = (i // self.batch_size) + 1
                total_batches = (len(prepared_data) + self.batch_size - 1) // self.batch_size
                
                logger.info(f"Processing batch {batch_number}/{total_batches} ({len(batch)} records)...")
                
                try:
                    inserted_count = self.insert_batch(batch)
                    self.processed_records += inserted_count
                    
                    progress_percent = (self.processed_records / self.total_records) * 100
                    logger.info(f"Progress: {self.processed_records:,}/{self.total_records:,} ({progress_percent:.1f}%)")
                    
                except Exception as e:
                    logger.error(f"Failed to insert batch {batch_number}: {str(e)}")
                    return False
            
            # Step 6: Validate results
            logger.info("Import completed successfully! Running validation...")
            self.validate_import()
            
            logger.info("Excel import process completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Import process failed: {str(e)}")
            return False

def main():
    """Main function to run the import."""
    print("="*70)
    print("🚀 EXCEL FILE IMPORTER - FileNos_Updated.xlsx")
    print("="*70)
    
    importer = ExcelImporter()
    
    # Confirm before proceeding
    print(f"📁 Excel file: {importer.excel_file_path}")
    print(f"🎯 Target table: fileNumber")
    print(f"📊 Batch size: {importer.batch_size}")
    print("\nThis will import all records from the Excel file into the database.")
    
    response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Import cancelled by user.")
        return
    
    success = importer.run_import()
    
    if success:
        print("\n🎉 Import completed successfully!")
    else:
        print("\n❌ Import failed. Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()