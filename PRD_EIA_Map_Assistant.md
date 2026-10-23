# PRD: Map-based EIA Assistant for the Northern Metropolis (name TBD)

*Version 0.1 – draft for team confirmation. Built entirely through vibe coding.*

## 1. Overview

**One-liner.** A map-based GenAI assistant that helps Northern Metropolis residents find, understand and verify official EIA reports, with every answer cited to its source.

**Problem.** EIA reports are long, split into many files and written for specialists, so public consultation is open in principle but inaccessible in practice.

**Users.** Residents and community groups with no technical background; staff at community venues who help them.

**Success for the prototype.** (1) A working demo of the full flow on a phone. (2) Measured answer accuracy, citation accuracy and refusal accuracy on a test set. (3) Tested with at least a few non-specialist users.

## 2. Scope

**In scope (MVP):** map entry, prepared report database, Q&A with citations, refusal when unsupported, report cards, topic shortcuts, English/Chinese interface, evaluation script, QR-code access.

**Out of scope:** user uploads, comment submission, policy or legal judgments, own impact predictions, reliable reading of figures and complex tables, official translations, login/accounts, question analytics for organisations (shelved for later).

## 3. User flow

1. User scans a QR code on a printed map, or opens the web link.
2. User sees a map of the Northern Metropolis, with a label for each EIA report placed at its report area.
3. User taps a label; **the report area(s) light up** and the report card opens (name, date, links to original and executive summaries).
4. User taps "Ask about this report" on the card, or taps the black-faced spoonbill button; the chat panel opens, scoped to the selected report (or all reports).
5. User taps a topic shortcut or types a question.
6. System returns a plain-language answer with citations (report, chapter, page).
7. User taps a citation to open the original document.

## 4. Features and acceptance criteria

| ID | Feature | Acceptance criteria |
| --- | --- | --- |
| F1 | **Map** | Shows a map of the Northern Metropolis with **administrative district outlines as context only** (the relevant Yuen Long and North District features from the official HAD 18-district GeoJSON). The district outlines are administrative context, **not an official Northern Metropolis boundary**; their union is not presented as the official boundary. Every included report appears as one label placed at its report area. Tapping (or clicking) a label selects that report: **its report area(s) are highlighted — not the whole district** — the report card opens, and Q&A is scoped to that report. A report with more than one report area still has one label; selecting it highlights all of its report areas. A report area is shown as a polygon only when the polygon can be traced to an official project layout or planning map, with its source recorded and `geometry_status: "indicative"`; otherwise the report is shown as a clearly labelled point marker whose position is also traceable to an official source (`geometry_status: "point_fallback"`). Districts are never used to establish Northern Metropolis eligibility (see `nm_scope_evidence`). Labels must not overlap and must stay readable on a phone screen. Boundaries and report areas are labelled "indicative, not official". Works with touch and mouse. The map fills the whole screen; all other interface elements float over it (see DESIGN.md). |
| F2 | **Report card** | Shows title, date, project area, link to original report, links to English and Chinese executive summaries where they exist. When a summary is not available, the card shows "Executive summary: not available" (zh: 沒有行政摘要) in place of a link. All data comes from one metadata file. |
| F3 | **Q&A** | Free-text question in English or Chinese. Retrieval is restricted to the selected report (or all reports if none selected). Answer is plain language, short, and written in the language of the question. |
| F4 | **Citations** | Every factual statement in an answer is tied to at least one source chunk. Each citation shows report, chapter, section and page where the source has verified page numbers; otherwise chapter and section only, with no page shown. It opens the original EPD file in a new tab at that page or section where possible (the app does not host or embed report files), with EPD acknowledged as the source. An answer with no valid citation is not shown. |
| F5 | **Refusal** | If retrieved text is not relevant enough, the system replies that the reports do not contain the answer, suggests the nearest relevant chapter, and links to the original. It must never answer from general knowledge. |
| F6 | **Topic shortcuts** | Buttons for Noise, Ecology, Water, Air, Landscape, Waste and Cultural heritage; each shows 3 suggested questions per report, stored in a config file. |
| F7 | **Language toggle** | Interface available in English and Traditional Chinese. |
| F8 | **Disclaimer and privacy notice** | Visible note: answers are AI-generated summaries, the official report prevails; no login, no personal data collected. |
| F9 | **Evaluation script** | Runs a test set (CSV) through the system and outputs answer correctness, citation correctness and refusal correctness. |
| F10 | **Chat panel and spoonbill button** | A black-faced spoonbill button sits at the bottom-right (phone) or bottom-left (computer) of the full-screen map and opens the chat panel (bottom sheet on phone, left-side panel on computer). The panel header shows a scope chip (selected report or all reports) that the user can remove. The map stays visible and keeps its state when the panel is closed. The button has a text label and a first-visit hint so users know they can ask questions. |

## 5. Data

**Reports (initial 2).** Northern Metropolis Highway – San Tin Section EIA (AEIAR-276/2026) and Development at Ngau Tam Mei Area EIA (AEIAR-271/2025). The dataset is designed to grow: any additional report must be an approved EIA from the EPD register, for a project demonstrably located within or directly related to an area in the official Northern Metropolis four-zone definition (nm.gov.hk), and must pass the ingestion scope gate below. Source: EPD public website; reports are published as separate chapter files (PDF and/or HTML), so ingestion must fetch and merge all main-text chapters. Figures and appendices are excluded from the MVP.

**reports.json (report registry, hand-maintained, one entry per report).**

| Field | Required | Notes |
|---|---|---|
| `report_id` | yes | Stable key; never changes |
| `register_no` | yes | e.g. AEIAR-276/2026 |
| `status` | yes | Only `approved` may be ingested |
| `approval_date` | yes | |
| `title_en`, `title_zh` | yes | |
| `project_area_en`, `project_area_zh` | yes | |
| `districts[]` | yes | Internal district IDs (`hk-district:{code}`) for context and filtering only; **never establishes Northern Metropolis eligibility** |
| `report_areas[]` | yes | Areas highlighted when the report is selected: `{area_id, name_en, name_zh, area_type, geometry, source_url, ozp_plan_no?, geometry_status}`. `area_type`: `project_area` \| `planning_scheme_area` \| `point`. `geometry`: GeoJSON Polygon or Point. `geometry_status`: `"indicative"` (Polygon traced to an official project layout or planning map) \| `"point_fallback"` (Point used when no defensible polygon exists; position must also be traceable to an official source). |
| `label_lat`, `label_lng` | yes | Where the single label sits |
| `original_url` | yes | Official EPD project page |
| `exec_summary_en_url`, `exec_summary_zh_url` | nullable | `null` = not available |
| `page_numbering` | yes | `printed` \| `pdf_index` \| `none` \| `unverified` |
| `nm_scope_evidence` | yes | `{zone, area, url}` from nm.gov.hk; establishes Northern Metropolis eligibility |
| `chapters[{number, title, format, file_url}]` | yes | `format`: `pdf` or `html` |
| `version`, `retrieved_at`, `checksum` | yes | Change detection and re-indexing |

`report_areas[]` drives the map highlight. `districts[]` provides administrative context and filtering only. `nm_scope_evidence` is the sole evidence of Northern Metropolis eligibility. Internal IDs use `hk-district:{code}`, `nm-zone:{slug}` and `nm-area:{slug}`; they are internal identifiers, not official identifiers. District boundaries come from the official HAD 18-district GeoJSON and are context only — their union is not presented as the official Northern Metropolis boundary.

**Geometry/status validation rule.** Reject a registry entry unless:
- `geometry_status = "indicative"` → `geometry.type = "Polygon"` and `source_url` is an official project-layout or planning-map URL;
- `geometry_status = "point_fallback"` → `geometry.type = "Point"` and `source_url` is an official source for the point's position;
- no other `geometry_status` value is accepted.

**Chunk schema.** `chunk_id, report_id, chapter_number, chapter_title, section_heading, section_ref` (e.g. "3.4.2"; always present), `page_label` (printed page label if the report has one, else null), `pdf_page_index` (index within the chapter file, else null), `source_url`, `anchor_url` (deep link to the cited page or section where possible, else null), `page_verified` (true only once the page label has been verified against the original source file — see pipeline step 6), `text`. Chunks are about 500–800 words, split at section headings where possible.

**Pipeline (offline, run once per report; a new version atomically replaces all chunks for that `report_id`).**

1. **Scope gate.** Proceed only if `status = approved`, `nm_scope_evidence` is present, and every URL passes the official-source rules: the EPD project page (`original_url`) **and each chapter file URL in `chapters[]`** must be official EPD URLs. Validating the project page alone does not validate the document URLs; any non-official URL rejects the report with a reason.
2. Download chapter files; record checksums.
3. Extract text per page; detect the page-numbering mode (printed labels / PDF index only / none) and set `page_numbering`. If it cannot be determined, record `unverified` — never invent page numbers.
4. Clean; chunk with metadata per the chunk schema.
5. Embed; store in the vector database with `report_id` metadata.
6. **Validate before publish.** Two distinct checks:
   - *Extraction-quality sampling* (general): all chapters present, chunk count > 0, every chunk has a `section_ref`, and page-label extraction spot-checked on a sample.
   - *Citation verification* (per displayed citation): a page number may be shown as verified (`page_verified = true`) only if it maps to the corresponding page in the original source file. Unverified page numbers must never be presented as verified.
7. **Record the run.** `report_id`, version, checksums, chapter/page counts, chunk count, `page_numbering`, date.

## 6. System design (simple, vibe-code friendly)

- **App:** FastAPI backend serving a single-page frontend (plain HTML/JS with Leaflet), responsive for phone and computer. A WorkBuddy test confirmed that the map, label click, two-region highlight and browser preview work.
- **Map:** Leaflet-based map (e.g. folium) with two layers: (1) administrative district polygons from the official HAD 18-district GeoJSON, filtered to the relevant Northern Metropolis districts and used as context only — their union is not drawn or labelled as the official Northern Metropolis boundary; (2) report areas from `reports.json → report_areas[]`. One label per report at its hand-set position; selecting a label highlights that report's `report_areas[]`, not its districts. A report area is drawn as a polygon only when traced to an official project layout or planning map (`geometry_status: "indicative"`); otherwise a labelled point marker is used (`geometry_status: "point_fallback"`), positioned only from a traceable official source.
- **Retrieval:** multilingual embedding model, ChromaDB (local), metadata filter by `report_id`, top-k chunks, optional rerank.
- **LLM:** accessed through one OpenAI-compatible interface, with model name and endpoint in a config file so local and cloud models can be swapped without code changes.
- **Answer flow:** question → retrieve → relevance check → generate with a strict prompt that only allows use of provided chunks and requires chunk IDs → validate that cited IDs exist in retrieved chunks → render answer with citation links, or refuse.
- **Logging:** none by default (no user data stored). Evaluation runs write to local files only.

## 7. Non-functional requirements

- Responsive: works on both phone and computer browsers with no installation; first screen loads in a few seconds.
- **Layout (map-first).** The map is the main canvas on both phone and computer; every other element floats over it. Phone: the map fills the screen, and the report card and chat panel open as expandable sheets over it (about 40% and about 75% of screen height), closing back to the map with state kept; large touch targets. Computer: the map stays the main canvas, the chat panel sits on the **left** (about 400px wide), and the report card floats at the top-right. Reports are selected from their map labels. Exact panel geometry is specified in DESIGN.md §5.
- Tested on at least one iPhone/Android phone and one laptop browser before each milestone; plain wording throughout.
- Reasonable answer time on the demo setup; answers cached for suggested questions.
- A fallback demo (recorded video and screenshots) is prepared in case of network failure.
- PDPO-aware by design: no login, no personal data stored, privacy notice shown.

## 8. Evaluation plan

- Test set of 30–50 questions: about 70% answerable (with expected source chapter/page), about 30% unanswerable or out of scope, in English and Chinese, covering all topic areas, written with input from the environmental team members.
- Metrics: answer correctness (manual 0/1/2), citation correctness (cited page supports the claim), refusal correctness (declines when it should, answers when it should), plus Chinese-vs-English comparison.
- Small user test: 5–8 non-specialist users, one task each (e.g. "find out whether this project affects noise near your home"); record success, time and confusion points.

## 9. Build stages (each ends with a working, testable result)

| Stage | Goal | Done when |
| --- | --- | --- |
| 0 | Data preparation | The two named reports downloaded; page-numbering mode verified and recorded for each; executive-summary availability recorded (may be "not available"); reports.json created per the registry schema; district IDs resolved against the district boundary source |
| 1 | Core Q&A (command line) | Ask a question, get a cited answer or refusal; 10 manual checks pass |
| 2 | Web interface | Same flow works in a browser on a phone |
| 3 | Map and report cards | Map markers open report cards; Q&A scoped to the selected report |
| 4 | Topic shortcuts, language toggle, disclaimer | F6–F8 complete |
| 5 | Evaluation | Test set run, results recorded, prompts and retrieval tuned |
| 6 | Demo readiness | QR code access tested on a phone, fallback prepared, remaining reports added |

## 10. Risks

| Risk | Mitigation |
| --- | --- |
| Phones cannot reach a locally hosted app at the demo | Decide hosting early; test with a phone hotspot; prepare fallback video |
| Wrong or unsupported answers | Chunk-bound prompting, citation validation, refusal threshold, evaluation set |
| Chinese questions on English documents perform poorly | Multilingual embeddings; test early; state limits honestly |
| Tables, maps and figures extract badly | Exclude from scope; point users to original pages |
| Several labels crowd the same district, especially on a phone | Hand-set label positions, short label text, offset or cluster labels; test on a small screen |
| Report-area geometry cannot be traced to an official layout or planning map | Use a clearly labelled point marker (`geometry_status: "point_fallback"`), positioned from a traceable official source; never approximate a polygon or invent coordinates |
| Page numbers do not match printed numbering | Store both printed label and PDF index; verify on samples; where page numbers are absent or unverifiable, cite section references only and state the limitation honestly |
| Documents change or are removed | Show report date and source link; re-index when updated |
| Copyright and reuse terms for EPD documents (EPD allows non-commercial reproduction with acknowledgement; commercial use needs written authorization; some content may carry third-party copyright) | Link out to EPD, show only short excerpts, acknowledge EPD, keep the database internal, seek written authorization before any commercial deployment |

## 11. Open decisions (for team confirmation)

1. LLM: local model or cloud API, and where the app is hosted for the demo.
2. Settled: initial reports are Northern Metropolis Highway – San Tin Section (AEIAR-276/2026) and Development at Ngau Tam Mei Area (AEIAR-271/2025); future additions must pass the ingestion scope gate.
3. Settled: administrative context uses the official HAD 18-district GeoJSON (`hksar_18_district_boundary.json`), filtered to Yuen Long and North Districts for the initial view; these district polygons are context only and their union is not presented as the official Northern Metropolis boundary. The primary highlight uses `report_areas[]`, not districts. Internal IDs use `hk-district:{code}`, `nm-zone:{slug}` and `nm-area:{slug}` and are not official identifiers. Authoritative OZP boundary integration remains a future option, subject to verifying the dataset schema and licence terms.
4. Level of Chinese support at launch (interface only, or full Chinese Q&A).
5. Settled: app framework is FastAPI + Leaflet.