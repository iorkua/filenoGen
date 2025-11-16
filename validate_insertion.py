import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.database_connection import DatabaseConnection

db = DatabaseConnection()
test = db.test_connection()

if test['preferred']:
    conn = db.get_connection(test['preferred'])
    cursor = conn.cursor()
    
    # Total count
    cursor.execute("SELECT COUNT(*) as TotalRows FROM [dbo].[grouping] WHERE [created_by] = 'Generated'")
    total = cursor.fetchone()[0]
    print(f'Total Records: {total:,}')
    
    # By Registry
    print('\nBy Registry:')
    cursor.execute("SELECT [registry], COUNT(*) as cnt FROM [dbo].[grouping] WHERE [created_by] = 'Generated' GROUP BY [registry] ORDER BY [registry]")
    for reg, cnt in cursor.fetchall():
        print(f'  Registry {reg}: {cnt:,}')
    
    # By Land Use
    print('\nBy Land Use:')
    cursor.execute("SELECT [landuse], COUNT(*) as cnt FROM [dbo].[grouping] WHERE [created_by] = 'Generated' GROUP BY [landuse] ORDER BY [landuse]")
    for lu, cnt in cursor.fetchall():
        print(f'  {lu}: {cnt:,}')
    
    # Year range
    print('\nYear Range:')
    cursor.execute("SELECT MIN([year]), MAX([year]) FROM [dbo].[grouping] WHERE [created_by] = 'Generated'")
    min_y, max_y = cursor.fetchone()
    print(f'  {min_y} - {max_y}')
    
    cursor.close()
    conn.close()
