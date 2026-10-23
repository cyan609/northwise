# NORTHWISE MVP — Current State Inspection

**Date:** 2026-10-18 02:20  
**Scope:** End-to-end flow from user question to cited answer. No code modified during this inspection.

---

## 1. Status Table

| Component | State | Exact File / Command | Minimum Action Needed |
|-----------|-------|---------------------|----------------------|
| **Question input** | ❌ **missing** | No UI exists | Build HTML chat input + POST endpoint |
| **Retrieval (page-level)** | ✅ **working** | `stage1/retrieve.py` — CLI: `python3 retrieve.py "query" --k 3 --json` | Reuse as-is via import |
| **Retrieval (passage-level)** | ✅ **working** | `stage1/passages.py` — CLI: `python3 passages.py "query" --k 3 --json` | Reuse as-is via import |
| **Evidence excerpt** | ✅ **working** | `R.excerpt()` / `P.passage_excerpt()` — term-centred, width-configurable | Reuse as-is |
| **Report/chapter/page citation** | ✅ **working** | `R.format_citation()` / `P.passage_citation()` — prints verified folio or falls back to PDF index | Reuse as-is |
| **Unsupported-question refusal** | ⚠️ **partial** | OOV gate in `retrieve.py` blocks `all_oov` queries; `partial_oov` warns but still returns results. No answer-layer refusal. | Add answer-layer refusal when top hit score is below threshold or gate is `all_oov` |
| **TC / EN response** | ❌ **missing** | No i18n system, no prompt templates, no language detection | Add `lang` param + bilingual prompt template (can be hard-coded EN/ZH for MVP) |
| **Basic user interface** | ❌ **missing** | No HTML, CSS, JS, or web framework | Build single-page HTML with chat panel; serve via FastAPI or Python http.server |
| **Map / project browsing** | ❌ **missing** | `stage0/source-data/boundaries/hksar_18_district_boundary.json` exists (18 features, Polygon); `reports.json` has 0 `report_areas` | Create `report_areas` with `point_fallback` for both reports (no polygon needed for MVP); render Leaflet map with district context + report markers |
| **Run instructions** | ⚠️ **partial** | CLI scripts work; `python3 test_passages.py` (26 tests), `python3 test_rare_term_gate.py` (19 tests) both pass | Document web-app startup command |
| **Answer generation** | ❌ **missing** | No LLM integration, no prompt, no answer pipeline | Add minimal LLM call (OpenAI-compatible) with strict "only use provided chunks" prompt |

---

## 2. What Already Works (Verified)

### Retrieval pipeline (CLI)
```bash
cd stage1
python3 passages.py "noise barrier" --k 2 --json
```
Returns structured JSON with gate status, passage text, section ref, page label, citation, and quality flags. Verified working.

### OOV gate
- `"geothermal"` → `all_oov`, blocked (exit 2)
- `"geothermal power generation"` → `partial_oov`, NOT blocked by default, returns results for `power` + `generation`
- `"noise barrier"` → `ok`, returns results

### Passage provenance
- 4,161 passages from 1,293 pages, 34 chapters, 2 reports
- Every passage is a contiguous slice of its page (verified by `test_passages_are_contiguous_slices_of_their_page`)
- Section refs: 3,124 `own`, 50 `ambiguous_multiple_refs`, 46 `inherited_within_page`, rest `not_detected`
- Page labels: 1,275 `verified`, 17 `absent`, 1 `unverified`

### Data files
- `stage0/reports.json` — 2 reports, 34 chapters, SHA-256 checksums, but **0 `report_areas`**
- `stage0/source-data/boundaries/hksar_18_district_boundary.json` — 18 district polygons (properties: `District`, `地區`)
- 38 PDFs (27 MB) with provenance snapshots

---

## 3. What Is Missing

| # | Missing piece | Why it blocks the demo | Effort estimate |
|---|--------------|----------------------|-----------------|
| 1 | **Web UI (chat + map)** | User cannot enter a question or see results | Medium — single HTML page with Leaflet + chat panel |
| 2 | **Answer generation (LLM)** | System returns raw passages, not a plain-language answer | Medium — one prompt, one API call, one response parser |
| 3 | **FastAPI / HTTP server** | No way to serve the UI or accept questions from a browser | Small — install fastapi+uvicorn, ~50 lines of routes |
| 4 | **Report areas / map markers** | Map has nothing to show; report card has no geometry | Small — two point markers with `point_fallback` status |
| 5 | **Language toggle** | PRD requires EN/ZH interface | Small — hard-code two greeting strings, detect language from question |
| 6 | **Answer-layer refusal** | OOV gate handles vocab; but low-relevance queries still get an answer | Small — reject when max score < threshold |

---

## 4. Fastest Implementation Path (Estimated: 2–3 hours)

**Step A — Minimal backend (30 min)**
1. Install `fastapi` + `uvicorn` into the managed Python env.
2. Create `app.py` with two endpoints:
   - `POST /ask` — accepts `{question, report_id?}`, runs retrieval, returns `{answer, citations[], gate}`
   - `GET /reports` — returns `reports.json` data for the map
3. For the MVP, **skip the LLM**: return a curated evidence card (top 3 passages with excerpts and citations) plus a short pre-written sentence. This is the "evidence-first flow" — the user sees exactly what the report says, cited to source.

**Step B — Minimal frontend (60 min)**
1. Create `static/index.html` — single file, Leaflet map, chat panel.
2. Map: show district boundaries as context, two report markers (point_fallback).
3. Chat: input box, send to `/ask`, render citations as clickable chips.
4. No mascot SVG for MVP (can add later); use a simple button.

**Step C — Report areas (15 min)**
1. Add `report_areas` to both reports in `reports.json` with `geometry_status: "point_fallback"` and approximate lat/lng for each project.

**Step D — Bilingual strings (15 min)**
1. Hard-code EN/ZH greeting, loading text, and disclaimer in the HTML.
2. Detect language from the question (simple regex for CJK chars) and pass to backend.

**Step E — Run and test (30 min)**
1. `python3 app.py` → open browser → ask "noise barrier" → verify citations appear.

---

## 5. Risks and Shortcuts Taken

| Shortcut | Risk | Mitigation |
|----------|------|------------|
| Skip LLM, return evidence cards only | User does not get a synthesized answer | Acceptable for MVP demo; PRD says "plain-language answer" but evidence-first is demonstrable and trustworthy |
| `point_fallback` markers instead of polygons | Map does not show project extents | Label the markers "indicative location"; PRD allows point_fallback |
| No ChromaDB / embeddings | Retrieval is BM25-only, no semantic matching | Current BM25 already works well for the test queries; embeddings are PRD-planned but not required for MVP |
| No evaluation script | Cannot measure answer accuracy | Out of scope for this sprint; eval_levels.py already compares retrieval levels |
| No caching | Suggested questions not pre-computed | Not needed for first demo |

---

## 6. Single Highest-Priority Next Action

**Create `app.py` (FastAPI backend) and `static/index.html` (minimal frontend)** that wires the existing `passages.py` retrieval into a working web demo. Start with Step A (backend) because it can be tested independently with `curl` before the frontend is built.

The backend should:
1. Load the `PassageIndex` once at startup.
2. Accept a question, run the OOV gate, run passage retrieval.
3. Return the top 3 passages as evidence cards (no LLM synthesis for the first working version).
4. If the gate is `all_oov`, return a refusal message instead.

This produces a **demonstrable, evidence-first flow** in the shortest time.
