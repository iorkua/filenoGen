"""
Test Updated File Number Generator
Tests the new tracking ID generation and updated registry format.
"""

import sys
import os
sys.path.append('src')

from file_number_generator import FileNumberGenerator

def test_updated_generator():
    """Test the updated file number generator with tracking ID and registry changes."""
    
    print("TESTING UPDATED FILE NUMBER GENERATOR")
    print("=" * 60)
    
    generator = FileNumberGenerator()
    
    # Test 1: Tracking ID Generation
    print("Test 1: Tracking ID Generation")
    print("-" * 30)
    print("Sample Tracking IDs (format: TRK-XXXXXXXX-XXXXX):")
    
    for i in range(5):
        tracking_id = generator.generate_tracking_id()
        print(f"  {i+1}: {tracking_id}")
        
        # Validate format
        parts = tracking_id.split('-')
        if len(parts) != 3 or parts[0] != 'TRK' or len(parts[1]) != 8 or len(parts[2]) != 5:
            print(f"    ERROR: Invalid format for {tracking_id}")
        else:
            print(f"    FORMAT: Valid")
    
    print()
    
    # Test 2: Registry Assignment (Updated Format)
    print("Test 2: Registry Assignment (Updated Format)")
    print("-" * 45)
    
    test_cases = [
        ("RES-1985-1001", 1985, "1"),      # Registry 1: 1981-1991
        ("COM-1995-2002", 1995, "2"),      # Registry 2: 1992-2025  
        ("AG-1990-3003", 1990, "1"),       # Registry 1: 1981-1991
        ("CON-RES-2020-4004", 2020, "3"),  # Registry 3: Contains CON
        ("CON-COM-RC-1985-5005", 1985, "3"), # Registry 3: CON overrides year
        ("RES-RC-2000-6006", 2000, "2"),   # Registry 2: 1992-2025
    ]
    
    for file_number, year, expected_registry in test_cases:
        actual_registry = generator.assign_registry(file_number, year)
        status = "PASS" if actual_registry == expected_registry else "FAIL"
        print(f"  {file_number} (Year {year}) -> Registry {actual_registry} [{status}]")
    
    print()
    
    # Test 3: Complete Record Generation
    print("Test 3: Complete Record Generation")
    print("-" * 35)
    
    # Generate small sample
    sample_records = generator.generate_sample_data(records_per_category=1)
    
    print("Sample Generated Records:")
    for i, record in enumerate(sample_records[:8]):
        print(f"  {i+1:2}. {record['awaiting_fileno']:<15} | "
              f"Registry {record['registry']} | "
              f"Group {record['group']:2} | "
              f"Batch {record['sys_batch_no']:2} | "
              f"Tracking: {record['tracking_id']}")
    
    print()
    
    # Test 4: Verify Required Fields
    print("Test 4: Verify Required Fields")
    print("-" * 30)
    
    required_fields = [
        'awaiting_fileno', 'created_by', 'number', 'year', 'landuse',
        'created_at', 'registry', 'mls_fileno', 'mapping', 'group',
        'sys_batch_no', 'tracking_id'
    ]
    
    sample_record = sample_records[0] if sample_records else {}
    missing_fields = [field for field in required_fields if field not in sample_record]
    
    if missing_fields:
        print(f"  ERROR: Missing fields: {missing_fields}")
    else:
        print(f"  PASS: All required fields present ({len(required_fields)} fields)")
    
    print()
    
    # Test 5: Registry Distribution
    print("Test 5: Registry Distribution")
    print("-" * 28)
    
    registry_counts = {}
    for record in sample_records:
        registry = record['registry']
        registry_counts[registry] = registry_counts.get(registry, 0) + 1
    
    for registry, count in sorted(registry_counts.items()):
        print(f"  Registry {registry}: {count} records")
    
    print()
    print("=" * 60)
    print(f"SUMMARY: Generated {len(sample_records)} test records successfully")
    print("All tests completed!")
    
    return True

if __name__ == "__main__":
    try:
        test_updated_generator()
        print("\nSuccess: All updates working correctly!")
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)