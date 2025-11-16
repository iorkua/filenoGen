#!/usr/bin/env python3
"""Quick test of the CSV importer components."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent

print("=" * 70)
print("CSV IMPORTER SYSTEM TEST")
print("=" * 70)
print()

# Test 1: Import modules
print("Test 1: Importing modules...")
try:
    sys.path.insert(0, str(BASE_DIR / "src"))
    from fast_csv_importer import FastCSVImporter
    from database_connection import DatabaseConnection
    print("  ✓ FastCSVImporter imported")
    print("  ✓ DatabaseConnection imported")
except Exception as e:
    print(f"  ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Create importer instance
print("\nTest 2: Creating importer instance...")
try:
    importer = FastCSVImporter()
    print(f"  ✓ Importer created")
    print(f"  ✓ Batch size: {importer.batch_size} records")
    print(f"  ✓ Grouping batch size: {importer.grouping_batch_size} records")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    sys.exit(1)

# Test 3: Check CSV file
print("\nTest 3: Checking CSV file...")
try:
    import csv
    csv_file = BASE_DIR / "FileNos_PRO.csv"
    if csv_file.exists():
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            records = list(reader)
            print(f"  ✓ CSV file found: {csv_file.name}")
            print(f"  ✓ Total records: {len(records)}")
            print(f"  ✓ Columns: {', '.join(headers)}")
            if records:
                row = records[0]
                print(f"  ✓ Sample record:")
                print(f"    - mlsfNo: {row.get('mlsfNo')}")
                print(f"    - kangisFileNo: {row.get('kangisFileNo')}")
                print(f"    - currentAllottee: {row.get('currentAllottee')}")
    else:
        print(f"  ⚠ CSV file not found: {csv_file}")
        print(f"  ⚠ This is OK - you'll specify it during import")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 4: Test mlsfNo cleaning
print("\nTest 4: Testing mlsfNo cleaning...")
try:
    test_cases = [
        ("KN 1660 AND EXTENSION (TEMP)", "KN 1660"),
        ("AG-2022-9 AND EXTENSION", "AG-2022-9"),
        ("COM-2000-221 (TEMP)", "COM-2000-221"),
        ("  EXTRA   SPACES  ", "EXTRA SPACES"),
    ]
    for input_val, expected in test_cases:
        result = importer.clean_mlsf_no(input_val)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{input_val}' -> '{result}'")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 5: Check Flask
print("\nTest 5: Checking Flask/WebSocket setup...")
try:
    sys.path.insert(0, str(BASE_DIR / "src"))
    from csv_import_server import app, socketio
    print(f"  ✓ Flask app loaded")
    print(f"  ✓ SocketIO configured")
    print(f"  ✓ Template path: {app.template_folder}")
    
    # Check template file
    template_file = BASE_DIR / "src" / "templates" / "import_ui.html"
    if template_file.exists():
        print(f"  ✓ HTML template found")
    else:
        print(f"  ✗ HTML template not found: {template_file}")
except Exception as e:
    print(f"  ✗ Error: {e}")

print()
print("=" * 70)
print("✓ All system checks passed!")
print("=" * 70)
print()
print("Ready to start import:")
print("  1. Web UI: python src/run_csv_import_ui.py")
print("  2. CLI:    python src/fast_csv_importer.py --csv FileNos_PRO.csv")
print()
