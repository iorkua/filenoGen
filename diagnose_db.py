"""
Diagnostic script - Check actual registry names and column names in database
"""

import pyodbc

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
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    
    print("✓ Connected to database\n")
    
    # Check table columns
    print("📋 Columns in 'grouping' table:")
    print("-" * 70)
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'grouping'
        ORDER BY ORDINAL_POSITION
    """)
    
    for col_name, data_type in cursor.fetchall():
        print(f"  {col_name:25} ({data_type})")
    
    # Check distinct registry values
    print("\n📊 Distinct Registry Values:")
    print("-" * 70)
    cursor.execute("SELECT DISTINCT registry, COUNT(*) as count FROM grouping GROUP BY registry ORDER BY registry")
    
    for registry, count in cursor.fetchall():
        print(f"  '{registry}': {count:,} records")
    
    # Show sample records
    print("\n🔍 Sample Records (first 5):")
    print("-" * 70)
    cursor.execute("SELECT TOP 5 id, awaiting_fileno, registry FROM grouping ORDER BY id")
    
    for row in cursor.fetchall():
        print(f"  id={row[0]}, fileno={row[1]}, registry='{row[2]}'")
    
    cursor.close()
    conn.close()
    
    print("\n✓ Diagnostic complete")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
