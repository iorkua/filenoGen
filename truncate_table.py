"""
Fast Table Truncation Script
Truncates the grouping table to start fresh
"""

import pyodbc
import time

def truncate_grouping_table():
    """Truncate the grouping table"""
    
    # Database connection
    SERVER = "VMI2583396"
    DATABASE = "klas"
    USERNAME = "klas"
    PASSWORD = "YourStrongPassword123!"
    
    connection_string = f"""
    Driver={{ODBC Driver 17 for SQL Server}};
    Server={SERVER};
    Database={DATABASE};
    UID={USERNAME};
    PWD={PASSWORD};
    """
    
    try:
        print("🗑️  TRUNCATING GROUPING TABLE")
        print("="*50)
        
        # Connect
        print("Connecting to database...", end=' ', flush=True)
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        print("✓")
        
        # Get current count
        print("Getting current record count...", end=' ', flush=True)
        cursor.execute("SELECT COUNT(*) FROM grouping WITH (NOLOCK)")
        current_count = cursor.fetchone()[0]
        print(f"✓ {current_count:,} records")
        
        if current_count == 0:
            print("⚠️  Table is already empty!")
            return True
        
        # Confirm truncation
        print(f"\n⚠️  This will DELETE ALL {current_count:,} records from the grouping table!")
        response = input("Continue? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("❌ Cancelled")
            return False
        
        # Truncate
        print("\nTruncating table...", end=' ', flush=True)
        start_time = time.time()
        
        cursor.execute("TRUNCATE TABLE grouping")
        conn.commit()
        
        elapsed = time.time() - start_time
        print(f"✓ Done in {elapsed:.2f}s")
        
        # Verify
        print("Verifying table is empty...", end=' ', flush=True)
        cursor.execute("SELECT COUNT(*) FROM grouping")
        final_count = cursor.fetchone()[0]
        print(f"✓ {final_count} records")
        
        print("\n" + "="*50)
        print("✅ TABLE TRUNCATED SUCCESSFULLY")
        print(f"   Deleted: {current_count:,} records")
        print(f"   Time: {elapsed:.2f} seconds")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        print("✓ Disconnected")

if __name__ == "__main__":
    success = truncate_grouping_table()
    
    if success:
        print("\n🎉 Ready for fresh data generation!")
    else:
        print("\n💥 Truncation failed!")