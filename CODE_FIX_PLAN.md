# Code Fix Plan for File Number Generator

## Current Problem

The `registry_counts` dictionary is **NOT reset when moving to a new registry**. This causes the per-registry counter to keep accumulating across all registries instead of resetting.

**Current behavior:**
- Registry 1 processes 880K records → `registry_counts['Registry 1']` goes 1 → 8,800
- Registry 2 processes 2.7M records → `registry_counts['Registry 2']` continues 1 → 27,200 ✅ (happens to work because it's new key)
- But the logic doesn't explicitly reset, making it unclear and error-prone

**Intended behavior:**
- Each registry should have its own independent `registry_batch_no` counter
- When we START processing a new registry, that registry's counter should start at 0

---

## The Fix (Two-Part)

### Part 1: Reset Registry Counter Per Registry
**Location:** Line 145 (after `for sequence in self.registry_sequences:`)

**Current code:**
```python
for sequence in self.registry_sequences:
    seq_start, seq_end = sequence['year_range']
    seq_start = max(seq_start, self.start_year)
    seq_end = min(seq_end, self.end_year)
    if seq_start > seq_end:
        continue

    for category in sequence['categories']:
```

**Fixed code:**
```python
for sequence in self.registry_sequences:
    registry_id = sequence['registry']
    registry_counts[registry_id] = 0  # ← ADD THIS LINE - Reset per registry
    
    seq_start, seq_end = sequence['year_range']
    seq_start = max(seq_start, self.start_year)
    seq_end = min(seq_end, self.end_year)
    if seq_start > seq_end:
        continue

    for category in sequence['categories']:
```

**Why:** Explicitly initializes each registry's counter to 0 when we START processing that registry. Makes the logic clear and correct.

---

### Part 2: Use Registry ID Consistently
**Location:** Lines 174-176 (in the yield section)

**Current code:**
```python
                        land_use = self.extract_land_use(file_number)
                        registry = self.assign_registry(file_number, year)
                        registry_counts[registry] = registry_counts.get(registry, 0) + 1
                        registry_batch_no = ((registry_counts[registry] - 1) // self.records_per_group) + 1
```

**Issue:** Line 175 uses `.get(registry, 0) + 1` which can bypass the reset we just set up.

**Fixed code:**
```python
                        land_use = self.extract_land_use(file_number)
                        registry = self.assign_registry(file_number, year)
                        registry_counts[registry] += 1  # ← SIMPLIFY (no need for .get() anymore)
                        registry_batch_no = ((registry_counts[registry] - 1) // self.records_per_group) + 1
```

**Why:** Since we now explicitly reset `registry_counts[registry_id] = 0` at the start of each sequence, we don't need the `.get(registry, 0)` fallback. This makes it clear we're incrementing an already-initialized counter.

---

## Summary of Changes

| Line | Current | Fixed | Purpose |
|------|---------|-------|---------|
| 145 (new) | - | `registry_id = sequence['registry']` | Store registry ID |
| 146 (new) | - | `registry_counts[registry_id] = 0` | Reset counter per registry |
| 175 | `registry_counts[registry] = registry_counts.get(registry, 0) + 1` | `registry_counts[registry] += 1` | Simplify increment |

---

## What This Achieves

✅ **Explicit Reset**: Each registry counter explicitly resets to 0  
✅ **Correct Logic**: `registry_batch_no` will correctly reset per registry  
✅ **No Data Changes**: Global counters (`number`, `group`, `sys_batch_no`) remain unchanged  
✅ **Test Case**: RES-RC-1981-1 will show `registry_batch_no=4,401` (Registry 1's 4,401st batch)

---

## Validation After Fix

Run this test to verify the fix works:

```python
from src.file_number_generator import FileNumberGenerator

gen = FileNumberGenerator()
records = list(gen.generate(records_per_category=2))

print("\n=== First 4 records (Registry 1) ===")
for r in records[:4]:
    print(f"{r['awaiting_fileno']:20} | reg_batch={r['registry_batch_no']:6}")

print("\n=== Should show continuous global counters ===")
for r in records[:4]:
    print(f"{r['awaiting_fileno']:20} | num={r['number']:8} | grp={r['group']:6}")
```

**Expected:**
- `registry_batch_no` will be unique per registry (resets for next registry)
- `number`, `group`, `sys_batch_no` will be continuous globally

---

## Files Modified

- `src/file_number_generator.py` - 2 changes (1 addition + 1 modification)

## Affected Records

- **Old Database**: 1.8M+ records have wrong `registry_batch_no` values (but correct global counters)
- **New Generation**: Will have correct values after fix is applied
- **SQL Fix**: Available in `NUMBERING_FIX_PLAN.md` if needed to correct existing data
