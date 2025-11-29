# Fast CSV File Number Importer

A high-performance CSV importer for the FileNos database with modern web UI, real-time progress tracking, and optimized database operations.

## Features

✅ **Fast Batch Processing**
- Configurable batches (default 1,000 rows) for balanced throughput
- Indexed grouping table lookups
- Optimized SQL queries with tuned chunk sizes
- Typically 1,000+ records/second import speed on healthy hardware

✅ **Modern Web UI**
- Real-time progress tracking via WebSocket
- Live statistics dashboard with duplicate counters
- Queue multiple 1k CSV chunks and let the server run them sequentially
- Responsive design that works on desktop and mobile browsers

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

**Using the Web UI (chunk queue):**

1. **Prepare slices:** Split large CSVs into chunks of up to 1,000 data rows (header included in each slice).
2. **Upload chunk:** Use the "Queue for Import" form to select a CSV file and optionally adjust the control tag.
3. **Auto-sequencing:** Each upload is added to the queue; the server processes chunks one at a time.
4. **Monitor progress:** The dashboard tracks status, percent complete, inserted/duplicate counts, and a live log for the active chunk.
5. **Review history:** Completed imports stay in the queue with their metrics so you can verify results or retry failed batches.

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

### Preparing 1k CSV Chunks

- Keep the header row in every slice so the importer can map columns correctly.
- Stay at or below 1,000 data rows per file; uploads above the limit are rejected.
- Name chunks descriptively (for example `filenos_part01.csv`, `filenos_part02.csv`) to make queue tracking easier.
- Uploaded files are stored under `uploads/` until processed; successful jobs keep their metrics so you have an audit trail.

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
    - Bulk lookups via IN clause (500 record batches to stay lock-friendly)
    - Cache-based deduplication

2. **Batch Inserts**
    - Default 1,000 records per batch (configurable)
    - Uses `executemany()` for optimal throughput
    - Frequent commits keep transaction log usage low

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
- **Duplicate records**: Rows ignored because the MLS number already exists or repeats in the CSV

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

## Duplicate Handling

- The importer normalizes MLS numbers (trims whitespace, collapses gaps, uppercases) before processing.
- Any record whose normalized MLS number already exists in `[dbo].[fileNumber]` is skipped.
- Duplicate MLS numbers within the same CSV file are also ignored.
- Progress and summary logs show how many records were skipped as duplicates.

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
├── uploads/                     # Queued CSV chunks + persistent job metadata
│   └── jobs.json                # Queue state (auto-created)
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

emit('start_import', {
emit('cancel_import')
emit('get_status')
### Server Endpoints

**HTTP (REST):**

- `POST /api/upload` — multipart form upload (`file`, `controlTag`). Validates ≤1,000 data rows and queues the job.
- `GET /api/jobs` — returns the current queue, job metrics, and the maximum row limit per chunk.

**WebSocket Events:**

- `jobs_update` — broadcast when the queue changes (new job, status change, completion).
- `progress` — live importer messages for the active job (`job_id`, `message`, `progress`).
- `import_complete` — fired after each job finishes with success flag and record counts.
- `status_update` — snapshot of queue and active job when requested.
- `error` — surfaced if the server encounters an issue (e.g., bad upload, database error).

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
