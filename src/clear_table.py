"""
Clear all generated records from the database
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__)))

from database_connection import DatabaseConnection

def clear_all_records():
    """Delete ALL records from the grouping table"""
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
        confirm = input("\n⚠️  This will DELETE ALL records from the grouping table. Continue? (type 'DELETE' to confirm): ").strip()
        
        if confirm.upper() != 'DELETE':
            print("❌ Deletion cancelled")
            return False
        
        # Delete ALL records
        print("\n🗑️  Deleting all records...")
        cursor.execute("DELETE FROM [dbo].[grouping]")
        deleted_count = cursor.rowcount
        connection.commit()
        cursor.close()
        
        print(f"✅ Deleted {deleted_count:,} records")
        
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
    success = clear_all_records()
    sys.exit(0 if success else 1)
