"""
Test Rack Shelf Labels Functionality
Simple script to test querying and using the imported rack shelf labels data.
"""

import sys
import os
sys.path.append('src')
from database_connection import DatabaseConnection

def test_rack_shelf_queries():
    """Test various queries against the Rack_Shelf_Labels table."""
    
    print("🧪 TESTING RACK SHELF LABELS FUNCTIONALITY")
    print("=" * 50)
    
    db_helper = DatabaseConnection()
    connection = db_helper.get_connection('pyodbc')
    
    if not connection:
        print("❌ Failed to connect to database")
        return False
    
    try:
        cursor = connection.cursor()
        
        # Test 1: Find available shelves in a specific rack
        print("Test 1: Find available shelves in Rack 'A'")
        cursor.execute("""
            SELECT [shelf], [full_label] 
            FROM [dbo].[Rack_Shelf_Labels] 
            WHERE [rack] = 'A' AND [is_used] = 0
            ORDER BY [shelf]
        """)
        
        available_a = cursor.fetchall()
        print(f"Available shelves in Rack A: {len(available_a)}")
        print(f"First 5: {[(shelf, label) for shelf, label in available_a[:5]]}")
        print()
        
        # Test 2: Find all available racks
        print("Test 2: Find all racks with available shelves")
        cursor.execute("""
            SELECT [rack], COUNT(*) as available_shelves
            FROM [dbo].[Rack_Shelf_Labels] 
            WHERE [is_used] = 0
            GROUP BY [rack]
            ORDER BY [rack]
        """)
        
        available_racks = cursor.fetchall()
        print(f"Racks with available shelves: {len(available_racks)}")
        print(f"First 10: {[(rack, count) for rack, count in available_racks[:10]]}")
        print()
        
        # Test 3: Reserve a shelf (simulate usage)
        print("Test 3: Reserve shelf A1 for testing")
        cursor.execute("""
            UPDATE [dbo].[Rack_Shelf_Labels] 
            SET [is_used] = 1, [reserved_by] = 'TEST_USER', [reserved_at] = GETDATE()
            WHERE [full_label] = 'A1'
        """)
        connection.commit()
        
        # Verify the reservation
        cursor.execute("""
            SELECT [rack], [shelf], [full_label], [is_used], [reserved_by], [reserved_at]
            FROM [dbo].[Rack_Shelf_Labels] 
            WHERE [full_label] = 'A1'
        """)
        
        reserved_shelf = cursor.fetchone()
        print(f"Reserved shelf A1: Used={reserved_shelf[3]}, By={reserved_shelf[4]}")
        print()
        
        # Test 4: Find next available shelf in Rack A
        print("Test 4: Find next available shelf in Rack A after reservation")
        cursor.execute("""
            SELECT TOP 1 [shelf], [full_label] 
            FROM [dbo].[Rack_Shelf_Labels] 
            WHERE [rack] = 'A' AND [is_used] = 0
            ORDER BY [shelf]
        """)
        
        next_available = cursor.fetchone()
        if next_available:
            print(f"Next available in Rack A: Shelf {next_available[0]} ({next_available[1]})")
        else:
            print("No available shelves in Rack A")
        print()
        
        # Test 5: Unreserve the shelf (cleanup)
        print("Test 5: Cleanup - unreserve shelf A1")
        cursor.execute("""
            UPDATE [dbo].[Rack_Shelf_Labels] 
            SET [is_used] = 0, [reserved_by] = NULL, [reserved_at] = NULL
            WHERE [full_label] = 'A1'
        """)
        connection.commit()
        print("Shelf A1 unreserved successfully")
        print()
        
        # Test 6: Search by shelf number across all racks
        print("Test 6: Find all shelves with number 1")
        cursor.execute("""
            SELECT [rack], [full_label] 
            FROM [dbo].[Rack_Shelf_Labels] 
            WHERE [shelf] = '1'
            ORDER BY [rack]
        """)
        
        shelf_ones = cursor.fetchall()
        print(f"All shelves numbered '1': {len(shelf_ones)}")
        print(f"Examples: {[(rack, label) for rack, label in shelf_ones[:10]]}")
        
        cursor.close()
        print("\n✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    finally:
        connection.close()

if __name__ == "__main__":
    success = test_rack_shelf_queries()
    
    if success:
        print("\n🎉 Rack Shelf Labels system is working correctly!")
    else:
        print("\n💥 Tests failed - check the database connection and table structure")
        sys.exit(1)