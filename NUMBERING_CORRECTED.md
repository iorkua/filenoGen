# CORRECTED Understanding - The REAL Numbering System

## 🎯 The ACTUAL Logic (What You're Saying)

```
ALL counters are GLOBAL and CONTINUOUS:
├─ 'number': 1 → 7,200,000 (global counter across ALL records)
├─ 'group': 1 → 72,000 (100 records per group, continuous)
├─ 'sys_batch_no': 1 → 72,000 (100 records per batch, continuous, SAME as group)
└─ 'registry_batch_no': Resets PER REGISTRY (only this one resets!)
```

---

## 📊 Examples (CORRECTED)

### RES-RC-1981-1

Your database shows:
```
id: 1,800,001
awaiting_fileno: RES-RC-1981-1
number: 1                    ← This seems wrong if it's supposed to be global?
group: 1                     ← This seems wrong if it's supposed to be 18,001?
sys_batch_no: 1              ← This seems wrong if it's supposed to be 18,001?
registry_batch_no: 1         ← This is correct (first in Registry 1)
```

But if numbers are GLOBAL and CONTINUOUS, it should be:

```
awaiting_fileno: RES-RC-1981-1
number: 1,800,001            ← Global position (1.8M from id=1,800,001)
group: 18,001                ← (1,800,001 / 100 = 18,000.01 → group 18,001)
sys_batch_no: 18,001         ← Same as group (100 per batch)
registry_batch_no: 4,401     ← Registry 1 counter (reset per registry)
```

---

## 🔄 The Fixed Code Logic

```python
# Initialize GLOBAL counters (NOT per-category):
global_record_count = 0              # Tracks ALL records
registry_counts: Dict[str, int] = {} # Per-registry counter

for sequence in self.registry_sequences:
    registry_id = sequence['registry']
    registry_counts[registry_id] = registry_counts.get(registry_id, 0)
    
    for category in sequence['categories']:
        for year in range(seq_start, seq_end + 1):
            for number in range(1, number_cap + 1):
                # INCREMENT GLOBAL:
                global_record_count += 1           # 1, 2, 3, ..., 7.2M
                
                # Calculate group (100 per group, global):
                group_number = ((global_record_count - 1) // 100) + 1
                
                # sys_batch_no = group (same thing, 100 per batch):
                sys_batch_no = group_number
                
                # Registry batch (resets per registry):
                registry_counts[registry_id] += 1
                registry_batch_no = ((registry_counts[registry_id] - 1) // 100) + 1
                
                yield {
                    'number': global_record_count,        # ← GLOBAL (1-7.2M)
                    'group': group_number,                # ← GLOBAL (1-72K)
                    'sys_batch_no': sys_batch_no,         # ← GLOBAL (1-72K)
                    'registry_batch_no': registry_batch_no # ← PER REGISTRY (resets)
                }
```

---

## 📈 Concrete Examples (CORRECTED)

```
RES-1981-1:
  Global record count: 1
  number: 1
  group: 1
  sys_batch_no: 1
  registry_batch_no: 1          ← 1st in Registry 1

RES-1981-100:
  Global record count: 100
  number: 100
  group: 1
  sys_batch_no: 1
  registry_batch_no: 1          ← Still in group 1

RES-1981-101:
  Global record count: 101
  number: 101
  group: 2                      ← NEW GROUP (crosses 100 boundary)
  sys_batch_no: 2               ← NEW BATCH
  registry_batch_no: 2          ← 2nd batch in Registry 1

RES-1981-10,000:
  Global record count: 10,000
  number: 10,000
  group: 100                    ← Group 100 of Registry 1
  sys_batch_no: 100
  registry_batch_no: 100        ← 100th batch in Registry 1

RES-1982-1:
  Global record count: 10,001
  number: 10,001                ← CONTINUES (doesn't reset)
  group: 101                    ← CONTINUES (doesn't reset)
  sys_batch_no: 101             ← CONTINUES (doesn't reset)
  registry_batch_no: 101        ← Still per-registry (101st batch in Reg 1)

...after RES finishes (110K records)...

COM-1981-1:
  Global record count: 110,001
  number: 110,001               ← KEEPS GOING
  group: 1,101                  ← KEEPS GOING (not back to 1!)
  sys_batch_no: 1,101           ← KEEPS GOING
  registry_batch_no: 1,101      ← Still per-registry

...eventually reaches RES-RC...

RES-RC-1981-1:
  Global record count: 440,001
  number: 440,001               ← GLOBAL position
  group: 4,401                  ← 4,401st group in Registry 1
  sys_batch_no: 4,401           ← 4,401st batch in Registry 1
  registry_batch_no: 4,401      ← 4,401st batch per Registry 1
```

Wait... `registry_batch_no` and `sys_batch_no` look the same for Registry 1?

---

## 🤔 Question: Does `registry_batch_no` Reset?

Looking at your data again:
```
id: 1,800,001
registry_batch_no: 1
```

If this is truly the first record in Registry 1, then yes it resets per registry.

But when do we move to Registry 2? Let me check:

**Registry 1**: 8 categories × 11 years × 10,000 = 880,000 records
**Registry 2**: 8 categories × 34 years × 10,000 = 2,720,000 records

So:
- Record 1-880,000 = Registry 1 (registry_batch_no: 1-8,800)
- Record 880,001-3,600,000 = Registry 2 (registry_batch_no: resets to 1-27,200!)
- Record 3,600,001-7,200,000 = Registry 3 (registry_batch_no: resets to 1-36,000!)

---

## ✅ FINAL CORRECTED LOGIC

```python
# FIXED CODE:
category_counts: Dict[str, int] = {}
global_record_count = 0              # ← GLOBAL counter (1-7.2M)
registry_counts: Dict[str, int] = {} # ← Per-registry counter (resets per registry)

for sequence in self.registry_sequences:
    registry_id = sequence['registry']
    registry_counts[registry_id] = 0  # Reset for each registry
    
    for category in sequence['categories']:
        for year in range(seq_start, seq_end + 1):
            for number in range(1, number_cap + 1):
                global_record_count += 1
                registry_counts[registry_id] += 1
                
                file_number = f"{category}-{year}-{number}"
                
                # All based on GLOBAL counter:
                group_number = ((global_record_count - 1) // 100) + 1
                batch_number = group_number
                
                # ONLY this resets per registry:
                registry_batch_no = ((registry_counts[registry_id] - 1) // 100) + 1
                
                yield {
                    'awaiting_fileno': file_number,
                    'number': global_record_count,      # ← GLOBAL
                    'group': group_number,              # ← GLOBAL
                    'sys_batch_no': batch_number,       # ← GLOBAL
                    'registry_batch_no': registry_batch_no,  # ← PER REGISTRY
                    # ... other fields ...
                }
```

---

## 📊 Comparison Table

| Field | Scope | When it Resets | Example |
|-------|-------|---|---|
| `number` | GLOBAL | Never (1→7.2M) | RES-1981-1=1, COM-1981-1=110,001, RES-RC-1981-1=440,001 |
| `group` | GLOBAL | Never (1→72K) | RES-1981-1=1, COM-1981-1=1,101, RES-RC-1981-1=4,401 |
| `sys_batch_no` | GLOBAL | Never (1→72K) | Same as group (100 records each) |
| `registry_batch_no` | PER REGISTRY | After each registry | Reg1: 1→8,800, Reg2: 1→27,200, Reg3: 1→36,000 |

---

## 🧪 Expected Test Output (CORRECTED)

```python
from src.file_number_generator import FileNumberGenerator
gen = FileNumberGenerator()
samples = gen.generate_sample_data(records_per_category=2)

for s in samples:
    print(f"{s['awaiting_fileno']:20} | num={s['number']:8} | grp={s['group']:6} | "
          f"batch={s['sys_batch_no']:6} | reg_batch={s['registry_batch_no']:6}")
```

**Expected Output:**
```
RES-1981-1           | num=       1 | grp=     1 | batch=     1 | reg_batch=     1
RES-1981-2           | num=       2 | grp=     1 | batch=     1 | reg_batch=     2
COM-1981-1           | num=  110001 | grp= 1101 | batch= 1101 | reg_batch=  1101
COM-1981-2           | num=  110002 | grp= 1101 | batch= 1101 | reg_batch=  1102
IND-1981-1           | num=  220001 | grp= 2201 | batch= 2201 | reg_batch=  2201
IND-1981-2           | num=  220002 | grp= 2201 | batch= 2201 | reg_batch=  2202
AG-1981-1            | num=  330001 | grp= 3301 | batch= 3301 | reg_batch=  3301
AG-1981-2            | num=  330002 | grp= 3301 | batch= 3301 | reg_batch=  3302
RES-RC-1981-1        | num=  440001 | grp= 4401 | batch= 4401 | reg_batch=  4401  ← Continues!
RES-RC-1981-2        | num=  440002 | grp= 4401 | batch= 4401 | reg_batch=  4402
```

---

## 🎯 Summary of ACTUAL Fixes Needed

In `src/file_number_generator.py`:

**Remove these lines:**
```python
global_record_count = 0  # ← REMOVE (not used correctly anyway)
```

**Keep/Fix these:**
```python
global_record_count = 0              # ← ADD BACK (global counter)
registry_counts: Dict[str, int] = {} # ← Keep (per-registry counter)

# Inside loops:
for sequence in self.registry_sequences:
    registry_counts[sequence['registry']] = 0  # ← RESET per registry
    
    for category in sequence['categories']:
        for year in range(seq_start, seq_end + 1):
            for number in range(1, number_cap + 1):
                global_record_count += 1              # ← Increment global
                registry_counts[registry] += 1        # ← Increment per-registry
                
                # Calculate based on GLOBAL:
                group_number = ((global_record_count - 1) // 100) + 1
                batch_number = group_number
                
                # Calculate based on PER-REGISTRY:
                registry_batch_no = ((registry_counts[registry] - 1) // 100) + 1
                
                yield {
                    'number': global_record_count,      # ← FIX: Was wrong
                    'group': group_number,              # ← FIX: Was wrong
                    'sys_batch_no': batch_number,       # ← FIX: Was wrong
                    'registry_batch_no': registry_batch_no  # ← Keep as is
                }
```

---

Is this correct now?
