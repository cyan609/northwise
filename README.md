# NORTHWISE

A map-based assistant that helps residents of Hong Kong's **Northern Metropolis** read the official
Environmental Impact Assessment (EIA) reports that affect them — in plain language, with every claim
traceable to a page in the published report.

The design rule that drives everything here: **abstain rather than speculate.** If the retrieved
evidence does not contain the kind of fact being asked for, the assistant says so and shows no
citations. A retrieved passage is never treated as support merely because it shares keywords with
the question.

---

## What it does

- Pick a project on the map, or ask a free-text question in English or Traditional Chinese.
- Get an answer assembled **only** from retrieved passages of the report, with citations of the form
  `[aeiar-276-2026, Ch.12, p.34]`.
- Switch the interface language and the answer is regenerated from the same evidence — an
  English-only source report still produces a Traditional Chinese answer.
- Ask something the report does not cover, and the answer is exactly
  `Sorry, I cannot answer this question` / `抱歉，我無法回答此問題。`

## Scope (deliberately narrow)

Only EIA reports published by the **Environmental Protection Department (EPD)** for projects that sit
within, or directly relate to, the official Northern Metropolis areas are ingested. Being in one of
the relevant districts is *not* sufficient on its own — each report must carry evidence of Northern
Metropolis scope, and ingestion is gated on every source URL being an official `epd.gov.hk` URL.

Eight reports are registered at present, including the two that anchor the dataset:

| Report | Project |
| --- | --- |
| AEIAR-276/2026 | Northern Metropolis Highway – San Tin Section |
| AEIAR-271/2025 | Development at Ngau Tam Mei Area |

## Quick start

Requires Python 3.9+ and nothing else — the server, retrieval and ranking are standard library only.

```bash
python3 app.py                 # http://localhost:8080
python3 app.py --port 9000     # custom port
```

The assistant runs **without any model**. Retrieval, ranking, citation verification and abstention
all work offline; answers are then assembled extractively from the best-matching passages.

To get synthesised prose instead of extracts, run a local model and it will be used automatically:

```bash
ollama pull granite4.1:3b      # served at http://localhost:11434
```

If the model is unreachable or exceeds its timeout, the request falls back to the extractive
summary rather than failing.

## How an answer is produced

1. **Retrieve** — BM25 ranking over a page-level index and a passage-level index
   (`stage1/data/*.pages.jsonl`), keeping at most 3 evidence cards.
2. **Check answerability** — `stage1/answerability.py` maps the question's intent to the kind of
   datum it needs and checks whether the retrieved evidence actually carries that datum. If not,
   abstain before any generation happens.
3. **Synthesise** (optional) — a model writes the summary from widened excerpts, under rules
   that forbid inventing mitigation measures, transliterating proper nouns, and citing a page that
   was not retrieved. Two providers sit behind one interface: a local Ollama model, and OpenRouter
   when `OPENROUTER_API_KEY` is set.
4. **Verify** — every displayed citation is checked against the retrieved evidence set, and the
   answer is repaired or replaced if a citation does not resolve.

## Repository layout

```
app.py                     HTTP server, retrieval wiring, synthesis, citation checks, tests
static/index.html          single-page front end: map, report list, chat, AI summary
static/assets/             mascot artwork

stage0/                    source acquisition and page-numbering verification
  reports.json             the report registry (scope, status, provenance)
  source-data/             downloaded official PDFs + manifests + HTML provenance snapshots
  tools/                   download, page-number analysis, inventory builders

stage1/                    extraction and retrieval
  data/*.pages.jsonl       one record per page: text, printed folio, status
  retrieve.py              BM25 page + passage indexes
  passages.py              passage segmentation and excerpting
  answerability.py         intent → datum → coverage gate
  claim_evaluator.py       claim-level evidence checking
  glossary_data.py         EN/TC terminology

*.md                       engineering reports for each build stage
screenshots/               browser evidence captured during testing
```

## Data and provenance

The PDFs under `stage0/source-data/` are **official public documents downloaded from `epd.gov.hk`**,
kept here so the corpus is reproducible offline. `stage0/source-data/download_manifest.json` records
the URL, fetch time and SHA-256 of every file.

Printed page numbers were verified rather than assumed. The verification is in
`stage0/STAGE0_INVENTORY.md` and `stage0/PAGE_NUMBERING_RECONCILIATION.md`, and it is the reason
citations carry a PDF page index alongside the printed folio: **a printed folio is not a unique page
identifier** — one chapter prints `10-119` on two different pages, and another never prints `12-23`.

## Tests

```bash
python3 app.py --test                    # application suite
python3 test_openrouter.py               # provider path, offline, mocked
python3 stage1/test_passages.py
python3 stage1/test_rare_term_gate.py
python3 stage1/test_citation_reliability.py
```

The citation suite verifies that every citation rendered to a user resolves to a real page in the
corpus — it is the check that matters most, because a wrong page number is worse than no answer.

## Deploying to Render

`render.yaml` is the blueprint. The equivalent dashboard settings:

| Setting | Value |
| --- | --- |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python3 app.py` |
| Health Check Path | `/health` |

`requirements.txt` is intentionally empty: an AST scan of `app.py` and all of `stage1/` found no
import outside the standard library, so there is nothing to install. The file exists only because
Render's default build command fails when it is missing.

Environment variables:

| Variable | Required | Purpose |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | yes, for AI summaries | Read from the server environment only. Never committed, never returned by an API, never shown in the UI. |
| `OPENROUTER_MODEL` | no | Defaults to `google/gemma-4-26b-a4b-it:free`. |
| `LLM_PROVIDER` | no | `openrouter` or `ollama`; `auto` (default) picks OpenRouter when a key exists. |
| `PORT` | set by Render | The server binds `0.0.0.0` on this port. |

Without a key the app still runs: retrieval, citations and refusal behave identically, and answers
come from the extractive summary instead of the model. `GET /health` reports which provider is live
and whether it is ready, without exposing the key.

## Known limitations

These are real and unfixed, not hypothetical:

- **Proper nouns are sometimes transliterated.** A 3B model occasionally renders a place name in
  Chinese characters instead of keeping the English name. Prompts carry counter-examples; compliance
  is not total.
- **Chinese-language retrieval is weaker than English.** The published reports are English-only, so a
  Chinese question is matched against English text. Some topics retrieve poorly and the answer
  degrades to the extractive fallback.
- **A verification banner fires on most answers.** The claim evaluator rejects an answer as soon as a
  single cited claim is classed `insufficient_evidence`, which is conservative to the point of noise.
- **Main report text is English-only as published.** Chinese exists only in the executive summaries.
- **OZP boundary geometry is not included.** The public dataset is token-gated, so zoning boundaries
  are absent rather than approximated.

## Third-party content

The EIA reports and their figures remain the copyright of the Hong Kong SAR Government and the
respective project proponents. They are included unmodified, for reference and reproducibility, and
are not relicensed by this repository. Everything else — the server, retrieval code and front end —
is the project's own work.
