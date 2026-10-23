# Text-quality audit — page-level extraction before retrieval design

Date: 2026-10-18. Scope: audit only. No chunking designed, no index, no packages,
no LLM, no Q&A. JSONL files were read, never modified.

Question: **is the extracted page text usable as retrieval evidence, especially
where tables, figures, headings and prose are interleaved?**

Short answer: prose pages are good. Table pages are not prose and must not be
treated as such. Two things need fixing before retrieval — boilerplate removal
and table-page flagging — and neither requires touching the extractor.

## Method

1. Read `BATCH_VALIDATION.md`, `STAGE1_INVENTORY.md`, and the JSONL records.
2. Measured every page: character count, line count, mean line length, share of
   short lines (<20 chars), figure/table caption counts.
3. Selected 15 pages covering the required categories, chosen from those
   measurements rather than by impression.
4. Read the extracted text of each, then rendered 4 pages to PNG with
   `stage1/render_page.js` and compared text against the actual page.

**Every page sampled is one of 1293 (1.2%).** The corpus-wide figures below are
heuristics over all 1293, not extrapolations from the sample.

## Sample

| # | Report | Ch | File | idx | `page_label` | Status | Chars | Lines | Mean line | Category / why chosen |
|---:|---|---|---|---:|---|---|---:|---:|---:|---|
| 1 | AEIAR-271/2025 | 4 | `s4_noise.pdf` | 49 | `4-47` | verified | 972 | 88 | 10.1 | Densest table-like page in corpus (93% short lines) |
| 2 | AEIAR-276/2026 | 5 | `eia_ch05_out.pdf` | 9 | `5-8` | verified | 2227 | 165 | 12.5 | Dense water-quality table, 165 lines |
| 3 | AEIAR-271/2025 | 9 | `s9_eco.pdf` | 44 | `9-42` | verified | 2258 | 187 | 11.1 | Dense species table, most lines in corpus |
| 4 | AEIAR-276/2026 | 3 | `eia_ch03_out.pdf` | 50 | `3-46` | verified | 3008 | 46 | 64.4 | Wide table with long cells (missed by short-line heuristic) |
| 5 | AEIAR-276/2026 | 10 | `eia_ch10_out.pdf` | 68 | `10-65` | verified | 1717 | 98 | 16.5 | **Previously observed mixed table/figure page** |
| 6 | AEIAR-276/2026 | 10 | `eia_ch10_out.pdf` | 2 | `10-iii` | verified | 1932 | 40 | 47.3 | List of Figures — caption-dense front matter |
| 7 | AEIAR-271/2025 | 11 | `s11_lvia.pdf` | 54 | `11-53` | verified | 4347 | 57 | 75.3 | Longest narrative page in corpus |
| 8 | AEIAR-276/2026 | 3 | `eia_ch03_out.pdf` | 40 | `3-36` | verified | 4213 | 56 | 74.2 | Long narrative |
| 9 | AEIAR-276/2026 | 15 | `eia_ch15_out.pdf` | 5 | `null` | **absent** | 3051 | 61 | 49.0 | **`page_label: null`** + table-shaped layout |
| 10 | AEIAR-276/2026 | 1 | `eia_ch01_out.pdf` | 3 | `null` | **absent** | 2900 | 81 | 34.8 | **`page_label: null`** + table fragment at page end |
| 11 | AEIAR-276/2026 | — | `eia_text_sign_page.pdf` | 0 | `null` | **unverified** | 3657 | 32 | 113.3 | Cover/legal page; only `unverified` page |
| 12 | AEIAR-276/2026 | 2 | `eia_ch02_out.pdf` | 22 | `2-21` | verified | 600 | 12 | 49.1 | Short clean narrative |
| 13 | AEIAR-276/2026 | 4 | `eia_ch04_out.pdf` | 57 | `4-55` | verified | 1041 | 20 | 51.1 | Table above heading, then prose |
| 14 | AEIAR-276/2026 | 10 | `eia_ch10_out.pdf` | 82 | `10-79` | verified | 256 | 7 | 35.7 | Near-blank page — tests "missing text" hypothesis |
| 15 | AEIAR-276/2026 | 8 | `eia_ch08_out.pdf` | 62 | `8-59` | verified | 3651 | 52 | 69.2 | Headings + section numbers + narrative |

Categories covered: dense tables (1–4), mixed table/figure (5), captions (6),
narrative (7, 8, 12, 15), headings/section refs (15, 4), `page_label: null`
(9, 10), `unverified` (11), blank (14).

## Per-page findings

**1. `s4_noise` 4-47 — dense table. Not usable as prose.**
Text is one table cell per line. Header cells and cell contents from different
columns interleave: `NSR Description` → `(1)` → `NAP ID` → `Depot at`. A narrow
column also splits a single value across lines: `OU(RDCRD)` / `-2a to` /
`OU(RDCRD)` / `-2c,`. No sentence survives. **Visually confirmed**: the page is a
10-column table where only two columns are populated.
Usable as: identifier lookup. Not usable as: quotable evidence.

**2. `eia_ch05_out` 5-8 — dense table. Not usable as prose.**
Header row collapsed onto one line (`Parameters RB1 RB2 RB3 (Beas Subzone)`),
then one value per line. Column association between value and parameter is lost;
only the ordering remains. Footnotes at the bottom survive as complete sentences.

**3. `s9_eco` 9-42 — dense table. Not usable as prose.**
Inconsistent cell handling within one page: some rows split across lines, others
merge two cells onto one line (`Corvus torquatus Collared Scops Owl`). Species
names and Chinese names are retrievable; their attributes are not attributable.

**4. `eia_ch03_out` 3-46 — wide table with long cells. Partially usable.**
Header cells concatenate into very long lines (`ASR Description AQO PA005
Proposed Private Residential atop Ngau Tam Mei Depot PA006 Proposed Fire Station
cum`). Numeric data rows at the page foot are clean and well-formed
(`1.5 - 120 57.8 - 60.5 20.1 - 21.9 10.3 - 11.2`). So values are readable but
which station/parameter they belong to is not reliably recoverable.
This page is why the "short line" heuristic alone is insufficient.

**5. `eia_ch10_out` 10-65 — mixed table + prose. Poorly usable.**
Prose sentences are broken mid-clause and interleaved with cell fragments:
`cutting, site formation` / `of tunnel section (DP` / `Item Q.1), at-grade` /
`and viaduct` / `carriageway and`. A retrieval hit here would quote a fragment.
**Visually confirmed earlier**: the table spans the page and the text order
follows columns, not reading order.

**6. `eia_ch10_out` 10-iii — List of Figures. Clean but low value.**
One caption per line, correct order, no interleaving. Fully readable. Useful as
a navigation aid; useless as evidence about impacts.

**7. `s11_lvia` 11-53 — narrative. Fully usable.**
Coherent continuous prose. Begins mid-sentence (`basis and provision of buffer
screen planting…`) and ends mid-sentence (`…including vegetation in`), because
the paragraph crosses the page boundary. This is faithful, not a defect — but it
means a page is not a self-contained passage.

**8. `eia_ch03_out` 3-36 — narrative. Fully usable.** Same boundary behaviour.

**9. `eia_ch15_out` idx 5, `page_label: null` — usable text, limited citation.**
Readable narrative inside a two-column "Environmental Issue Description" layout;
the left column label separates from its content but the right column reads
coherently. No printed folio, so citation must fall back to chapter + section.

**10. `eia_ch01_out` idx 3, `page_label: null` — prose usable, ends in a table.**
Prose is coherent until the page's final lines, which are a table fragment:
`S/YL-KTN/11, Ngau Tam Mei OZP no. S/YL-NTM/15 and San Tin Technopole OZP no.
S/STT/2`. A chunk ending here would trail into a table. Note this is the same
text that once produced a false folio (`S/STT/2`) in Stage 0.

**11. `eia_text_sign_page` idx 0, `unverified` — not evidence.**
Cover page plus a long legal disclaimer. Contains **Chinese text** (`路 政 署`,
Highways Department) — the only Chinese in the chapter corpus. The status is
`unverified` because no month-year footer sits at the page end, not because text
is missing.

**12. `eia_ch02_out` 2-21 — short narrative. Fully usable.** Complete sentences,
clean heading (`2.9 Concurrent Projects`), correct order.

**13. `eia_ch04_out` 4-55 — table above heading, then prose. Prose usable.**
Two-column table at the top, heading `Identification of Assessment Area and NSR`
below it, then prose. Text order matches visual order; the heading is **not**
misplaced. Row association in the small table is implied by adjacency only.
**Visually confirmed.**

**14. `eia_ch10_out` 10-79 — near-blank page. Faithful.**
Only one paragraph (`10.7.4 The significance thresholds…`). **Visually
confirmed**: the rest of the page is genuinely blank. This is the control case
for "missing text" — nothing is missing.

**15. `eia_ch08_out` 8-59 — narrative with headings. Fully usable.**
Headings, section numbers (`8.8.1.8`) and prose in correct order. Contains
`S/YL-NTM/15` and `S/STT/2` in body text without disturbing the folio.

## Corrections to earlier statements

Two things I previously asserted need correcting:

1. **The sign page is not empty.** I earlier described `eia_text_sign_page.pdf` as
   having "no text at all". It has 3657 characters of cover and disclaimer text.
   The `unverified` status is still correct (no footer at page end), but the
   reason I gave was wrong.
2. **No duplicated text was found.** An early preview suggested duplication on
   `eia_ch02_out` 2-21; that was an artefact of my own preview printing the first
   and last lines of a 12-line page, which overlapped. A corpus-wide scan found
   248 pages with repeated *lines* and 8 with a repeated 150-character passage;
   inspection shows these are table cells legitimately repeated across rows
   (confirmed visually on `eia_ch03_out` 3-20, where one cell repeats for rows
   14–20). **No duplicated extraction.**

## Failure patterns

| # | Pattern | Evidence | Severity |
|---|---|---|---|
| P1 | Table cells emitted one per line; row/column association lost | pages 1, 2, 3 | High for those pages |
| P2 | A single cell value split across lines (`OU(RDCRD)` / `-2a to`) | page 1 | Medium |
| P3 | Adjacent cells merged onto one line (`Corvus torquatus Collared Scops Owl`) | page 3 | Medium |
| P4 | Running header repeated on **100%** of pages; footer on all | 722/722 San Tin pages start with `Agreement No. CE 4/2024 (HY)`; boilerplate is **5.2%** of San Tin text and **2.9%** of Ngau Tam Mei text | High for retrieval |
| P5 | Sentences cross page boundaries (start/end mid-sentence) | pages 7, 8, 10 | Medium |
| P6 | Figure content absent from text; captions only in the List of Figures | page 6 | High for figure questions |
| — | **Not observed:** duplicated text, empty pages, misplaced headings | pages 11, 14, 13 | — |

Corpus-wide sizing:

- **132 pages (10.2%)** have a mean line length under 20 characters — the
  fragmentation signature.
- **36 pages (2.8%)** are extreme: ≥40 lines with ≥80% short lines.
- **0 pages** are text-empty.
- Note: a "loose" table heuristic based on line-ending punctuation gave 89.6%,
  which is meaningless — PDF text breaks lines mid-sentence. It was discarded
  rather than reported as a finding.

## Observation vs. what needed the source PDF

| Claim | Basis |
|---|---|
| Table pages interleave cells | Text observation, **confirmed visually** on `4-47`, `10-65` |
| Heading not misplaced on `4-55` | Text suspicion, **confirmed visually** |
| `10-79` is genuinely blank, not truncated | Text suspicion, **confirmed visually** |
| No duplicated text | Corpus scan, **confirmed visually** on `3-20` |
| Pages 2, 3, 4 table behaviour | **Text only** — not rendered |
| Figure content is unavailable | **Text only** — where figures physically live was not determined |

## Recommendation — minimum changes before retrieval

Only what the evidence requires. No chunking design, no index.

1. **Strip the running header and footer before chunking.** Drop leading lines
   matching the known report header and the trailing `<folio> <Month> <Year>`
   line. Removes 5.2% / 2.9% boilerplate that would otherwise match every query
   containing "Environmental Impact Assessment".
2. **Tag each page with a `text_form`** — `prose` / `table_fragmented` /
   `list` — using mean line length (<20 = fragmented) and line count. 132 pages
   need the `table_fragmented` tag. This is a labelling step, not a repair.
3. **Keep the chunk unit at one page.** Do not merge pages, because sentences
   cross boundaries (P5) and merging would silently join unrelated chapters.
   Instead, allow retrieval to expand to the adjacent page when a hit begins or
   ends mid-sentence.
4. **Prefer `prose` pages for narrative answers; for `table_fragmented` pages,
   cite the page and say the value comes from a table** rather than quoting a
   fragment as a sentence.
5. **Carry `page_label` + `pdf_page_index` into every chunk** (already available)
   and keep the existing rule that a folio alone is not unique.

Explicitly **not** recommended now: reconstructing table structure, OCR, or
cross-page sentence stitching. All three are large changes with no evidence yet
that they are needed.

## Limitations

1. 15 of 1293 pages sampled (1.2%); 5 visually compared. The 132-page fragmented
   population is estimated by heuristic and was not inspected page by page.
2. Figure location is unresolved. Chapter PDFs contain embedded images (100 in
   ch.10, 106 in ch.8), yet no body page carries a standalone figure caption and
   no page is figure-dominated. Whether figures sit in a separate volume or
   inline without captions was not determined.
3. Only the cover page contains Chinese; no Chinese body text was assessed.
4. Table *content* correctness was not checked against the source — only whether
   text order preserves row/column meaning, which it does not.

## Files

Created: `stage1/TEXT_QUALITY_AUDIT.md` (this report).

Unmodified: all 34 `stage1/data/*.pages.jsonl`, `stage1/extract_pages.py`,
`stage1/render_page.js`, `stage0/reports.json` (`validation_status: incomplete`),
PRD, DESIGN. Project geometry remains deferred.
