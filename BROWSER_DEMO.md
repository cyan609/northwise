# NORTHWISE Browser Demo — Implementation Report

**Date:** 2026-10-18  
**Scope:** Full browser demo with map, report cards, topic shortcuts, and evidence-first Q&A.

---

## What Was Built

### 1. Report Scoping (backend)
- `POST /ask` now accepts an optional `report_id` field.
- When provided, retrieval is restricted to passages from that report only.
- Unknown `report_id` returns HTTP 400.
- Test: `test_report_scoping_limits_results` verifies scoped results contain only the selected report.

### 2. Leaflet Map
- Full-screen OpenStreetMap base layer.
- District boundary overlay: Yuen Long District and North District from the official HAD 18-district GeoJSON.
  - Styled as light outline with 3% fill (administrative context only, not presented as official NM boundary).
- Two report markers (orange circleMarkers) at approximate `point_fallback` locations:
  - **San Tin** (AEIAR-276/2026): 22.50°N, 114.07°E
  - **Ngau Tam Mei** (AEIAR-271/2025): 22.47°N, 114.05°E
  - Labels state these are indicative locations, not official project boundaries.

### 3. Report Card
- Floating card at top-right (phone: would be bottom sheet; desktop: top-right as implemented).
- Shows: report title (EN/ZH), register number, project area, approval date.
- Links: EPD project page, English executive summary, Chinese executive summary.
- Primary button: "Ask about this report" — opens chat panel and scopes Q&A to that report.
- Close button returns to map view.

### 4. Chat Panel
- Bottom-right floating panel (phone: would be bottom sheet; desktop: bottom-right as implemented).
- Scope chip shows selected report (click to clear → search all reports).
- Topic shortcut pills: Noise, Ecology, Water, Waste, Cultural Heritage, Landscape — 6 pills with emoji icons, each pre-filled with a relevant question.
- Text input with Enter-to-submit.
- Renders up to 3 evidence cards with excerpts, citations, source links, and disclaimers.
- Refusal card for empty/all-OOV/low-relevance queries.

### 5. Bilingual UI
- Language toggle EN / 繁 in the top bar.
- All UI strings, topic questions, and refusal messages have EN and zh-Hant versions.
- Auto-detects language from CJK presence in the question.

---

## Files Modified / Created

| File | Action | Notes |
|------|--------|-------|
| `app.py` | **Modified** | Added `report_id` to `ask()` and POST handler; added `test_report_scoping_limits_results` |
| `static/index.html` | **Rewritten** | Full Leaflet map + report cards + chat panel + topic shortcuts |

---

## How to Run

```bash
cd /Users/chloeyan/workbuddy-ai/NORTHWISE
python3 app.py --port 8080
```

Open `http://localhost:8080` in a browser.

**Test with curl:**
```bash
# Scoped search
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"noise barrier","report_id":"aeiar-271-2025"}'

# All reports
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"noise barrier"}'
```

---

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| app.py (backend) | 9 | ✅ all pass |
| stage1/test_passages.py | 26 | ✅ all pass |
| stage1/test_rare_term_gate.py | 19 | ✅ all pass |
| **Total** | **54** | **✅ all pass** |

---

## Sample Response (Scoped)

```json
{
  "question": "noise barrier",
  "lang": "en",
  "report_id": "aeiar-271-2025",
  "refused": false,
  "message": "Here are the most relevant passages...",
  "evidence": [
    {
      "rank": 1,
      "report_id": "aeiar-271-2025",
      "report_title": "Development at Ngau Tam Mei Area",
      "chapter": 4,
      "chapter_title": "NOISE",
      "section_ref": "4.5.4.10",
      "page_label": "4-28",
      "page_label_status": "verified",
      "pdf_page_index": 30,
      "source_url": "https://www.epd.gov.hk/eia/files/.../s4_noise.pdf",
      "citation": "[aeiar-271-2025 · Ch.4 NOISE · §4.5.4.10 · p.4-28 · ...]",
      "excerpt": "Use of Temporary Noise Barriers and Noise Enclosures..."
    }
  ]
}
```

---

## Remaining Gaps (Honest)

1. **No LLM synthesis.** Responses are evidence excerpts only. The PRD calls for "plain-language answers" — this is the next step if time allows.
2. **Chinese query terms are not searchable.** The tokenizer drops CJK characters; Chinese questions return `empty_query`.
3. **No project-area polygons.** Markers are `point_fallback` only; no official geometry was obtainable.
4. **Layout is desktop-leaning.** The floating panels work on desktop; phone layout needs bottom-sheet styling.
5. **No caching.** Topic shortcuts are not pre-computed.
6. **No evaluation script.** PRD F9 (test set runner) is not built.
