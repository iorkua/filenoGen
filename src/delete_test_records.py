"""
Delete test records from database
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from database_connection import DatabaseConnection

def main():
    print("Deleting test records from database...")
    print("=" * 40)
    
    db = DatabaseConnection()
    connection = db.get_connection('pyodbc')
    
    if not connection:
        print("❌ Could not connect to database")
        return
    
    try:
        cursor = connection.cursor()
        
        # Count existing test records
        cursor.execute("SELECT COUNT(*) FROM [dbo].[grouping] WHERE [created_by] = 'Generated'")
        count_before = cursor.fetchone()[0]
        print(f"Found {count_before} test records to delete")
        
        if count_before > 0:
            # Delete test records
            cursor.execute("DELETE FROM [dbo].[grouping] WHERE [created_by] = 'Generated'")
            deleted_count = cursor.rowcount
            connection.commit()
            
            print(f"✅ Successfully deleted {deleted_count} test records")
        else:
            print("✅ No test records found to delete")
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM [dbo].[grouping] WHERE [created_by] = 'Generated'")
        count_after = cursor.fetchone()[0]
        print(f"Remaining test records: {count_after}")
        
        cursor.close()
        
    except Exception as e:
        print(f"❌ Error deleting records: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    main()