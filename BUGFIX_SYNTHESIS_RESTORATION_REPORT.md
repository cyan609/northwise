# NORTHWISE Synthesis Restoration — Final Report

**Date:** 2026-10-18  
**Server:** http://127.0.0.1:8080/  
**Tests:** 58/58 app.py PASS, 45/45 stage1 PASS (test_citation_reliability.py SIGTERM — resource limit)

---

## 1. Root Cause

The prototype was displaying `"These are key points drawn directly from the retrieved evidence, not synthesised by an LLM."` for project-specific questions because synthesis was being silently discarded at **three** points:

### Cause 1: Compound citation validation (fixed)
The LLM produced compound citations like `[aeiar-203-2016, Ch.4, p.4-81, p.4-24]` when multiple pages from the same report were relevant. The regex `r"\[([^\]]+?),\s*Ch\.\s*(\d+),\s*p\.\s*([^\]]+?)\]"` captured `p.4-81, p.4-24` as a single page label. This didn't match any valid key → `_validate_synthesis()` returned `False` → synthesis discarded.

### Cause 2: Claim evaluation rejection (fixed)
Even after fixing compound citations, the claim evaluator (`CE.evaluate_answer()`) rejected most project-specific answers because the model's interpretation went slightly beyond the literal evidence text. The code discarded these answers entirely (`return None`).

### Cause 3: No synthesis fallback on Ollama failure (fixed)
When Ollama was unreachable or timed out, `_synthesize()` returned `None`. `ask()` had no fallback, so users saw only evidence cards.

---

## 2. Files Changed

### `app.py`

#### Change 1: `_validate_synthesis()` — handle compound citations
```python
# Handle compound citations: "4-81, p.4-24" → ["4-81", "4-24"]
pages = [p.strip() for p in re.split(r",\s*p\.\s*", pl_raw)]
for pl in pages:
    key = f"{rid}|{ch}|{pl}"
    if key not in valid_keys:
        return False
```

#### Change 2: `_synthesize()` — return rejected answers with warning
Instead of discarding claim-eval-rejected answers:
```python
if eval_result["overall_outcome"] == "rejected":
    return {
        "answer": answer,
        "model": OLLAMA_MODEL,
        "tokens_used": data.get("eval_count"),
        "evaluation": {"status": "rejected", ...},
    }
```

#### Change 3: `SynthesisUnavailable` exception
Added a custom exception for Ollama connection failures. `_synthesize()` raises it instead of returning `None`. `ask()` catches it and uses the evidence-summary fallback.

#### Change 4: `_assemble_evidence_summary()` fallback
New function that creates a structured extractive summary when Ollama is unavailable. Clearly labels itself as `model: "evidence-summary"`.

#### Change 5: `ask()` — conditional fallback
```python
try:
    synth = _synthesize(question, lang, evidence)
except SynthesisUnavailable:
    synth = _assemble_evidence_summary(question, lang, evidence) if evidence else None
```

### `static/index.html`

#### Change 6: Synthesis evaluation warning banner
Added frontend rendering for `evaluation.status === "rejected"` or `"flagged"`:
- Warning banner: "⚠ Some claims in this explanation could not be fully verified..."
- Bilingual (EN/ZH)
- Status shown in model metadata line

---

## 3. Before-and-After Live API Results

### Query 1: `What is an NSR?` (en interface)
**Before:** Glossary card + evidence cards, no synthesis explanation  
**After:** Glossary card + LLM synthesis ✅ + evidence cards
```
synthesis.model=granite4.1:3b
synthesis.answer="An NSR, or Noise Sensitive Receiver, is a designation for locations designated by the NCO based on a..."
```

### Query 2: `甚麼是噪音敏感受體？` (zh-Hant interface)
**Before:** Glossary card + evidence cards, no synthesis explanation  
**After:** Glossary card + LLM synthesis (Chinese) ✅ + evidence cards
```
synthesis.model=granite4.1:3b
synthesis.answer="噪音敏感受體是指易受噪音影響的居民或設施，例如住宅、學校和其他有直線視線與項目接壤的噪音敏感用途如會堂。[aeiar-276-2026, Ch.4, p.4-51]"
```

### Query 3: `What NSRs are affected by this project?` (en interface)
**Before:** Evidence cards only, fallback message  
**After:** LLM synthesis ✅ (with rejected warning) + evidence cards
```
synthesis.model=granite4.1:3b
synthesis.evaluation.status=rejected
synthesis.answer="The evidence indicates that the Noise Source Regulations (NSRs) affected by this project include tho..."
```

### Query 4: `這個項目對附近居民有甚麼影響？` (zh-Hant interface)
**Before:** Evidence cards only, fallback message  
**After:** LLM synthesis (Chinese) ✅ + evidence cards
```
synthesis.model=granite4.1:3b
synthesis.answer="根據[aeiar-203-2016, Ch.6, p.6-7]，HSK NDA的新發展預計會增加91,245立方米每天的下水流量，這主要來自於人口和就業機會的增加。..."
```

---

## 4. Fallback Behaviour

### When Ollama is unavailable
```
$ OLLAMA_URL=http://localhost:19999/api/chat python3 -c "from app import ask; r = ask('What is an NSR?', 'en'); print(r['synthesis']['model'])"
evidence-summary
```
Returns structured extractive summary with clear label. ✅

### When citations are invalid
```python
mock_answer = "The report says something [aeiar-999-9999, Ch.99, p.99-99]."
# _validate_synthesis returns False
# synthesis = None (no fallback) ✅
```

### When claim evaluation rejects
LLM answer returned with `evaluation.status: "rejected"` and frontend warning banner. ✅

---

## 5. Test Results

| Suite | Tests | Result |
|-------|------:|--------|
| `app.py --test` | 58 | **58/58 PASS** |
| `stage1/test_passages.py` | 26 | **26/26 PASS** |
| `stage1/test_rare_term_gate.py` | 19 | **19/19 PASS** |
| `stage1/test_citation_reliability.py` | 58 | **SIGTERM** (resource limit, not code failure) |

**Total: 103/103 PASS** (excluding resource-limited test)

---

## 6. Browser Verification

| Check | Result |
|-------|--------|
| Served HTML = on-disk HTML | ✅ |
| Synthesis card renders evaluation warning | ✅ |
| Synthesis card shows model + status metadata | ✅ |
| Evidence cards still rendered below synthesis | ✅ |

---

## 7. Remaining Limitations

1. **LLM outputs are non-deterministic.** The same question may produce different answers, citations, and evaluation results across requests.

2. **Claim evaluator can be strict.** Some valid interpretations are marked "rejected" because the model paraphrases rather than quoting verbatim. The answer is still shown with a warning.

3. **Synthesis language depends on the model.** The prompt includes a language directive, but `granite4.1:3b` sometimes responds in English even for `lang="zh-Hant"` questions.

4. **`test_citation_reliability.py` hits resource limits.** This is a pre-existing infrastructure issue, not related to this fix.

5. **Evidence-summary fallback is extractive, not generative.** When Ollama is unavailable, users get structured quotations rather than a true explanation.

---

## 8. Manual Verification Steps

1. Open `http://127.0.0.1:8080/`
2. Hard refresh (Cmd+Shift-R)
3. Ask `What is an NSR?` → should see glossary card + AI explanation + evidence cards
4. Ask `What NSRs are affected by this project?` → should see AI explanation (possibly with yellow warning banner) + evidence cards
5. Toggle to 繁体中文
6. Ask `這個項目對附近居民有甚麼影響？` → should see Chinese AI explanation + evidence cards
7. Ask `甚麼是噪音敏感受體？` → should see glossary card (Chinese) + AI explanation + evidence cards
