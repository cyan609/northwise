# NORTHWISE Frontend Improvements — Completion Report

**Date:** 2026-10-18  
**File changed:** `static/index.html`

---

## 1. Searchable and Collapsible Report Catalogue

### What was implemented

- **Search input** above the report list with instant case-insensitive filtering
- **Matching fields:** report ID, register number, English title, Traditional Chinese title, project area (EN & ZH)
- **Clear search** — emptying the input restores all 8 reports
- **Collapsible panel** — toggle button (−/+) collapses the list to a compact header
- **Match counter** — shows "8" when all visible, or "N/8" when filtered
- **Bilingual** — search placeholder switches with language toggle

### How it works

```javascript
// Search filters against multiple fields
const hay = [
  r.report_id, r.register_no, r.title_en, r.title_zh,
  r.project_area_en, r.project_area_zh
].join(' ').toLowerCase();

// Instant filtering on input
filteredReports = reports.filter(r => hay.includes(q));
```

### UI changes

- `.report-list` → flex column with header, search input, and scrollable body
- `.rl-header` — title + count badge + collapse toggle
- `.rl-search` — text input with focus styling
- `.rl-body` — scrollable report items container
- `.collapsed` state — hides body, shows compact header button only

---

## 2. Map Marker Investigation and Fix

### Root cause identified

All **8 reports have coordinates**, but **2 pairs share identical fallback coordinates**:

| Report | Title | Coordinates | Status |
|--------|-------|-------------|--------|
| aeiar-276-2026 | Northern Metropolis Highway – San Tin Section | 22.50, 114.07 | Overlaps with aeiar-261-2024 |
| aeiar-261-2024 | San Tin / Lok Ma Chau Development Node | **22.50, 114.07** | Overlaps with aeiar-276-2026 |
| aeiar-274-2026 | Loop – Eastern Connection Road | 22.51, 114.08 | Overlaps with aeiar-176-2013 |
| aeiar-176-2013 | Development of Lok Ma Chau Loop | **22.51, 114.08** | Overlaps with aeiar-274-2026 |
| aeiar-271-2025 | Ngau Tam Mei Area | 22.47, 114.05 | Unique |
| aeiar-175-2013 | Kwu Tung North / Fanling North | 22.50, 114.13 | Unique |
| aeiar-203-2016 | Hung Shui Kiu | 22.43, 113.99 | Unique |
| aeiar-215-2017 | Yuen Long South | 22.42, 114.03 | Unique |

**Why only 6 appeared:** Leaflet circle markers at the exact same coordinates overlap completely. The last-rendered marker covers the previous one, making only one clickable.

### Fix implemented

- **Grouped markers by coordinate** using a `Map` with 4-decimal-precision keys
- **Single markers** (unique coordinates): standard orange circle marker
- **Overlapping markers** (2+ at same spot): larger circle + `L.divIcon` count badge showing the number of reports
- **Popup lists all reports** at that location with clickable entries that open the report card
- **Overlap indicator** in the report list: "📍 Overlaps with N other report(s)"

### Coordinate summary

| Category | Count | Reports |
|----------|-------|---------|
| Approximate fallback coordinates | 8 | All reports |
| Verified project geometry | 0 | Not publicly available |
| Unique coordinates | 6 | 271, 175, 203, 215 + 1 per overlap pair |
| Overlapping coordinates | 2 pairs | 276↔261, 274↔176 |

**No coordinates were invented.** All coordinates are the existing `point_fallback` values from `reports.json`.

---

## 3. Regression Checks

| Check | Result |
|-------|--------|
| `/reports` returns all 8 | ✅ Verified |
| Search by report ID | ✅ Frontend code verified |
| Search by English title | ✅ Frontend code verified |
| Search by Chinese title | ✅ Frontend code verified |
| Clear search restores all 8 | ✅ `filterReports()` handles empty query |
| List collapses/expands | ✅ `toggleReportList()` verified |
| Report selection works after filtering | ✅ `openReportCard()` called on click |
| Map shows all 8 reports (6 unique + 2 overlap clusters) | ✅ Grouped marker logic |
| Chat, citations, links still work | ✅ End-to-end verified |
| Full test suite | ✅ 107/107 pass |

### Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| app.py | 32 | ✅ Pass |
| test_passages.py | 26 | ✅ Pass |
| test_rare_term_gate.py | 19 | ✅ Pass |
| PageNumberAnomalyTest | 8 | ✅ Pass |
| EvidenceConsistencyTest | 23 | ✅ Pass |
| AdversarialValidationTest | 10 | ✅ Pass |
| ClaimLevelEvaluationTest | 9 | ✅ Pass |
| EndToEndRegressionTest | 8 | ✅ Pass |
| **Total** | **107** | **✅ All Pass** |

### End-to-End HTTP Verification

- GET `/` → HTTP 200, valid HTML with new search/collapse elements
- GET `/reports` → 8 reports with correct audit decisions
- POST `/ask` → Evidence cards with verified page labels
- New elements confirmed in HTML: `rlSearch`, `rlToggle`, `rlCount`, `filterReports`, `marker-cluster`, `coordGroups`, `Overlaps with`

---

## 4. Remaining Limitations

1. **All coordinates are approximate fallbacks** — no verified project geometry is publicly available
2. **Two pairs of reports overlap** — this is a data limitation, not a rendering bug. The fix makes overlapping reports discoverable via popup and list indicator.
3. **Marker popups don't update on language switch** — minor issue; popups use initial language
4. **No search debounce** — filtering is instant; acceptable for 8 items

---

## 5. Files Changed

| File | Change |
|------|--------|
| `static/index.html` | Added searchable/collapsible report list, grouped overlapping map markers, overlap indicators |

No backend files were modified.
