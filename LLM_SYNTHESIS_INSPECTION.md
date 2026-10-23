# NORTHWISE MVP — LLM Synthesis Inspection Report

**Date:** 2026-10-18  
**Scope:** Determine whether evidence-grounded answer synthesis is feasible before implementation.

---

## 1. LLM Availability

### Discovered: Local Ollama instance

| Property | Value |
|----------|-------|
| Endpoint | `http://localhost:11434` |
| Access | No API key required |
| Transport | HTTP POST, JSON request/response |
| Python access | `urllib.request` (stdlib only — no packages needed) |

### Available models

| Model | Size | Context | Test result |
|-------|------|---------|-------------|
| `granite4.1:3b` | 3.4B | 131K | ✅ **Working** — produces cited, evidence-grounded answers |
| `gemma4:latest` | 8.0B | 131K | ❌ Non-functional — returns empty responses |

**Selected model:** `granite4.1:3b` (verified working with `/api/chat` endpoint and system prompt).

### Verified synthesis quality

Test prompt (real evidence from `noise barrier` query):
```
System: You are NORTHWISE... Answer using ONLY the provided evidence passages.
        Cite every factual claim with [report_id, chapter, page_label].
User:   Question: What noise mitigation measures are proposed?
        Evidence 1 [aeiar-276-2026, Ch.4, p.4-28]: <excerpt>
        Evidence 2 [aeiar-276-2026, Ch.4, p.4-45]: <excerpt>
```

**Model output:**
> "The noise mitigation measures proposed include the use of Temporary Noise Barriers and Noise Enclosures [aeiar-276-2026, Ch.4, p.4-28]. Additionally, a Cantilevered noise barrier (absorptive) is planned to be implemented before the population intake of the planned development [aeiar-276-2026, Ch.4, p.4-45]."

**Assessment:** Accurate, evidence-only, cites sources correctly, 83 tokens (~2 seconds).

---

## 2. Backend Capability

`app.py` already:
- Retrieves up to 3 evidence passages with full metadata
- Has `report_id`, `chapter`, `page_label`, `excerpt`, `source_url` for every card
- Can be extended with a `synthesize()` function that calls Ollama via `urllib.request`

**Proposed response schema change (additive only):**
```json
{
  "question": "...",
  "lang": "en",
  "refused": false,
  "synthesis": {
    "answer": "plain-language answer with inline citations...",
    "model": "granite4.1:3b",
    "tokens_used": 83
  },
  "evidence": [ /* unchanged */ ],
  "gate": { /* unchanged */ }
}
```

If Ollama is unavailable: `synthesis` is `null`, app falls back to evidence-only display.

---

## 3. Frontend Capability

`static/index.html` `renderResults()` already:
- Renders a notice card (`data.message`) at the top
- Then renders evidence cards below

**Smallest UI change:** Replace the notice card with a synthesized answer card when `data.synthesis` is present. Evidence cards remain unchanged below it.

No framework, no build step, no package installation needed.

---

## 4. What Is NOT Available

| Missing | Impact | Workaround |
|---------|--------|------------|
| `openai` / `anthropic` SDKs | Cannot use cloud APIs | Use Ollama via stdlib urllib |
| `requests` / `httpx` | Cannot use convenience HTTP libs | Use `urllib.request` |
| `gemma4` functional | 8B model would be better | `granite4.1:3b` is sufficient for MVP |
| General Chinese synthesis | Model is English-optimized | Synthesize in English; translate UI only |

---

## 5. Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Ollama not running on user's machine | Medium | Graceful fallback: evidence-only mode |
| Model hallucinates despite system prompt | Low | Temperature 0.3 + strict "ONLY use evidence" prompt + keep evidence cards visible for verification |
| Model produces generic answer instead of specific evidence | Low | Include full excerpts in prompt, not just summaries |
| Synthesis is slow (>5s) | Low | 3B model, 83 tokens observed; cap at 200 tokens |

---

## 6. Single Next Action

**Implement `synthesize()` in `app.py`** with the following contract:

1. Accept `question`, `lang`, `evidence[]`.
2. Build a strict system prompt: "You are NORTHWISE... Answer using ONLY the provided evidence. Cite every claim. Keep it short."
3. Call Ollama `/api/chat` with `granite4.1:3b` via `urllib.request`.
4. Return `{"answer": str, "model": str, "tokens_used": int}` or `None` if Ollama fails.
5. Attach to response as `synthesis` field.
6. Update `renderResults()` to display `synthesis.answer` as the top card when present.
7. Add tests: synthesis produces text, citations are preserved in evidence, fallback when Ollama down.

**Estimated effort:** 30 minutes (backend) + 15 minutes (frontend) + 15 minutes (tests).
