# Stage 1 — Minimal Retrieval Prototype

**Status:** prototype, for review. Not wired into any UI, no answer generation.
**Date:** 2026-10-17
**Corpus:** 1,293 pages / 34 chapters / 2 reports (unchanged from Stage 1 batch extraction)
**Runtime:** Python 3.13 standard library only. No packages, no embeddings, no vector DB, no network calls, no model.

This document reports what was built, how it ranks, what it got right on a
hand-written test set, and where it fails. **It does not report answer accuracy
or refusal accuracy** — the prototype produces neither answers nor refusals.

---

## 1. Files created

| File | Purpose | Lines |
|---|---|---|
| `stage1/retrieve.py` | Lexical retrieval over the extracted JSONL. CLI + importable `Corpus`. | 367 |
| `stage1/RETRIEVAL_PROTOTYPE.md` | This report. | — |

No other file was created or modified. Verified:

- All 34 `stage1/data/*.pages.jsonl` are **byte-identical** before and after every
  run in this step (`shasum -a 256` diff, empty).
- `stage0/reports.json` untouched (mtime 00:35, still carrying
  `validation_status` + `incomplete_reasons`).
- `PRD_EIA_Map_Assistant.md`, `DESIGN.md`, `stage1/extract_pages.py` untouched.

The retriever reads the JSONL and builds an in-memory search copy. It never
writes to the corpus.

---

## 2. Deliberately out of scope

No AI answer generation · no LLM · no external API · no embedding model · no
vector index · no map UI · no chunking design · no changes to the extractor or
the approved PRD/DESIGN. Geometry and `reports.json` completeness remain
deferred exactly as before.

---

## 3. Corpus as loaded

| Measure | Value |
|---|---|
| Pages (records) | 1,293 |
| Reports | 2 (`aeiar-276-2026` San Tin, `aeiar-271-2025` Ngau Tam Mei) |
| Chapters | 34 |
| Mean tokens per page | 248.6 |
| Vocabulary | 12,732 terms |
| Characters before cleaning | 3,267,017 |
| Characters after cleaning | 3,107,744 (−4.9%) |
| Pages with running header stripped | 1,183 |
| Pages with footer stripped | 1,253 |
| Pages with a section reference detected | 735 (56.8%) |

Text-form classification (evidence-based, see §4.3):

| Form | Pages | Share | Search weight |
|---|---|---|---|
| `prose` | 883 | 68.3% | 1.00 |
| `table_fragmented` | 343 | 26.5% | 0.60 |
| `list` | 65 | 5.0% | 0.50 |
| `non_substantive` | 2 | 0.2% | 0.15 |

The 26.5% table share is higher than the 10.2% reported in
`TEXT_QUALITY_AUDIT.md` because that audit measured **only** the mean-line-length
signal. The second signal added here (stopword ratio) flags 195 further pages.
A random sample of 6 of those 195 was inspected: all 6 are genuine tables
(species-distribution tables, a waste table, two NSR tables, two air-quality
tables). The rule is not over-flagging on the evidence available.

---

## 4. Method

Five steps, all deterministic. The same query always returns the same ranking.

### 4.1 Boilerplate removed from the *search copy* only

The running header is identical on 100% of San Tin pages and the footer carries
the printed folio plus month-year. Left in, they would match almost any query
mentioning "environmental impact assessment". `strip_boilerplate()` removes up
to 8 leading header lines and one trailing footer line.

The stored `text` field is never modified. Only the in-memory copy is cleaned,
so every citation can still be re-checked against the original PDF.

### 4.2 Page-level unit

The page is the retrieval unit, not a chunk. Reasons:

- A page is the smallest unit that can *always* be cited exactly, and the
  extracted JSONL is already one record per page.
- Section-level chunking would need a section detector that currently works on
  56.8% of pages. Building retrieval on top of a 43%-failing detector would
  bake that failure in.
- Splitting long pages into windows is a refinement (see §8), not a prerequisite.

### 4.3 Text-form classification, then down-weighting

Order of tests, first match wins:

1. Empty, or matches a disclaimer / sign-page marker → `non_substantive`.
2. ≥40% of lines are `Figure N` / `Table N` captions, **or** ≥30% carry dot
   leaders, **or** the folio is roman (front matter) → `list`.
3. ≥20 lines and mean line length < 20 chars → `table_fragmented`.
4. ≥12 lines and stopword ratio < 0.25 → `table_fragmented`.
5. Otherwise → `prose`.

The score used for ranking is `BM25 × FORM_WEIGHT`. A table page stays
searchable — its terms are real — but must not outrank narrative prose for a
narrative question. The unweighted BM25 is reported alongside, so the effect of
the weight is always visible rather than hidden.

### 4.4 BM25

Okapi BM25, `k1=1.5`, `b=0.75`, `idf = ln((N − df + 0.5)/(df + 0.5) + 1)`,
computed over the cleaned tokens of all 1,293 pages. Stopwords and 1-character
tokens are dropped from both query and document.

### 4.5 Citation format

```
[report_id · Ch.N TITLE · §section · p.folio · PDF idx N (viewer p.N+1) · status]
```

- `pdf_page_index` is **0-based** (PDFKit order). The viewer page is **1-based**.
  Both are printed because a PDF viewer's `#page=` anchor uses the 1-based
  number and the two differ by one.
- A missing folio prints as `no printed folio`, never as a guess.
- `§not detected` prints when no section reference was found, never an invented one.
- A section reference must begin with the chapter's own number (`chapter 9` →
  `9.x`), which prevents a measurement such as "1.88 ha" at a line start from
  being cited as `§1.88`.

---

## 5. Test queries and results

Six queries, `--k 3` unless noted. Scores are the weighted ranking score.
Form in parentheses is what the classifier decided.

### Q1 — Ordinary narrative: `black-faced spoonbill` (3/3 terms matched)

| # | Citation | Form | Score |
|---|---|---|---|
| 1 | `aeiar-276-2026 · Ch.8 ECOLOGY · §not detected · p.8-40 · PDF idx 43` | table_fragmented (0.6) | 10.94 (BM25 18.23) |
| 2 | `aeiar-271-2025 · Ch.9 · §9.3.6 · p.9-4 · PDF idx 6` | prose | 10.78 |
| 3 | `aeiar-271-2025 · Ch.9 · §9.6.41 · p.9-21 · PDF idx 23` | prose | 10.60 |

**Observation.** The species-table page wins despite the 0.6 penalty, because
its raw BM25 (18.23) is far above the prose pages. This is defensible: for a
*species name*, the species table is the strongest evidence in the corpus. But
the excerpt is a run-on of cells — "Locally common resident Besra … Common
winter visitor and passage migrant Black-faced Spoonbill(19)…" — and a reader
cannot tell which column each fragment came from. Ranks 2 and 3 are prose and
read correctly.

### Q2 — Table-related: `predicted mitigated noise level` (4/4)

| # | Citation | Form | Score |
|---|---|---|---|
| 1 | `aeiar-271-2025 · Ch.4 NOISE · §not detected · p.4-48 · PDF idx 50` | **prose (miss)** | 16.59 |
| 2 | `aeiar-271-2025 · Ch.4 NOISE · §4.6.17 · p.4-49 · PDF idx 51` | prose | 16.51 |
| 3 | `aeiar-276-2026 · Ch.3 AIR QUALITY · §3.6.2.5 · p.3-27 · PDF idx 31` | prose | 13.54 |

**Observation.** Rank 1 is a table (`Predicted Mitigated Noise Level, dB(A)` as a
column header) but the classifier called it `prose`, so no penalty was applied.
This is the documented classifier miss — see §7.2. Rank 2 is genuine prose about
the same subject, which is the behaviour we want: the substantive discussion is
one rank below the header row, not buried.

### Q3 — Weak / irrelevant: `geothermal power generation` (2/3)

| # | Citation | Score | Why it is not an answer |
|---|---|---|---|
| 1 | `aeiar-276-2026 · Ch.2 · p.2-4 · idx 5` | 8.57 | About **CLP power cables** and headroom clearance |
| 2 | `aeiar-276-2026 · Ch.14 · §14.2.1.8 · p.14-3 · idx 4` | 7.77 | Same text duplicated in the summary chapter |
| 3 | `aeiar-271-2025 · Ch.5 · §5.9.11 · p.5-29 · idx 29` | 5.45 | About **backup power supply** for pumps |

**Observation — the important negative result.** `geothermal` occurs on
**0 of 1,293 pages**. The retriever still returned three hits, because `power`
and `generation` are common. The top irrelevant score (8.57) sits only ~1.7
points below the weakest *relevant* top hit in this set (10.22). **A score floor
therefore cannot separate "no such content" from "weakly relevant"** — the two
distributions overlap. What *is* decisive is binary: the query's most distinctive
term has document frequency 0. See §8.1.

### Q4 — Duplicate folio: `long viewing distance` (3/3)

| # | Citation | Form | Score |
|---|---|---|---|
| 1 | `aeiar-276-2026 · Ch.10 · §10.9.4.1 · p.10-119 · PDF idx 123` | prose (miss) | 13.14 |
| 2 | `aeiar-276-2026 · Ch.10 · §not detected · p.10-81 · idx 84` | prose | 12.66 |
| 3 | `aeiar-276-2026 · Ch.10 · §not detected · p.10-86 · idx 89` | prose | 12.46 |

**Observation.** Rank 1 is the duplicated folio. Measured across the whole corpus:

- **29** `(report, page_label)` pairs occur more than once.
- **28** of them are separated by chapter (repeated front-matter roman folios and
  plain 1–23 series across different chapter PDFs), so a citation that includes
  the chapter is unambiguous.
- **1** is genuinely ambiguous: `p.10-119` in chapter 10 appears twice —
  `idx 122` (683 chars, near-blank, mean line 17.1) and `idx 123` (3,087 chars,
  the real content page). The top hit is `idx 123`.

So the citation must carry `PDF idx`, and it does. `p.10-119` alone would not
identify a page.

### Q5 — Table topic: `noise barrier` (2/2)

| # | Citation | Form | Score |
|---|---|---|---|
| 1 | `aeiar-276-2026 · Ch.4 · §not detected · p.4-45 · idx 47` | **prose (miss)** | 10.83 |
| 2 | `aeiar-276-2026 · Ch.4 · §4.5.4.7 · p.4-28 · idx 30` | prose | 10.57 |
| 3 | `aeiar-271-2025 · Ch.4 · §4.5.23 · p.4-24 · idx 26` | prose | 9.36 |

**Observation.** Rank 1 is the noise-mitigation table (`C13 (ST) Cantilevered
noise barrier (absorptive) 7+4 900 NTM5-12`). Again classified `prose`. Rank 2 is
prose but is about *quieter plant*, not barriers — so for this query the table is
the better evidence and the ranking is acceptable, even though the reason it won
was a classification failure rather than a correct weight.

### Q6 — Null folio: `wetland habitat enhancement` (3/3)

| # | Citation | Form | Score |
|---|---|---|---|
| 1 | `aeiar-271-2025 · Ch.17 · §17.6 · p.17-13 · idx 13` | prose | 10.83 |
| 2 | `aeiar-276-2026 · Ch.15 CONCLUSION · §not detected · **no printed folio** · PDF idx 3 · absent` | prose | 10.53 |
| 3 | `aeiar-276-2026 · Ch.8 · §8.10.1.1 · p.8-102 · idx 105` | prose | 10.31 |

**Observation.** Rank 2 exercises the null-label path. The page is still fully
locatable — report, chapter, `PDF idx 3 (viewer p.4)` — and the citation states
`no printed folio` with status `absent` rather than inventing `15-3`. There are
18 such pages in the corpus (17 `absent`, 1 `unverified`).

---

## 6. What works

1. **Every hit is locatable.** Report + chapter + `PDF idx` is enough to open the
   exact page in a viewer, with or without a printed folio.
2. **Boilerplate does not dominate.** Header/footer stripping removed 4.9% of
   characters and the remaining text is what carries meaning.
3. **Section refs are conservative.** 735 pages (56.8%) get a `§`; the rest say
   `§not detected`. No fabricated references survived testing — the chapter-prefix
   check eliminated the one class of false positive found (`§1.88` from "1.88 ha").
4. **Duplicate folios are handled without silent de-duplication.** Both copies of
   `10-119` remain in the corpus; the ambiguity is resolved by the citation, not
   by deleting a record.
5. **Table pages remain searchable but are usually demoted.** For narrative
   queries the top prose pages read correctly (Q1 ranks 2–3, Q2 rank 2).
6. **Fully deterministic and offline.** No model, no network, no package install;
   results are reproducible byte-for-byte.

## 7. Known limitations

### 7.1 No semantic matching
Lexical only. `bird` will not find `avifauna`; `spoonbill` and `Platalea minor`
are unrelated tokens. Paraphrase-heavy questions will miss. This is inherent to
the method and is the main argument for embeddings later.

### 7.2 The table classifier misses sentence-rich tables
Confirmed live on three pages: `p.4-45` (stopword 0.305), `p.4-48` (0.264) and
`p.10-119` idx 123 (0.362). All exceed the 0.25 threshold, so all were called
`prose` and received no penalty.

I tested the obvious fix — detecting a `Table N.N` caption — and it **does not
work**:

- `p.4-45`, `p.4-48`, `p.10-119` carry **no** `Table N.N` caption in their
  extracted text (captions sit on earlier pages, or the table is a continuation).
- The one caption the regex did match on `p.4-45` was a *cross-reference* in
  prose ("Figure 4.5.2, the extent of noise barrier would…"), i.e. a false positive.

So this is not a threshold that needs tuning; text statistics and caption regexes
cannot see row/column structure. The real fix is layout-aware extraction
(coordinates / `pdfplumber`-style), which is a separate decision with a package
install and a re-extraction — out of scope here and not recommended as the
immediate next step.

### 7.3 Table headers are term magnets
A column header like `Predicted Mitigated Noise Level, dB(A)` packs four query
terms into one line, so header rows score high for exactly the queries they
describe. The result is a *plausible* citation whose excerpt is a header, not a
finding. Acceptable for a retrieval prototype; not acceptable for an answer.

### 7.4 Page-level granularity
A hit is a whole page. When an answer spans a page break, one citation is
incomplete. Excerpts are a 260-character window around the first matching term,
which on table pages reads as a run-on.

### 7.5 Scores are not calibrated
BM25 scores are comparable within one query only. They cannot be compared across
queries, and §5/Q3 shows they do not separate relevant from irrelevant at a fixed
cut-off.

### 7.6 Front-matter noise
Roman-folio pages and the 65 `list` pages are down-weighted to 0.50 but not
removed. A query about report structure will surface them.

## 8. Recommendation for the next step

Ranked by value per unit of risk. I recommend **(1) only** for the next scoped
task.

**8.1 Add a rare-term gate (recommended next).** Before ranking, check the
document frequency of the query's highest-IDF term. If it is 0 across the corpus,
return an explicit `no page in the corpus contains "<term>"` result instead of
low-score hits. This is deterministic, needs no threshold tuning, and directly
fixes the Q3 failure, which is the most trust-damaging behaviour observed: a
confident-looking citation for content that does not exist. It also gives the
later answer layer an honest refusal signal that does not depend on score.

**8.2 Paragraph-level passages within long pages (next after that).** Split each
page into paragraph windows and rank windows, keeping the page as the citation
unit. This shortens excerpts to something a human can read and check, and on
table pages it isolates a single cell instead of a run-on. No new packages.

**8.3 A continuation-header signal for tables (optional, needs measurement).**
`aeiar-271-2025` ch.4 idx 47–49 all begin with the repeated header row
`NSR Description`, and `aeiar-276-2026` ch.10 idx 122–123 are adjacent pages of
one table. A page whose first body line repeats the previous page's first body
line is very likely a table continuation. This is cheap and evidence-based, but I
have measured it on only two table runs — it needs a corpus-wide count before it
is trusted, so I am not recommending it as the next step.

**8.4 Embeddings (later, and a separate decision).** Needed for synonyms and
paraphrase (§7.1). It requires choosing a model, installing packages, and
accepting that similarity scores are not citations. It should not be adopted
before the rare-term gate and paragraph passages are in place, because it will
make failures harder to see, not easier.

**Do not** proceed to answer generation on top of the current ranking. §7.2–7.3
mean a top hit can be a table header, and §7.5 means the score cannot tell you
whether the corpus contains the answer at all.

---

## 9. Reproduce

```bash
cd /Users/chloeyan/workbuddy-ai/NORTHWISE

python3 stage1/retrieve.py "black-faced spoonbill" --k 3
python3 stage1/retrieve.py "predicted mitigated noise level" --k 3
python3 stage1/retrieve.py "geothermal power generation" --k 3
python3 stage1/retrieve.py "long viewing distance" --k 3
python3 stage1/retrieve.py "noise barrier" --k 3
python3 stage1/retrieve.py "wetland habitat enhancement" --k 3

# machine-readable, includes unweighted BM25, matched terms, form weight
python3 stage1/retrieve.py "noise barrier" --k 3 --json

# scope to one report
python3 stage1/retrieve.py "noise barrier" --report aeiar-276-2026
```

The corpus is re-read on every invocation (34 files, 1,293 records, ~1 s).
No state is written.
