"""
Rack Shelf Labels CSV Importer
Imports rack and shelf label data from CSV file into the Rack_Shelf_Labels database table.
"""

import pandas as pd
import logging
from datetime import datetime
from database_connection import DatabaseConnection
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rack_shelf_import.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class RackShelfImporter:
    def __init__(self, csv_file_path):
        """
        Initialize the importer with the CSV file path.
        
        Args:
            csv_file_path (str): Path to the Rack_Shelf_Labels.csv file
        """
        self.csv_file_path = csv_file_path
        self.connection = None
        self.total_records = 0
        self.successful_imports = 0
        
    def validate_csv_file(self):
        """Validate that the CSV file exists and has the expected structure."""
        if not os.path.exists(self.csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {self.csv_file_path}")
        
        # Read a small sample to check structure
        sample_df = pd.read_csv(self.csv_file_path, nrows=5)
        expected_columns = ['Rack', 'Shelf', 'Full Label']
        
        missing_columns = [col for col in expected_columns if col not in sample_df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        logging.info(f"CSV file validation successful. Columns: {list(sample_df.columns)}")
        return True
    
    def load_csv_data(self):
        """Load and prepare data from CSV file."""
        logging.info(f"Loading data from: {self.csv_file_path}")
        
        try:
            # Read the CSV file with proper encoding
            df = pd.read_csv(self.csv_file_path, encoding='utf-8')
            self.total_records = len(df)
            
            logging.info(f"Loaded {self.total_records} records from CSV")
            logging.info(f"Sample data:")
            logging.info(f"{df.head()}")
            
            # Prepare data for database insertion
            prepared_data = self.prepare_data_for_insertion(df)
            return prepared_data
            
        except Exception as e:
            logging.error(f"Error loading CSV data: {str(e)}")
            raise
    
    def prepare_data_for_insertion(self, df):
        """
        Prepare the DataFrame for database insertion by mapping columns 
        and adding required fields.
        """
        logging.info("Preparing data for database insertion...")
        
        # Map CSV columns to database columns
        column_mapping = {
            'Rack': 'rack',
            'Shelf': 'shelf', 
            'Full Label': 'full_label'
        }
        
        # Rename columns to match database schema
        df = df.rename(columns=column_mapping)
        
        # Add default values for additional database columns
        current_time = datetime.now()
        df['is_used'] = False  # Default to not used
        df['reserved_by'] = None  # No reservation initially
        df['reserved_at'] = None  # No reservation time initially
        df['created_at'] = current_time
        df['updated_at'] = current_time
        
        # Clean and validate data
        df['rack'] = df['rack'].astype(str).str.strip()
        df['shelf'] = pd.to_numeric(df['shelf'], errors='coerce')
        df['full_label'] = df['full_label'].astype(str).str.strip()
        
        # Remove any rows with invalid data
        initial_count = len(df)
        df = df.dropna(subset=['rack', 'shelf', 'full_label'])
        final_count = len(df)
        
        if initial_count != final_count:
            logging.warning(f"Removed {initial_count - final_count} rows with invalid data")
        
        logging.info(f"Data preparation complete. {final_count} records ready for insertion")
        
        return df
    
    def check_table_structure(self):
        """Check if the target table exists and has the expected structure."""
        try:
            cursor = self.connection.cursor()
            
            # Check if table exists and get its structure
            query = """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'Rack_Shelf_Labels'
            ORDER BY ORDINAL_POSITION
            """
            
            cursor.execute(query)
            columns = cursor.fetchall()
            
            if not columns:
                raise Exception("Table 'Rack_Shelf_Labels' does not exist")
            
            logging.info("Target table structure:")
            for col in columns:
                logging.info(f"  {col[0]} ({col[1]}) - Nullable: {col[2]}")
            
            cursor.close()
            return True
            
        except Exception as e:
            logging.error(f"Error checking table structure: {str(e)}")
            raise
    
    def insert_data_batch(self, df, batch_size=1000):
        """Insert data into database in batches."""
        try:
            cursor = self.connection.cursor()
            
            # Prepare the INSERT statement
            insert_query = """
            INSERT INTO [dbo].[Rack_Shelf_Labels] 
            ([rack], [shelf], [full_label], [is_used], [reserved_by], [reserved_at], [created_at], [updated_at])
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            total_batches = (len(df) + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min((batch_num + 1) * batch_size, len(df))
                batch_df = df.iloc[start_idx:end_idx]
                
                # Prepare batch data for insertion
                batch_data = []
                for _, row in batch_df.iterrows():
                    batch_data.append((
                        row['rack'],
                        int(row['shelf']),
                        row['full_label'],
                        row['is_used'],
                        row['reserved_by'],
                        row['reserved_at'],
                        row['created_at'],
                        row['updated_at']
                    ))
                
                # Execute batch insert
                cursor.executemany(insert_query, batch_data)
                self.connection.commit()
                
                self.successful_imports += len(batch_data)
                logging.info(f"Batch {batch_num + 1}/{total_batches} completed: {len(batch_data)} records inserted")
            
            cursor.close()
            logging.info(f"Data insertion completed successfully!")
            
        except Exception as e:
            logging.error(f"Error during data insertion: {str(e)}")
            self.connection.rollback()
            raise
    
    def generate_summary_report(self):
        """Generate a summary report of the import process."""
        logging.info("=" * 60)
        logging.info("RACK SHELF LABELS IMPORT SUMMARY")
        logging.info("=" * 60)
        logging.info(f"CSV File: {self.csv_file_path}")
        logging.info(f"Total records in CSV: {self.total_records}")
        logging.info(f"Successfully imported: {self.successful_imports}")
        logging.info(f"Import success rate: {(self.successful_imports/self.total_records)*100:.1f}%")
        logging.info(f"Import completed at: {datetime.now()}")
        logging.info("=" * 60)
    
    def run_import(self):
        """Execute the complete import process."""
        try:
            logging.info("Starting Rack Shelf Labels import process...")
            
            # Step 1: Validate CSV file
            self.validate_csv_file()
            
            # Step 2: Establish database connection
            logging.info("Connecting to database...")
            db_helper = DatabaseConnection()
            self.connection = db_helper.get_connection('pyodbc')
            
            # Step 3: Check table structure
            self.check_table_structure()
            
            # Step 4: Load and prepare data
            prepared_data = self.load_csv_data()
            
            # Step 5: Insert data in batches
            logging.info("Starting data insertion...")
            self.insert_data_batch(prepared_data)
            
            # Step 6: Generate summary report
            self.generate_summary_report()
            
            return True
            
        except Exception as e:
            logging.error(f"Import process failed: {str(e)}")
            return False
        
        finally:
            if self.connection:
                self.connection.close()
                logging.info("Database connection closed")

def main():
    """Main function to run the import process."""
    # Define the CSV file path
    csv_file_path = r"c:\Users\Administrator\Documents\filenoGen\Rack_Shelf_Labels.csv"
    
    # Create and run the importer
    importer = RackShelfImporter(csv_file_path)
    success = importer.run_import()
    
    if success:
        print("\n✅ Rack Shelf Labels import completed successfully!")
        print(f"📊 Imported {importer.successful_imports} records")
    else:
        print("\n❌ Import process failed. Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()