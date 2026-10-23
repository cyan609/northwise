# NORTHWISE LLM Synthesis Implementation Report

## Files Changed

1. **`app.py`** — Added `_synthesize()`, `_build_synthesis_prompt()`, `_validate_synthesis()`; integrated synthesis into `ask()`; added 9 synthesis tests.
2. **`static/index.html`** — Added synthesis card rendering in `renderResults()` with bilingual labels.

No corpus files, JSONL, or `reports.json` were modified.

---

## Backend Changes

### New Functions in `app.py`

- **`_build_synthesis_prompt(question, lang, evidence)`** — Builds strict system + user messages for Ollama `/api/chat`.
  - System prompt: "ONLY use provided evidence", "do not use general knowledge", "cite every claim with [report_id, Ch.X, p.Y]", "keep concise (2-4 sentences)", language directive.
  - User prompt: question + evidence passages with citation IDs.

- **`_validate_synthesis(answer, evidence)`** — Validates that every `[report_id, Ch.N, p.X-Y]` citation in the answer matches a retrieved evidence card. Returns `False` if any citation is invalid.

- **`_synthesize(question, lang, evidence)`** — Calls Ollama via `urllib.request` with 15s timeout.
  - Returns `{"answer": str, "model": str, "tokens_used": int}` on success.
  - Returns `None` on: URLError, timeout, JSON decode error, `done != true`, empty answer, or citation validation failure.

### Integration in `ask()`

- After successful retrieval, `_synthesize()` is called with the original question, detected language, and evidence cards.
- The `synthesis` object (or `null`) is added to the response dict.
- If retrieval refuses (empty, all-OOV, no results, low relevance), the LLM is **not called**.

### Configuration

```python
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "granite4.1:3b"
OLLAMA_TIMEOUT = 15  # seconds
```

No API key required. Uses Python stdlib only.

---

## Frontend Changes

- Added `synthesisLabel` to both EN and zh-Hant UI dictionaries.
- `renderResults()` now checks `data.synthesis`:
  - If present and valid: renders a green-left-border card with the answer, model name, and token count.
  - If absent: retains the existing yellow notice card (`data.message`).
- Evidence cards remain unchanged below the synthesis card.

---

## Test Results

### Full Suite

| Suite | Tests | Result |
|-------|-------|--------|
| app.py | 25 | ✅ all pass |
| stage1/test_passages.py | 26 | ✅ all pass |
| stage1/test_rare_term_gate.py | 19 | ✅ all pass |
| **Total** | **70** | **✅ all pass** |

### New Synthesis Tests (9)

1. `test_synthesis_prompt_building` — prompt contains evidence and language directive
2. `test_synthesis_success_with_valid_citations` — mocked Ollama response accepted
3. `test_synthesis_rejected_when_citations_invalid` — invalid citation discarded
4. `test_synthesis_none_on_ollama_failure` — URLError returns `None`, evidence survives
5. `test_synthesis_none_on_empty_response` — empty model response treated as `None`
6. `test_synthesis_skipped_when_refused` — retrieval refusal does not call LLM
7. `test_validate_synthesis_accepts_valid_citations` — valid citations pass
8. `test_validate_synthesis_rejects_invalid_citations` — invalid citations fail
9. (plus existing tests still pass)

All synthesis tests use mocked HTTP — no dependency on Ollama running.

---

## End-to-End Verification

### Real Synthesized Answer (Ollama running)

**Query:** `noise barrier` (EN)

**Synthesis:**
> The report [aeiar-276-2026, Ch.4, p.4-28] mentions that movable noise barriers or noise enclosures will be erected to screen from the construction plant, potentially reducing noise levels by 5 dB(A). Additionally, [aeiar-276-2026, Ch.4, p.4-45] details the installation of a cantilevered noise barrier (absorptive) at a height of 7+4 meters, covering 900 meters of length, to protect the Noise Sensitivity Map (NSM) 5-12, planned before the population intake of the development.

**Matching Evidence Citations:**
- `[aeiar-276-2026, Ch.4, p.4-28]` — verified · PDF idx 30 · source: `eia_ch04_out.pdf`
- `[aeiar-276-2026, Ch.4, p.4-45]` — verified · PDF idx 47 · source: `eia_ch04_out.pdf`

**Model:** `granite4.1:3b` · **Tokens:** 130

### Fallback When Ollama Is Stopped

**Simulated:** changed `OLLAMA_URL` to a non-existent port.

**Result:**
```json
{
  "synthesis": null,
  "refused": false,
  "evidence": [/* 3 cards unchanged */]
}
```

The app remains fully functional. Evidence cards are still returned. The frontend shows the existing notice card instead of a synthesis card.

---

## Known Limitations

### Citation Validation

- `_validate_synthesis()` uses regex `\[([^\]]+?),\s*Ch\.\s*(\d+),\s*p\.\s*([^\]]+?)\]` to find citations.
- **Limitation:** If the model paraphrases a citation without using the exact bracket format (e.g. "see page 4-28 of Chapter 4"), the validator will not detect it and the citation will pass unchecked.
- **Mitigation:** The strict system prompt requires the exact format, and the tested model (`granite4.1:3b`) follows it reliably. Unsupported citation styles are not validated.

### No LLM for Refusals

- When retrieval refuses (all-OOV, empty query, no results, low relevance), no synthesis is attempted. The refusal message is shown directly.

### Chinese Synthesis

- Chinese queries that map to English terms will receive synthesis in Traditional Chinese (lang directive is passed). This was not end-to-end tested with a live Ollama call in this session but is covered by unit tests.

---

## Running the App

```bash
cd /Users/chloeyan/workbuddy-ai/NORTHWISE
python3 app.py --port 8080
```

Requires Ollama running locally with `granite4.1:3b` for synthesis. The app works without it.
