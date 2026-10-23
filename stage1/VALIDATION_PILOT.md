# Pilot validation report — three additional chapters

Date: 2026-10-18. Scope: **three chapters only**. The remaining 30 chapter files
are not extracted. No index, no Q&A, no LLM, no packages.

## Why these three

Chosen from `stage0/STAGE0_INVENTORY.md` to test the three failure classes that
the Stage 0 reconciliation exposed. Each chapter has one primary job, so a
failure is attributable rather than ambiguous.

| # | Report ID | Ch | Title | File | Pages | Primary purpose |
|---|---|---|---|---|---|---|
| 1 | AEIAR-276/2026 | 8 | ECOLOGY | `eia_ch08_out.pdf` | 124 | **Three-digit folios** `8-100`…`8-120`, plus `chapter-roman` front matter `8-i`…`8-iv`. This is the exact case that broke v1 (read `100` as a plain folio) and v2b (rejected it entirely). |
| 2 | AEIAR-271/2025 | 9 | ECOLOGICAL IMPLICATION (TERRESTRIAL AND AQUATIC) | `s9_eco.pdf` | 113 | **Table-of-contents noise.** p.0 is a two-part contents page (sections + `LIST OF TABLES`) carrying ~39 `9-nn` references while its own footer folio is `i`. |
| 3 | AEIAR-276/2026 | 10 | LANDSCAPE AND VISUAL IMPACT | `eia_ch10_out.pdf` | 137 | **Known duplicate folio.** `10-119` is printed on two different pages. Tests whether page identity survives when the folio does not. |

Rejected candidates, and why:

- `s3_aq.pdf` — its 112 folio-like tokens on p.44 are air-quality table values,
  not contents entries. Numeric noise, not TOC noise.
- `s12_cultural_heritage.pdf` — its skipped `12-23` is the weaker anomaly. A gap
  does not threaten citation uniqueness the way a duplicate does. **Left untested.**

## Method

- Extraction reuses `stage1/extract_pages.py` **unchanged**. No code change was
  needed, which is itself a result: the pilot did not require matcher edits.
- Each file's SHA-256 is re-verified against `stage0/reports.json` before
  extraction; a changed file would have been refused.
- Schema is byte-for-byte the approved one (10 fields), verified identical
  across all four JSONL files:
  `report_id · chapter · chapter_title · pdf_page_index · page_label ·
  page_label_status · page_label_evidence · text · source_pdf · source_sha256`
- `pdf_page_index` remains **0-based** (PDFKit `pageAtIndex`).
- No folio was inferred from arithmetic, the page index, or a neighbouring page.

### New verification tool

`stage1/render_page.js` renders one PDF page to PNG through PDFKit so a label can
be checked by **looking at the page**. It is a verification tool only — it is not
on the extraction path and writes nothing into the JSONL.

Control test: rendering `eia_ch04_out.pdf` p.0 shows footer `i` / `March 2026`,
matching the already-approved extraction.

## Results

| Chapter | Records | PDF pages | Match | verified | absent | unverified | Distinct labels | Duplicates | Missing numbers | Offset | Three-digit folios |
|---|---:|---:|---|---:|---:|---:|---:|---|---|---|---:|
| `eia_ch08_out.pdf` | 124 | 124 | **yes** | 124 | 0 | 0 | 124 | none | none | 4 | 21 |
| `s9_eco.pdf` | 113 | 113 | **yes** | 113 | 0 | 0 | 113 | none | none | 3 | 11 |
| `eia_ch10_out.pdf` | 137 | 137 | **yes** | 137 | 0 | 0 | **136** | **`10-119`** | none | **4 and 5** | 34 |

Totals: 374 records over 374 pages, 0 extraction failures.

All three sequences are internally consistent with the page counts:

- ch.8: 4 roman (`8-i`…`8-iv`) + `8-1`…`8-120` = 124
- ch.9: 3 roman (`i`…`iii`) + `9-1`…`9-110` = 113
- ch.10: 4 roman (`10-i`…`10-iv`) + `10-1`…`10-132` = 136 distinct, **137
  records** because one number is printed twice

## Machine-extracted vs manually verified

`page_label_status: verified` means *the extractor read a folio off that page's
own footer*. It is **not** the same claim as "a human checked this page". The
table separates the two.

| Chapter | `pdf_page_index` | Machine label | Manually verified on rendered page | Agree |
|---|---:|---|---|---|
| ch.8 | 0 | `8-i` | `8-i` (TOC page) | yes |
| ch.8 | 62 | `8-59` | `8-59` | yes |
| ch.8 | 103 | `8-100` | `8-100` | yes |
| ch.8 | 123 | `8-120` | `8-120` (last page) | yes |
| ch.9 | 0 | `i` | `i` (TOC + LIST OF TABLES page) | yes |
| ch.9 | 56 | `9-54` | `9-54` | yes |
| ch.9 | 112 | `9-110` | `9-110` (last page) | yes |
| ch.10 | 0 | `10-i` | `10-i` (TOC page) | yes |
| ch.10 | 68 | `10-65` | `10-65` | yes |
| ch.10 | 122 | `10-119` | `10-119`, footer month `March 2026` | yes |
| ch.10 | 123 | `10-119` | `10-119`, footer month `April 2026` | yes |
| ch.10 | 136 | `10-132` | `10-132` (last page) | yes |

**12 of 12 manually verified labels agree with the machine.** First, middle and
last pages were checked for every chapter, plus the specific pages each chapter
was chosen to stress. The other 362 records are machine-extracted only.

## What each test actually proved

**1. Three-digit folios (ch.8, and ch.10 as a second sample).**
`8-100` is labelled `8-100`, not `100` and not `absent`. 21 three-digit folios in
ch.8 and 34 in ch.10 all resolved as `compound`. Manually confirmed on rendered
p.103 and p.104-adjacent pages.

**2. TOC noise (ch.9).**
p.0 contains `9-1` … `9-76` in dot-leader entries. The extractor returned `i`,
the real footer folio, because the match is anchored to the token immediately
before the month-year and the **last** such match wins. A naive "first folio-like
token" or "largest number" rule would have produced `9-1` or `9-76`. This is the
strongest evidence in the pilot that the anchoring rule does real work.

**3. Duplicate folio (ch.10).**
`10-119` appears twice, on `pdf_page_index` 122 and 123, with different footer
months (`March 2026` vs `April 2026`). The extractor **preserved both records**
rather than deduplicating, and `pdf_page_index` keeps them distinguishable. The
offset reading `4 and 5` is the direct, expected consequence of one extra page in
the sequence — not a matcher fault.

This confirms the citation rule already in `stage1/PROPOSAL_CLI_QA.md`: a folio
alone is ambiguous, so every citation must carry `pdf_page_index`.

## Anomaly handling — deliberate non-correction

The source PDF has a duplicate folio. Nothing was "fixed":

- No record was dropped.
- No label was renumbered.
- No offset was applied to make the sequence look contiguous.

A continuous sequence is **not** a validation requirement when the source itself
is discontinuous. The requirement is that the output faithfully represents the
source, which it does.

## What this pilot does NOT cover

Stated plainly, because the selection was deliberately hard but not exhaustive:

1. **No pilot chapter exercises the `absent` path.** All 374 records are
   `verified`; there are 0 `absent` and 0 `unverified` records here. The null
   branch is still evidenced only by the earlier ch.1 test (2 verified, 5 absent).
   A chapter with genuinely unnumbered pages (San Tin ch.15, 9 absent) has not
   been run through the extractor.
2. **`s12_cultural_heritage.pdf`'s skipped `12-23` remains untested.**
3. **Text quality on figure-heavy pages is not assessed.** Table cells can
   interleave with prose because text order comes from PDFKit. Visible on ch.10
   p.68, where a table spans the page. This affects readability, not folio
   detection, but it will matter for retrieval and must be measured before Q&A.
4. **No Chinese-language chapter exists to test** — the chapter files are
   English-only as published (documented in Stage 0).

## Files

Created:

- `stage1/data/eia_ch08_out.pages.jsonl` — 124 records
- `stage1/data/s9_eco.pages.jsonl` — 113 records
- `stage1/data/eia_ch10_out.pages.jsonl` — 137 records
- `stage1/render_page.js` — page-to-PNG verification tool
- `stage1/VALIDATION_PILOT.md` — this report

Not modified: `stage1/extract_pages.py`, `stage1/data/eia_ch04_out.pages.jsonl`
(still SHA-256 `2b7559b2b804de345f227b0d87841f90560d20833f015a3c5f8200f86bd1b560`,
re-checked after this batch), `stage0/reports.json`
(`validation_status: incomplete`), `stage0/PAGE_NUMBERING_RECONCILIATION.md`,
`stage0/source-data/page_numbering.v1_end_anchored.json`, PRD, DESIGN.

Project geometry remains deferred (`deferred_no_public_geometry`).
