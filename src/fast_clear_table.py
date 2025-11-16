"""
Fast clear of all records using TRUNCATE (fastest method)
"""

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__)))

from database_connection import DatabaseConnection

def fast_clear_table():
    """Delete ALL records using TRUNCATE (fastest method)"""
    db = DatabaseConnection()
    test_results = db.test_connection()
    
    if not test_results['preferred']:
        print("❌ Database connection failed")
        return False
    
    connection = db.get_connection(test_results['preferred'])
    if not connection:
        print("❌ Could not establish database connection")
        return False
    
    try:
        cursor = connection.cursor()
        
        # Get current count
        cursor.execute("SELECT COUNT(*) FROM [dbo].[grouping]")
        current_count = cursor.fetchone()[0]
        print(f"Current records in table: {current_count:,}")
        
        # Confirm deletion
        confirm = input("\n⚠️  This will DELETE ALL records from the grouping table using TRUNCATE (very fast). Continue? (type 'TRUNCATE' to confirm): ").strip()
        
        if confirm.upper() != 'TRUNCATE':
            print("❌ Deletion cancelled")
            return False
        
        # Use TRUNCATE (fastest method - removes all data instantly)
        print("\n🚀 Truncating table (this should be very fast)...")
        start_time = time.time()
        
        cursor.execute("TRUNCATE TABLE [dbo].[grouping]")
        connection.commit()
        cursor.close()
        
        elapsed = time.time() - start_time
        print(f"✅ Table truncated in {elapsed:.2f} seconds")
        
        # Verify empty
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM [dbo].[grouping]")
        final_count = cursor.fetchone()[0]
        cursor.close()
        
        print(f"✅ Table now contains: {final_count:,} records")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()


if __name__ == "__main__":
    success = fast_clear_table()
    sys.exit(0 if success else 1)
