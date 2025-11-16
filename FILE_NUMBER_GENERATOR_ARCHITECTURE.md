# File Number Generator Architecture Design

## 🏗️ System Overview

**Purpose:** Generates 7.2M pre-computed file numbers stored in the `grouping` table for the CSV Importer to match against incoming MLS file numbers.

**Key Stats:**
- 16 Categories × 45 Years × 10,000 Numbers = 7.2M Records
- Indexed on `awaiting_fileno` for fast CSV Importer lookups
- Output feeds the CSV Importer matching engine

---

## 📊 Data Generation Pipeline

### Generation Flow

```
File Number Generation
        ↓
    ┌───────────────────────────────────────────────┐
    │  For Each Registry Sequence:                  │
    │  ├─ Registry 1 (1981-1991)                    │
    │  ├─ Registry 2 (1992-2025)                    │
    │  └─ Registry 3 (All CON files)                │
    └───────────────┬─────────────────────────────┘
                    ↓
    ┌───────────────────────────────────────────────┐
    │  For Each Category in Sequence:               │
    │  ├─ RES, COM, IND, AG (8 families)           │
    │  ├─ Including -RC variants                    │
    │  └─ Including CON variants                    │
    └───────────────┬─────────────────────────────┘
                    ↓
    ┌───────────────────────────────────────────────┐
    │  For Each Year in Range:                      │
    │  ├─ Generate 10,000 numbers                   │
    │  └─ Format: CATEGORY-YEAR-NUMBER              │
    └───────────────┬─────────────────────────────┘
                    ↓
    ┌───────────────────────────────────────────────┐
    │  Extract Attributes:                          │
    │  ├─ Land Use (from prefix)                    │
    │  ├─ Registry (based on CON & year rules)      │
    │  ├─ Group Number (100 records each)           │
    │  ├─ Batch Number (100 records each)           │
    │  ├─ Registry Batch Number (per registry)      │
    │  └─ Tracking ID (unique TRK-XXXXXXXX-XXXXX)  │
    └───────────────┬─────────────────────────────┘
                    ↓
        Insert into Grouping Table (Batches of 1,000)
```

---

## 📋 Registry Assignment Rules

### Three-Registry System

| Registry | Years | Scope |
|----------|-------|-------|
| **Registry 1** | 1981-1991 | Standard categories (RES, COM, IND, AG + RC variants) |
| **Registry 2** | 1992-2025 | Standard categories (RES, COM, IND, AG + RC variants) |
| **Registry 3** | All Years | Conversion files (all CON-* files, highest priority) |

### Assignment Logic (Priority Order)

```python
if 'CON' in file_number:           # Priority 1: CON prefix
    return '3'
elif 1981 <= year <= 1991:         # Priority 2: Year range
    return '1'
elif 1992 <= year <= 2025:
    return '2'
else:
    return '2'  # Fallback
```

---

## 🏷️ File Number Categories (16 Total)

### Category Classification

```
Standard Land Use Types (8 categories):
├─ RES (Residential)
├─ COM (Commercial)
├─ IND (Industrial)
├─ AG (Agriculture)
├─ RES-RC (Residential + Recertification)
├─ COM-RC (Commercial + Recertification)
├─ IND-RC (Industrial + Recertification)
└─ AG-RC (Agriculture + Recertification)

Conversion Land Use Types (8 categories):
├─ CON-RES (Conversion → Residential)
├─ CON-COM (Conversion → Commercial)
├─ CON-IND (Conversion → Industrial)
├─ CON-AG (Conversion → Agriculture)
├─ CON-RES-RC (Conversion → Residential + Recertification)
├─ CON-COM-RC (Conversion → Commercial + Recertification)
├─ CON-IND-RC (Conversion → Industrial + Recertification)
└─ CON-AG-RC (Conversion → Agriculture + Recertification)
```

### Generation Sequence

```
Registry 1 Sequence (1981-1991):
  RES → COM → IND → AG → RES-RC → COM-RC → IND-RC → AG-RC

Registry 2 Sequence (1992-2025):
  RES → COM → IND → AG → RES-RC → COM-RC → IND-RC → AG-RC

Registry 3 Sequence (All Years):
  CON-RES → CON-COM → CON-IND → CON-AG → CON-RES-RC → CON-COM-RC → CON-IND-RC → CON-AG-RC
```

---

## 📊 Grouping Table Schema

### Table Structure

```sql
CREATE TABLE [dbo].[grouping] (
    [id] INT IDENTITY(1,1) PRIMARY KEY,
    [awaiting_fileno] NVARCHAR(50),     -- File number (e.g., RES-1981-1)
    [created_by] NVARCHAR(50),          -- 'Generated'
    [number] INT,                       -- Sequential record number
    [year] INT,                         -- Year from file number
    [landuse] NVARCHAR(20),             -- Land use type
    [created_at] DATETIME,              -- Timestamp
    [registry] NVARCHAR(20),            -- Registry (1, 2, or 3)
    [mls_fileno] NVARCHAR(50),          -- MLS match (NULL initially)
    [mapping] INT,                      -- Match status (0=unmatched, 1=matched)
    [group] INT,                        -- Group number (100 records each)
    [sys_batch_no] INT,                 -- System batch number
    [registry_batch_no] INT,            -- Registry-specific batch
    [tracking_id] NVARCHAR(50)          -- Unique tracking ID (TRK-XXXXXXXX-XXXXX)
)

-- CRITICAL INDEX for CSV Importer
CREATE NONCLUSTERED INDEX idx_awaiting_fileno 
ON dbo.grouping(awaiting_fileno)
```

### Record Example

```
awaiting_fileno:    "RES-1981-1"
registry:           "1"
year:               1981
landuse:            "Residential"
group:              1
tracking_id:        "TRK-Y7K2M9P1-Q8X3B"
mapping:            0 (unmatched)
mls_fileno:         NULL (awaiting match)
```

---

## 🔢 Data Volume & Scale

```
Categories:              16 types
Years:                   45 (1981-2025)
Numbers per year:        10,000 per category
Total Records:           16 × 45 × 10,000 = 7,200,000

Distribution by Registry:
├─ Registry 1 (1981-1991):  8 categories × 11 years × 10,000 = 880,000
├─ Registry 2 (1992-2025):  8 categories × 34 years × 10,000 = 2,720,000
└─ Registry 3 (CON files):  8 categories × 45 years × 10,000 = 3,600,000

Groups:                 72,000 groups (100 records each)
Batches:                72,000 batches (100 records each)
```

---

## 🔄 Generation Flow Example

```
Global Counter = 0

REGISTRY 1 (1981-1991):
  RES:
    1981: RES-1981-1 through RES-1981-10,000
         → Records 1-10,000 → Groups 1-100 → Registry Batches 1-100
    1982: RES-1982-1 through RES-1982-10,000
         → Records 10,001-20,000 → Groups 101-200 → Registry Batches 101-200
    ...
  COM:
    1981: COM-1981-1 through COM-1981-10,000
         → Records X-Y → Groups N-M → Registry Batches P-Q
    ...

REGISTRY 2 (1992-2025):
  RES, COM, etc. (similar pattern)

REGISTRY 3 (All Years):
  CON-RES, CON-COM, etc. (independent counter)
```

**Key Points:**
- Each 100 records = 1 group and 1 batch
- Global counter increments across all registries
- Registry batch counter is independent per registry
- CON files always go to Registry 3

---

## 🎯 Key Features

- ✅ **Registry-Driven:** Processes registries sequentially (1 → 2 → 3)
- ✅ **Automatic Classification:** Extracts land use from file number prefix
- ✅ **Unique Tracking:** Generates unique TRK-XXXXXXXX-XXXXX IDs
- ✅ **Flexible:** Can filter by category or limit records per category
- ✅ **Memory Efficient:** Uses generator pattern (no loading all 7.2M into RAM)
- ✅ **Fast Indexing:** Grouping table indexed on awaiting_fileno for O(log n) CSV Importer lookups

---

## 🛠️ Core Implementation

### FileNumberGenerator Class (src/file_number_generator.py)

**Key Methods:**

```python
def __init__()
    # Initialize with categories, years (1981-2025), config

def generate_file_numbers(
    categories: Optional[Iterable[str]] = None,
    max_per_category: Optional[int] = None
) -> Generator[Dict[str, Any]]
    # Main generator - yields records one at a time
    
def extract_land_use(file_number: str) -> str
    # "RES-1981-1" → "Residential"
    
def assign_registry(file_number: str, year: int) -> str
    # Applies three-registry rules
    
def generate_tracking_id() -> str
    # Creates unique TRK-XXXXXXXX-XXXXX ID
    
def generate_sample_data(records_per_category: int = 10) -> List[Dict]
    # Creates test data
    
def get_category_stats(records: List[Dict]) -> Dict
    # Analyzes generated records
 
 

 

**Last Updated:** November 2025  
**Version:** 1.0.02 
**Status:** Complete

