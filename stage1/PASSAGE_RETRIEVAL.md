# Stage 1 — Paragraph-level Passages

**Status:** implemented, tested, evaluated. Awaiting review.
**Date:** 2026-10-18
**Corpus:** 1,293 pages / 34 chapters / 2 reports — unchanged.
**Runtime:** Python 3.13 standard library only. No packages, no embeddings, no model, no network.

The page-level retriever is untouched and remains the baseline
(`python3 stage1/retrieve.py`). This adds a layer above it; it does not replace it.

---

## 1. Files

| File | Purpose |
|---|---|
| `stage1/passages.py` (585 lines) | Segmentation, passage index, CLI. Imports `retrieve.py`; never modifies it. |
| `stage1/test_passages.py` (216 lines) | 21 deterministic tests. |
| `stage1/eval_levels.py` (70 lines) | Side-by-side page vs passage comparison for the query set. |
| `stage1/PASSAGE_RETRIEVAL.md` | This report. |

Verified unchanged after all work:

- `stage1/retrieve.py` — SHA-256 `eafc264c…` (identical to the hash recorded when
  the OOV gate was signed off). The page-level baseline is byte-for-byte intact.
- 34/34 `stage1/data/*.pages.jsonl` — byte-identical.
- The five validated outputs still hash to `2b7559b2…` (ch04), `f73e5f3c…` (ch08),
  `6b2f72d1…` (ch10), `baf96e18…` (ch15), `b89f7e91…` (s9_eco).
- `stage1/test_rare_term_gate.py` — 19/19 still pass.
- `stage0/reports.json` still `incomplete`; geometry still deferred; PRD/DESIGN and
  `extract_pages.py` untouched (mtimes predate this task).

---

## 2. Passage schema

One JSON object per passage.

| Field | Type | Meaning |
|---|---|---|
| `passage_id` | str | `"<report_id>\|c<chapter>\|p<pdf_page_index>\|s<ordinal>"` |
| `passage_ordinal` | int | 0-based within the page |
| `passage_type` | enum | `prose_paragraph`, `prose_page`, `prose_continuation`, `heading`, `table_fragmented`, `list`, `non_substantive`, `blank` |
| `quality_flags` | list | `low_context`, `fragmented`, `near_blank`, `no_verified_folio`, `page_start_continuation`, `heading_only` |
| `text` | str | passage text, header/footer/banner removed |
| `char_len`, `line_count` | int | size of the passage |
| `section_ref` | str \| null | literal `N.N…` at the start of a line **within this page**; never carried across pages |
| `section_ref_status` | enum | `own`, `inherited_within_page`, `ambiguous_multiple_refs`, `not_detected` |
| `report_id`, `report_title` | str | from the registry |
| `chapter`, `chapter_title` | int, str | from the record |
| `pdf_page_index` | int | **0-based**, copied unchanged from the record |
| `page_label` | str \| null | copied unchanged; null stays null |
| `page_label_status` | enum | `verified`, `absent`, `unverified` — copied unchanged |
| `page_label_verified` | bool | derived: `status == "verified"` |
| `line_start`, `line_end` | int | line range within the cleaned page text |
| `source_pdf`, `source_sha256` | str | from the record |
| `page_text_sha256` | str | SHA-256 of the **original** record `text` |
| `page_boilerplate_removed` | dict | counts of header lines, folio footer, month footer, banner, repeated header |

**Provenance is checkable in one step.** `page_text_sha256` proves which source
record the passage came from without trusting this file, and
`text == cleaned_lines[line_start:line_end]` is asserted by a test.

Context expansion, when requested with `--expand`, is returned in a separate
`context` object holding `prev`/`next` with their own `page_label`,
`pdf_page_index`, `source_pdf`. **It is never merged into `text`.**

---

## 3. Segmentation rules

Segmentation splits only where the document itself supplies a literal marker.
It never guesses a paragraph break from punctuation, line length or layout.

1. **Clean the page.** Reuse `retrieve.strip_boilerplate` (leading header, folio
   footer), then remove three things it does not cover:
   - a bare `Month YYYY` footer on pages with no folio (it survived because the
     footer rule requires a folio before the month);
   - a chapter banner at the top (`NOISE`, `4 NOISE`, `ECOLOGY`, `AIR QUALITY`);
   - a **repeated header anywhere on the page** — 110 pages carry
     `Agreement No. CE 33/2021 (CE)` mid-page, between paragraph numbers and body
     text (max 3 lines per page; every removal is counted in
     `page_boilerplate_removed`).
2. **Anchor on numbered paragraphs.** A line starting `N.N[.N[.N]]` where the
   first component equals the chapter number begins a paragraph. The chapter
   check is essential: chapter 3 alone contains **331** lines of numeric table
   data (`1.5 - 10 54.5 - 54.6 …`) that would otherwise shatter a table page into
   hundreds of 10-character fragments.
3. **Attach a heading to its paragraph.** A short line (≤80 chars, ≤12 words, no
   terminal punctuation) immediately before an anchor moves into that paragraph.
   This is the only place a line-shape heuristic is trusted, and only with the
   anchor as corroboration.
4. **Everything before the first anchor** is a `prose_continuation` — text
   continuing from the previous page. It is kept separate, never joined.
5. **A page with no anchor** becomes a single `prose_page` passage.
6. **Table, list and non-substantive pages are never split.** One passage, typed
   and flagged `fragmented`. Splitting cell fragments into passages would be
   table reconstruction, which this stage does not do.
7. **A numbered line with a title and no sentence** (`6.1 Introduction`,
   `16.14 Impact from Electric and Magnetic Field`) is typed `heading`, flagged
   `heading_only`, and weighted 0.20. Citing a heading as evidence would answer a
   question with a title and no content.

### Signals I tested and rejected (measured, not assumed)

| Signal | Measurement | Why rejected |
|---|---|---|
| Line-shape heading detection alone | 5,056 candidates, **7.2 per page** | Sample was dominated by continuation lines and table cells. Only used with an anchor as corroboration. |
| `Table N.N` caption presence | Already measured in the prototype stage | Absent on the table pages that matter; also matches prose cross-references. |
| Digit density for missed tables | tables **0.030–0.035**, prose **0.001–0.017** | Overlaps at ~0.03, which is the 75th percentile of prose. No usable threshold. |
| Punctuation density for missed tables | tables **1.8–2.3**, prose **1.9–4.1** per 10 lines | Overlaps. |

The last two matter: they are the third and fourth text-statistic attempts to
detect the tables the page classifier misses. All four failed. That is now
strong evidence that **row/column structure cannot be recovered from extracted
text statistics** — it needs layout-aware extraction.

---

## 4. Result on the corpus

| Measure | Value |
|---|---|
| Pages | 1,293 |
| Passages | 4,161 (3.22 per page) |
| Mean tokens per passage | 76.9 (page level: 248.6) |
| Passage length | min 0 · p10 131 · median **495** · p90 1,772 · max 5,612 |
| `section_ref` resolved | **3,124 own** + 50 ambiguous = 3,174 of 4,161 (76%) |
| `section_ref` not detected | 987 (continuations, unsectioned pages, tables, lists) |

| Type | Count |
|---|---|
| `prose_paragraph` | 2,941 |
| `prose_continuation` | 383 |
| `table_fragmented` | 343 |
| `heading` | 233 |
| `prose_page` | 191 |
| `list` | 65 |
| `blank` | 4 |
| `non_substantive` | 1 |

Flags: `fragmented` 408 · `page_start_continuation` 383 · `heading_only` 233 ·
`low_context` 58 · `no_verified_folio` 40 · `near_blank` 13.

**Every one of the 1,293 pages yields at least one passage.** No record is
dropped, and no page is silently skipped.

---

## 5. Before / after — the query set

Six baseline queries from `RETRIEVAL_PROTOTYPE.md` §5 / `RARE_TERM_GATE.md` §4,
plus `offshore wind`.

> **Note on the query list.** The task described the six as including
> `offshore wind`. It is not one of the six — it was the blind-spot probe in
> `RARE_TERM_GATE.md` §7. I ran the six exact baseline queries *plus*
> `offshore wind`, rather than substituting anything. Scores are not comparable
> across levels (different document frequency and average length); only ranks and
> text are.

### 5.1 `black-faced spoonbill` — improved

| | Rank 1 | Score |
|---|---|---|
| Page | `Ch.8 ECOLOGY · §not detected · p.8-40 · idx 43` — species table, cells interleaved | 10.94 |
| Passage | `Ch.9 · §9.6.42 · p.9-21 · idx 23 · s2` — *"…17.4% utilisation by ardeids and other waterbirds, including Black-faced Spoonbill and Great Cormorant, at major flight height of 20 m to 25 m."* | 18.39 |

The passage is a complete, readable paragraph that names the species in context.
The species table is demoted to rank 3 but **remains findable** — for a question
like "is the spoonbill recorded here?", the table's `Common winter visitor` row is
arguably the better evidence, and it is now one rank lower.

### 5.2 `predicted mitigated noise level` — **no change**

| | Rank 1 | Score |
|---|---|---|
| Page | `Ch.4 · p.4-48 · idx 50` — table header row | 16.59 |
| Passage | `Ch.4 · p.4-48 · idx 50 · s0 prose_page` — **the same page, whole** | 17.04 |

`p.4-48` is 76 lines of table cells with no numbered paragraph, so rule 5 applies
and the whole page becomes one passage. The passage layer does not help here.
Rank 2 improves slightly (`§4.6.5.1`, a real paragraph about indirect mitigation),
but the top hit is unchanged. **This is the clearest limitation** — see §7.1.

### 5.3 `geothermal power generation` — not fixed, and weaker

| | Rank 1 | Score |
|---|---|---|
| Page | `Ch.2 · p.2-4 · idx 5` — "clearance requirement for CLP **power** cables", matched 2/3 | 8.57 |
| Passage | `Ch.7 · §7.8.4.3 · p.7-51 · idx 52 · s2` — "No large-scale polluting installations … such as oil depots and **power** plants are identified", matched **1/3** | 7.58 |

The gate still reports `partial_oov` and warns that `geothermal` occurs on 0
pages. Neither level answers the question. The passage is marginally more on-topic
(a statement about power plants) but **matches fewer query terms** than the page
did — a genuine regression in term coverage for this query.

### 5.4 `long viewing distance` — neutral, with a more honest citation

| | Rank 1 | Score |
|---|---|---|
| Page | `Ch.10 · §10.9.4.1 · p.10-119 · idx 123` | 13.14 |
| Passage | `Ch.10 · §10.9.4.1 **(ambiguous)** · p.10-119 · idx 123 · s0` | 13.10 |

Same page, same text, same folio. The passage adds `(ambiguous)` because the page
opens with six stacked section numbers (`10.9.4.1 10.9.5.1 … 10.9.5.5`) and which
one owns the following paragraph is not recoverable. The duplicate folio `10-119`
still appears twice in the corpus and the citation still carries `PDF idx`.

*Correction to my own first reading:* I initially recorded this as a readability
regression because the passage excerpt began with the number chain. That was an
artifact of my comparison harness — page excerpts were centred on the query term
while passage excerpts started at the passage beginning. Both now centre on the
match (`passage_excerpt()`), and the two excerpts are near-identical.

### 5.5 `noise barrier` — improved

| | Rank 1 | Score |
|---|---|---|
| Page | `Ch.4 · p.4-45 · idx 47` — mitigation-measures table | 10.83 |
| Passage | `Ch.4 · §4.5.4.10 · p.4-28 · idx 30 · s3` — *"Use of Temporary Noise Barriers and Noise Enclosures … Movable noise barriers or noise enclosures would be erected to provide screening from the construction plant."* | 13.37 |

The prose paragraph that actually answers the query now ranks first, and the table
moves to rank 2. This is the clearest win of the change.

### 5.6 `wetland habitat enhancement` — improved

| | Rank 1 | Score |
|---|---|---|
| Page | `Ch.17 · §17.6 · p.17-13 · idx 13` — summary table; excerpt is about landfill gas | 10.83 |
| Passage | `Ch.8 · §8.4.2.10 · p.8-9 · idx 12 · s1` — *"Planned Wetland Compensation Site in Kam Tin … a wetland compensation site of about 1.9 ha is identified…"* | 12.93 |

The page-level top hit matched all three terms but its excerpt was not about
wetland enhancement; the passage is squarely on topic.

One loss: the page-level rank 2 was the `Ch.15` null-folio page (a good
demonstration of `no printed folio`). It is no longer in the top 2. Null-label
handling is still covered by the citation test, but this query no longer surfaces it.

### 5.7 `offshore wind` — not fixed

| | Rank 1 | Score |
|---|---|---|
| Page | `Ch.12 · §12.6.19 · p.12-37 · idx 37` — "Former **Offshore** Area" (marine geology), matched 1/2 | 7.29 |
| Passage | `Ch.5 · §5.6.1.6 · p.5-19 · idx 20 · s3` — "**Wind**-blown dust …", matched 1/2 | 9.92 |

Both are wrong; the corpus says nothing about offshore wind energy. The passage is
more readable, which makes the mismatch easier for a human to reject, but it does
not fix it. The gate still returns `ok` because both words exist.

### 5.8 Summary

| Query | Verdict |
|---|---|
| `black-faced spoonbill` | **Improved** (readable paragraph at rank 1) |
| `predicted mitigated noise level` | **No change** (unsectioned table page) |
| `geothermal power generation` | **Not fixed**; fewer query terms matched |
| `long viewing distance` | **Neutral**; citation now flags ambiguity |
| `noise barrier` | **Improved** (prose answer at rank 1) |
| `wetland habitat enhancement` | **Improved** (on-topic at rank 1) |
| `offshore wind` | **Not fixed** |

3 improved · 1 neutral · 1 unchanged · 2 not fixed.

---

## 6. Tests

`stage1/test_passages.py` — **23 tests, all pass** (7.7 s).
`stage1/test_rare_term_gate.py` — **19 tests, all pass** (4.8 s). Total 42.

| Requirement | Tests |
|---|---|
| Segmentation | `test_numbered_anchors_split_a_page`, `test_every_page_yields_at_least_one_passage`, `test_table_page_is_one_flagged_passage`, `test_list_page_is_one_flagged_passage`, `test_heading_only_passages_are_typed_and_flagged` |
| Provenance | `test_passages_are_contiguous_slices_of_their_page`, `test_no_passage_crosses_a_page`, `test_page_text_hash_matches_source_record`, `test_required_provenance_fields_present`, `test_section_ref_is_literal` |
| Unverified labels | `test_unverified_labels_are_preserved_not_invented`, `test_label_is_always_copied_from_source`, `test_null_label_citation_states_the_gap` |
| Repeated headers | `test_repeated_headers_are_removed_and_recorded`, `test_month_footer_does_not_become_a_passage`, `test_chapter_banner_removed` |
| Fragmented tables | `test_table_page_is_one_flagged_passage`, `test_list_page_is_one_flagged_passage` |
| Stable IDs | `test_passage_ids_are_unique_and_well_formed`, `test_passage_ids_are_stable_across_rebuilds` |
| Gate unchanged | `test_gate_is_unchanged_at_passage_level`, `test_search_results_carry_full_provenance`, `test_multi_ref_anchor_is_marked_ambiguous` |
| Context kept separate | `test_context_expansion_is_separate_and_provenanced`, `test_context_is_absent_at_a_chapter_boundary` |

The strongest one is `test_passages_are_contiguous_slices_of_their_page`: it
re-reads each source page, re-runs the cleaning, and asserts
`passage.text == lines[line_start:line_end]` exactly. If segmentation ever drifts
from its provenance, that test fails.

---

## 7. Known failure modes

### 7.1 A table page with no numbered paragraph stays whole
`p.4-48` (76 lines of cells) becomes one `prose_page` passage and keeps winning
`predicted mitigated noise level`. Rule 5 cannot help: there is no anchor to split
on, and splitting cells would be reconstruction. Four different text-statistic
signals failed to detect this page as a table (§3). **Only layout-aware extraction
can fix it.**

### 7.2 Pages the classifier wrongly calls prose get segmented as prose
`p.4-45` and `p.10-119 idx 123` are tables that `retrieve.py` labels `prose`. They
are segmented on their numbered lines, which is defensible, but `p.10-119 s0`
begins with a chain of six section numbers and reads poorly.

### 7.3 Stacked section numbers make 50 references ambiguous
The PDF emits a column of paragraph numbers as one line
(`4.2.1 4.2.2 4.2.3 The criteria of evaluating…`). Which paragraph owns the
following text is unrecoverable, so the first number is kept **and** the passage
is marked `ambiguous_multiple_refs`, shown as `§4.2.1 (ambiguous)`. 50 passages.

### 7.4 Continuations have no section reference
383 passages are text continuing from the previous page. By design they do not
inherit a reference from the previous page, so `section_ref` is null for most of
them. That is honest but reduces citation precision exactly where the report is
most continuous.

### 7.5 An answer spanning two paragraphs is split
A passage is one paragraph. Where an argument runs across two, neither passage
holds it whole; page level kept them together. This is the cost of the precision
gained in §5.5–5.6, and it is why `--expand` exists — but expansion is returned
separately and is not used for ranking.

### 7.6 Whole-page passages are not an improvement
191 `prose_page` passages are the page, unchanged in granularity. For those pages
the passage layer adds provenance and flags, not precision.

### 7.7 Mid-page header removal could in principle remove a real line
110 pages had 2–3 header-pattern lines removed. All were counted, and no page lost
more than 3 lines, but the rule trusts line shape. A body line that exactly
matches a header string would be removed.

### 7.8 Heading detection is shape-based
233 passages are typed `heading`. The rule (numbered line, ≤12 words, no terminal
punctuation) is corroborated by nothing else. A short paragraph that happens to
lack a full stop at a page break is misclassified; the cost is that it is weighted
0.20 instead of 1.00.

---

## 8. Recommendation for the next single step

**Visually verify a sample of passage boundaries against rendered PDF pages.**

Reasoning: everything downstream now depends on the claim that a passage begins
and ends where a paragraph does. That claim rests on invariants (contiguity,
hash provenance) and on spot checks I made while building — but **no passage has
been checked against the rendered page**. The project's own standard is that
machine extraction is not verification: `STAGE1_INVENTORY.md` already flags that
only 24 of 1,293 pages were visually inspected.

Concretely: render 20–30 passages with the existing `stage1/render_page.js`,
covering each type (`prose_paragraph` with and without a heading, `prose_continuation`,
`heading`, `table_fragmented`, `prose_page`, `ambiguous_multiple_refs`), and record
per passage whether the segment boundary matches the paragraph boundary on the page.

That is cheap, uses only existing tooling, and converts the segmentation from
"machine-derived" to "verified on a sample" — the same transition this project
made for page labels. It should precede answer generation, because an answer layer
built on unverified boundaries would produce confident citations to half-paragraphs.

**Not** recommended as the next step: another retrieval heuristic. Four signals
have now failed to detect tables; the remaining fixes are layout-aware extraction
(a package install and a re-extraction — a decision for you, not a tweak) or the
answer layer.

---

## 9. Reproduce

```bash
cd /Users/chloeyan/workbuddy-ai/NORTHWISE

python3 stage1/passages.py --stats
python3 stage1/passages.py "noise barrier" --k 3
python3 stage1/passages.py "noise barrier" --k 2 --expand   # context kept separate
python3 stage1/passages.py "long viewing distance" --json

python3 stage1/eval_levels.py --k 2 --width 210              # page vs passage
python3 stage1/test_passages.py
python3 stage1/test_rare_term_gate.py
python3 stage1/retrieve.py "noise barrier" --k 3             # baseline unchanged
```

Exit codes: `0` results, `1` no hits or empty query, `2` blocked by the OOV gate.
