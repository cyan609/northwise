# NORTHWISE AI Summary Section — Final Report

**Date:** 2026-10-18  
**Server:** http://127.0.0.1:8080/  
**Tests:** 58/58 PASS

---

## 1. What Was Implemented

The NORTHWISE chatbot already had an AI-generated explanation layer ("synthesis") produced by Ollama. This task focused on **making it more visible, clearly labelled, and properly separated** from the raw source evidence.

### Backend fix: semicolon-separated citation validation

The model sometimes produces semicolon-separated multi-report citations:
```
[aeiar-274-2026, Ch.4, p.4-39; aeiar-276-2026, Ch.4, p.4-51]
```

The existing regex captured the entire string as one citation, causing validation to fail and the synthesis to be silently discarded. `_validate_synthesis()` in `app.py` was updated to:
- Detect `;` in the captured bracket content
- Split on `;` and validate each sub-citation independently
- Preserve existing comma-separated page validation (`p.4-81, p.4-24`)

### Frontend changes in `static/index.html`

#### New CSS classes
- `.ai-summary-label` — uppercase, primary colour, small font, letter-spaced
- `.ai-summary-card` — teal background with primary left border, rounded
- `.ai-summary-body` — 14px, comfortable line-height, pre-wrap
- `.evidence-divider` — horizontal rule with "Supporting Evidence" text in the middle
- `.insufficient-banner` — yellow banner for fallback summaries

#### New i18n strings
| English | Traditional Chinese |
|---------|---------------------|
| `synthesisLabel: "AI Summary"` | `synthesisLabel: "AI 摘要"` |
| `evidenceSectionLabel: "Supporting Evidence"` | `evidenceSectionLabel: "支援證據"` |
| `insufficientEvidence: "The retrieved evidence does not fully answer this question. Please review the source passages below."` | `insufficientEvidence: "檢索到的證據未能完整回答此問題。請參閱下方的原文段落。"` |

#### Updated `buildAnswerHtml()`
- AI Summary card rendered first with `.ai-summary-card` styling
- Warning banner shown when claim evaluation status is `rejected` or `flagged`
- **Fallback banner** shown when `model === "evidence-summary"` (Ollama unavailable) — clearly states the limitation
- **Evidence divider** (`<div class="evidence-divider">`) separates the summary from source cards
- Source evidence cards rendered below the divider, unchanged

---

## 2. Live Verification

### API response structure (unchanged)
```json
{
  "synthesis": {
    "answer": "The proposed noise mitigation measures include at-source mitigation...",
    "model": "granite4.1:3b",
    "tokens_used": 180
  },
  "evidence": [ {...}, {...}, {...} ],
  "glossary": { ... }
}
```

### Query: `What noise mitigation measures are proposed?` (en)
- **Before fix:** synthesis was `None` (semicolon citation validation failed)
- **After fix:** synthesis returned with LLM explanation ✅

### Frontend structure verification

| Check | Result |
|-------|--------|
| `.ai-summary-label` CSS | ✅ |
| `.ai-summary-card` CSS | ✅ |
| `.ai-summary-body` CSS | ✅ |
| `.evidence-divider` CSS | ✅ |
| `.insufficient-banner` CSS | ✅ |
| `AI Summary` label (EN) | ✅ |
| `AI 摘要` label (ZH) | ✅ |
| `Supporting Evidence` divider text (EN) | ✅ |
| `支援證據` divider text (ZH) | ✅ |

---

## 3. Visual Structure of Each Response

```
┌─────────────────────────────────────┐
│  AI SUMMARY                         │  ← .ai-summary-label
│                                     │
│  The report proposes noise barriers │  ← .ai-summary-body
│  and enclosures... [r, Ch.4, p.4] │
│                                     │
│  Model: granite4.1:3b · Tokens: 180 │
└─────────────────────────────────────┘

────────── Supporting Evidence ──────────  ← .evidence-divider

┌─────────────────────────────────────┐
│  Northern Metropolis Highway        │  ← evidence card 1
│  Report: aeiar-276-2026             │
│  Chapter: 4 · NOISE                 │
│  §4.5.4 · p.4-51 (verified)         │
│  ...                                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Development at Ngau Tam Mei        │  ← evidence card 2
│  ...                                │
└─────────────────────────────────────┘
```

---

## 4. Fallback Behaviour

### When Ollama is unavailable
- `model: "evidence-summary"`
- Yellow banner: "The retrieved evidence does not fully answer this question..."
- Structured extractive summary (not a synthesized explanation)
- Evidence cards still shown below the divider

### When claim evaluation rejects
- `evaluation.status: "rejected"`
- Red warning banner: "⚠ Some claims in this summary could not be fully verified..."
- LLM answer still shown (not discarded)
- Evidence cards shown below

### When citations are invalid
- `synthesis: null`
- Only evidence cards shown (no fake summary)

---

## 5. Test Results

| Suite | Tests | Result |
|-------|------:|--------|
| `app.py --test` | 58 | **58/58 PASS** |

---

## 6. Files Changed

- `app.py` — `_validate_synthesis()` now handles semicolon-separated multi-report citations
- `static/index.html` — new CSS, new i18n strings, updated `buildAnswerHtml()` with AI Summary card and evidence divider

---

## 7. Remaining Limitations

1. **No real-browser visual testing.** All verification was via API calls and static HTML inspection.

2. **LLM synthesis language not fully controlled.** The model may respond in English even for `zh-Hant` interface.

3. **Synthesis is non-deterministic.** Same question may produce different answers, citations, and evaluation results across requests.

4. **Evidence-summary fallback is extractive, not generative.** When Ollama is unavailable, users get structured quotations rather than a true explanation.

---

## 8. Manual Verification Steps

1. Open `http://127.0.0.1:8080/`
2. Hard refresh (Cmd+Shift-R)
3. Click 💬 chat button
4. Type `What noise mitigation measures are proposed?`
5. Verify:
   - "AI Summary" section appears at the top of the response
   - A divider line with "Supporting Evidence" separates summary from source cards
   - Evidence cards appear below the divider
6. Toggle to 繁体中文
7. Ask the same question
8. Verify "AI 摘要" and "支援證據" labels appear
