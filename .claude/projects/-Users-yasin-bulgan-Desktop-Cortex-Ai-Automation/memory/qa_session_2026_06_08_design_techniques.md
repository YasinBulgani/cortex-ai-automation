---
name: qa-session-2026-06-08-design-techniques
description: Session fixes for pairwise algorithm bugs and design technique enhancements
metadata:
  type: project
---

## Design Techniques QA Session — 2026-06-08 (continuation)

**Fixed 3 critical unit test bugs:**

1. **Whitespace stripping in `DtRunCreate.effective_fields()`** (`schemas.py:1046`): Changed `name=c` to use stripped value — `conds = [c.strip() for c in ...]`.

2. **Pairwise greedy algorithm coverage bug** (`design_service.py:_fallback_pairwise`): Added look-ahead scoring — when computing score for a value, now checks all possible values for unassigned fields, not just already-assigned ones. Fixes 2×2 case only producing 2 rows.

3. **Safety cap off-by-one** (`design_service.py:673`): Changed `> 200` to `>= 200`, checking BEFORE append so cap is truly ≤200 rows.

**New: Pairwise page enhancements (`apps/web/.../design/pairwise/page.tsx`):**
- Added `viewMode` state (`"list" | "matrix"`)
- List view: shows parameter key-value chip pairs for each case row
- Matrix view: HTML table with parameter names as column headers, each row is a test case
- View toggle (Liste/Tablo) appears when cases exist

**New: DT/Pairwise integration tests** added to `backend/tests/test_management/test_design_techniques.py`:
- `TestDtRunCreate` (5 tests): happy path, conditions→bool fields, fields override conditions, no-fields raises, tenant isolation
- `TestPairwiseRunCreate` (5 tests): happy path, 2×2 all-pairs covered, min-2-fields validation, safety cap, tenant isolation
- Updated `TestAllowedConstants` to include DT and PAIRWISE in ALLOWED_TECHNIQUES

**New: QA test cases (`qa/cases/design-techniques/`):**
- `TC-DESIGN-001`: DT generation + matrix view E2E steps
- `TC-DESIGN-002`: Pairwise generation + matrix view E2E steps
- `TC-DESIGN-003`: Pairwise 2×2 coverage (automated, linked to unit test)
- `TC-DESIGN-004`: AI regression suggestion panel UI test
- Added `DESIGN` domain to `qa/tools/lib/domains.mjs`

**Status:** 10318 tests pass, 0 TS errors, QA validate: 25 ok / 0 fail

**Why:** These fixed hidden algorithmic bugs that would cause incorrect pairwise coverage in production; the enhancements make design technique results readable at a glance.

**How to apply:** The pairwise algorithm change is now correct; do not revert the `>= 200` cap or the look-ahead scoring.
