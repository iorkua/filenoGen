"""
Production File Number Insertion Script
Generates and inserts all 5.4M file numbers with real-time progress tracking
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

from database_connection import DatabaseConnection
from file_number_generator import FileNumberGenerator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ProductionInserter:
    """Production-grade file number insertion with progress tracking"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.generator = FileNumberGenerator()
        
        # Configuration
        self.batch_size = int(os.getenv('BATCH_SIZE', 1000))
        self.transaction_size = int(os.getenv('TRANSACTION_SIZE', 10000))
        self.records_per_group = int(os.getenv('RECORDS_PER_GROUP', 100))
        
        # Progress tracking
        self.start_time = None
        self.total_records = 0
        self.processed_records = 0
        self.current_category = ""
        self.categories_completed = 0
        self.total_categories = len(self.generator.categories)
        
        # Performance metrics
        self.records_per_second = 0
        self.estimated_time_remaining = timedelta(0)
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Threading for progress display
        self.progress_thread = None
        self.stop_progress = False
        
    def setup_logging(self):
        """Setup detailed logging"""
        os.makedirs('logs', exist_ok=True)
        log_filename = f"logs/production_insertion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def calculate_total_records(self) -> int:
        """Calculate total records to be generated"""
        years = self.generator.end_year - self.generator.start_year + 1
        numbers_per_year = self.generator.numbers_per_year
        categories = len(self.generator.categories)
        return years * numbers_per_year * categories
    
    def display_progress(self):
        """Display real-time progress in a separate thread"""
        while not self.stop_progress:
            if self.start_time and self.processed_records > 0:
                # Calculate progress
                progress_percent = (self.processed_records / self.total_records) * 100
                elapsed_time = datetime.now() - self.start_time
                
                # Calculate rate and ETA
                if elapsed_time.total_seconds() > 0:
                    self.records_per_second = self.processed_records / elapsed_time.total_seconds()
                    if self.records_per_second > 0:
                        remaining_records = self.total_records - self.processed_records
                        eta_seconds = remaining_records / self.records_per_second
                        self.estimated_time_remaining = timedelta(seconds=eta_seconds)
                
                # Create progress bar
                bar_width = 50
                filled_width = int(bar_width * progress_percent / 100)
                progress_bar = "█" * filled_width + "░" * (bar_width - filled_width)
                
                # Display progress
                print(f"\r🚀 Progress: {progress_bar} {progress_percent:.1f}% " +
                      f"({self.processed_records:,}/{self.total_records:,}) " +
                      f"| {self.records_per_second:.0f} rec/sec " +
                      f"| ETA: {str(self.estimated_time_remaining).split('.')[0]} " +
                      f"| Category: {self.current_category} " +
                      f"({self.categories_completed}/{self.total_categories})", end="", flush=True)
            
            time.sleep(1)  # Update every second
    
    def start_progress_display(self):
        """Start the progress display thread"""
        self.stop_progress = False
        self.progress_thread = threading.Thread(target=self.display_progress, daemon=True)
        self.progress_thread.start()
    
    def stop_progress_display(self):
        """Stop the progress display thread"""
        self.stop_progress = True
        if self.progress_thread:
            self.progress_thread.join(timeout=2)
        print()  # New line after progress bar
    
    def clear_existing_data(self, connection) -> int:
        """Clear any existing generated data"""
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM [dbo].[grouping] WHERE [created_by] = 'Generated'")
            deleted_count = cursor.rowcount
            connection.commit()
            cursor.close()
            
            self.logger.info(f"Cleared {deleted_count} existing records")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error clearing existing data: {e}")
            connection.rollback()
            return 0
    
    def insert_batch(self, connection, records: List[Dict[str, Any]]) -> bool:
        """Insert a batch of records"""
        try:
            cursor = connection.cursor()
            
            # Prepare batch data
            batch_data = []
            for record in records:
                batch_data.append((
                    record['awaiting_fileno'],
                    record['created_by'],
                    record['number'],
                    record['year'],
                    record['landuse'],
                    record['created_at'],
                    record['registry'],
                    record['mls_fileno'],
                    record['mapping'],
                    record['group'],
                    record['sys_batch_no']
                ))
            
            # Execute batch insert
            insert_sql = """
                INSERT INTO [dbo].[grouping] 
                ([awaiting_fileno], [created_by], [number], [year], [landuse], 
                 [created_at], [registry], [mls_fileno], [mapping], [group], [sys_batch_no])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.executemany(insert_sql, batch_data)
            cursor.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error inserting batch: {e}")
            return False
    
    def process_category(self, connection, category: str) -> bool:
        """Process a single category with batch processing"""
        self.current_category = category
        self.logger.info(f"Starting category: {category}")
        
        try:
            batch_records = []
            transaction_records = 0
            
            # Generate records for this category
            for record in self.generator.generate_file_numbers([category]):
                batch_records.append(record)
                
                # Process batch when it reaches batch_size
                if len(batch_records) >= self.batch_size:
                    if not self.insert_batch(connection, batch_records):
                        return False
                    
                    self.processed_records += len(batch_records)
                    transaction_records += len(batch_records)
                    batch_records = []
                    
                    # Commit transaction when it reaches transaction_size
                    if transaction_records >= self.transaction_size:
                        connection.commit()
                        transaction_records = 0
            
            # Process remaining records in final batch
            if batch_records:
                if not self.insert_batch(connection, batch_records):
                    return False
                self.processed_records += len(batch_records)
            
            # Final commit for this category
            connection.commit()
            self.categories_completed += 1
            
            self.logger.info(f"Completed category: {category}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing category {category}: {e}")
            connection.rollback()
            return False
    
    def run_production_insertion(self) -> bool:
        """Run the complete production insertion"""
        print("🚀 PRODUCTION FILE NUMBER INSERTION")
        print("=" * 60)
        
        # Calculate totals
        self.total_records = self.calculate_total_records()
        
        print(f"📊 INSERTION PLAN:")
        print(f"   • Total Records: {self.total_records:,}")
        print(f"   • Categories: {self.total_categories}")
        print(f"   • Years: {self.generator.start_year}-{self.generator.end_year}")
        print(f"   • Numbers per Year: {self.generator.numbers_per_year:,}")
        print(f"   • Batch Size: {self.batch_size:,}")
        print(f"   • Transaction Size: {self.transaction_size:,}")
        print("=" * 60)
        
        # Test database connection
        print("🔗 Testing database connection...")
        test_results = self.db.test_connection()
        if not test_results['preferred']:
            print("❌ Database connection failed")
            return False
        
        connection = self.db.get_connection(test_results['preferred'])
        if not connection:
            print("❌ Could not establish database connection")
            return False
        
        print(f"✅ Connected using {test_results['preferred'].upper()}")
        
        try:
            # Clear existing data
            print("\n🧹 Clearing existing test data...")
            cleared_count = self.clear_existing_data(connection)
            print(f"✅ Cleared {cleared_count} existing records")
            
            # Start timing and progress tracking
            self.start_time = datetime.now()
            print(f"\n⏰ Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Start progress display
            self.start_progress_display()
            
            # Process each category
            success = True
            for category in self.generator.categories:
                if not self.process_category(connection, category):
                    success = False
                    break
            
            # Stop progress display
            self.stop_progress_display()
            
            if success:
                # Calculate final statistics
                end_time = datetime.now()
                total_duration = end_time - self.start_time
                
                print("\n" + "=" * 60)
                print("🎉 INSERTION COMPLETED SUCCESSFULLY!")
                print("=" * 60)
                print(f"📊 FINAL STATISTICS:")
                print(f"   • Total Records Inserted: {self.processed_records:,}")
                print(f"   • Categories Completed: {self.categories_completed}/{self.total_categories}")
                print(f"   • Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   • End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   • Total Duration: {str(total_duration).split('.')[0]}")
                print(f"   • Average Rate: {self.processed_records/total_duration.total_seconds():.0f} records/second")
                print("=" * 60)
                
                self.logger.info("Production insertion completed successfully")
                return True
            else:
                print("\n❌ INSERTION FAILED!")
                self.logger.error("Production insertion failed")
                return False
                
        except Exception as e:
            self.stop_progress_display()
            print(f"\n❌ Critical error: {e}")
            self.logger.error(f"Critical error in production insertion: {e}")
            return False
        finally:
            connection.close()
    
    def validate_final_results(self) -> Dict[str, Any]:
        """Validate the final insertion results"""
        print("\n🔍 VALIDATING FINAL RESULTS...")
        
        connection = self.db.get_connection('pyodbc')
        if not connection:
            return {'error': 'Could not connect to database for validation'}
        
        try:
            cursor = connection.cursor()
            results = {}
            
            # Total count
            cursor.execute("SELECT COUNT(*) FROM [dbo].[grouping] WHERE [created_by] = 'Generated'")
            results['total_count'] = cursor.fetchone()[0]
            
            # Registry distribution
            cursor.execute("""
                SELECT [registry], COUNT(*) 
                FROM [dbo].[grouping] 
                WHERE [created_by] = 'Generated'
                GROUP BY [registry]
                ORDER BY [registry]
            """)
            results['registry_distribution'] = dict(cursor.fetchall())
            
            # Land use distribution
            cursor.execute("""
                SELECT [landuse], COUNT(*) 
                FROM [dbo].[grouping] 
                WHERE [created_by] = 'Generated'
                GROUP BY [landuse]
                ORDER BY [landuse]
            """)
            results['landuse_distribution'] = dict(cursor.fetchall())
            
            # Year range
            cursor.execute("""
                SELECT MIN([year]), MAX([year]) 
                FROM [dbo].[grouping] 
                WHERE [created_by] = 'Generated'
            """)
            year_range = cursor.fetchone()
            results['year_range'] = {'min': year_range[0], 'max': year_range[1]}
            
            # Group statistics
            cursor.execute("""
                SELECT MIN([group]), MAX([group]), COUNT(DISTINCT [group])
                FROM [dbo].[grouping] 
                WHERE [created_by] = 'Generated'
            """)
            group_info = cursor.fetchone()
            results['group_info'] = {'min': group_info[0], 'max': group_info[1], 'distinct_count': group_info[2]}
            
            cursor.close()
            
            # Display validation results
            print(f"✅ Total Records: {results['total_count']:,}")
            print(f"✅ Year Range: {results['year_range']['min']} - {results['year_range']['max']}")
            print(f"✅ Groups: {results['group_info']['min']} - {results['group_info']['max']} ({results['group_info']['distinct_count']:,} groups)")
            
            print(f"\n📊 Registry Distribution:")
            for registry, count in results['registry_distribution'].items():
                print(f"   • {registry}: {count:,} records")
            
            print(f"\n📊 Land Use Distribution:")
            for landuse, count in results['landuse_distribution'].items():
                print(f"   • {landuse}: {count:,} records")
            
            return results
            
        except Exception as e:
            return {'error': str(e)}
        finally:
            connection.close()


def main():
    """Run the production insertion"""
    inserter = ProductionInserter()
    
    # Confirmation prompt
    print("⚠️  WARNING: This will insert 5.4 MILLION records into the database!")
    print("   This process will take 2-4 hours to complete.")
    print("   Make sure you have:")
    print("   • Database backup completed")
    print("   • Sufficient disk space")
    print("   • Stable network connection")
    print("   • No other processes using the database")
    print()
    
    confirm = input("Do you want to proceed? (type 'YES' to confirm): ").strip()
    
    if confirm.upper() != 'YES':
        print("❌ Insertion cancelled by user")
        return False
    
    # Run the production insertion
    success = inserter.run_production_insertion()
    
    if success:
        # Validate results
        inserter.validate_final_results()
        print("\n🏆 PRODUCTION INSERTION COMPLETED SUCCESSFULLY!")
        return True
    else:
        print("\n💥 PRODUCTION INSERTION FAILED!")
        return False


if __name__ == "__main__":
    main()