# Proposal — Stage 1: local command-line Q&A prototype

Status: **for review, not approved.** Nothing in this document has been implemented.
Date: 2026-10-18. Author: assistant, for the NORTHWISE project owner.

Scope of this proposal: the smallest practical step that turns the downloaded
official EIA PDFs into a working question-and-answer loop in a terminal, with
citations a reader can check against the original EPD file.

---

## 0. What already exists (inspected before writing this)

| Artefact | State |
|---|---|
| `PRD_EIA_Map_Assistant.md`, `DESIGN.md` | Approved. **Will not be modified.** |
| `stage0/source-data/` | 38 official PDFs, 27.0 MB, SHA-256 recorded and re-verified |
| `stage0/source-data/page_numbering.json` | Per-chapter page-count, folio counts, folio forms, offsets |
| `stage0/reports.json` | 2 reports, 34 chapter entries; `validation_status: incomplete` (geometry deferred by decision) |
| `stage0/STAGE0_INVENTORY.md` | Full evidence trail, exit-criteria status |

Two facts from Stage 0 drive every decision below:

1. **Printed folios are compound and are not the viewer index.** San Tin uses
   `4-1`, `2-i`, `1-1-i`; Ngau Tam Mei uses `4-1`, `i`. Offsets vary per chapter
   (1–5). Any citation that derives a page number by arithmetic will be wrong.
2. **Some pages have no printed folio at all** — San Tin ch.1 pp.3–7 and ch.15
   pp.3–11. A citation model that assumes every page has a number will silently
   fabricate one.

---

## 1. How the prototype searches the downloaded chapters

**Page-first extraction, then page-level chunks.** No embeddings, no vector
database, no packages.

```
PDF  →  per-page text  →  chunks (one per page, split if very long)  →  lexical index
```

- **Extraction** reuses the working Stage 0 approach: macOS PDFKit through
  JavaScript for Automation (`stage0/tools/pdf_pages.js`), writing one JSONL
  record per page. This already works on all 38 files.
- **Chunking** is per page rather than per section. These chapters run roughly
  2,500–3,200 characters per page (≈400–500 words), which already sits inside
  the PRD's 500–800-word target. Page-based chunks keep the citation honest: a
  chunk can always name the exact page it came from, and splitting at section
  headings is then a refinement rather than a prerequisite.
- **Section attribution** uses a heading regex over page text, with the TOC
  pages excluded (they match the same pattern and produced 220 false candidates
  in a probe of San Tin ch.4). Where no heading is detected, `section_ref` is
  `null` and `section_ref_status` is `"not_detected"` — it is not invented.
- **Index** is a plain BM25 table over chunk tokens (English lowercased,
  stop-worded, numbers preserved), written to a JSON file. Chinese query terms
  are expanded through a small glossary before scoring (see §6).

Why lexical and not embeddings: the prototype must be auditable, and a BM25 hit
can be explained to a reviewer in one sentence. The PRD already anticipates
tuning retrieval at Stage 5; switching to embeddings later changes one module,
not the citation model.

**Retrieval filters, in order:** `report_id` (if the user has scoped a report) →
topic/chapter filter (if a shortcut was used) → BM25 top-k = 8 → drop chunks
from pages already represented twice (so one noisy page cannot fill the context).

---

## 2. How answers stay grounded in retrieved text

The model never sees the corpus, only the retrieved chunks, and it must return
structured output:

```json
{ "answer": "...", "citations": ["aeiar-276-2026:ch04:p41:c003"], "refused": false }
```

Three gates, in order:

1. **Prompt contract.** System prompt states: use only the supplied chunks; every
   factual sentence carries at least one chunk id; if the chunks do not answer
   the question, refuse. No outside knowledge, no inference about impacts.
2. **Citation validation.** Every returned chunk id must exist in the retrieved
   set. A citation to a chunk that was not retrieved is a hard failure.
3. **Uncited-claim check.** If a non-boilerplate sentence carries no citation,
   one repair attempt is made; a second failure becomes a refusal, not a
   partially-cited answer.

The answer is rendered only after all three pass. This mirrors the PRD's answer
flow and its rule that an answer with no valid citation is not shown.

---

## 3. Citation model

Each citation is a single line, and every field is stored, not recomputed:

```
[AEIAR-276-2026 · Ch.4 NOISE · §4.3.2 · p.4-12 (PDF p.41) · verified]
```

| Field | Source | Rule |
|---|---|---|
| `report_id` | registry | stable key |
| `chapter_number` / `chapter_title` | EPD chapter list | verbatim |
| `section_ref` | heading regex on page text | `null` + `section_ref_status` if not detected |
| `page_label` | **the folio printed on that page** | never derived from the index |
| `page_label_parts` | split of the label, e.g. `{chapter: 4, page: 12}` | verbatim parts |
| `pdf_page_index` | position in the chapter file | always known |
| `page_verified` | `true` only if a folio was read off that page | absent folio → `false` |
| `anchor_url` | `file_url + "#page=" + pdf_page_index` | deep link to the EPD file |

**Compound labels.** The label is copied as a string and additionally split into
parts, because `4-12` means chapter 4, page 12 — not page 412 and not page 12 of
the file. The split is recorded so a future map or PDF link never has to parse
it again.

**Pages with no folio.** The citation omits the page rather than guessing:

```
[AEIAR-276-2026 · Ch.15 CONCLUSION · §15.2 · no printed folio (PDF p.7)]
```

`page_verified: false` in the data, and the rendered chip shows only chapter and
section. This is exactly the PRD's rule: an unverified page number is never
presented as verified.

---

## 4. Refusal

Refusal is a first-class outcome, produced by three independent gates so no
single failure can produce a confident wrong answer:

| Gate | Trigger | Message |
|---|---|---|
| Retrieval floor | best BM25 score below threshold | "These reports don't appear to cover that." + nearest chapter by score |
| Citation failure | validation in §2 fails twice | same, with the near-miss chapter |
| Model refusal | the model returns `refused: true` | model's reason, normalised to house wording |

The refusal names the **nearest chapter and page it did find**, so the user
leaves with a lead rather than a dead end — the behaviour the PRD specifies and
DESIGN's refusal card already describes.

Out-of-scope questions (policy, prediction, "should they build it") are refused
by prompt rule, not by retrieval score, because a high-scoring chunk could
otherwise tempt the model into opinion.

---

## 5. English and Traditional Chinese

The report body is **English only** — verified in Stage 0: the `/tc/` chapter
lists return 404 and the Chinese project pages link to the English report index.
Only the executive summaries exist in Chinese.

So:

- **Questions in Traditional Chinese** are handled by expanding query terms
  through a hand-maintained bilingual glossary (noise/噪音, ecology/生態,
  water quality/水質, air quality/空氣質素, cultural heritage/文物, landfill
  gas/堆填氣體, …). Retrieval then runs on English terms, and every expansion is
  logged so a reviewer can see why a chunk was retrieved.
- **Answers are written in the language of the question.** A Chinese answer is
  generated from English chunks by the model.
- **Every Chinese answer carries a fixed notice**, shown above the text:
  「報告正文只有英文版。以下中文內容是根據英文原文整理，並非官方中文譯本。」
  ("The report body is in English only. This Chinese text is prepared from the
  English original; it is not an official Chinese translation.")
- **Quoted evidence stays in English**, with the Chinese rendering alongside, so
  the reader can always see the wording the citation actually points at.
- The app never claims, implies, or formats anything as an official Chinese
  translation of the report body.

This is the honest position the PRD's F7 (interface language) and F4 (citations)
allow: the interface is bilingual; the source document is not.

---

## 6. Files this step would create

Nothing in `PRD_EIA_Map_Assistant.md`, `DESIGN.md` or `stage0/reports.json` is
modified.

| File | Purpose |
|---|---|
| `stage1/extract_pages.py` | PDF → `stage1/data/pages.jsonl` (one record per page: report, chapter, folio, folio_status, pdf_page_index, text) |
| `stage1/build_index.py` | pages → `stage1/data/chunks.jsonl` + `stage1/data/index.json` (BM25) |
| `stage1/ask.py` | CLI: question in, cited answer or refusal out |
| `stage1/config.json` | LLM endpoint/model (OpenAI-compatible), top-k, refusal threshold, glossary path |
| `stage1/glossary_zh_en.json` | the bilingual expansion list, human-editable |
| `stage1/README.md` | how to run it, and its known limits |

Estimated size: ~600 lines of Python total, standard library only.

**Dependency check:** none. HTTP to the model uses `urllib`. PDF text uses the
existing PDFKit bridge. If a dependency turns out to be unavoidable, I will stop
and ask before installing, per the standing rule.

---

## 7. Acceptance checks for this step (PRD Stage 1: "10 manual checks")

1. A question answerable from one chapter returns a citation with a **compound**
   label (`4-12`) and the correct PDF index.
2. The same question scoped to the other report does not return the first
   report's text.
3. A question about a topic only in San Tin, asked of Ngau Tam Mei, refuses.
4. A question about page 7 of San Tin ch.15 cites **no printed page** and says so.
5. A Chinese question retrieves the right English chunks and answers in Chinese
   with the fixed notice attached.
6. A policy question ("should the government build this?") refuses.
7. A question with a fabricated premise ("the 2019 EIA says…") refuses.
8. Every citation's `pdf_page_index` opens the right page in the EPD PDF.
9. No answer contains a citation id that was not retrieved.
10. Re-running extraction on the same PDF produces byte-identical `pages.jsonl`.

Check 10 is the one that catches silent drift in the folio parser.

---

## 8. Remaining blockers and risks

| Item | Status | Effect on this step |
|---|---|---|
| **Project geometry** | Deferred by decision: no public OZP geometry; CSDI/SPP3 token-gated | **None.** Q&A does not need geometry. `reports.json` stays `incomplete`; Stage 0 is not marked complete. |
| **`section_ref` extraction** | Heuristic; probe found headings but with TOC noise | Citations fall back to chapter + page where detection fails. Will be validated on a sample before any answer is trusted. |
| **`page_verified`** | Only `true` where a folio exists (San Tin ch.1/ch.15 have gaps) | Those pages cite chapter + section only. |
| **LLM endpoint and key** | **Needed from you** | The CLI cannot run without an endpoint. It will be read from `stage1/config.json`; I will not hardcode or guess one. |
| **Chinese retrieval quality** | Unknown until measured | Glossary expansion is a bridge, not a solution; it is the first thing Stage 5 evaluation should test. |
| **Tables and figures** | Excluded by PRD scope | Extracted text may contain table debris; the prompt tells the model not to reason over broken tables. |

---

## 9. What this step deliberately does not do

- No embeddings, no vector database (explicitly excluded until you approve).
- No web UI, no map, no UI implementation of the map styling decisions — those
  belong to Stage 2/3 and will be expressed in code and CSS at that point, not by
  editing `DESIGN.md`.
- No package installation.
- No change to the approved PRD or DESIGN.
- No marking of Stage 0 as complete.

---

## 10. The decision requested

Approve, reject, or amend **§6 (files)** and **§1 (page-level chunks instead of
section-level chunks)**. Those are the two choices that shape everything else.

If approved, the first deliverable is `extract_pages.py` plus its `pages.jsonl`
output for one chapter, so you can inspect the page/folio records before any
indexing or model call happens.
