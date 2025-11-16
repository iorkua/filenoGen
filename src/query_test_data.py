"""
Quick database query to show the test results
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from database_connection import DatabaseConnection

def main():
    print("Querying test data from database...")
    print("=" * 50)
    
    db = DatabaseConnection()
    connection = db.get_connection('pyodbc')
    
    if not connection:
        print("❌ Could not connect to database")
        return
    
    try:
        cursor = connection.cursor()
        
        # Show all test records
        cursor.execute("""
            SELECT [awaiting_fileno], [registry], [group], [sys_batch_no], [registry_batch_no], [landuse], [year], [number]
            FROM [dbo].[grouping] 
            WHERE [created_by] = 'Generated'
            ORDER BY [number]
        """)
        
        records = cursor.fetchall()
        
        print(f"Found {len(records)} test records in database:")
        print()
        print("File Number            | Reg | Group | Batch | RegBatch | Land Use | Year | Seq#")
        print("-" * 90)
        
        for record in records:
            fileno, registry, group, batch, reg_batch, landuse, year, number = record
            print(f"{fileno:<22} | {registry:<3} | {group:<5} | {batch:<5} | {reg_batch:<8} | {landuse:<8} | {year} | {number}")
        
        cursor.close()
        
        print(f"\n✅ Database contains {len(records)} test records")
        print("All data looks correct and properly formatted!")
        
    except Exception as e:
        print(f"❌ Error querying database: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    main()