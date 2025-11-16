"""
Database Insertion Test
Test script to insert a small sample of file numbers into the database
"""

import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from dotenv import load_dotenv

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

from database_connection import DatabaseConnection
from file_number_generator import FileNumberGenerator

# Load environment variables
load_dotenv()

class DatabaseInserter:
    """Handle database insertion operations"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.generator = FileNumberGenerator()
        self.batch_size = int(os.getenv('BATCH_SIZE', 1000))
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def clear_test_data(self, connection) -> int:
        """
        Clear any existing test data (created_by = 'Generated')
        Args:
            connection: Database connection
        Returns:
            Number of records deleted
        """
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM [dbo].[grouping] WHERE [created_by] = 'Generated'")
            deleted_count = cursor.rowcount
            connection.commit()
            cursor.close()
            
            self.logger.info(f"Cleared {deleted_count} existing test records")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error clearing test data: {e}")
            connection.rollback()
            return 0
    
    def insert_records(self, connection, records: List[Dict[str, Any]]) -> bool:
        """
        Insert records into the database
        Args:
            connection: Database connection
            records: List of record dictionaries
        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = connection.cursor()
            
            # Prepare the INSERT statement
            insert_sql = """
                INSERT INTO [dbo].[grouping] 
                ([awaiting_fileno], [created_by], [number], [year], [landuse], 
                 [created_at], [registry], [mls_fileno], [mapping], [group], [sys_batch_no], [registry_batch_no], [tracking_id])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            # Prepare data for batch insert
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
                    record['sys_batch_no'],
                    record['registry_batch_no'],
                    record['tracking_id']
                ))
            
            # Execute batch insert
            cursor.executemany(insert_sql, batch_data)
            connection.commit()
            
            inserted_count = len(batch_data)
            self.logger.info(f"Successfully inserted {inserted_count} records")
            cursor.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error inserting records: {e}")
            connection.rollback()
            return False
    
    def validate_inserted_data(self, connection, expected_count: int) -> Dict[str, Any]:
        """
        Validate the inserted data
        Args:
            connection: Database connection
            expected_count: Expected number of records
        Returns:
            Validation results dictionary
        """
        try:
            cursor = connection.cursor()
            results = {}
            
            # Check total count
            cursor.execute("SELECT COUNT(*) FROM [dbo].[grouping] WHERE [created_by] = 'Generated'")
            actual_count = cursor.fetchone()[0]
            results['total_count'] = {'expected': expected_count, 'actual': actual_count, 'match': actual_count == expected_count}
            
            # Check registry distribution
            cursor.execute("""
                SELECT [registry], COUNT(*) 
                FROM [dbo].[grouping] 
                WHERE [created_by] = 'Generated'
                GROUP BY [registry]
                ORDER BY [registry]
            """)
            registry_counts = dict(cursor.fetchall())
            results['registry_distribution'] = registry_counts
            
            # Check land use distribution
            cursor.execute("""
                SELECT [landuse], COUNT(*) 
                FROM [dbo].[grouping] 
                WHERE [created_by] = 'Generated'
                GROUP BY [landuse]
                ORDER BY [landuse]
            """)
            landuse_counts = dict(cursor.fetchall())
            results['landuse_distribution'] = landuse_counts
            
            # Check year range
            cursor.execute("""
                SELECT MIN([year]), MAX([year]) 
                FROM [dbo].[grouping] 
                WHERE [created_by] = 'Generated'
            """)
            year_range = cursor.fetchone()
            results['year_range'] = {'min': year_range[0], 'max': year_range[1]}
            
            # Check group range
            cursor.execute("""
                SELECT MIN([group]), MAX([group]), COUNT(DISTINCT [group])
                FROM [dbo].[grouping] 
                WHERE [created_by] = 'Generated'
            """)
            group_info = cursor.fetchone()
            results['group_info'] = {'min': group_info[0], 'max': group_info[1], 'distinct_count': group_info[2]}
            
            # Check CON registry assignments
            cursor.execute("""
                SELECT COUNT(*) 
                FROM [dbo].[grouping] 
                WHERE [created_by] = 'Generated' 
                AND [awaiting_fileno] LIKE '%CON%' 
                AND [registry] = '3'
            """)
            con_registry3_count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) 
                FROM [dbo].[grouping] 
                WHERE [created_by] = 'Generated' 
                AND [awaiting_fileno] LIKE '%CON%'
            """)
            total_con_count = cursor.fetchone()[0]
            
            results['con_registry_check'] = {
                'total_con': total_con_count,
                'registry3_con': con_registry3_count,
                'all_con_in_registry3': con_registry3_count == total_con_count
            }
            
            # Sample records
            cursor.execute("""
                SELECT TOP 5 [awaiting_fileno], [registry], [group], [registry_batch_no], [landuse], [year]
                FROM [dbo].[grouping] 
                WHERE [created_by] = 'Generated'
                ORDER BY [number]
            """)
            sample_records = cursor.fetchall()
            results['sample_records'] = sample_records
            
            cursor.close()
            return results
            
        except Exception as e:
            self.logger.error(f"Error validating data: {e}")
            return {'error': str(e)}
    
    def run_test(self, records_per_category: int = 5, categories: Optional[List[str]] = None) -> bool:
        """
        Run the complete test: generate, insert, and validate
        Args:
            records_per_category: Number of records per category to test
            categories: Optional subset of categories to include
        Returns:
            True if test passed, False otherwise
        """
        active_categories = categories or self.generator.categories
        missing_categories = [cat for cat in active_categories if cat not in self.generator.categories]
        if missing_categories:
            print(f"❌ Unknown categories requested: {', '.join(missing_categories)}")
            return False
        total_expected = records_per_category * len(active_categories)

        print("Starting Database Insertion Test")
        print(f"Records per category: {records_per_category}")
        print(f"Categories: {', '.join(active_categories)}")
        print(f"Total expected records: {total_expected}")
        print("=" * 60)
        
        # Get database connection
        test_results = self.db.test_connection()
        if not test_results['preferred']:
            print("❌ Database connection failed")
            return False
        
        connection = self.db.get_connection(test_results['preferred'])
        if not connection:
            print("❌ Could not establish database connection")
            return False
        
        try:
            # Step 1: Clear existing test data
            print("Step 1: Clearing existing test data...")
            cleared_count = self.clear_test_data(connection)
            print(f"✅ Cleared {cleared_count} existing records")
            
            # Step 2: Generate test data
            print(f"\nStep 2: Generating {records_per_category} records per category...")
            test_records = self.generator.generate_sample_data(records_per_category, categories=active_categories)
            print(f"✅ Generated {len(test_records)} records")
            
            # Step 3: Insert data
            print(f"\nStep 3: Inserting records into database...")
            insert_success = self.insert_records(connection, test_records)
            if not insert_success:
                print("❌ Data insertion failed")
                return False
            print(f"✅ Inserted {len(test_records)} records")
            
            # Step 4: Validate data
            print(f"\nStep 4: Validating inserted data...")
            validation_results = self.validate_inserted_data(connection, len(test_records))
            
            if 'error' in validation_results:
                print(f"❌ Validation error: {validation_results['error']}")
                return False
                
            # Print validation results
            print(f"\n📊 Validation Results:")
            print(f"Total Records: {validation_results['total_count']['actual']} (Expected: {validation_results['total_count']['expected']}) {'✅' if validation_results['total_count']['match'] else '❌'}")
            
            print(f"\nRegistry Distribution:")
            for registry, count in validation_results['registry_distribution'].items():
                print(f"  {registry}: {count} records")
            
            print(f"\nLand Use Distribution:")
            for landuse, count in validation_results['landuse_distribution'].items():
                print(f"  {landuse}: {count} records")
            
            print(f"\nYear Range: {validation_results['year_range']['min']} - {validation_results['year_range']['max']}")
            print(f"Groups: {validation_results['group_info']['min']} - {validation_results['group_info']['max']} ({validation_results['group_info']['distinct_count']} distinct)")
            
            print(f"\nCON Registry Check:")
            con_check = validation_results['con_registry_check']
            print(f"  Total CON records: {con_check['total_con']}")
            print(f"  CON in Registry 3: {con_check['registry3_con']}")
            print(f"  All CON correctly assigned: {'✅' if con_check['all_con_in_registry3'] else '❌'}")
            
            print(f"\nSample Records:")
            for i, record in enumerate(validation_results['sample_records'], 1):
                fileno, registry, group, registry_batch, landuse, year = record
                print(f"  {i}. {fileno} | {registry} | Group {group} | RegBatch {registry_batch} | {landuse} | {year}")
            
            # Overall test result
            all_checks_passed = (
                validation_results['total_count']['match'] and
                validation_results['con_registry_check']['all_con_in_registry3']
            )
            
            print(f"\n{'='*60}")
            if all_checks_passed:
                print("🎉 TEST PASSED: All validations successful!")
                return True
            else:
                print("❌ TEST FAILED: Some validations failed")
                return False
                
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return False
        finally:
            connection.close()


def main():
    """Run the database insertion test"""
    parser = argparse.ArgumentParser(description="Insert test file numbers into the database")
    parser.add_argument("--records-per-category", type=int, default=5,
                        help="Number of records to generate per category (default: 5)")
    parser.add_argument("--categories", type=str, default=None,
                        help="Comma-separated list of categories to include")

    args = parser.parse_args()

    categories = None
    if args.categories:
        categories = [cat.strip().upper() for cat in args.categories.split(',') if cat.strip()]

    inserter = DatabaseInserter()
    success = inserter.run_test(records_per_category=args.records_per_category, categories=categories)
    
    if success:
        print("\n✅ Database insertion test completed successfully!")
        print("Ready to proceed with full data insertion.")
    else:
        print("\n❌ Database insertion test failed!")
        print("Please check the errors above and fix issues before proceeding.")
    
    return success


if __name__ == "__main__":
    main()