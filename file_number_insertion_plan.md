# File Number Insertion Plan - SQL Server with Python

## Overview
Insert generated file numbers into SQL Server `klas.dbo.grouping` table using Python with proper registry assignment and grouping logic.

## Database Configuration
```
Host: VMI2583396
Port: 1433
Database: klas
Username: klas
Password: YourStrongPassword123!
Table: grouping
```

## Table Schema
```sql
CREATE TABLE [dbo].[grouping] (
    [id] INT IDENTITY(1,1) PRIMARY KEY,
    [awaiting_fileno] NVARCHAR(50),        -- Generated file number
    [created_by] NVARCHAR(50),             -- 'Generated'
    [number] INT,                          -- Sequential number (1 to N)
    [year] INT,                            -- Year from file number
    [landuse] NVARCHAR(20),                -- Extracted from file number prefix
    [created_at] DATETIME,                 -- Current timestamp
    [registry] NVARCHAR(20),               -- Assigned based on year/CON rules
    [mls_fileno] NVARCHAR(50),             -- NULL
    [mapping] INT,                         -- 0
    [group] INT,                           -- Group number: group 1 = 100 records, group 2 = 100 records, etc.
    [sys_batch_no] INT,                    -- System batch: sys_batch_no 1 = 100 records, sys_batch_no 2 = 100 records, etc.
    [registry_batch_no] INT,               -- Batch counter per registry in 100-record increments
    [tracking_id] NVARCHAR(20)             -- Unique tracking identifier TRK-XXXXXXXX-XXXXX
)
```

## Registry Assignment Rules
1. **Registry 1**: Years 1981-1991 for RES, COM, IND, AG families (including -RC)
2. **Registry 2**: Years 1992-2025 for RES, COM, IND, AG families (including -RC)
3. **Registry 3**: Any file number containing "CON" (overrides year rules) across all land uses

## File Number Categories (16 types)
1. RES (Residential)
2. COM (Commercial)
3. IND (Industrial)
4. AG (Agriculture)
5. RES-RC (Residential Recertification)
6. COM-RC (Commercial Recertification)
7. IND-RC (Industrial Recertification)
8. AG-RC (Agriculture Recertification)
9. CON-RES (Conversion to Residential) → Registry 3
10. CON-COM (Conversion to Commercial) → Registry 3
11. CON-IND (Conversion to Industrial) → Registry 3
12. CON-AG (Conversion to Agriculture) → Registry 3
13. CON-RES-RC (Conversion to Residential + Recertification) → Registry 3
14. CON-COM-RC (Conversion to Commercial + Recertification) → Registry 3
15. CON-IND-RC (Conversion to Industrial + Recertification) → Registry 3
16. CON-AG-RC (Conversion to Agriculture + Recertification) → Registry 3

## Data Volume
- **Years**: 1981-2025 (45 years)
- **Numbers per year**: 10,000
- **Categories**: 16
- **Total records**: 7,200,000 records
- **Groups**: 72,000 groups (100 records each)
- **System batches**: 72,000 batches (100 records each)
- **Registry batches**: 72,000 batches (tracked per registry)

## Python Implementation Plan

### Phase 1: Setup & Connection
- [ ] Install required packages (`pyodbc`, `pandas`)
- [ ] Create database connection helper
- [ ] Test connection to SQL Server
- [ ] Verify table structure

### Phase 2: Data Generation Logic
- [ ] Create file number generator function
- [ ] Implement registry assignment logic
- [ ] Create land use extraction function
- [ ] Add grouping and batch numbering logic

### Phase 3: Batch Processing
- [ ] Process records in batches of 1,000 for performance
- [ ] Implement transaction handling
- [ ] Add progress tracking and logging
- [ ] Error handling and retry logic

### Phase 4: Data Validation
- [ ] Verify record counts per category
- [ ] Validate registry assignments
- [ ] Check group and batch numbering
- [ ] Confirm no duplicate file numbers

## Implementation Structure

```python
# Main components needed:
1. database_connection.py    # SQL Server connection
2. file_number_generator.py  # Generate file numbers
3. registry_assigner.py      # Assign registries by rules
4. batch_processor.py        # Insert in batches
5. data_validator.py         # Validate inserted data
6. main_insertion.py         # Orchestrate the process
```

## Sample Data Flow

### Input Generation
```
Records 1-100:    RES-1981-1 to RES-1981-100 → Registry 1, Group 1, Batch 1
Records 101-200:  RES-1981-101 to RES-1981-200 → Registry 1, Group 2, Batch 2
Records 201-300:  RES-1981-201 to RES-1981-300 → Registry 1, Group 3, Batch 3
...
CON-RES records:  → Registry 3, Group X, Batch X (100 records each)
```

### Database Insert
```sql
-- Group 1, Batch 1 (Records 1-100)
INSERT INTO [dbo].[grouping] VALUES
('RES-1981-1', 'Generated', 1, 1981, 'RES', GETDATE(), 'Registry 1', NULL, 0, 1, 1),
('RES-1981-2', 'Generated', 2, 1981, 'RES', GETDATE(), 'Registry 1', NULL, 0, 1, 1),
...
('RES-1981-100', 'Generated', 100, 1981, 'RES', GETDATE(), 'Registry 1', NULL, 0, 1, 1),

-- Group 2, Batch 2 (Records 101-200)
('RES-1981-101', 'Generated', 101, 1981, 'RES', GETDATE(), 'Registry 1', NULL, 0, 2, 2),
('RES-1981-102', 'Generated', 102, 1981, 'RES', GETDATE(), 'Registry 1', NULL, 0, 2, 2),
...
```

## Performance Considerations
- **Batch size**: 1,000 records per insert
- **Transaction size**: 10,000 records per transaction
- **Memory usage**: Process one category at a time to manage memory
- **Indexing**: Consider adding indexes after bulk insert
- **Estimated time**: 2-4 hours for full dataset

## Error Handling Strategy
- Log all operations with timestamps
- Checkpoint after each category completion
- Ability to resume from last checkpoint
- Duplicate detection and handling
- Connection retry logic

## Validation Queries
```sql
-- Check total records
SELECT COUNT(*) FROM [dbo].[grouping]

-- Verify registry distribution
SELECT [registry], COUNT(*) FROM [dbo].[grouping] GROUP BY [registry]

-- Check land use distribution
SELECT [landuse], COUNT(*) FROM [dbo].[grouping] GROUP BY [landuse]

-- Verify year ranges
SELECT MIN([year]), MAX([year]) FROM [dbo].[grouping]

-- Check CON assignments
SELECT COUNT(*) FROM [dbo].[grouping] 
WHERE [awaiting_fileno] LIKE '%CON%' AND [registry] = '3'
```

## Risk Mitigation
- Backup database before insertion
- Test with small dataset first (100 records)
- Monitor disk space during insertion
- Set up connection timeouts
- Plan for rollback scenarios

## Success Criteria
- [ ] All 7.2M records inserted successfully
- [ ] Registry assignments follow rules correctly
- [ ] Groups and batches numbered sequentially
- [ ] No duplicate file numbers
- [ ] All land use categories represented
- [ ] Performance within acceptable limits

## Next Steps
1. Review and approve this plan
2. Set up Python development environment
3. Create database backup
4. Implement Phase 1 (connection testing)
5. Start with small test batch (1,000 records)