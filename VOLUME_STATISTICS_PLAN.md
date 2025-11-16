# Volume Statistics & Batch Reset Plan

## Expected volume metrics for generated file numbers.
- Capture batch behavior for `number`, `group`, `sys_batch_no`, and `registry_batch_no`.
- Outline validation steps to ensure counters behave as intended across registries.

## Volume Statistics
- **Total Categories:** 16
- **Year Range:** 1981-2025 (45 years)
- **Numbers per Year per Category:** 10,000
- **Expected Total Records:** 16 × 45 × 10,000 = **7.2 million**
- **Records per Group/System Batch:** 100
- **Expected Groups/System Batches:** ~72,000

## Generation Sequence
- **Registry 1 (1981-1991):** RES → COM → IND → AG → RES-RC → COM-RC → IND-RC → AG-RC
- **Registry 2 (1992-2025):** RES → COM → IND → AG → RES-RC → COM-RC → IND-RC → AG-RC
- **Registry 3 (All Years):** CON-RES → CON-COM → CON-IND → CON-AG → CON-RES-RC → CON-COM-RC → CON-IND-RC → CON-AG-RC

## Registry Allocation Summary
| Registry | Years Covered | Categories (8 each) | Expected Records |
|----------|---------------|---------------------|------------------|
| 1 | 1981-1991 (11 years) | Standard (RES, COM, IND, AG, RES-RC, COM-RC, IND-RC, AG-RC) | 8 × 11 × 10,000 = **880,000** |
| 2 | 1992-2025 (34 years) | Standard (RES, COM, IND, AG, RES-RC, COM-RC, IND-RC, AG-RC) | 8 × 34 × 10,000 = **2,720,000** |
| 3 | 1981-2025 (45 years) | Conversion (CON-RES, CON-COM, CON-IND, CON-AG, CON-RES-RC, CON-COM-RC, CON-IND-RC, CON-AG-RC) | 8 × 45 × 10,000 = **3,600,000** |

## Counter Behavior Plan
- **`number`:** Global serial 1 → 7,200,000 with no reset.
- **`group`:** Increments every 100 global records. Record 1-100 → group 1, 101-200 → group 2, etc.
- **`sys_batch_no`:** Mirrors `group`; functions as system-wide batch ID.
- **`registry_batch_no`:** Counts records per registry in batches of 100. Resets to 1 whenever a new registry sequence begins.
  - Example: Registry 1 records 1-100 → `registry_batch_no` 1. Registry 2 first record resets `registry_batch_no` back to 1. Same for Registry 3.

 