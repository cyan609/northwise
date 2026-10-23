# NORTHWISE Page-Number Verification and Completion Report

**Date:** 2026-10-18  
**Scope:** Verify page numbering for 6 new reports, find executive summaries, clean up frontend, end-to-end validation.

---

## 1. Page-Number Verification — Per-Report Statistics

### AEIAR-274/2026 (Loop Eastern Connection Road)
| Metric | Value |
|--------|-------|
| Total pages | 478 |
| Verified | 477 (99.8%) |
| Absent | 0 |
| Unverified | 1 (sign page) |
| Footer format | Standard EPD: `chapter-page Month Year` |
| Anomalies | None |
| **Status** | **✅ Verified** |

### AEIAR-261/2024 (San Tin / Lok Ma Chau Development Node)
| Metric | Value |
|--------|-------|
| Total pages | 811 |
| Verified | 811 (100%) |
| Absent | 0 |
| Unverified | 0 |
| Footer format | Standard EPD: `chapter-page Month Year` |
| Anomalies | None |
| **Status** | **✅ Verified** |

### AEIAR-175/2013 (Kwu Tung North / Fanling North NDA)
| Metric | Value |
|--------|-------|
| Total pages | 1,658 |
| Verified | 1,565 (94.4%) |
| Absent | 39 |
| Unverified | 54 |
| Footer format | File-path footer: `Page X-Y` on separate line from date |
| Anomalies | Figure/table pages often lack printed folios |
| **Status** | **✅ Partial — 94.4% verified** |

### AEIAR-176/2013 (Lok Ma Chau Loop)
| Metric | Value |
|--------|-------|
| Total pages | 886 |
| Verified | 872 (98.4%) |
| Absent | 0 |
| Unverified | 14 |
| Footer format | File-path footer: `Page X-Y` (date often absent) |
| Anomalies | None |
| **Status** | **✅ Verified** |

### AEIAR-203/2016 (Hung Shui Kiu NDA)
| Metric | Value |
|--------|-------|
| Total pages | 1,054 |
| Verified | 1,054 (100%) |
| Absent | 0 |
| Unverified | 0 |
| Footer format | Standard EPD: `chapter-page Month Year` |
| Anomalies | None |
| **Status** | **✅ Verified** |

### AEIAR-215/2017 (Yuen Long South Housing Sites)
| Metric | Value |
|--------|-------|
| Total pages | 719 |
| Verified | 719 (100%) |
| Absent | 0 |
| Unverified | 0 |
| Footer format | `Page X-Y` with project code and date |
| Anomalies | **ch.1:** printed folio 1-28 is skipped (goes 1-27 → 1-29); **ch.11:** numbering resets to 11-0 mid-chapter |
| **Status** | **✅ Verified** |

### Summary
| Report | Verified % | Format | Issues |
|--------|-----------|--------|--------|
| AEIAR-274-2026 | 99.8% | Standard EPD | None |
| AEIAR-261-2024 | 100% | Standard EPD | None |
| AEIAR-175-2013 | 94.4% | Page X-Y in file path | 93 figure/table pages without folios |
| AEIAR-176-2013 | 98.4% | Page X-Y in file path | 14 figure/table pages without folios |
| AEIAR-203-2016 | 100% | Standard EPD | None |
| AEIAR-215-2017 | 100% | Page X-Y | 2 publishing anomalies documented |

---

## 2. How Page Numbers Were Verified

### Method
1. **Initial extraction** used the existing `analyze_page()` regex from `extract_pages.py`, which requires a printed folio and month-year date on the same line.
2. **Re-analysis** for 3 reports (AEIAR-175, 176, 215) added a second strategy:
   - Search for `Page X-Y` patterns in the last 400 characters
   - Take the **last** match (closest to the end = most likely the footer)
   - Strip spaces from the label (e.g., `6 - 1` → `6-1`)
   - Mark as `verified` because the `Page` prefix is unambiguous evidence of a printed folio
3. **Sequence validation** checked for:
   - Duplicate labels within a chapter
   - Sudden jumps in numeric sequence
   - Consistency with PDF page index

### Key Findings
- **AEIAR-175, 176, 215** use a different footer format from the original 2 reports: the page number is embedded in a file-path line (e.g., `G:\...\Ch 4 - Noise(clean).doc Page 4-51`) with the date on a separate line.
- **AEIAR-215-2017 ch.11** has a genuine publishing anomaly: the printed numbering resets to `11-0` after `11-6`, then counts up again.
- **AEIAR-215-2017 ch.1** skips printed folio `1-28` (goes from `1-27` to `1-29`).
- **AEIAR-276-2026 ch.10** already-known duplicate `10-119` was preserved.

### Unresolved Risks
- **AEIAR-175-2013:** 93 pages (5.6%) remain without verifiable folios. These are mostly figure/table pages where the PDF extraction did not capture the footer. The `absent`/`unverified` status correctly indicates this gap.
- **AEIAR-176-2013:** 14 pages (1.6%) similarly lack verifiable folios.
- No manual visual inspection was performed on the new reports. All verification was machine-based against extracted text.

---

## 3. Executive Summary URLs

| Report | English URL | Chinese URL | Status |
|--------|-------------|-------------|--------|
| AEIAR-274-2026 | `.../es/es_eng.pdf` | `.../es/es_chi.pdf` | ✅ Verified |
| AEIAR-261-2024 | `.../ES/ES_eng.pdf` | `.../ES/ES_chi.pdf` | ✅ Verified |
| AEIAR-175-2013 | `.../es/pdf/es-e.pdf` | `.../es/pdf/es-c.pdf` | ✅ Verified |
| AEIAR-176-2013 | `.../PDF/ES/ES 20130617_combined_clear v2.pdf` | `.../pdf_1/ES 20131025_Final (Chinese)_combined.pdf` | ✅ Verified |
| AEIAR-203-2016 | `.../ES/Eng/ES (Eng).pdf` | `.../ES/Chi/ES (Chi).pdf` | ✅ Verified |
| AEIAR-215-2017 | `.../Executive Summary - Eng/REP-00_EIA_Executive Summary_clean_revised.pdf` | `.../Executive Summary - Chi/REP-228228-00_EIA_行政摘要_clean_revised.pdf` | ✅ Verified |

All 6 new reports have both English and Traditional Chinese executive summary PDFs linked from their official EPD report index pages.

---

## 4. Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| `app.py` | 32 | ✅ Pass |
| `stage1/test_passages.py` | 26 | ✅ Pass |
| `stage1/test_rare_term_gate.py` | 19 | ✅ Pass |
| **Total** | **77** | **✅ All Pass** |

### Test Updates Made
- `stage1/test_passages.py`: Updated `null_pages` assertion from `> 3000` to `> 100` (reflects improved page-label extraction)
- `stage1/test_rare_term_gate.py`: Updated corpus count from 1293 to 6899; replaced `spoonbills` fold test with `monitorings`; replaced `quantum` with `nanotechnology` in all-oov test

---

## 5. End-to-End Query Examples

### Query: `noise barrier` scoped to AEIAR-274/2026 (needs_review)
```
refused: False
evidence: 3
  1. aeiar-274-2026 Ch.4 4-15 (verified)
  2. aeiar-274-2026 Ch.4 4-40 (verified)
```

### Query: `noise barrier` scoped to AEIAR-175/2013 (historical)
```
refused: False
evidence: 3
  1. aeiar-175-2013 Ch.4 4-77 (verified)
     citation: [aeiar-175-2013 · Ch.4 NOISE · §4.9.2.1 · p.4-77 · PDF idx 76 ...]
  2. aeiar-175-2013 Ch.4 4-72 (verified)
```

### Query: `noise barrier` unscoped (all reports)
```
refused: False
evidence: 3
reports found: {'aeiar-215-2017', 'aeiar-276-2026', 'aeiar-261-2024'}
  1. aeiar-276-2026 Ch.4 4-28 (verified)
  2. aeiar-261-2024 Ch.4 4-34 (verified)
  3. aeiar-215-2017 Ch.5 5-37 (verified)
```

### Query: `geothermal` (OOV refusal)
```
refused: True
gate: all_oov
message: The reports do not contain information about "geothermal"...
evidence: 0
```

### Query: `噪音屏障` (Chinese mapped)
```
refused: False
translation_applied: True
mapped_terms: ['noise', 'barrier']
evidence: 3
  1. aeiar-276-2026 Ch.4 4-28 (verified)
  2. aeiar-261-2024 Ch.4 4-34 (verified)
```

---

## 6. Files Changed

### Modified
- **`stage0/reports.json`** — Added executive summary URLs (EN + ZH) for all 6 new reports; added `page_numbering`, `page_numbering_note`, `page_numbering_anomalies` fields; updated `exec_summary_status`
- **`stage1/test_passages.py`** — Updated `null_pages` assertion threshold
- **`stage1/test_rare_term_gate.py`** — Updated corpus count, fold test term, all-oov test term
- **`static/index.html`** — Removed obsolete "text not yet searchable" note from `renderReportList()`
- **81 `.pages.jsonl` files** in `stage1/data/` — Re-analyzed page labels for AEIAR-175-2013, AEIAR-176-2013, AEIAR-215-2017

### Added
- None

### Preserved
- `stage0/core_nm_inventory.json`
- `CORE_NM_AUDIT_REPORT.md`
- All source PDFs
- Original 34 `.pages.jsonl` files for AEIAR-276-2026 and AEIAR-271-2025

---

## 7. Known Limitations

1. **No manual visual inspection** was performed on the 6 new reports. All page-number verification was machine-based against extracted text.
2. **AEIAR-175-2013 and AEIAR-176-2013** have ~5% of pages without verifiable printed folios (mostly figure/table pages).
3. **AEIAR-215-2017** has documented publishing anomalies (skipped folio 1-28; ch.11 numbering reset).
4. **Synthesis** (`LLM synthesis` from earlier work) is not present in the current `app.py`. The evidence-only response mode is fully functional.
5. **Project geometry** remains deferred for all reports.

---

## 8. How to Run

```bash
cd /Users/chloeyan/workbuddy-ai/NORTHWISE
python3 app.py --port 8080
```

Open `http://localhost:8080/` in a browser. All 8 reports are searchable with verified page labels where available.
