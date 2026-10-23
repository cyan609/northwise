# NORTHWISE — Chinese Source Citation and Evidence Display

**Date:** 2026-10-18
**Scope:** make Traditional Chinese questions retrieve and display original Chinese
source passages, without changing English behaviour.

---

## 1. Root cause

The complaint was "when users ask in Traditional Chinese, the chatbot does not
properly quote Chinese-language source material". There were **four** separate
causes, and the first one alone was enough to make Chinese citation impossible.

### 1.1 No Chinese source text existed in the index

`stage1/data/` held 132 files and 6,899 pages, and **all of it was English**.
A scan for Han characters found only incidental CJK (heritage names, table
fragments) — never a Chinese sentence.

The reason is not that EPD publishes no Chinese. Both reports in the project's
initial, locally downloaded dataset publish a full Traditional Chinese executive
summary:

| Report | Chinese source | Pages |
|---|---|---|
| AEIAR-276-2026 (San Tin) | `es_chi_out.pdf` | 51 |
| AEIAR-271-2025 (Ngau Tam Mei) | `es_tc.pdf` | 62 |

They were never extracted, for two reasons:

- `stage1/extract_pages.py` only accepts a PDF that is listed as a **chapter** in
  `stage0/reports.json`. These two are listed under `exec_summary_zh_url`, not
  `chapters[]`, so the script refused them by design.
- Their footers are Chinese (`4 2026 年 3 月`, `58 二零二五年八月`). The stage-1
  footer rule requires an English month name, so every page would have been
  classified `unverified` — no page numbers at all.

### 1.2 The tokenizer could not index Chinese

```python
def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) ...]
```

`re.findall(r"[a-z0-9]+", "噪音影響")` returns `[]`. Even if the PDFs had been
extracted, every Chinese page would have had **zero tokens** and been invisible
to BM25 — unrankable and unreachable.

### 1.3 Chinese questions were translated, not searched

For a `zh-Hant` question, `ask()` called `_map_chinese_terms()`, which converts
known Chinese phrases into English search terms through a 52-entry lookup table
(`噪音 → noise`, `水質 → water quality`, …). The pipeline therefore always
searched **English** chapters and could never surface a Chinese original, even if
one existed. That is precisely the substitution the brief rules out: a translated
query is not a retrieved Chinese source.

### 1.4 Chinese prose was misclassified as a fragmented table

Found while testing the fix. `classify_form()` decides "prose vs table" partly by
measuring the share of English stopwords. Chinese text has none, so every Chinese
page scored 0% and was labelled `table_fragmented`, down-weighting it to 0.6 and
skipping paragraph segmentation. Measured: **91 of 113** Chinese pages were
mislabelled.

---

## 2. What changed

| File | Change |
|---|---|
| `stage1/extract_zh_es.py` | **New.** Extracts a Chinese executive-summary PDF into the stage-1 record shape, adding `doc_kind: "executive_summary"` and `doc_lang: "zh-Hant"`. Handles the Chinese footer (`<folio> <year> 年 <month> 月`, Arabic or Chinese numerals). |
| `stage1/data/aeiar-276-2026_es_zh.pages.jsonl` | **New.** 51 page records. |
| `stage1/data/aeiar-271-2025_es_zh.pages.jsonl` | **New.** 62 page records. |
| `stage1/retrieve.py` | CJK bigram tokenizer (opt-in), Chinese running-header patterns, Chinese footer rule, Chinese disclaimer marker, CJK-aware form classifier, `Corpus(lang=, records=, cjk=)`, `load_all_records()`, `zh_query_terms()`; drops functional `會不` / `不會` bigrams. |
| `stage1/passages.py` | `PassageIndex(records=)`; propagate `doc_lang` / `doc_kind` onto every passage; name the executive summary for what it is in `passage_citation()`. |
| `app.py` | Separate Chinese index; `_zh_evidence_hits()` with score, coverage and generic-overlap safeguards; Chinese-first routing in `ask()`; `_source_url()` resolves the executive-summary PDF; evidence cards carry `doc_kind` and `excerpt_lang`; Chinese token budget and truncation repair; honest refusal wording. |
| `static/index.html` | Chapter line shows "Executive Summary" for ES passages; language badge on each excerpt; EN/zh-Hant strings. |
| `stage1/test_rare_term_gate.py` | Measures the English corpus explicitly (`Corpus(lang="en")`) and asserts the new 6,899 + 113 split. |
| `stage1/test_citation_reliability.py` | Keeps its baseline corpus explicitly English; replaces retired "Chinese must be translated" assertions with Chinese-original, official-PDF, honest-fallback and refusal checks. |

No change was made to the map, the draggable/resizable chat window, the glossary,
or any English retrieval or prompt path.

---

## 3. How Chinese retrieval works now

```
Traditional Chinese question
        │
        ├─ 1. search the ORIGINAL Chinese executive summaries
        │      (CJK bigrams, own BM25 index, own df / avgdl)
        │      gate: top score ≥ 2.5 AND ≥ 2 distinct query bigrams matched
        │
        │      hit ──► evidence = Chinese originals, cited as Ch.0 p.N
        │
        └─ 2. no usable Chinese hit → the existing English path, unchanged
               (topic map → English BM25 → English evidence, labelled "English original")
```

### Why two separate indexes

The English corpus is built with `lang="en"` and `cjk=False`. It therefore keeps
exactly the 6,899 documents, token counts, term frequencies, df and `avgdl`
(286.6) it had before Chinese sources existed. Chinese pages are indexed
separately, so a Chinese BM25 score is never compared with an English one, and
adding Chinese cannot move an English ranking. Verified after the change:
**6,899 English documents, avgdl 286.6 — identical**.

### Why character bigrams

Chinese is not space-delimited and this project uses the standard library only —
no segmenter, no model. A two-character window is the smallest unit that still
carries meaning (`噪音` noise, `生態` ecology) and avoids the noise of single
characters like `的` / `會`. A short list of purely functional bigrams
(`是否`, `會唔`, `有冇`, …) is dropped.

### Why chapter 0

The executive summary is a separate document with its own pagination — it is not
a chapter, and it is not numbered as one. It is stored as `chapter: 0` **only**
because the citation token must stay numeric: `_validate_synthesis()` and
`claim_evaluator.CITATION_RE` both parse `Ch.<digits>`. Keeping it numeric means
citation validation is not weakened or forked for Chinese; the same exact
`(report, chapter, page)` match is still required. The UI and the citation string
call it "Executive Summary (Chinese original)", never "Chapter 0".

### Why a relevance gate

Without it, a Chinese question matched pages on a single incidental bigram.
Measured before the gate:

| Question | Top hit | Problem |
|---|---|---|
| 今日天氣點樣？ | a land-use table | matched `天氣` once |
| 有冇提及中華白海豚？ | an unrelated page | the summary never mentions the species |
| 股票市場走勢 | — | no hit (correct) |

With the gate (`score ≥ 2.5`, `≥ 2` distinct bigrams), both fall through to the
English path and end in an honest refusal. A second measured safeguard handles
generic overlap: when no controlled EIA topic phrase is present, the top passage
must match at least one bigram beyond `項目` / `會影` / `影響`. This closes the
observed false positive where `這個項目會不會影響房價` matched an EIA passage only
on the generic frame, while `房價` itself was absent. Functional `會不` / `不會`
bigrams are removed during tokenisation.

Every genuine EIA topic tested still clears the gate: 噪音, 生態, 廢物, 空氣質素,
文化遺產, 水質, 景觀, 堆填區氣體, 電磁場, 隧道工程, 環境效益, 施工安排, and the
general `主要環境影響` question.

---

## 4. Evidence display

Each card now states what it is showing:

- **Chapter line** — "行政摘要（中文原文）" / "Executive Summary (Chinese original)"
  for Chinese passages; the normal "Chapter N · Title" otherwise.
- **Language badge** — `中文原文` when the excerpt is an original Chinese passage;
  `英文原文（目前索引沒有中文段落）` when a Chinese question had to fall back to
  English. This describes the local index and does not claim EPD publishes no
  Chinese source for that report.
- **Citation** — report id, chapter, page label, PDF index, viewer page, folio
  status, passage id, exactly as before.
- **Source link** — points to the official Chinese PDF
  (`exec_summary_zh_url` from `stage0/reports.json`), not to a chapter file.

Excerpts are always verbatim. Nothing is translated, so an English passage is
never presented as a Chinese quotation.

---

## 5. Verification

### Corpus integrity

| Check | Result |
|---|---|
| English corpus size | 6,899 documents (unchanged) |
| English `avgdl` | 286.6 (unchanged) |
| Chinese pages extracted | 113 (51 + 62), 0 gaps in the folio run |
| Chinese folio status | 109 verified, 1 absent, 3 unverified |
| Chinese form classification | 44 prose, 63 table, 4 list, 2 non-substantive (was 16 prose / 91 table) |

### Test suites

| Suite | Result |
|---|---|
| `stage1/test_passages.py` | 26 tests, **OK** |
| `stage1/test_rare_term_gate.py` | 19 tests, **OK** |
| `app.py` non-LLM `AskTest` regression | 52 tests, **OK** |
| `app.py` isolated synthesis/validation tests | 8 tests, **OK** |
| Updated Chinese `AskTest` subset | 12 tests, **OK** |
| Citation-reliability non-LLM regression | 55 tests, **OK** |

The all-in-one suites also invoke the real local Ollama model repeatedly. They
were not used as the final pass/fail signal here because concurrent generation
runs exceeded the process budget. The deterministic retrieval, routing, citation,
claim-evaluation and mocked synthesis paths above all completed cleanly; live
single-query generation was verified separately below.

### Citation validation is not weakened

Tested directly against Chinese evidence (`Ch.0`):

| Answer | Valid? |
|---|---|
| `[aeiar-271-2025, Ch.0, p.27]` (real page) | ✅ accepted |
| `[aeiar-271-2025, Ch.0, p.999]` (wrong page) | ❌ rejected |
| `[aeiar-271-2025, Ch.4, p.27]` (wrong chapter) | ❌ rejected |
| no citation at all | ❌ rejected |

The claim evaluator also parses `Ch.0` and returned `supported: 1` for the same
answer.

### Live behaviour

| Question | Gate | Evidence language | Result |
|---|---|---|---|
| 堆填區氣體風險 | `zh_original` | zh-Hant | 2 Chinese passages, complete Chinese summary with citations |
| 噪音會唔會影響附近居民？ | `zh_original` | zh-Hant | 3 TC ES cards; complete 273-character summary, valid citations, 33 s |
| 復耕安排係點？ | `mapped` | en | 3 English passages, badge "英文原文（目前索引沒有中文段落）" |
| 今日天氣點樣？ | `chinese_unsupported` | — | honest refusal |
| 有冇提及中華白海豚？ | `chinese_unsupported` | — | honest refusal (the summary never mentions it) |
| 這個項目會不會影響房價 | `chinese_unsupported` | — | generic-overlap safeguard; honest refusal |
| noise barrier | `ok` | en | 3 English passages; live LLM summary returned, English path unchanged |

---

## 6. Known limitations

1. **Coverage is the executive summary, not the whole report.** The two locally
   indexed Chinese documents are executive summaries, which are broad but
   shallow. A detailed question ("what mitigation applies at chainage X") will
   often fall back to English. Chinese chapter text is not indexed.
2. **No section references in Chinese citations.** The stage-1 paragraph anchor
   rule expects `N.N.N` numbering and is chapter-scoped; the executive summaries
   use four-level numbering (`3.9.1.4`). Rather than fork the segmentation logic,
   Chinese passages keep `section_ref: null` and the UI shows "Section: —". The
   page number and PDF index are still exact.
3. **`_TC_TOPIC_MAP` is still a lookup table.** It is now the *fallback* for
   Chinese questions the Chinese index cannot answer, not the primary path.
4. **Chinese answers are slower and shorter.** A Traditional Chinese answer costs
   ~1.3 tokens per character on `granite4.1:3b` against ~0.2 for English, so the
   Chinese budget is 650 tokens (English stays at 400) and the answer is asked to
   stay near 300–400 characters. If the cap is still reached, the trailing partial
   sentence is trimmed rather than shown cut off.
5. **Two Chinese PDFs are currently indexed.** The registry records official
   Chinese executive-summary URLs for all eight reports, but only the two PDFs
   from the initial dataset are present under `stage0/source-data/` and extracted
   into Stage 1. The other six are known external sources, not yet downloaded or
   indexed; Chinese questions scoped to those reports therefore fall back to
   English evidence. The application does not claim that the Chinese source is
   unavailable — only that no relevant Chinese passage exists in the current
   local index.

---

## 7. Reproducing

```bash
# re-extract the Chinese executive summaries
python3 stage1/extract_zh_es.py \
  --pdf stage0/source-data/AEIAR-276-2026/executive-summary/es_chi_out.pdf \
  --out stage1/data/aeiar-276-2026_es_zh.pages.jsonl
python3 stage1/extract_zh_es.py \
  --pdf stage0/source-data/AEIAR-271-2025/executive-summary/es_tc.pdf \
  --out stage1/data/aeiar-271-2025_es_zh.pages.jsonl

# tests
python3 stage1/test_passages.py
python3 stage1/test_rare_term_gate.py

# run
python3 app.py --port 8080
```
