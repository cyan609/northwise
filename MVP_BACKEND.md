# NORTHWISE MVP Backend — Implementation Summary

**Date:** 2026-10-18  
**Scope:** Smallest runnable evidence-first Q&A backend over official EIA report passages.

---

## Files Created

| File | Description |
|------|-------------|
| `app.py` | Backend: stdlib HTTP server, `POST /ask`, `GET /`, `GET /reports`. Reuses `stage1/passages.py` and `stage1/retrieve.py`. |
| `static/index.html` | Minimal bilingual chat UI (EN / 繁). No framework, no build step. |

## Files Unchanged

All existing files preserved: `stage1/*.py`, `stage1/data/*.jsonl`, `stage0/reports.json`, `PRD_EIA_Map_Assistant.md`, `DESIGN.md`.

---

## How to Run

```bash
cd /Users/chloeyan/workbuddy-ai/NORTHWISE
python3 app.py --port 8080
```

Then open `http://localhost:8080` in a browser, or test with curl:

```bash
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"noise barrier"}'
```

---

## Endpoint: POST /ask

**Request body:**
```json
{"question": "noise barrier", "lang": "en"}
```
(`lang` is optional; auto-detected from CJK presence if omitted.)

**Success response:**
```json
{
  "question": "noise barrier",
  "lang": "en",
  "refused": false,
  "message": "Here are the most relevant passages...",
  "disclaimer": "AI-generated excerpt. The official report prevails.",
  "gate": {"status": "ok", "message": "...", "blocked": false, ...},
  "evidence": [
    {
      "rank": 1,
      "score": 13.3749,
      "passage_id": "aeiar-276-2026|c4|p30|s3",
      "passage_type": "prose_paragraph",
      "report_id": "aeiar-276-2026",
      "report_title": "Northern Metropolis Highway – San Tin Section",
      "chapter": 4,
      "chapter_title": "NOISE",
      "section_ref": "4.5.4.10",
      "section_ref_status": "own",
      "page_label": "4-28",
      "page_label_status": "verified",
      "pdf_page_index": 30,
      "viewer_page": 31,
      "source_url": "https://www.epd.gov.hk/eia/files/.../eia_ch04_out.pdf",
      "citation": "[aeiar-276-2026 · Ch.4 NOISE · §4.5.4.10 · p.4-28 · PDF idx 30 (viewer p.31) · verified · passage s3 prose_paragraph]",
      "excerpt": "Use of Temporary Noise Barriers and Noise Enclosures 4.5.4.10 Movable noise barriers...",
      "quality_flags": [],
      "matched_terms": ["noise", "barrier"],
      "query_terms_total": 2
    }
  ]
}
```

**Refusal response (all-OOV):**
```json
{
  "question": "geothermal",
  "lang": "en",
  "refused": true,
  "message": "The reports do not contain information about 'geothermal'...",
  "gate": {"status": "all_oov", "blocked": true, ...},
  "evidence": []
}
```

---

## Test Results

```
python3 app.py --test
```
→ 8/8 pass

- `test_supported_query_returns_evidence` — 3 cards, all required fields present
- `test_all_oov_query_is_refused` — blocked, no evidence, message mentions the term
- `test_empty_query_is_refused` — empty_query status, no evidence
- `test_chinese_question_detected` — CJK input → `lang: "zh-Hant"`
- `test_citation_includes_page_label_when_verified` — verified folio appears in citation
- `test_source_url_is_official_epd` — every source_url starts with `https://www.epd.gov.hk/`
- `test_evidence_is_labeled_not_answer` — message explicitly states "not a synthesized answer"
- `test_gate_exposed_in_response` — gate object always present

All existing tests also pass: 26 passage tests + 19 gate tests = 45/45.

---

## Known Limitations (Honest)

1. **Chinese query terms are not searchable.** The tokenizer is English-only; a question like `噪音屏障` returns `empty_query` because no content terms survive tokenization. The UI can still be in Chinese, and English questions work fine.
2. **No LLM synthesis.** Responses are evidence excerpts, not plain-language answers. This is by design for the evidence-first MVP.
3. **No map.** `reports.json` has no `report_areas`; the frontend is a chat panel only.
4. **No report scoping.** The `/ask` endpoint searches all reports; per-report filtering is not wired yet.
5. **Relevance threshold is coarse.** `MIN_SCORE = 1.0` is a simple guard; edge cases may slip through.
