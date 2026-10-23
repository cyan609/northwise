# STAGE 0 INVENTORY — official EIA source verification

Step 1 of Stage 0 (data preparation). Generated from the downloaded files and the page-numbering probe. Manifest: `source-data/download_manifest.json` (machine) and `source-data/file_manifest.csv` (flat table).

## Method (what was actually done)

1. Fetched each official EPD project page, then followed its `[環境影響評估報告]` link to the report index page.
2. Read the chapter list from the report's own `list of main text (PDF)` page. Every chapter URL below was copied from that page — none was constructed.
3. Downloaded each file with `curl`/urllib, recorded HTTP status, byte size, SHA-256 and a UTC timestamp; saved the project page, report index and chapter list HTML as provenance snapshots.
4. Opened every PDF and read per-page text with macOS PDFKit (built in). No PDF library was installed.
5. Determined page numbering from the token that immediately precedes the `<Month> <Year>` footer on each page, then compared it with the 1-based viewer index and checked the raw PDF for a `/PageLabels` tree.

## AEIAR-276-2026 — Northern Metropolis Highway – San Tin Section

- Chinese title: 北都公路 – 新田段
- Project page: https://www.epd.gov.hk/eia/tc/alpha/aspd.php?id=955
- Report index: https://www.epd.gov.hk/eia/files/applications/en/pp_955/eia_6390/progress/action_180296/NMHST%20v3/cover_page_pdf.htm
- Status: Conditionally approved 12 August 2026 (per project page); permit EP-681/2026
- Files: 18 (16 chapter files + 2 executive summaries), 13.27 MB

**Page numbering: `printed`** — Printed folios are compound chapter-page labels (e.g. 2-1, 1-1-i) and are NOT the PDF viewer page index. 705/723 pages numbered (97.5%); some pages are genuinely unnumbered.

| # | Chapter (as listed by EPD) | File | Pages | MB | SHA-256 |
|---|---|---|---|---|---|
| 1 | INTRODUCTION | `eia_ch01_out.pdf` | 7 | 0.25 | `d83b2e09490fc235e5009d0607eb79031d57971a65b4c38cd3a1374ab8aac909` |
| 2 | PROJECT DESCRIPTION | `eia_ch02_out.pdf` | 35 | 0.50 | `d707488b2bfea68171f67263a8ded287df3f16598cd1f571ec3d75885c053721` |
| 3 | AIR QUALITY | `eia_ch03_out.pdf` | 66 | 0.96 | `2e384e16b1033118b745169e5c236d1fcc2020516d980e7f4c7bdc953c4a0929` |
| 4 | NOISE | `eia_ch04_out.pdf` | 62 | 0.76 | `ce4158a00a73c615cddeff93f92330cbbedcc9c9978c2616f5a8e7c9ba1887d5` |
| 5 | WATER QUALITY | `eia_ch05_out.pdf` | 39 | 0.55 | `5d0d4b39283d55ea989a46055bef6301c97f4781c31e3d8d5799f0c37dce8ac5` |
| 6 | WASTE MANAGEMENT IMPLICATIONS | `eia_ch06_out.pdf` | 28 | 0.40 | `57e9147f72f29c9c7f1585842d381c554821c83a1d6edbd4ed8fc64840a7c94c` |
| 7 | LAND CONTAMINATION | `eia_ch07_out.pdf` | 55 | 0.85 | `2e0eff44a3b80c7cd619ef07098bd27650a0d4f6f80ac6e902d66dc3df866bfe` |
| 8 | ECOLOGY | `eia_ch08_out.pdf` | 124 | 1.37 | `29aba05f30777d6c49341152f4c1c81dca130be607ef87a24526397b31ff0564` |
| 9 | FISHERIES | `eia_ch09_out.pdf` | 21 | 0.39 | `225eea57423fe1e1df1b4097c68c18d17188db898e8582b67492d69f62fb48fd` |
| 10 | LANDSCAPE AND VISUAL IMPACT | `eia_ch10_out.pdf` | 137 | 1.28 | `5d9d42c072331d11fa767bbe1a47762eeaa435e05fdad3c726be791b24ec0059` |
| 11 | CULTURAL HERITAGE | `eia_ch11_out.pdf` | 25 | 0.64 | `8e2e00f2760d146a25122463efabc235c0969d99890b4bcd694f64c78adff60f` |
| 12 | HAZARD TO LIFE | `eia_ch12_out.pdf` | 89 | 2.09 | `035c5963caa4b0f5516018f48a8aed03f20e8cf87fe3a870a3225917c0c4641f` |
| 13 | ENVIRONMENTAL MONITORING AND AUDIT REQUIREMENTS | `eia_ch13_out.pdf` | 7 | 0.26 | `e27e1717c08b5e959d672cdc37fd1957b6e1024c5dda256d960fd329e453b2f2` |
| 14 | SUMMARY OF ENVIRONMENTAL OUTCOMES | `eia_ch14_out.pdf` | 16 | 0.34 | `86ad6549f283b1f7beb212d6215438adfa7aff230225e9845341baf9141030ab` |
| 15 | CONCLUSION | `eia_ch15_out.pdf` | 11 | 0.44 | `b29b0648452a91d28debcc19060e6243250102148c2f29af58de76c1da41cb47` |
| — | Sign page | `eia_text_sign_page.pdf` | 1 | 0.16 | `3c7ca4b14bff155b7b4f2effdf5da26a45c02efeabf3078f8b4d916dd43e9492` |

**Executive summaries**

| Language | File | Pages | MB | SHA-256 | Available |
|---|---|---|---|---|---|
| Traditional Chinese | `es_chi_out.pdf` | 51 | 1.25 | `951047cb722bac965cb225ced81e1a076c20b2c226f02d6469eb6f3e27b173b9` | yes (opens as valid PDF) |
| English | `es_eng_out.pdf` | 66 | 0.79 | `d8e37bc3886ddce0173a2ea3e86be4e4ccdca5c2b677854c18ab41c7a72061d3` | yes (opens as valid PDF) |

**Page-numbering evidence (per chapter)**

Counts are from the corrected matcher (v2c). `verified` = a folio was read from the page footer; `absent` = the footer date is present but no folio precedes it; `unverified` = no recognisable footer or no text.

| File | Pages | Verified | Absent | Unverified | Coverage | Folio forms | Offset (viewer − printed) | Sequence note |
|---|---|---|---|---|---|---|---|---|
| `eia_ch01_out.pdf` | 7 | 2 | 5 | 0 | 29% | compound:2 | n/a (no numeric folio) | — |
| `eia_ch02_out.pdf` | 35 | 35 | 0 | 0 | 100% | chapter-roman:2, compound:33 | 2..2 | — |
| `eia_ch03_out.pdf` | 66 | 66 | 0 | 0 | 100% | chapter-roman:5, compound:61 | 5..5 | — |
| `eia_ch04_out.pdf` | 62 | 62 | 0 | 0 | 100% | compound:59, roman:3 | 3..3 | — |
| `eia_ch05_out.pdf` | 39 | 38 | 1 | 0 | 97% | chapter-roman:2, compound:36 | 2..2 | — |
| `eia_ch06_out.pdf` | 28 | 28 | 0 | 0 | 100% | plain:26, roman:2 | 2..2 | — |
| `eia_ch07_out.pdf` | 55 | 55 | 0 | 0 | 100% | chapter-roman:2, compound:53 | 2..2 | — |
| `eia_ch08_out.pdf` | 124 | 124 | 0 | 0 | 100% | chapter-roman:4, compound:120 | 4..4 | — |
| `eia_ch09_out.pdf` | 21 | 21 | 0 | 0 | 100% | chapter-roman:2, compound:19 | 2..2 | — |
| `eia_ch10_out.pdf` | 137 | 137 | 0 | 0 | 100% | chapter-roman:4, compound:133 | 4..5 | duplicate folio `10-119`; offset varies |
| `eia_ch11_out.pdf` | 25 | 25 | 0 | 0 | 100% | plain:23, roman:2 | 2..2 | — |
| `eia_ch12_out.pdf` | 89 | 89 | 0 | 0 | 100% | chapter-roman:3, compound:86 | 3..3 | — |
| `eia_ch13_out.pdf` | 7 | 6 | 1 | 0 | 86% | chapter-roman:1, compound:5 | 1..1 | — |
| `eia_ch14_out.pdf` | 16 | 15 | 1 | 0 | 94% | chapter-roman:2, compound:13 | 2..2 | — |
| `eia_ch15_out.pdf` | 11 | 2 | 9 | 0 | 18% | chapter-roman:2 | n/a (no numeric folio) | — |
| `eia_text_sign_page.pdf` | 1 | 0 | 0 | 1 | 0% | none | n/a (no numeric folio) | — |

Full before/after comparison with the superseded matcher, and the reason for every changed count, is in `PAGE_NUMBERING_RECONCILIATION.md`.

## AEIAR-271-2025 — Development at Ngau Tam Mei Area

- Chinese title: 牛潭尾地區發展
- Project page: https://www.epd.gov.hk/eia/tc/alpha/aspd.php?id=363
- Report index: https://www.epd.gov.hk/eia/files/applications/en/pp_363/eia_6226/progress/action_176330/Index.htm
- Status: Conditionally approved 18 December 2025 (per project page); permit EP-680/2025
- Files: 20 (18 chapter files + 2 executive summaries), 13.74 MB

**Page numbering: `printed`** — Printed folios are compound chapter-page labels (e.g. 2-1, 1-1-i) and are NOT the PDF viewer page index. 570/570 pages numbered (100.0%); some pages are genuinely unnumbered.

| # | Chapter (as listed by EPD) | File | Pages | MB | SHA-256 |
|---|---|---|---|---|---|
| 1 | INTRODUCTION | `s1_introduction.pdf` | 7 | 0.24 | `aec64bcb6512cc1d93d27e4d5aa25964b94312aa51c3f1ba899c10b3daa1baf3` |
| 2 | PROJECT DESCRIPTION | `s2_project_description.pdf` | 35 | 0.51 | `f3d952fd7a1306bd96ee58ce942ad9ea22f19bfe048926e9cadd7e033f154b3a` |
| 3 | AIR QUALITY | `s3_aq.pdf` | 55 | 1.41 | `55dd4e8cadef09bab40f8e8fdd3e0079bb395955167b90d18cc754bd7df38050` |
| 4 | NOISE | `s4_noise.pdf` | 68 | 1.02 | `780c5efa07c742218c85a0ef74757400b306cc796c93684e9002fa1617f81ac3` |
| 5 | WATER QUALITY | `s5_water_quality.pdf` | 33 | 0.53 | `276a9584c06bea49ee8b018d0b3b0d9155e5d9f5414e5f7c7dfcd7738413f3ea` |
| 6 | SEWERAGE AND SEWAGE TREATMENT IMPLICATIONS | `s6_sewerage.pdf` | 9 | 0.66 | `851b012300986a68977ce8f9abd76fe264247750163ef0ba104437a61346bf64` |
| 7 | WASTE MANAGEMENT IMPLICATIONS | `s7_wast.pdf` | 32 | 0.45 | `4ae26388af5eaa0605870047d839cfd15594295f9495994d46099cc4aad39d90` |
| 8 | LAND CONTAMINATION | `s8_land_con.pdf` | 36 | 0.64 | `ef275374a42366e4b79ca834759f51d26675984c098b0aa7bcb37d9c31582c55` |
| 9 | ECOLOGICAL IMPLICATION (TERRESTRIAL AND AQUATIC) | `s9_eco.pdf` | 113 | 1.35 | `515b8fe92fd48ab56a9b845dc37316d4bb915c795791180a42995841f9d253c5` |
| 10 | FISHERIES IMPACT | `s10_fisheries.pdf` | 19 | 0.36 | `f9bf4e21e938f80dcdf5739e85550af89821c2165f4197697c5e893f7a9d12a1` |
| 11 | LANDSCAPE AND VISUAL IMPACT | `s11_lvia.pdf` | 56 | 0.64 | `57e3f7399b5abb68120e11a62534da63f495fd285bfd97b6e6ad3410541de37e` |
| 12 | IMPACT ON CULTURAL HERITAGE | `s12_cultural_heritage.pdf` | 53 | 0.90 | `cef66994462134ebcbd9bbff6cc84f04d7113a94f22e91d958c7b7956235af0c` |
| 13 | HAZARD TO LIFE | `s13_hazard_to_life.pdf` | 3 | 0.19 | `c022edda6687785930a8763e3d35f36cd05a14f68f976fc207d483c71adc3552` |
| 14 | LANDFILL GAS HAZARD | `s14_landfill_gas.pdf` | 15 | 0.36 | `16c63d9eb5838ee5638f536868553cada98f4afaea23354d88f9af5a7bcdd1e4` |
| 15 | IMPACT FROM ELECTRIC AND MAGNETIC FIELD | `S15_EMF.pdf` | 5 | 0.19 | `d321b341677a2f00987f69a498873fd6f301db4541d074a4f8387905d98226fe` |
| 16 | ENVIRONMENTAL MONITORING AND AUDIT | `s16_ema.pdf` | 7 | 0.21 | `b3811b179a55cc7e7cef41f211685ae4012e93ef1c2a3de94ebff5cc70365f73` |
| 17 | SUMMARY OF OUTCOMES | `s17_summary_of_outcomes.pdf` | 14 | 0.30 | `9d0cada069adaaf4917312f7dbeec159d50fc86e8b474954990014d860ed2e0c` |
| 18 | CONCLUSION | `s18_conclusion.pdf` | 10 | 0.24 | `e74ec305d011510865351ae0956ebf9a18a71c15352a7099a560745143f7c47b` |

**Executive summaries**

| Language | File | Pages | MB | SHA-256 | Available |
|---|---|---|---|---|---|
| English | `es_e.pdf` | 78 | 1.50 | `2d1bb31dd72c7d04b21375981381fe378ed5a1dd178422f0bbc4b936f6363942` | yes (opens as valid PDF) |
| Traditional Chinese | `es_tc.pdf` | 62 | 2.05 | `0a6b0781151ae5958d8cbbdfc89a2d287cf0d37356c9fafc24e476f75abf584b` | yes (opens as valid PDF) |

**Page-numbering evidence (per chapter)**

Counts are from the corrected matcher (v2c). `verified` = a folio was read from the page footer; `absent` = the footer date is present but no folio precedes it; `unverified` = no recognisable footer or no text.

| File | Pages | Verified | Absent | Unverified | Coverage | Folio forms | Offset (viewer − printed) | Sequence note |
|---|---|---|---|---|---|---|---|---|
| `s1_introduction.pdf` | 7 | 7 | 0 | 0 | 100% | compound:6, roman:1 | 1..1 | — |
| `s2_project_description.pdf` | 35 | 35 | 0 | 0 | 100% | compound:34, roman:1 | 1..1 | — |
| `s3_aq.pdf` | 55 | 55 | 0 | 0 | 100% | compound:52, roman:3 | 3..3 | — |
| `s4_noise.pdf` | 68 | 68 | 0 | 0 | 100% | compound:65, roman:3 | 3..3 | — |
| `s5_water_quality.pdf` | 33 | 33 | 0 | 0 | 100% | compound:32, roman:1 | 1..1 | — |
| `s6_sewerage.pdf` | 9 | 9 | 0 | 0 | 100% | compound:8, roman:1 | 1..1 | — |
| `s7_wast.pdf` | 32 | 32 | 0 | 0 | 100% | compound:31, roman:1 | 1..1 | — |
| `s8_land_con.pdf` | 36 | 36 | 0 | 0 | 100% | compound:34, roman:2 | 2..2 | — |
| `s9_eco.pdf` | 113 | 113 | 0 | 0 | 100% | compound:110, roman:3 | 3..3 | — |
| `s10_fisheries.pdf` | 19 | 19 | 0 | 0 | 100% | compound:18, roman:1 | 1..1 | — |
| `s11_lvia.pdf` | 56 | 56 | 0 | 0 | 100% | compound:54, roman:2 | 2..2 | — |
| `s12_cultural_heritage.pdf` | 53 | 53 | 0 | 0 | 100% | compound:51, roman:2 | 1..2 | folio printed on no page: 23; offset varies |
| `s13_hazard_to_life.pdf` | 3 | 3 | 0 | 0 | 100% | compound:2, roman:1 | 1..1 | — |
| `s14_landfill_gas.pdf` | 15 | 15 | 0 | 0 | 100% | compound:14, roman:1 | 1..1 | — |
| `S15_EMF.pdf` | 5 | 5 | 0 | 0 | 100% | compound:4, roman:1 | 1..1 | — |
| `s16_ema.pdf` | 7 | 7 | 0 | 0 | 100% | compound:6, roman:1 | 1..1 | — |
| `s17_summary_of_outcomes.pdf` | 14 | 14 | 0 | 0 | 100% | compound:13, roman:1 | 1..1 | — |
| `s18_conclusion.pdf` | 10 | 10 | 0 | 0 | 100% | compound:9, roman:1 | 1..1 | — |

Full before/after comparison with the superseded matcher, and the reason for every changed count, is in `PAGE_NUMBERING_RECONCILIATION.md`.

## Verified facts

- Both project pages resolve and name the expected register numbers (AEIAR-276/2026 on id=955; AEIAR-271/2025 on id=363).
- 38 of 38 files downloaded with HTTP 200 and a valid `%PDF` header; total 27.0 MB.
- Chapter counts: **15** for San Tin (plus a sign page), **18** for Ngau Tam Mei.
- Executive summaries **exist for both reports in both languages** and open as valid PDFs (San Tin EN 66 pp / TC 51 pp; Ngau Tam Mei EN 78 pp / TC 62 pp).
- Neither PDF contains a `/PageLabels` tree, so the viewer index is the raw file page order, not the printed label.
- Printed folios differ from the viewer index in every chapter examined. The offset is constant within **32 of 34** chapters; the two exceptions (`eia_ch10_out.pdf` 4..5, `s12_cultural_heritage.pdf` 1..2) are caused by source-side sequence defects, listed under caveats. Offset ranges across reports: San Tin 1–5, Ngau Tam Mei 1–3.
- San Tin chapter 1 uses a three-part folio in its front matter (`1-1-i`) while later chapters use two-part folios (`2-i`, `2-1`). Chapter front matter can also be numbered `chapter-roman` (`15-i`), which is a distinct form.
- Page-number coverage after the corrected matcher: San Tin 705/723 pages (97.5%, page-weighted), Ngau Tam Mei 570/570 (100%).

## Unresolved / caveats

- **San Tin ch.1 pp.3–7 and ch.15 pp.3–11 carry no printed folio at all** (only the date). Citations to those pages must show chapter + section only.
- **`eia_ch10_out.pdf` prints folio `10-119` twice** (viewer pages 123 and 124), and the footer month changes from March to April at the same point. A printed folio is therefore **not a unique page identifier**; every citation must also carry the PDF page index.
- **`s12_cultural_heritage.pdf` never prints folio `12-23`** (viewer 23 is `12-22`, viewer 24 is `12-24`). Recorded as a source defect, not corrected.
- San Tin ch.1 page 3 footer reads `April 2026` while every other page in the file reads `March 2026`. Source-side inconsistency; recorded, not corrected.
- San Tin ch.6 and ch.11 use plain folios (`1`, `2`, …) rather than `chapter-page`, so the label scheme is not uniform across the report.
- The project page itself does not link the executive summaries; they are reachable only through the report index page. Any future ingestion must follow the index page, not the project page.
- Chapter titles are English only **as published**. The Chinese (`/tc/`) chapter lists return HTTP 404, and both TC project pages link to the English report index (`.../applications/en/...`). Only the executive summaries exist in Chinese. So this is a source limitation, not a capture gap.
- Figures and appendices were deliberately not downloaded (out of MVP scope).

## Step 2 — report registry and district resolution

**District boundary source.** HAD dataset `District boundary` (`hk-had-json1-hong-kong-administrative-boundaries`), JSON resource `https://www.had.gov.hk/psi/hong-kong-administrative-boundaries/hksar_18_district_boundary.json` — 796,586 bytes, SHA-256 `ab2123b5a48c2e39e29ce594a0c51590cf6081922ab2c5c14ff78338b788f760`, saved at `source-data/boundaries/`.

- 18 `Polygon` features, one ring each; properties `地區號碼`, `District`, `地區`.
- **M = Yuen Long District (元朗區)**, **N = North District (北區)** — read directly from the file, not assumed.
- The file declares **no `crs` member**; coordinates span lon 113.817–114.502, lat 22.137–22.568, which is consistent with WGS84 (the RFC 7946 default) but the file does not state it. Treated as WGS84, recorded as an observation rather than a declared fact.

**District assignment.** Both reports map to `hk-district:M` (Yuen Long). The basis is the OZP plan numbers cited inside the reports (San Tin: `S/STT/2`; Ngau Tam Mei: `S/YL-NTM/15`), **not** point-in-polygon, because no project coordinates exist yet.

**Northern Metropolis scope evidence.** The nm.gov.hk Innovation and Technology Zone lists three subzones — **San Tin Technopole**, **Ngau Tam Mei New Development Area** and Au Tau (read from `https://www.nm.gov.hk/api/zone/6cb72190-c16b-48c9-a322-5b89c32fa840`, saved as `provenance/nm_it_zone_api.json`; the rendered page is `https://www.nm.gov.hk/en/four-zones/innovation-and-technology-zone`). Both reports therefore have area-level scope evidence. Caveat: the evidence links the **area**, while the link from each project to that area rests on the project name.

**Registry.** `stage0/reports.json` written with 2 reports and 34 chapter entries (16 incl. sign page; 18). `validation_status: incomplete` — see blockers below.

**Blockers carried forward.**

- `report_areas[]` is empty and `label_lat`/`label_lng` are null for both reports. No polygon could be traced to an official project layout or planning map, and a search of the report text found **no coordinates** (no lat/long, no HK1980 grid references, no degree-minute values). The PRD validation rule will therefore reject both entries — deliberately, rather than inventing geometry.
- District assignment rests on OZP plan numbers, not on geometry, for the same reason.

## Step 3 — OZP boundary investigation (S/STT/2, S/YL-NTM/15)

**Outcome: no official OZP boundary geometry could be obtained.** The data exists and is published, but its distribution channel is not openly reachable. Nothing was digitised, estimated or inferred.

### Sources checked

| # | Source | Result |
|---|---|---|
| 1 | data.gov.hk dataset *Digital Planning Data of Statutory Plans* (`tpd-tpb1-digital-planning-data-of-statutory-plans`) | Dataset exists and states it contains all GIS data, a data dictionary and terms of use. Its **only** resource is a CSDI geoportal link (`datasetId=f5334b37-85de-557c-bcb6-fe7061b332bb`) — no direct file, no format list. |
| 2 | CSDI ArcGIS server, public folder `common` (2,252 services, 32 of them Planning Department `pland_*`) | No OZP / statutory-plan boundary layer. The planning services present are Tertiary Planning Unit boundaries, TPB guideline graphics and enforcement statistics. |
| 3 | SPP3 `OZP_PLAN` MapServer (layers 1000, 1001, 1004, 1010–1015, 1019), referenced by the portal's own code | Folder `SPP3` returns **HTTP 499 “Token Required”**. Not publicly queryable. |
| 4 | SPP3 API (`/api/Plan/*`) | Only answers POST with an undocumented body; `GetPlanMoreInfor` returned an empty result for `S/STT/2`. The per-plan GeoJSON links the UI uses (`dlGeoJSONLink`) sit behind `proxyAPI` plus authorisation. |
| 5 | Town Planning Board website | Delegates all OZP content to SPP3 (`https://www.ozp.tpb.gov.hk/?lang=en`); no separate OZP GIS page. |
| 6 | Gazetted statutory plans XML (`https://www.ozp.tpb.gov.hk/api/OZPStatistic?year=YYYY&quarter=N&type=xml`) | **Public and readable.** Confirms both plan numbers, official names and gazette dates — but contains no geometry. |

### Verified plan metadata (from source 6)

| Plan | Official name | Draft exhibited |
|---|---|---|
| `S/STT/2` | San Tin Technopole Outline Zoning Plan / 新田科技城分區計劃大綱圖 | 20/09/2024 (2024 Q3) |
| `S/YL-NTM/15` | Ngau Tam Mei Outline Zoning Plan / 牛潭尾分區計劃大綱圖 | 31/10/2025 (2025 Q4) |

The exhibition date is the s.5/s.7 gazette date of the draft plan. It is **not** a final approval date and **not** a geometry-version date.

### What could not be verified

- **Geometry:** no Polygon or MultiPolygon, therefore no geometry type, vertex count or topology to report.
- **CRS:** unknown. The SPP3 map uses HK80 basemaps, but that is a display choice, not a declaration about the data.
- **Schema / data dictionary:** referenced by the dataset but not retrievable.
- **Licence:** the dataset requires acceptance of Terms and Conditions of Use “enclosed in the downloaded data”. Since no download succeeded, the licence text is **unverified**, not assumed permissive.

### Consequence

- `reports.json` is **unchanged**: `report_areas[]` stays empty and `label_lat/lng` stay null. Validation remains incomplete, deliberately.
- No mapping to the `report_areas[]` schema is proposed, because a proposal without verified geometry would only invite it to be treated as approved.
- An OZP boundary is a **planning-scheme boundary**, not the EIA project footprint. Even once obtained it must be recorded as `area_type: "planning_scheme_area"` and must never be described as the project footprint.
- **Decision (2026-10-18):** official public data only; no approach to TPB or CSDI. Project-area highlighting is **deferred**. `report_areas_status` is now `deferred_no_public_geometry` and the map will use the district context layer plus an accessible report list/card instead of a highlighted area.

## Stage 0 exit criteria — status

| Criterion (PRD §9) | Status | Evidence |
|---|---|---|
| Both reports downloaded | **Met** | 38 files, 27.0 MB, checksums re-verified |
| Page-numbering mode verified and recorded | **Met** | `printed` for both; `page_numbering.json`. Counts re-derived with the corrected matcher (v2c) and diffed against the superseded output in `PAGE_NUMBERING_RECONCILIATION.md` |
| Executive-summary availability recorded | **Met** | EN + TC PDFs for both; `reports.json` |
| District IDs resolved against the boundary source | **Met** | M = Yuen Long, N = North, read from the HAD file |
| `reports.json` created per the registry schema | **NOT met** | `validation_status: incomplete` — `report_areas[]` and label coordinates missing |

**Stage 0 is therefore blocked on exactly one item: report-area geometry.** Everything else is complete and evidenced.

