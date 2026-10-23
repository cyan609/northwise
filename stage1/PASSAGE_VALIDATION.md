# Passage-Level Visual Validation Report

**Scope:** 30 passages visually inspected against rendered source PDFs out of 4,161 total passages.  
**Date:** 2026-10-18  
**Inspectors:** Automated sampling + human (assistant) visual review.  
**Method:** Stratified random sample rendered via `render_page.js` (PDFKit/macOS JXA) at 2× scale; each passage text compared to its PNG.

> ⚠️ **Limitation statement:** Only 30 of 4,161 passages were manually inspected. The findings below are representative, not a census. No claim is made that the full corpus is verified.

---

## 1. Sampling Design

| Stratum | Count | Description |
|---------|-------|-------------|
| A — Ordinary numbered prose | 8 | Mid-chapter prose_paragraph passages with verified folios |
| B — Table-heavy / number-dense | 6 | table_fragmented, prose_page with tables, or pages without anchors |
| C — Header / footer / banner / short | 5 | list, banner page, month-footer page, repeated-header page, non_substantive |
| D — Continuation / heading / short | 4 | prose_continuation, heading_only, low_context |
| E — Ambiguous-ref / unverified-label | 4 | ambiguous_multiple_refs, absent/unverified folios |
| F — Query-driven hits | 3 | Top hit for `geothermal`, top hit for `offshore wind`, noise-table page |

All 30 samples are from distinct pages across both reports (12 × AEIAR-271/2025, 18 × AEIAR-276/2026).

---

## 2. Ledger

| # | Passage ID | Type | Stratum | Page label | Label status | PDF idx | Section ref | Ref status | Verdict | Key issue |
|---|------------|------|---------|------------|--------------|---------|-------------|------------|---------|-----------|
| 1 | `aeiar-271-2025\|c1\|p4\|s1` | prose_paragraph | A | 1-4 | verified | 4 | 1.5.5 | own | **minor_issue** | Stray table fragment (`Road Local Roads`) prepended to paragraph start; `(a)`/`(b)` sub-items flattened into running text. |
| 2 | `aeiar-271-2025\|c5\|p18\|s2` | prose_paragraph | A | 5-18 | verified | 18 | 5.7.9 | own | **pass** | Ends mid-sentence at page break; continuation correctly on next page. |
| 3 | `aeiar-271-2025\|c9\|p55\|s3` | prose_paragraph | A | 9-53 | verified | 55 | 9.8.19 | own | **pass** | Clean, complete paragraph. |
| 4 | `aeiar-271-2025\|c13\|p1\|s5` | prose_paragraph | A | 13-1 | verified | 1 | 13.2.3 | own | **pass** | Clean; banner stripped as expected. |
| 5 | `aeiar-276-2026\|c2\|p11\|s5` | prose_paragraph | A | 2-10 | verified | 11 | 2.6.3.4 | own | **pass** | Exact match. |
| 6 | `aeiar-276-2026\|c5\|p24\|s4` | prose_paragraph | A | 5-23 | verified | 24 | 5.6.2.3 | own | **pass** | Italic sub-heading (`Surface Runoff`) correctly prepended. |
| 7 | `aeiar-276-2026\|c8\|p67\|s2` | prose_paragraph | A | 8-64 | verified | 67 | 8.8.1.28 | own | **pass** | Heading (`Mammal`) correctly prepended. |
| 8 | `aeiar-276-2026\|c11\|p9\|s3` | prose_paragraph | A | 8 | verified | 9 | 11.4.1.32 | own | **minor_issue** | (a) Plain-numeric folio `8` is ambiguous across chapters; (b) Superscript footnote marker flattened → `AD220)31` (inherited extraction artifact). |
| 9 | `aeiar-276-2026\|c2\|p14\|s0` | table_fragmented | B | 2-13 | verified | 14 | — | not_detected | **minor_issue** | Table 2.2 truncated at page boundary (Cons on next page); column association recoverable only by repeated `Pros` marker; `§2.6.5.1` present in text but `section_ref` suppressed because type is `table_fragmented`. |
| 10 | `aeiar-276-2026\|c3\|p11\|s0` | table_fragmented | B | 3-7 | verified | 11 | — | not_detected | **minor_issue** | Table 3.6 header block interleaved; data rows intact and readable. |
| 11 | `aeiar-276-2026\|c4\|p13\|s0` | table_fragmented | B | 4-11 | verified | 13 | — | not_detected | **minor_issue** | Table 4.10 header column order permuted vs row order; distance value identifiable only by position at line end. |
| 12 | `aeiar-271-2025\|c3\|p40\|s0` | prose_page | B | 3-38 | verified | 40 | — | not_detected | **minor_issue** | Table 3.15 typed as `prose_page` (undetected); header badly interleaved; row data positionally coherent; no `fragmented` flag. |
| 13 | `aeiar-276-2026\|c3\|p48\|s0` | prose_page | B | 3-44 | verified | 48 | — | not_detected | **minor_issue** | Table 3.44 continuation typed as `prose_page`; header partially interleaved; lacks table caption (on previous page). |
| 14 | `aeiar-271-2025\|c7\|p7\|s0` | prose_page | B | 7-7 | verified | 7 | — | not_detected | **minor_issue** | Whole page = one passage: Table 7.4 + prose paragraph + Table 7.5. Coarse granularity by design (no numbered anchors in this chapter), but yields a heterogeneous evidence unit. |
| 15 | `aeiar-271-2025\|c15\|p0\|s0` | list | C | i | verified | 0 | — | not_detected | **fail** | TOC page: section numbers `15.2 15.3 15.4 15.6 15.7` hoisted onto one line, detached from their titles. Titles appear later without numbers. Mitigated by `list` + `fragmented` flags. |
| 16 | `aeiar-271-2025\|c15\|p1\|s1` | prose_paragraph | C | 15-1 | verified | 1 | 15.1.1.1 | own | **pass** | Clean paragraph; banner stripped. |
| 17 | `aeiar-276-2026\|c1\|p2\|s2` | prose_paragraph | C | None | absent | 2 | 1.2.1.1 | own | **pass** | `Project Background` heading correctly prepended; month footer `April 2026` stripped; `no_verified_folio` flag correct. |
| 18 | `aeiar-276-2026\|cNone\|p0\|s0` | non_substantive | C | None | unverified | 0 | — | not_detected | **pass** | Sign/disclaimer page correctly typed as `non_substantive`; entire page text preserved. |
| 19 | `aeiar-271-2025\|c10\|p10\|s0` | table_fragmented | C | 10-10 | verified | 10 | — | not_detected | **fail** | Table: all row labels (`Criteria`, `Size of affected area`, etc.) hoisted before all cell contents; cell values follow unmapped. Passage is unusable as direct evidence for any specific cell claim. |
| 20 | `aeiar-271-2025\|c15\|p2\|s0` | prose_continuation | D | 15-2 | verified | 2 | — | not_detected | **pass** | Correctly captures tail of paragraph from previous page; `page_start_continuation` flag set. `section_ref` lost because inheritance is page-scoped (known limitation). |
| 21 | `aeiar-271-2025\|c15\|p3\|s0` | prose_continuation | D | 15-3 | verified | 3 | — | not_detected | **pass** | Same as #20 — accurate continuation, no section ref. |
| 22 | `aeiar-276-2026\|c2\|p2\|s2` | heading | D | 2-1 | verified | 2 | 2.2 | own | **pass** | Clean heading-only passage; `heading_only` flag set. |
| 23 | `aeiar-276-2026\|c3\|p23\|s0` | prose_paragraph | D | 3-19 | verified | 23 | 3.5.1 | own | **minor_issue** | Very short (63 chars): heading `Identification of Environmental Impact` + `3.5.1 Construction Phase` with no paragraph body. `low_context` flag correctly set. |
| 24 | `aeiar-276-2026\|c8\|p14\|s2` | prose_paragraph | E | 8-11 | verified | 14 | 8.5.2.3 | ambiguous | **minor_issue** | Upstream extraction merged three paragraph starts (`8.5.2.3 8.5.2.4 8.5.2.5`) onto one line. Passage covers three paragraphs; `ambiguous_multiple_refs` correctly flagged. |
| 25 | `aeiar-276-2026\|c8\|p25\|s3` | prose_paragraph | E | 8-22 | verified | 25 | 8.6.3.1 | ambiguous | **minor_issue** | Same pattern as #24: `8.6.3.1 8.6.3.2 8.6.3.3` merged by extraction. Ambiguous ref flagged. |
| 26 | `aeiar-276-2026\|c1\|p3\|s1` | prose_paragraph | E | None | absent | 3 | 1.2.1.8 | own | **pass** | Exact match; month footer stripped; `no_verified_folio` flag correct. |
| 27 | `aeiar-276-2026\|c1\|p4\|s0` | prose_paragraph | E | None | absent | 4 | 1.3.1.2 | own | **pass** | Exact match; month footer stripped. |
| 28 | `aeiar-276-2026\|c7\|p52\|s2` | prose_paragraph | F | 7-51 | verified | 52 | 7.8.4.3 | own | **pass** | Retrieved for `geothermal power generation` (matches "power plants"). Passage accurate; underlined heading correctly attached. |
| 29 | `aeiar-276-2026\|c5\|p20\|s3` | prose_paragraph | F | 5-19 | verified | 20 | 5.6.1.6 | own | **pass** | Retrieved for `offshore wind` (matches "wind-blown"). Passage accurate; false-positive is a ranking issue, not segmentation. |
| 30 | `aeiar-271-2025\|c4\|p50\|s0` | prose_page | F | 4-48 | verified | 50 | — | not_detected | **minor_issue** | Noise-level table typed as `prose_page` (undetected); header scrambled; row values and notes intact. No `fragmented` flag. |

---

## 3. Summary Counts

| Verdict | Count | Rate |
|---------|-------|------|
| pass | 17 | 56.7 % |
| minor_issue | 11 | 36.7 % |
| fail | 2 | 6.7 % |

### By passage type (within sample)

| Type | Inspected | pass | minor_issue | fail |
|------|-----------|------|-------------|------|
| prose_paragraph | 17 | 12 | 5 | 0 |
| table_fragmented | 4 | 0 | 3 | 1 |
| prose_page | 4 | 0 | 4 | 0 |
| prose_continuation | 2 | 2 | 0 | 0 |
| heading | 1 | 1 | 0 | 0 |
| list | 1 | 0 | 0 | 1 |
| non_substantive | 1 | 1 | 0 | 0 |

### By stratum

| Stratum | pass | minor_issue | fail |
|---------|------|-------------|------|
| A — Ordinary prose | 7 | 1 | 0 |
| B — Table/number-dense | 0 | 6 | 0 |
| C — Header/footer/banner | 3 | 1 | 1 |
| D — Continuation/heading/short | 3 | 1 | 0 |
| E — Ambiguous/unverified | 2 | 2 | 0 |
| F — Query hits | 2 | 1 | 0 |

---

## 4. Systematic Failure Modes (with Corpus Evidence)

### 4.1 Undetected tables typed as `prose_page`
**Observation:** Pages with dense tables but no numbered paragraph anchors become single `prose_page` passages with no `fragmented` flag. The answer layer cannot know the content is tabular.

**Corpus scale:** 191 `prose_page` passages; 16 contain `"Table "` + 4-digit numbers (a crude proxy for table content). 11 contain **more than one** `"Table "` caption (heterogeneous pages like sample 14). Average `prose_page` length is 2,097 chars — too coarse for precise evidence.

**Examples:** #12 (Table 3.15), #13 (Table 3.44 continuation), #14 (Tables 7.4 + 7.5 + prose), #30 (noise-level table).

### 4.2 Table header scrambling / column permutation
**Observation:** PDFKit columnar extraction often interleaves header labels or permutes their order relative to data rows. Row values are usually intact.

**Impact:** A passage can support claims like "A001 is 272 m from the boundary" only if the reader trusts positional order; column-specific claims (e.g., "the 19th highest hourly NO2") are unreliable without visual verification.

**Examples:** #9 (repeated `Pros` acts as separator), #10 (header interleaved), #11 (column order permuted), #19 (row labels hoisted), #30 (header scrambled).

### 4.3 `section_ref` lost on non-prose passages that contain literal anchors
**Observation:** `section_ref` is computed only for `prose_paragraph`, `heading`, and `prose_continuation`. `table_fragmented` and `list` passages with a literal section anchor receive `None`.

**Corpus scale:** 46 `table_fragmented` passages carry a literal anchor but have `section_ref=None`. (20 `list` passages also do, but those are mostly TOC pages where assigning the ref would be wrong.)

**Example:** #9 contains `2.6.5.1` but `section_ref=None`.

### 4.4 Multiple paragraph starts merged by upstream extraction
**Observation:** PDFKit sometimes concatenates consecutive paragraph numbers onto one line (e.g., `8.5.2.3 8.5.2.4 8.5.2.5`). The `MULTI_REF` regex catches this and flags `ambiguous_multiple_refs`.

**Corpus scale:** 50 passages have `ambiguous_multiple_refs`; all are `prose_paragraph`.

**Examples:** #24, #25.

### 4.5 Page-break truncation of paragraphs
**Observation:** A paragraph that spans a page break is split into a `prose_paragraph` (first page, ends mid-sentence) and a `prose_continuation` (next page, starts mid-sentence). This is correct by design, but the `prose_continuation` cannot inherit the section ref because inheritance is page-scoped.

**Corpus scale:** 383 `prose_continuation` passages; 33 flagged `low_context`.

**Examples:** #2 (truncation), #20, #21 (continuation with no ref).

### 4.6 Plain-numeric folios create citation ambiguity
**Observation:** Some chapters use plain numeric folios (e.g., chapter 11 page `8`) rather than compound folios (`11-8`). The label `8` is not unique across chapters.

**Example:** #8 (`page_label='8'` in chapter 11).

### 4.7 Extraction-level text artifacts
**Observation:** PDFKit flattens superscripts (footnote markers), loses italic formatting, and merges lines in narrow table cells. These are inherited by passages and cannot be fixed by segmentation.

**Examples:** #8 (`AD220)31`), #1 (flattened `(a)`/`(b)` sub-items), #19 (row labels hoisted).

---

## 5. Concrete Correct vs Incorrect Boundary Examples

### Correct boundaries (what the segmenter gets right)
- **#3** `9.8.19`: starts exactly at the numbered anchor, ends at the paragraph boundary. No stray text before or after.
- **#6** `5.6.2.3`: italic sub-heading `Surface Runoff` is correctly prepended to the paragraph because it immediately precedes the anchor.
- **#22** `2.2`: heading-only passage is cleanly isolated; `heading_only` flag set.

### Incorrect or problematic boundaries
- **#1** `1.5.5`: starts with stray table fragment (`Road Local Roads`) because the table row is the last line before the anchor. The paragraph itself is correct, but the start boundary is polluted.
- **#19** `c10|p10|s0`: the entire table is one passage, but row labels and cell contents are completely separated within the passage text. The boundary (whole page) is correct; the *internal structure* is destroyed by extraction.
- **#14** `c7|p7|s0`: one passage covers two tables and a prose paragraph. The page boundary is correct, but the semantic boundary is far too coarse.

---

## 6. Ranked Recommendations

### R1 — Compute `section_ref` for `table_fragmented` when the anchor is a genuine paragraph start
**Evidence:** 46 `table_fragmented` passages lose a derivable ref; sample #9 is a concrete case.  
**Proposed change:** In `passages.py` `build_page_passages`, extend the ref-computation block to cover `table_fragmented`, but guard against TOC entries by requiring the anchor line to contain ≥5 words and not end with a folio-like token or dot leaders.  
**Impact:** +46 passages gain a usable section citation; zero risk of mis-citing TOC pages if the guard is strict.

### R2 — Accept undetected-table limitation; add a search-time heuristic flag
**Evidence:** 16 `prose_page` passages contain table-like content; no build-time signal was found in task (b).  
**Proposed change:** Do **not** attempt table detection at build time. Instead, when a `prose_page` passage is retrieved, prepend a lightweight check: if the passage text contains `"Table N.N"` + a line with ≥4 numeric tokens, add a transient `likely_table` caution to the citation.  
**Impact:** Low engineering cost; warns the answer layer without changing the segmenter.

### R3 — Document table-header unreliability for the answer layer
**Evidence:** Samples #9–#12, #19, #30 all show scrambled or interleaved headers.  
**Proposed change:** Add a rule to the answer-generation specification: "Do not cite column-specific values from `table_fragmented` or `prose_page` passages unless the column header mapping is visually confirmed. Prefer row-identifiable claims (e.g., 'A001 is listed at 272 m') over column-identifiable claims."

### R4 — Keep `ambiguous_multiple_refs` as a first-class caution
**Evidence:** 50 passages affected; samples #24, #25.  
**Proposed change:** No code change. Ensure the answer layer renders the `(ambiguous)` suffix in citations and treats the passage as covering multiple sections.

### R5 — Display compound citations for plain-numeric folios
**Evidence:** Sample #8 (`page_label='8'` in chapter 11).  
**Proposed change:** In `passage_citation()`, when `page_label` is a plain integer (not matching `\d+-\d+`), render as `Chapter {chapter}, p. {label}` instead of `p. {label}`.

### R6 — No action needed for TOC pages and non_substantive pages
**Evidence:** Sample #15 (TOC) is correctly typed `list` + `fragmented`; sample #18 (sign page) is correctly typed `non_substantive`.  
**Proposed change:** None. The type system is working as intended.

---

## 7. Distinguishing Visual Observations from Automated Checks

| Finding | Source | Verdict impact |
|---------|--------|----------------|
| Boundary starts at exact anchor line | Visual (PDF vs text) | #3, #5, #6, #7, #16, #17, #22, #26, #27, #28, #29 |
| Stray table fragment before anchor | Visual | #1 |
| Header/column order permuted | Visual | #9, #10, #11, #19, #30 |
| Row labels hoisted before cells | Visual | #19 |
| Multiple refs merged on one line | Visual + automated (`MULTI_REF`) | #24, #25 |
| TOC numbers detached | Visual | #15 |
| Page-break mid-sentence | Visual | #2 |
| `section_ref` missing on table_fragmented | Automated | #9 |
| `prose_page` with >1 Table caption | Automated | #14 (confirmed by visual) |
| Superscript flattened | Visual | #8 |
| Plain-numeric folio | Visual + automated | #8 |

---

## 8. Next Single Step Recommendation

**Implement R1** (compute `section_ref` for `table_fragmented` with a TOC guard). It is the smallest code change with the highest citation-quality return (46 passages). The guard prevents the mistake that would occur if the fix were applied blindly to `list` passages (TOC mis-citation). After R1, re-run the six baseline queries plus the three query-driven samples to verify that table hits now carry section citations.
