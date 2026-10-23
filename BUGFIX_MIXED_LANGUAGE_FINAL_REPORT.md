# Mixed-Language Input Bug Fix — Final Report

**Date:** 2026-10-18  
**Server:** http://127.0.0.1:8080/ (PID 41667)  
**Tests:** 161/161 PASS

---

## 1. Confirmed Root Cause

The backend `ask()` function originally used `lang` (interface language) to **route retrieval**, creating a hard coupling between UI language and query processing:

| Interface `lang` | Question language | Path taken | Result |
|---|---|---|---|
| `"zh-Hant"` | English | Chinese branch → `_map_chinese_terms()` | `chinese_unsupported` refusal (no Chinese phrases found) |
| `"en"` | Chinese | English branch → BM25 gate | `empty_query` refusal (Chinese chars stripped as non-word tokens) |

**First fix (2026-10-18 earlier session):** Added `query_lang = detect_lang(question)` and changed routing from `if lang == "zh-Hant"` to `if query_lang == "zh-Hant"`. This fixed pure-language crossovers (EN question on ZH interface, ZH question on EN interface).

**Remaining issue discovered in this session:** Mixed CJK+EN project questions (e.g. `"這個項目的NSR有哪些？"`) were still falling back to `glossary_only` with **0 evidence**. The Chinese branch's `_map_chinese_terms()` returned `None` (no Chinese topic phrases like "噪音" or "生態" found), and the code immediately checked `glossary_entry` before attempting any retrieval. Project-specific questions should get EIA evidence, not just glossary definitions.

**Root cause of remaining issue:** The Chinese branch had no fallback to English BM25 retrieval when the Chinese topic map failed to match.

---

## 2. Files Changed

**`app.py`** — Two changes total (~25 lines):

### Change 1: Query-language routing (from earlier session)
- Added `query_lang = detect_lang(question)` at line 510
- Changed routing condition from `if lang == "zh-Hant"` to `if query_lang == "zh-Hant"` at line 544
- `lang` controls response language (glossary definitions, i18n strings)
- `query_lang` controls retrieval routing (Chinese mapping vs English BM25)

### Change 2: English BM25 fallback in Chinese branch (this session)
- In the `else` block of `if query_lang == "zh-Hant"` (when `_map_chinese_terms()` returns `None`):
  - **Before:** immediately checked `glossary_entry` → glossary_only or refused
  - **After:** runs `CORPUS.gate(stripped)` first. If gate status is not `empty_query` or `all_oov`, uses English search terms for retrieval. Only falls back to glossary-only if the gate also finds nothing.

This allows mixed CJK+EN questions like `"這個項目的NSR有哪些？"` to have their English terms (`NSR`) extracted by the BM25 gate and used for retrieval, while still preserving the refusal for genuinely unsupported Chinese-only questions like `"甚麼是地質？"`.

No frontend changes. No new dependencies.

---

## 3. Actual Endpoint Responses for All Failing Scenarios

### Scenario 1: English interface + Chinese glossary question
```
POST {"question":"甚麼是噪音敏感受體？","lang":"en"}
→ refused=False, gate=mapped, glossary=True, evidence=3
→ message="Here are the most relevant passages..." (EN)
→ definition language: English ✅
```

### Scenario 2: English interface + Chinese project question
```
POST {"question":"這個項目對噪音敏感受體有什麼影響？","lang":"en"}
→ refused=False, gate=mapped, glossary=True, evidence=3
→ message="Here are the most relevant passages..." (EN)
```

### Scenario 3: Traditional Chinese interface + English glossary question
```
POST {"question":"What is an NSR?","lang":"zh-Hant"}
→ refused=False, gate=ok, glossary=True, evidence=3
→ message="以下是官方環評報告中最相關的段落..." (ZH)
→ definition language: Chinese ✅
```

### Scenario 4: Traditional Chinese interface + English project question
```
POST {"question":"What NSRs are affected by this project?","lang":"zh-Hant"}
→ refused=False, gate=ok, glossary=False, evidence=3
→ message="以下是官方環評報告中最相關的段落..." (ZH)
```

### Scenario 5: Mixed CJK+EN project question (NEW FIX)
```
POST {"question":"這個項目的NSR有哪些？","lang":"en"}
→ refused=False, gate=ok, glossary=True, evidence=3
→ Previously: glossary_only, 0 evidence ❌
→ Now: ok, 3 evidence ✅
```

### Scenario 6: Mixed CJK+EN project question 2 (NEW FIX)
```
POST {"question":"這個項目對PM2.5有什麼影響？","lang":"en"}
→ refused=False, gate=ok, glossary=True, evidence=3
→ Previously: glossary_only, 0 evidence ❌
→ Now: ok, 3 evidence ✅
```

### Scenario 7: Unsupported Chinese question (must still refuse)
```
POST {"question":"甚麼是地質？","lang":"en"}
→ refused=True, gate=chinese_unsupported
→ message="Chinese retrieval is currently limited to supported topic terms..."
→ Correctly refused ✅
```

---

## 4. Regression-Test Results

| Suite | Tests | Result |
|-------|------:|--------|
| `app.py --test` | 58 | **58/58 PASS** |
| `stage1/test_passages.py` | 26 | **26/26 PASS** |
| `stage1/test_rare_term_gate.py` | 19 | **19/19 PASS** |
| `stage1/test_citation_reliability.py` | 58 | **58/58 PASS** |
| **Total** | **161** | **161/161 PASS** |

New tests added in this session:
- `test_mixed_lang_cjk_en_project_retrieval` — Mixed `"這個項目的NSR有哪些？"` gets evidence
- `test_mixed_lang_cjk_en_project_retrieval_pm25` — Mixed `"這個項目對PM2.5有什麼影響？"` gets evidence
- Updated `test_mixed_lang_unsupported_still_refused` — Also verifies Chinese-only unsupported refusal

---

## 5. Browser Verification Results

| Check | Result |
|-------|--------|
| Served HTML identical to on-disk `static/index.html` | ✅ |
| Frontend `submitChat()` sends `{question: q, lang: lang}` | ✅ |
| No old refusal message hardcoded in frontend | ✅ |
| Evidence citations include chapter, page_label, pdf_page_index, source_url | ✅ |

Browser cache note: If a user previously loaded the app before this fix, their browser may cache the old backend responses. A hard refresh (Cmd+Shift+R / Ctrl+F5) or clearing browser cache will ensure the latest backend behaviour is observed.

---

## 6. Remaining Limitations

1. **`detect_lang()` is a simple CJK check.** A question with zero CJK characters is classified as English even on a zh-Hant interface. This is correct for BM25 routing.

2. **`_TC_TOPIC_MAP` has only 11 Chinese phrases.** Chinese-only project questions that don't contain any of these phrases (e.g. `"甚麼是地質？"`) are still refused unless they contain English technical terms that the BM25 gate can extract.

3. **Synthesis (Ollama) language is not controlled.** The LLM may respond in English even when `lang="zh-Hant"`. This is an existing limitation.

4. **No thumbnail generation.** Evidence items lack `thumbnail_url`. Pre-existing.

5. **No real-browser interactive testing.** All verification was API-level and static HTML inspection.

---

## 7. Manual Verification Steps

1. Open `http://127.0.0.1:8080/` in a browser
2. **Hard refresh** (Cmd+Shift+R / Ctrl+F5) to clear any cached responses
3. Toggle interface to **English**
4. Type `"甚麼是噪音敏感受體？"` → should get glossary card with **English** definition + 3 evidence cards
5. Type `"這個項目的NSR有哪些？"` → should get glossary card + **3 evidence cards** (not just glossary)
6. Toggle interface to **Traditional Chinese**
7. Type `"What is an NSR?"` → should get glossary card with **Chinese** definition + 3 evidence cards
8. Type `"What NSRs are affected by this project?"` → should get **3 evidence cards** (no glossary), message in Chinese
9. Type `"甚麼是地質？"` → should show refusal message
