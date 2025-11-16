# Fast CSV File Number Importer

A high-performance CSV importer for the FileNos database with modern web UI, real-time progress tracking, and optimized database operations.

## Features

✅ **Fast Batch Processing**
- 2000+ records per batch for optimal throughput
- Indexed grouping table lookups
- Optimized SQL queries with bulk inserts
- Typically 1000+ records/second import speed

✅ **Modern Web UI**
- Real-time progress tracking via WebSocket
- Live statistics dashboard
- Beautiful, responsive design
- Works on desktop and mobile browsers

✅ **Real-time Progress Feedback**
- Live import progress percentage
- Record insertion rate (records/second)
- Matched/unmatched grouping counts
- Live import log

✅ **Intelligent Grouping Matching**
- Automatic prefetch of grouping data
- Cache-based lookups for speed
- Batch updates to grouping table
- Supports control tags for record tracking

✅ **Error Handling & Recovery**
- Comprehensive error logging
- Graceful error recovery
- Cancellation support
- Detailed operation statistics

## Installation

### 1. Install Dependencies

```bash
# Activate your virtual environment
.venv\Scripts\activate.bat

# Install required packages
pip install -r requirements.txt
```

The following packages will be installed:
- `Flask` - Web framework
- `flask-socketio` - WebSocket support for real-time updates
- `pyodbc` - SQL Server connection
- `pymssql` - Alternative SQL Server driver
- `pandas` - Data processing

### 2. Environment Setup

Ensure your `.env` file is configured with database credentials:

```env
DB_SQLSRV_HOST=your_server
DB_SQLSRV_PORT=1433
DB_SQLSRV_DATABASE=your_database
DB_SQLSRV_USERNAME=your_username
DB_SQLSRV_PASSWORD=your_password
CONNECTION_TIMEOUT=30
```

## Usage

### Option 1: Web UI (Recommended)

**Start the web server:**

```bash
# Using batch file (easiest)
run_csv_import_ui.bat

# Or manually
cd src
python run_csv_import_ui.py
```

The server will:
1. Start on `http://localhost:5000`
2. Automatically open your browser
3. Display the import UI

**Using the Web UI:**

1. **Specify CSV file**: Enter the path to your CSV file (default: `FileNos_PRO.csv`)
2. **Control tag**: Enter a tag for tracking (default: `PROD`)
3. **Start Import**: Click the "Start Import" button
4. **Monitor Progress**: Watch real-time progress, statistics, and logs
5. **Cancel if needed**: Click "Cancel" to stop the import at any time

### Option 2: Command Line

**Basic import:**

```bash
cd src
python fast_csv_importer.py --csv FileNos_PRO.csv --control-tag PROD
```

**Command options:**

```bash
python fast_csv_importer.py --help

--csv PATH              Path to CSV file (default: FileNos_PRO.csv)
--control-tag TAG       Control tag for tracking (default: PROD)
```

## CSV File Format

Expected CSV columns:
- `SN` - Serial number
- `mlsfNo` - MLSF file number (primary key for matching)
- `kangisFileNo` - KANGIS file number
- `plotNo` - Plot number
- `tpPlanNo` - TP plan number
- `currentAllottee` - Current allottee name
- `layoutName` - Layout name
- `districtName` - District name
- `lgaName` - LGA name

Example:
```csv
SN,mlsfNo,kangisFileNo,plotNo,tpPlanNo,currentAllottee,layoutName,districtName,lgaName
1,KN 1660,KNML 08791,879,LPKN 1032,MUTAQQA UMAR,DANBARE,KUMBOTSO,KUMBOTSO
```

## Database Operations

### Fast Processing Pipeline

```
Read CSV (5%)
    ↓
Prefetch Grouping Data (20%)
    ↓
Prepare Records (20%)
    ↓
Insert in Batches (50%)
    ↓
Validate Results (5%)
```

### Performance Optimization

1. **Indexed Lookups**
   - Uses indexed `awaiting_fileno` in grouping table
   - Bulk lookups via IN clause (1000 records/chunk)
   - Cache-based deduplication

2. **Batch Inserts**
   - 2000 records per batch
   - Uses `executemany()` for optimal throughput
   - Commits after each batch

3. **Staged Updates**
   - Grouping updates staged in memory
   - Flushed in batches of 1000 records
   - Reduces round-trips to database

### Statistics Tracked

- **Total records**: Records in CSV
- **Processed records**: Records prepared for insertion
- **Inserted records**: Records successfully inserted
- **Matched records**: Records with grouping matches
- **Unmatched records**: Records without grouping matches
- **Skipped records**: Records with errors

## mlsfNo Cleaning

The importer automatically cleans `mlsfNo` values for matching:

```python
# Removes:
- "AND EXTENSION"
- "(TEMP)"
- Extra whitespace

# Example:
Input:  "KN 1660 AND EXTENSION (TEMP)"
Output: "KN 1660"
```

## Web UI Features

### Real-Time Progress
- Live percentage progress
- Current operation description
- Records processed per second

### Statistics Dashboard
- Total records
- Inserted count
- Matched groupings
- Unmatched count

### Live Import Log
- Timestamped log entries
- Color-coded message types
- Auto-scrolling
- Searchable content

### Connection Status
- Server connection indicator
- Top-right corner badge
- Automatic reconnection

## Import Results

After import completion, you'll see:

```
📊 Import Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Records Read    : 10,000
Records Inserted      : 9,850
Matched Groupings     : 7,500
Unmatched Groupings   : 2,350
Skipped Records       : 150
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Elapsed Time          : 8.5 seconds
Import Rate           : 1,159 rec/sec
```

## Troubleshooting

### "Database connection failed"
- Check `.env` file is correctly configured
- Verify SQL Server is running
- Test connection with `python src/database_connection.py`

### "CSV file not found"
- Verify the file path is correct
- Use absolute path if relative path doesn't work
- Check file permissions

### "Import is running very slowly"
- Check database server load
- Verify grouping table indexes exist
- Check network latency

### "WebSocket connection failed"
- Check firewall settings
- Verify port 5000 is not in use
- Try `netstat -ano | findstr :5000`

### Browser won't open automatically
- Check browser security settings
- Manually navigate to `http://localhost:5000`
- Try a different browser

## File Locations

```
filenoGen/
├── FileNos_PRO.csv              # Main CSV file to import
├── run_csv_import_ui.bat        # Quick launcher (Windows)
├── requirements.txt             # Python dependencies
├── .env                         # Database configuration
└── src/
    ├── fast_csv_importer.py     # Core importer logic
    ├── csv_import_server.py     # Flask/WebSocket server
    ├── run_csv_import_ui.py     # UI launcher
    ├── database_connection.py    # DB connection manager
    └── templates/
        └── import_ui.html       # Web UI template
```

## Control Tags

Control tags allow you to track and manage import batches:

- `PROD` - Production data (default)
- `TEST` - Test import
- `BATCH_001` - Named batches
- `KANGIS_GIS` - Source identifier

All records tagged with the same control tag can be:
- Easily identified in the database
- Bulk updated if needed
- Cleaned up if necessary

## API Reference

### FastCSVImporter Class

```python
from src.fast_csv_importer import FastCSVImporter

importer = FastCSVImporter()

# Set progress callback
importer.set_progress_callback(lambda msg, pct: print(f"{msg} ({pct}%)"))

# Run import
success = importer.run_import(
    csv_path=Path("FileNos_PRO.csv"),
    control_tag="PROD"
)

# Check results
print(f"Inserted: {importer.inserted_records}")
print(f"Matched: {importer.matched_records}")
print(f"Unmatched: {importer.unmatched_records}")
```

### Server Endpoints

**WebSocket Events:**

```
emit('start_import', {
    'csv_file': 'FileNos_PRO.csv',
    'control_tag': 'PROD'
})

emit('cancel_import')
emit('get_status')

# Received events:
on('progress', data)          # Progress update
on('import_complete', data)   # Import finished
on('import_cancelled', data)  # Import cancelled
on('error', data)             # Error occurred
on('status_update', data)     # Status change
```

## Performance Tips

1. **Use indexed grouping table**
   - Ensure `awaiting_fileno` is indexed
   - Run: `CREATE INDEX idx_awaiting ON grouping(awaiting_fileno)`

2. **Batch appropriate size**
   - Default 2000 is optimal for most cases
   - Reduce if memory is limited
   - Increase only if server is very fast

3. **Network optimization**
   - Use direct database connection if possible
   - Run importer on same network as database
   - Close other applications using network

4. **Database optimization**
   - Disable non-clustered indexes during import
   - Run statistics after import
   - Check transaction log space

## Logging

Logs are written to:
- `csv_import.log` - Main import log
- Console output - Real-time progress

Enable debug logging:
```python
import logging
logging.getLogger('fast_csv_importer').setLevel(logging.DEBUG)
```

## License

See LICENSE file for details.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the import log file
3. Verify database connection
4. Check CSV file format
