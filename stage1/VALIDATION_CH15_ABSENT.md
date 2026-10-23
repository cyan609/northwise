# Chapter 15 — absent-folio path validation

Date: 2026-10-18. Scope: **one chapter**, `eia_ch15_out.pdf` (AEIAR-276/2026,
Chapter 15 CONCLUSION). No other chapter extracted. No index, no Q&A, no LLM, no
packages.

Purpose: the three-chapter pilot left the `absent` path untested — all 374 of its
records were `verified`. This chapter was chosen because Stage 0 reports 9 of its
11 pages as having no printed folio.

## Source and integrity

| Item | Value |
|---|---|
| File | `stage0/source-data/AEIAR-276-2026/chapters/eia_ch15_out.pdf` |
| Registry | AEIAR-276/2026, chapter 15 — CONCLUSION |
| SHA-256 | `b29b0648452a91d28debcc19060e6243250102148c2f29af58de76c1da41cb47` |
| Re-verified against `reports.json` before extraction | yes, matched |
| Extraction script | `stage1/extract_pages.py` — **unmodified** |

No reproducible defect was found, so the script was not changed.

## Totals

| Measure | Value |
|---|---|
| PDF pages | **11** |
| JSONL records | **11** |
| Match | **yes** |
| Distinct labels | 2 (`15-i`, `15-ii`) |

## Machine-extracted counts

| `page_label_status` | Count | Page indices (0-based) |
|---|---:|---|
| `verified` | **2** | 0, 1 |
| `absent` | **9** | 2, 3, 4, 5, 6, 7, 8, 9, 10 |
| `unverified` | **0** | — |

Stage 0 predicted exactly this (`verified: 2, absent: 9, unverified: 0`), so the
extractor and the Stage 0 analyser agree on this chapter.

Every `absent` record has `page_label: null` (a JSON `null`, verified
programmatically, not an empty string) and a non-null `page_label_evidence`.

## Manual inspection — all 11 pages, not a sample

Every page of the chapter was rendered to PNG with `stage1/render_page.js` and
looked at directly. Because the chapter is only 11 pages, the sample is the whole
chapter.

| Idx | Machine label | Machine status | Rendered footer shows | Agrees |
|---:|---|---|---|---|
| 0 | `15-i` | verified | `15-i` + `March 2026` (TABLE OF CONTENTS page) | yes |
| 1 | `15-ii` | verified | `15-ii` + `March 2026` (List of Table / Appendices) | yes |
| 2 | `null` | absent | `March 2026` only, no folio | yes |
| 3 | `null` | absent | `March 2026` only, no folio | yes |
| 4 | `null` | absent | `March 2026` only, no folio | yes |
| 5 | `null` | absent | `March 2026` only, no folio | yes |
| 6 | `null` | absent | `March 2026` only, no folio | yes |
| 7 | `null` | absent | `March 2026` only, no folio | yes |
| 8 | `null` | absent | `March 2026` only, no folio | yes |
| 9 | `null` | absent | `March 2026` only, no folio | yes |
| 10 | `null` | absent | `March 2026` only, no folio | yes |

**11 of 11 inspected pages agree with the rendered source.** 2 labels retained,
9 correctly null.

The folio on pages 0–1 is centred between the AECOM logo and the right-aligned
date. On pages 2–10 that centre position is simply empty — the page number was
never printed, not merely failed by the extractor. This is the distinction the
`absent` status is meant to capture, and it is visible in the rendered page.

## Why `absent` and not `unverified`

The status taxonomy is load-bearing here:

- `absent` = the month-year footer **is** present, and no folio precedes it.
- `unverified` = no recognisable footer, or no extractable text at all.

All nine pages carry `March 2026`, so `absent` is the accurate status. The
extracted `page_label_evidence` for each ends in `March 2026`, which is the
evidence for that classification. Had the extractor reported `unverified`, it
would have been claiming it could not find a footer — which is false.

## Labels were not inferred

Checked deliberately, because these pages are full of folio-shaped body text:

- Page 2 body contains `Table 15.1`, `Appendix 15.1`, `Appendix 15.2`,
  `Section 14.` and `15.1.1.1`–`15.1.1.6`. None was taken as a label.
- No label was carried over from page 1, and no label was computed from
  `pdf_page_index`.
- The offset is `None` for this chapter (no numeric folio exists), so no
  arithmetic could be applied even accidentally.

## Near-miss worth recording

Page 0 is a table-of-contents page whose text ends:

```
..........................15-1 15-i March 2026
```

The TOC entry `15-1` sits immediately before the real folio `15-i`. A
"first token before the date" rule would have produced `15-1`. The last-match
rule returns `15-i`, which is correct. This is the same anchoring behaviour
proven by `s9_eco` in the pilot, now confirmed on a chapter whose only two
numbered pages are front matter.

## Consequences for citation

- 9 of 11 pages cannot be cited by page number. A citation for them must fall
  back to chapter + section (e.g. `Ch.15 §15.1.1.3`), which is what
  `stage1/PROPOSAL_CLI_QA.md` already specifies.
- `pdf_page_index` remains the only reliable page reference for this chapter, and
  it is present on every record.
- This chapter must never be used to demonstrate page-level citation, because
  most of its pages have no page label to cite.

## Issues found

**None in the extractor.** The `absent` path behaves as designed on the first
attempt, with no code change.

Two observations, neither a defect:

1. The chapter is **mostly unnumbered** (9 of 11 pages). Any future UI that
   promises "jump to page N" must handle this, since the EPD PDF viewer index and
   the printed folio diverge completely here — 2 of 11 pages have a folio and
   neither is numeric.
2. Pages 0–1 are front matter (`15-i`, `15-ii`), so the chapter has **no numeric
   folio at all**. Offset-based reasoning is impossible for it, which is a
   property of the source, not a limitation of the extractor.

## Files

Created:

- `stage1/data/eia_ch15_out.pages.jsonl` — 11 records, SHA-256
  `baf96e1824a1bce408a90add0c78d5454f4a303bfd82d88e25a6572b36920dfb`
- `stage1/VALIDATION_CH15_ABSENT.md` — this report

Preserved unchanged (re-checksummed after this work):

| File | SHA-256 (unchanged) |
|---|---|
| `stage1/data/eia_ch04_out.pages.jsonl` | `2b7559b2…` |
| `stage1/data/eia_ch08_out.pages.jsonl` | `f73e5f3c…` |
| `stage1/data/eia_ch10_out.pages.jsonl` | `6b2f72d1…` |
| `stage1/data/s9_eco.pages.jsonl` | `b89f7e91…` |
| `stage1/VALIDATION_PILOT.md` | not modified |

Also unmodified: `stage1/extract_pages.py`, `stage1/render_page.js`,
`stage0/reports.json` (`validation_status: incomplete`),
`stage0/PAGE_NUMBERING_RECONCILIATION.md`,
`stage0/source-data/page_numbering.v1_end_anchored.json`, PRD, DESIGN.

Project geometry remains deferred (`deferred_no_public_geometry`).
