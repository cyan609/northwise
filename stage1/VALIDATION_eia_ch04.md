# Validation report — `stage1/data/eia_ch04_out.pages.jsonl`

Date: 2026-10-18. Step: Stage 1 extraction only (no chunking, no index, no LLM).

## Chapter selected

**`stage0/source-data/AEIAR-276-2026/chapters/eia_ch04_out.pdf`**
— AEIAR-276/2026, Chapter 4 **NOISE**, 62 pages, SHA-256
`ce4158a00a73c615cddeff93f92330cbbedcc9c9978c2616f5a8e7c9ba1887d5`.

Why this chapter:

- It uses **compound printed folios** (`4-1` … `4-59`) — the case the citation
  model has to get right.
- It also has **roman front matter** (`i`, `ii`, `iii`), so more than one folio
  form is exercised in a single file.
- It is a normal body chapter with real content, not a front-matter stub.
- It is 62 pages, large enough that an off-by-one error would be visible.

## Indexing convention

`pdf_page_index` is **0-based**, matching PDFKit's `pageAtIndex(i)`. Index `0`
is the first page of the chapter file. The convention is stated in the script
docstring and in every record.

## Record shape

Each line contains exactly the required fields plus `chapter_title`:

```
report_id · chapter · chapter_title · pdf_page_index · page_label ·
page_label_status · page_label_evidence · text · source_pdf · source_sha256
```

- `text` is stored exactly as PDFKit returned it. Whitespace is normalised only
  on a throwaway copy used for footer matching, so the stored text is not altered.
- `page_label_evidence` keeps the last 140 characters of the page text, so a
  label can be audited without reopening the PDF.

## Results

| Check | Result |
|---|---|
| Records written | **62** |
| PDF page count | **62** — **match** |
| `page_label_status` | `verified: 62`, `absent: 0`, `unverified: 0` |
| Distinct labels | 62 (no duplicates) |
| Label sequence | `i`, `ii`, `iii`, then `4-1` … `4-59` |
| Contiguity | body labels are exactly 1…59 — **no gaps** |
| Offset (index − printed page) | constant `2` for all 59 body pages |
| Label present in its own evidence | 62 / 62 |
| File size | 165,632 bytes, 130,870 characters of text |

**First, middle and last pages**

| Index | Label | Status | Footer evidence (tail) |
|---|---|---|---|
| 0 | `i` | verified | `… 4-58 i March 2026` |
| 31 | `4-29` | verified | `… Figure 4.3. 4 4-29 March 2026` |
| 61 | `4-59` | verified | `… proposed fixed noise sources. 4-59 March 2026` |

No extraction failures. No ambiguous labels in this chapter.

## Two bugs found during validation (and fixed)

Both were found by cross-checking the output against the PDF rather than
trusting the first run.

**1. Missing folios that were actually present.** The first run reported 59
verified and 3 `unverified` (indices 49, 52, 55). Inspection showed those pages
*do* print `4-47`, `4-50`, `4-53` — but each is followed by a stray character
`4` after the footer, which defeated an end-anchored regex.

> The trailing `4` is unexplained. It is not a folio and is not interpreted; it
> is simply tolerated so the real folio is still found.

Fix: the pattern no longer requires the footer to be the last thing on the page,
but still anchors the folio to the month-year and only searches the last 240
characters, so a date quoted in body text cannot be mistaken for the footer.

**2. A body number read as a folio.** Testing the `absent` branch on chapter 1
produced label `2` for page index 3 — taken from `S/STT/2` in body text, not
from a folio.

Fix: a lookbehind requires the folio not to be preceded by a word character,
slash, hyphen or dot. A real folio never is.

After both fixes: chapter 4 is 62/62 verified and the sequence is contiguous.

## The `absent` branch was tested, not assumed

Chapter 4 happens to have no unnumbered pages, so the null path was exercised on
**chapter 1** instead (written to `/tmp`, not shipped as a deliverable):

| Result | Value |
|---|---|
| Records | 7 / 7 pages |
| `verified` | 2 (`1-1-i`, `1-1-ii`) |
| `absent` | 5 (indices 2–6, footer date present, no folio) |
| `unverified` | 0 |

That is the behaviour the requirement asks for: no folio → `page_label: null`,
status `absent`, evidence retained, nothing inferred.

## Discrepancy with Stage 0 — found here, then fixed there

When this chapter was first extracted, the extractor disagreed with
`stage0/source-data/page_numbering.json`:

| Chapter | Stage 0 `pages_with_folio` (old) | This extractor | Cause |
|---|---|---|---|
| ch.4 NOISE | 59 | **62** | Stage 0's end-anchored regex missed 3 folios |
| ch.1 INTRODUCTION | 4 | **2** | Stage 0 counted 2 false positives (`2` from `S/STT/2`, plus one more) |

That disagreement is what prompted the approved re-run of the Stage 0 analyser.
**Stage 0 has since been re-run with the corrected matcher and now agrees with
this extractor**: ch.4 = 62/62 verified, ch.1 = 2 verified + 5 `absent`.

Full before/after comparison, including two further defects found during that
re-run (chapter-roman folios such as `15-i`, and three-digit page parts such as
`8-100`), is in `stage0/PAGE_NUMBERING_RECONCILIATION.md`. `reports.json` still
carries `validation_status: incomplete`: the re-run corrected counts, it did not
complete Stage 0.

Re-verified after the matcher changes: re-extracting this chapter produces a
**byte-identical** file (SHA-256
`2b7559b2b804de345f227b0d87841f90560d20833f015a3c5f8200f86bd1b560`), so this
deliverable is unaffected by the later fixes.

## Known limitations

- Text order comes from PDFKit, so table cells can interleave with prose. This
  affects readability of table-heavy pages, not the folio detection.
- A folio is `verified` only because it was read off that page's own footer.
  Pages with no footer stay `null`; nothing is calculated from neighbours.
- **A printed folio is not a unique page identifier.** The Stage 0 re-run found
  that `eia_ch10_out.pdf` prints `10-119` on two different pages, and that
  `s12_cultural_heritage.pdf` never prints `12-23`. Citations must therefore
  carry `pdf_page_index` alongside the folio — which is why both fields exist in
  every record here.
- Only one chapter has been extracted. The other 33 chapter files are untested
  by this script.
