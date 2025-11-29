# File Number Filtering Plan with Year-Batch Segmentation

## Problem Statement

Current filter design needs to support:
1. **Registry** - Which registry (1, 2, 3)
2. **Purpose/Category** - RES, COM, IND, AG, etc.
3. **Year** - Specific year (1981-2025)
4. **Year-Batch Range** - Segments within a year (1-30, 31-61, ..., up to 100)

**Issue:** The `grouping` table currently has `registry_batch_no` but no `year_batch_no` to segment records by year within a category.

---

## Current Table Schema

```sql
[grouping]
├── awaiting_fileno      -- e.g., "RES-1981-1"
├── year                 -- e.g., 1981
├── category             -- e.g., "RES"
├── registry             -- 1, 2, or 3
├── group                -- Global group (100 records each)
├── sys_batch_no         -- System batch
├── registry_batch_no    -- Registry-specific batch
├── tracking_id          -- Unique ID
└── ... other fields
```

**Missing:** `year_batch_no` - Batch number within each year for a category

---

## Proposed Year-Batch Implementation Plan

### Option 1: Add `year_batch_no` Column (RECOMMENDED)

**Approach:**
- Add new column: `year_batch_no INT` to the `grouping` table
- For each category-year combination with 10,000 records:
  - Total year_batch_no values: 1 through 100 (100 batches per category-year)
  - Records per batch: ~100 records (10,000 ÷ 100 = 100 per batch)
  - Query selection range: 30 records from each batch
  
**Example:** When you query `year_batch_no = 5` with range 1-30:
  - You get records 5001-5030 (30 records from batch 5)

**Pattern per Year-Category:**
```
Category: RES, Year: 1981 (10,000 records total)
├── year_batch_no 1:   Records 1-100
├── year_batch_no 2:   Records 101-200
├── year_batch_no 3:   Records 201-300
├── year_batch_no 4:   Records 301-400
├── ...
└── year_batch_no 100: Records 9,901-10,000

Category: RES, Year: 1982 (new year resets counter)
├── year_batch_no 1:   Records 1-100
├── year_batch_no 2:   Records 101-200
├── year_batch_no 3:   Records 201-300
├── ...
└── year_batch_no 100: Records 9,901-10,000

When Filtering with Range Selection (e.g., range 1-30 in batch 5):
  → Returns records 401-430 (30 records from batch 5)
```

**SQL Migration:**
```sql
-- Add new column
ALTER TABLE [dbo].[grouping]
ADD [year_batch_no] INT NULL;

-- Populate with calculation based on existing data
-- For each year-category combination, calculate batch number (1-100)
UPDATE [dbo].[grouping]
SET [year_batch_no] = (
    SELECT CEILING(ROW_NUMBER_IN_YEAR / 100.0)
    FROM (
        SELECT 
            ROW_NUMBER() OVER (
                PARTITION BY [category], [year] 
                ORDER BY [awaiting_fileno]
            ) as ROW_NUMBER_IN_YEAR
        FROM [dbo].[grouping]
    ) ranked
    WHERE [grouping].id = ranked.id
)

-- Verify: Each category-year should have exactly 100 unique year_batch_no values
SELECT category, year, COUNT(DISTINCT year_batch_no) as batch_count
FROM [dbo].[grouping]
GROUP BY category, year
HAVING COUNT(DISTINCT year_batch_no) <> 100
```

---

## Filter Design with Year-Batch

### Filter Interface

```
┌─────────────────────────────────────┐
│ FILE NUMBER FILTER                   │
├─────────────────────────────────────┤
│                                     │
│ Registry:        [Dropdown ▼]       │
│ Purpose/Category:[Dropdown ▼]       │
│ Year:            [Dropdown ▼]       │
│ Year-Batch:      [Dropdown ▼]       │
│                                     │
│ [FILTER] [CLEAR]                    │
│                                     │
├─────────────────────────────────────┤
│ Results: 30 records                 │
└─────────────────────────────────────┘
```

### Query Example

**User Selection:**
- Registry: 1
- Purpose: RES
- Year: 1985
- Year-Batch: 5
- Range: 1-30 (records to select from the batch)

**Generated Query:**
```sql
SELECT 
    awaiting_fileno,
    year,
    category,
    registry,
    year_batch_no,
    tracking_id,
    group,
    registry_batch_no
FROM [dbo].[grouping]
WHERE 
    registry = '1'
    AND category = 'RES'
    AND year = 1985
    AND year_batch_no = 5
ORDER BY awaiting_fileno
OFFSET 0 ROWS FETCH NEXT 30 ROWS ONLY
    
-- Result: Records RES-1985-401 through RES-1985-430 (30 records from batch 5)
-- Batch 5 contains records 401-500, we select first 30
```

---

## Year-Batch Segmentation Mapping

### Registry 1 (1981-1991) - Example RES Category

| Year | Batch 1 | Batch 2 | Batch 3 | ... | Batch 100 | Total Batches |
|------|---------|---------|---------|-----|-----------|---------------|
| 1981 | 1-100 | 101-200 | 201-300 | ... | 9,901-10,000 | 100 |
| 1982 | 1-100 | 101-200 | 201-300 | ... | 9,901-10,000 | 100 |
| 1983 | 1-100 | 101-200 | 201-300 | ... | 9,901-10,000 | 100 |
| 1984 | 1-100 | 101-200 | 201-300 | ... | 9,901-10,000 | 100 |
| 1985 | 1-100 | 101-200 | 201-300 | ... | 9,901-10,000 | 100 |
| 1986 | 1-100 | 101-200 | 201-300 | ... | 9,901-10,000 | 100 |
| 1987 | 1-100 | 101-200 | 201-300 | ... | 9,901-10,000 | 100 |
| 1988 | 1-100 | 101-200 | 201-300 | ... | 9,901-10,000 | 100 |
| 1989 | 1-100 | 101-200 | 201-300 | ... | 9,901-10,000 | 100 |
| 1990 | 1-100 | 101-200 | 201-300 | ... | 9,901-10,000 | 100 |
| 1991 | 1-100 | 101-200 | 201-300 | ... | 9,901-10,000 | 100 |

**Pattern:** Each category-year combination has exactly 100 year-batches (year_batch_no = 1 to 100)

**Selection Range:** When you query a batch with range "1-30", you get the first 30 records from that batch

---

## Implementation Steps

### Step 1: Database Schema Update
- Add `year_batch_no` column to `grouping` table
- Create index on `(registry, category, year, year_batch_no)`

### Step 2: Generator Update
- Modify `file_number_generator.py` to calculate and populate `year_batch_no`
- When generating records, track position within each category-year
- Assign batch number: `CEILING(position / 30)`

### Step 3: Query Builder Update
- Update filter interface to include Year-Batch dropdown
- Dropdowns cascade: Registry → Category → Year → Year-Batch
- Show record count for selected batch

### Step 4: Query Execution
- Execute filtered query against `grouping` table
- Display records in tabular format
- Show summary: "30 records from RES-1985, Batch 2"

---

## Sample Data Flow

### Input
- Registry: 1
- Category: RES
- Year: 1981
- Year-Batch: 1

### Processing
```
Query: WHERE registry='1' AND category='RES' AND year=1981 AND year_batch_no=1

Results:
├─ RES-1981-1  (year_batch_no=1, position 1 in year)
├─ RES-1981-2  (year_batch_no=1, position 2 in year)
├─ RES-1981-3  (year_batch_no=1, position 3 in year)
...
└─ RES-1981-30 (year_batch_no=1, position 30 in year)
```

### Output (30 records)
```
| awaiting_fileno | year | category | registry | year_batch_no | tracking_id |
|-----------------|------|----------|----------|---------------|-------------|
| RES-1981-1      | 1981 | RES      | 1        | 1             | TRK-XXXX    |
| RES-1981-2      | 1981 | RES      | 1        | 1             | TRK-XXXX    |
| RES-1981-3      | 1981 | RES      | 1        | 1             | TRK-XXXX    |
...
| RES-1981-30     | 1981 | RES      | 1        | 1             | TRK-XXXX    |
```

---

## Batch Structure Reference

### For Each Category-Year:
- **Total records:** 10,000 (for each category)
- **Year-batch_no values:** 1 through 100 (100 batches per category-year)
- **Records per batch:** 100 records (10,000 ÷ 100)
- **Selection range per query:** 30 records (configurable - can select 1-30, 31-61, 62-92, etc.)
- **Total queries possible per batch:** 100÷30 ≈ 3-4 queries per batch

### Batch Breakdown Example (RES-1985):
```
year_batch_no 1:   Records 1-100         (Query range 1-30, 31-61, 62-92, 93-100)
year_batch_no 2:   Records 101-200       (Query range 1-30, 31-61, 62-92, 93-100)
year_batch_no 3:   Records 201-300       (Query range 1-30, 31-61, 62-92, 93-100)
...
year_batch_no 100: Records 9,901-10,000 (Query range 1-30, 31-61, 62-92, 93-100)
```

### Query Selection Pattern:
```
User selects: Registry=1, Category=RES, Year=1985, year_batch_no=5, Range=1-30
→ Database returns: RES-1985-401 through RES-1985-430 (30 records)

User selects: Registry=1, Category=RES, Year=1985, year_batch_no=5, Range=31-61
→ Database returns: RES-1985-431 through RES-1985-461 (31 records)

User selects: Registry=1, Category=RES, Year=1985, year_batch_no=5, Range=62-92
→ Database returns: RES-1985-462 through RES-1985-492 (31 records)

User selects: Registry=1, Category=RES, Year=1985, year_batch_no=5, Range=93-100
→ Database returns: RES-1985-493 through RES-1985-500 (8 records)
```

---

## Implementation Summary

**Confirmed Approach: Option 4 (Query-Time Calculation, No Schema Changes)**

Instead of adding `year_batch_no` column, extract category from `awaiting_fileno` on-the-fly:
- No table modifications needed
- Zero impact on database
- Calculate `year_batch_no` and extract `category` during filtering
- Fast for typical queries

### How It Works

**File Number Format:** `CATEGORY-YEAR-NUMBER`
- Example: `RES-1981-96` → Category: `RES`, Year: `1981`, Number: `96`
- Example: `CON-RES-1985-5` → Category: `CON-RES`, Year: `1985`, Number: `5`

**Extraction Pattern:**
```sql
-- Extract category from awaiting_fileno
CASE 
    WHEN awaiting_fileno LIKE 'CON-%-%-' THEN LEFT(awaiting_fileno, CHARINDEX('-', awaiting_fileno, CHARINDEX('-', awaiting_fileno) + 1) - 1)
    ELSE LEFT(awaiting_fileno, CHARINDEX('-', awaiting_fileno) - 1)
END as category

-- Extract year from awaiting_fileno
CAST(SUBSTRING(awaiting_fileno, CHARINDEX('-', awaiting_fileno) + 1, 4) as INT) as year

-- Calculate year_batch_no (1-100)
CEILING(ROW_NUMBER() OVER (PARTITION BY extracted_category, extracted_year ORDER BY awaiting_fileno) / 100.0) as year_batch_no
```

| Metric | Value |
|--------|-------|
| Batches per category-year | 100 |
| Records per batch | 100 |
| Selection range (configurable) | 30 records |
| Total category-years (all registries) | 720 |
| Table modifications | NONE ✅ |
| Query complexity | Moderate (but fast) |

---

## Next Steps

1. Confirm batch size (30, 50, 100, or other?)
2. Decide: Add new column or use existing `group` column?
3. Update filter interface markdown
4. Create SQL migration script
5. Update generator to populate `year_batch_no`

---

**Last Updated:** November 21, 2025  
**Version:** 1.0

