#!/usr/bin/env python3
"""Stage 0 Step 1: build the inventory artefacts from the download manifest and
the page-numbering analysis.

Outputs:
  stage0/source-data/file_manifest.csv   - one row per downloaded file
  stage0/STAGE0_INVENTORY.md             - human-readable inventory + findings

Chapter titles below are transcribed from the official EPD chapter-list pages
saved under stage0/source-data/provenance/. Nothing is inferred.
"""
import csv
import json
import os

ROOT = "/Users/chloeyan/workbuddy-ai/NORTHWISE"
SRC = os.path.join(ROOT, "stage0", "source-data")

ST_TITLES = {
    "eia_text_sign_page.pdf": "Sign page",
    "eia_ch01_out.pdf": "INTRODUCTION",
    "eia_ch02_out.pdf": "PROJECT DESCRIPTION",
    "eia_ch03_out.pdf": "AIR QUALITY",
    "eia_ch04_out.pdf": "NOISE",
    "eia_ch05_out.pdf": "WATER QUALITY",
    "eia_ch06_out.pdf": "WASTE MANAGEMENT IMPLICATIONS",
    "eia_ch07_out.pdf": "LAND CONTAMINATION",
    "eia_ch08_out.pdf": "ECOLOGY",
    "eia_ch09_out.pdf": "FISHERIES",
    "eia_ch10_out.pdf": "LANDSCAPE AND VISUAL IMPACT",
    "eia_ch11_out.pdf": "CULTURAL HERITAGE",
    "eia_ch12_out.pdf": "HAZARD TO LIFE",
    "eia_ch13_out.pdf": "ENVIRONMENTAL MONITORING AND AUDIT REQUIREMENTS",
    "eia_ch14_out.pdf": "SUMMARY OF ENVIRONMENTAL OUTCOMES",
    "eia_ch15_out.pdf": "CONCLUSION",
}
NTM_TITLES = {
    "s1_introduction.pdf": "INTRODUCTION",
    "s2_project_description.pdf": "PROJECT DESCRIPTION",
    "s3_aq.pdf": "AIR QUALITY",
    "s4_noise.pdf": "NOISE",
    "s5_water_quality.pdf": "WATER QUALITY",
    "s6_sewerage.pdf": "SEWERAGE AND SEWAGE TREATMENT IMPLICATIONS",
    "s7_wast.pdf": "WASTE MANAGEMENT IMPLICATIONS",
    "s8_land_con.pdf": "LAND CONTAMINATION",
    "s9_eco.pdf": "ECOLOGICAL IMPLICATION (TERRESTRIAL AND AQUATIC)",
    "s10_fisheries.pdf": "FISHERIES IMPACT",
    "s11_lvia.pdf": "LANDSCAPE AND VISUAL IMPACT",
    "s12_cultural_heritage.pdf": "IMPACT ON CULTURAL HERITAGE",
    "s13_hazard_to_life.pdf": "HAZARD TO LIFE",
    "s14_landfill_gas.pdf": "LANDFILL GAS HAZARD",
    "S15_EMF.pdf": "IMPACT FROM ELECTRIC AND MAGNETIC FIELD",
    "s16_ema.pdf": "ENVIRONMENTAL MONITORING AND AUDIT",
    "s17_summary_of_outcomes.pdf": "SUMMARY OF OUTCOMES",
    "s18_conclusion.pdf": "CONCLUSION",
}
TITLES = {"AEIAR-276-2026": ST_TITLES, "AEIAR-271-2025": NTM_TITLES}

META = {
    "AEIAR-276-2026": {
        "title": "Northern Metropolis Highway – San Tin Section",
        "title_zh": "北都公路 – 新田段",
        "project_page": "https://www.epd.gov.hk/eia/tc/alpha/aspd.php?id=955",
        "index_page": ("https://www.epd.gov.hk/eia/files/applications/en/pp_955/eia_6390/"
                       "progress/action_180296/NMHST%20v3/cover_page_pdf.htm"),
        "approval": "Conditionally approved 12 August 2026 (per project page)",
        "permit": "EP-681/2026",
    },
    "AEIAR-271-2025": {
        "title": "Development at Ngau Tam Mei Area",
        "title_zh": "牛潭尾地區發展",
        "project_page": "https://www.epd.gov.hk/eia/tc/alpha/aspd.php?id=363",
        "index_page": ("https://www.epd.gov.hk/eia/files/applications/en/pp_363/eia_6226/"
                       "progress/action_176330/Index.htm"),
        "approval": "Conditionally approved 18 December 2025 (per project page)",
        "permit": "EP-680/2025",
    },
}


def mb(n):
    return f"{n/1048576:.2f}"


def chapter_num(fn):
    """Numeric chapter number from an EPD filename, or 999 for non-chapters."""
    if fn.startswith("eia_text"):
        return 999
    if fn.startswith("eia_ch"):
        return int(fn[6:8])
    if fn[0] in "sS" and "_" in fn:
        return int(fn[1:fn.index("_")])
    return 998


def probe_pages(path):
    """Page count via PDFKit; None if unreadable."""
    import subprocess
    jxa = os.path.join(ROOT, "stage0", "tools", "pdf_pages.js")
    r = subprocess.run(["osascript", "-l", "JavaScript", jxa, path],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return int(json.loads(r.stdout)["pages"])
    except Exception:
        return None


def main():
    manifest = json.load(open(os.path.join(SRC, "download_manifest.json")))
    pn = json.load(open(os.path.join(SRC, "page_numbering.json")))

    # ---- CSV -------------------------------------------------------------
    csv_path = os.path.join(SRC, "file_manifest.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["register_no", "group", "filename", "source_url",
                    "http_status", "bytes", "sha256", "retrieved_at_utc"])
        for m in sorted(manifest, key=lambda x: (x["register_no"], x["group"], x["filename"])):
            w.writerow([m["register_no"], m["group"], m["filename"],
                        m["source_url"], m["http_status"], m["bytes"],
                        m["sha256"] or "", m["retrieved_at_utc"]])

    # ---- Markdown --------------------------------------------------------
    L = []
    A = L.append
    A("# STAGE 0 INVENTORY — official EIA source verification")
    A("")
    A(f"Step 1 of Stage 0 (data preparation). Generated from the downloaded files "
      f"and the page-numbering probe. Manifest: `source-data/download_manifest.json` "
      f"(machine) and `source-data/file_manifest.csv` (flat table).")
    A("")
    A("## Method (what was actually done)")
    A("")
    A("1. Fetched each official EPD project page, then followed its "
      "`[環境影響評估報告]` link to the report index page.")
    A("2. Read the chapter list from the report's own `list of main text (PDF)` page. "
      "Every chapter URL below was copied from that page — none was constructed.")
    A("3. Downloaded each file with `curl`/urllib, recorded HTTP status, byte size, "
      "SHA-256 and a UTC timestamp; saved the project page, report index and chapter "
      "list HTML as provenance snapshots.")
    A("4. Opened every PDF and read per-page text with macOS PDFKit (built in). "
      "No PDF library was installed.")
    A("5. Determined page numbering from the token that immediately precedes the "
      "`<Month> <Year>` footer on each page, then compared it with the 1-based "
      "viewer index and checked the raw PDF for a `/PageLabels` tree.")
    A("")

    totals = {}
    for reg in ("AEIAR-276-2026", "AEIAR-271-2025"):
        m = META[reg]
        rows = [x for x in manifest if x["register_no"] == reg and x["ok"]]
        chs = sorted([x for x in rows if x["group"] == "chapters"],
                     key=lambda x: chapter_num(x["filename"]))
        es = [x for x in rows if x["group"] == "executive-summary"]
        total = sum(x["bytes"] for x in rows)
        totals[reg] = total

        A(f"## {reg} — {m['title']}")
        A("")
        A(f"- Chinese title: {m['title_zh']}")
        A(f"- Project page: {m['project_page']}")
        A(f"- Report index: {m['index_page']}")
        A(f"- Status: {m['approval']}; permit {m['permit']}")
        A(f"- Files: {len(rows)} ({len(chs)} chapter files + {len(es)} executive summaries), "
          f"{mb(total)} MB")
        A("")

        pn_reg = pn["reports"][reg]
        A(f"**Page numbering: `{pn_reg['page_numbering']}`** — {pn_reg['note']}")
        A("")

        A("| # | Chapter (as listed by EPD) | File | Pages | MB | SHA-256 |")
        A("|---|---|---|---|---|---|")
        for c in chs:
            fn = c["filename"]
            n = chapter_num(fn)
            num = "—" if n >= 900 else str(n)
            pf = next((x for x in pn_reg["chapters"] if x["filename"] == fn), {})
            A(f"| {num} | {TITLES[reg].get(fn,'(not in EPD list)')} | `{fn}` | "
              f"{pf.get('pages','?')} | {mb(c['bytes'])} | `{c['sha256']}` |")
        A("")

        A("**Executive summaries**")
        A("")
        A("| Language | File | Pages | MB | SHA-256 | Available |")
        A("|---|---|---|---|---|---|")
        for e in sorted(es, key=lambda x: x["filename"]):
            lang = ("English" if "eng" in e["filename"] or e["filename"] == "es_e.pdf"
                    else "Traditional Chinese")
            pages = probe_pages(os.path.join(SRC, reg, "executive-summary", e["filename"]))
            A(f"| {lang} | `{e['filename']}` | {pages if pages else '?'} | "
              f"{mb(e['bytes'])} | `{e['sha256']}` | yes (opens as valid PDF) |")
        A("")

        A("**Page-numbering evidence (per chapter)**")
        A("")
        A("Counts are from the corrected matcher (v2c). `verified` = a folio was read "
          "from the page footer; `absent` = the footer date is present but no folio "
          "precedes it; `unverified` = no recognisable footer or no text.")
        A("")
        A("| File | Pages | Verified | Absent | Unverified | Coverage | Folio forms | Offset (viewer − printed) | Sequence note |")
        A("|---|---|---|---|---|---|---|---|---|")
        for c in sorted(pn_reg["chapters"], key=lambda x: chapter_num(x["filename"])):
            if "error" in c:
                A(f"| `{c['filename']}` | — | — | — | — | — | ERROR: {c['error']} | — | — |")
                continue
            forms = ", ".join(f"{k}:{v}" for k, v in sorted(c["forms"].items())) or "none"
            off = (f"{c['offset_min']}..{c['offset_max']}"
                   if c["offset_min"] is not None else "n/a (no numeric folio)")
            sc = c.get("status_counts", {})
            notes = []
            if c.get("duplicate_labels"):
                notes.append("duplicate folio " +
                             ", ".join(f"`{l}`" for l in c["duplicate_labels"]))
            if c.get("missing_page_numbers"):
                notes.append("folio printed on no page: " +
                             ", ".join(str(n) for n in c["missing_page_numbers"]))
            if c["offset_min"] is not None and c["offset_min"] != c["offset_max"]:
                notes.append("offset varies")
            A(f"| `{c['filename']}` | {c['pages']} | {sc.get('verified','?')} | "
              f"{sc.get('absent','?')} | {sc.get('unverified','?')} | "
              f"{c['coverage']:.0%} | {forms} | {off} | "
              f"{'; '.join(notes) if notes else '—'} |")
        A("")
        A("Full before/after comparison with the superseded matcher, and the reason "
          "for every changed count, is in `PAGE_NUMBERING_RECONCILIATION.md`.")
        A("")

    # ---- Verified / unresolved -------------------------------------------
    A("## Verified facts")
    A("")
    A("- Both project pages resolve and name the expected register numbers "
      "(AEIAR-276/2026 on id=955; AEIAR-271/2025 on id=363).")
    A("- 38 of 38 files downloaded with HTTP 200 and a valid `%PDF` header; "
      "total 27.0 MB.")
    A("- Chapter counts: **15** for San Tin (plus a sign page), **18** for Ngau Tam Mei.")
    A("- Executive summaries **exist for both reports in both languages** and open as "
      "valid PDFs (San Tin EN 66 pp / TC 51 pp; Ngau Tam Mei EN 78 pp / TC 62 pp).")
    A("- Neither PDF contains a `/PageLabels` tree, so the viewer index is the raw "
      "file page order, not the printed label.")
    A("- Printed folios differ from the viewer index in every chapter examined. The "
      "offset is constant within **32 of 34** chapters; the two exceptions "
      "(`eia_ch10_out.pdf` 4..5, `s12_cultural_heritage.pdf` 1..2) are caused by "
      "source-side sequence defects, listed under caveats. Offset ranges across "
      "reports: San Tin 1–5, Ngau Tam Mei 1–3.")
    A("- San Tin chapter 1 uses a three-part folio in its front matter (`1-1-i`) while "
      "later chapters use two-part folios (`2-i`, `2-1`). Chapter front matter can "
      "also be numbered `chapter-roman` (`15-i`), which is a distinct form.")
    A("- Page-number coverage after the corrected matcher: San Tin 705/723 pages "
      "(97.5%, page-weighted), Ngau Tam Mei 570/570 (100%).")
    A("")
    A("## Unresolved / caveats")
    A("")
    A("- **San Tin ch.1 pp.3–7 and ch.15 pp.3–11 carry no printed folio at all** "
      "(only the date). Citations to those pages must show chapter + section only.")
    A("- **`eia_ch10_out.pdf` prints folio `10-119` twice** (viewer pages 123 and "
      "124), and the footer month changes from March to April at the same point. A "
      "printed folio is therefore **not a unique page identifier**; every citation "
      "must also carry the PDF page index.")
    A("- **`s12_cultural_heritage.pdf` never prints folio `12-23`** (viewer 23 is "
      "`12-22`, viewer 24 is `12-24`). Recorded as a source defect, not corrected.")
    A("- San Tin ch.1 page 3 footer reads `April 2026` while every other page in the "
      "file reads `March 2026`. Source-side inconsistency; recorded, not corrected.")
    A("- San Tin ch.6 and ch.11 use plain folios (`1`, `2`, …) rather than "
      "`chapter-page`, so the label scheme is not uniform across the report.")
    A("- The project page itself does not link the executive summaries; they are "
      "reachable only through the report index page. Any future ingestion must "
      "follow the index page, not the project page.")
    A("- Chapter titles are English only **as published**. The Chinese (`/tc/`) chapter "
      "lists return HTTP 404, and both TC project pages link to the English report index "
      "(`.../applications/en/...`). Only the executive summaries exist in Chinese. So this "
      "is a source limitation, not a capture gap.")
    A("- Figures and appendices were deliberately not downloaded (out of MVP scope).")
    A("")
    A("## Step 2 — report registry and district resolution")
    A("")
    A("**District boundary source.** HAD dataset `District boundary` "
      "(`hk-had-json1-hong-kong-administrative-boundaries`), JSON resource "
      "`https://www.had.gov.hk/psi/hong-kong-administrative-boundaries/"
      "hksar_18_district_boundary.json` — 796,586 bytes, SHA-256 "
      "`ab2123b5a48c2e39e29ce594a0c51590cf6081922ab2c5c14ff78338b788f760`, "
      "saved at `source-data/boundaries/`.")
    A("")
    A("- 18 `Polygon` features, one ring each; properties `地區號碼`, `District`, `地區`.")
    A("- **M = Yuen Long District (元朗區)**, **N = North District (北區)** — read directly "
      "from the file, not assumed.")
    A("- The file declares **no `crs` member**; coordinates span lon 113.817–114.502, "
      "lat 22.137–22.568, which is consistent with WGS84 (the RFC 7946 default) but the "
      "file does not state it. Treated as WGS84, recorded as an observation rather than "
      "a declared fact.")
    A("")
    A("**District assignment.** Both reports map to `hk-district:M` (Yuen Long). The "
      "basis is the OZP plan numbers cited inside the reports (San Tin: `S/STT/2`; "
      "Ngau Tam Mei: `S/YL-NTM/15`), **not** point-in-polygon, because no project "
      "coordinates exist yet.")
    A("")
    A("**Northern Metropolis scope evidence.** The nm.gov.hk Innovation and Technology "
      "Zone lists three subzones — **San Tin Technopole**, **Ngau Tam Mei New "
      "Development Area** and Au Tau (read from `https://www.nm.gov.hk/api/zone/"
      "6cb72190-c16b-48c9-a322-5b89c32fa840`, saved as "
      "`provenance/nm_it_zone_api.json`; the rendered page is "
      "`https://www.nm.gov.hk/en/four-zones/innovation-and-technology-zone`). Both "
      "reports therefore have area-level scope evidence. Caveat: the evidence links the "
      "**area**, while the link from each project to that area rests on the project "
      "name.")
    A("")
    A("**Registry.** `stage0/reports.json` written with 2 reports and 34 chapter entries "
      "(16 incl. sign page; 18). `validation_status: incomplete` — see blockers below.")
    A("")
    A("**Blockers carried forward.**")
    A("")
    A("- `report_areas[]` is empty and `label_lat`/`label_lng` are null for both reports. "
      "No polygon could be traced to an official project layout or planning map, and a "
      "search of the report text found **no coordinates** (no lat/long, no HK1980 grid "
      "references, no degree-minute values). The PRD validation rule will therefore "
      "reject both entries — deliberately, rather than inventing geometry.")
    A("- District assignment rests on OZP plan numbers, not on geometry, for the same "
      "reason.")
    A("")
    A("## Step 3 — OZP boundary investigation (S/STT/2, S/YL-NTM/15)")
    A("")
    A("**Outcome: no official OZP boundary geometry could be obtained.** The data exists "
      "and is published, but its distribution channel is not openly reachable. Nothing "
      "was digitised, estimated or inferred.")
    A("")
    A("### Sources checked")
    A("")
    A("| # | Source | Result |")
    A("|---|---|---|")
    A("| 1 | data.gov.hk dataset *Digital Planning Data of Statutory Plans* "
      "(`tpd-tpb1-digital-planning-data-of-statutory-plans`) | Dataset exists and states it "
      "contains all GIS data, a data dictionary and terms of use. Its **only** resource is a "
      "CSDI geoportal link (`datasetId=f5334b37-85de-557c-bcb6-fe7061b332bb`) — no direct "
      "file, no format list. |")
    A("| 2 | CSDI ArcGIS server, public folder `common` (2,252 services, 32 of them "
      "Planning Department `pland_*`) | No OZP / statutory-plan boundary layer. The "
      "planning services present are Tertiary Planning Unit boundaries, TPB guideline "
      "graphics and enforcement statistics. |")
    A("| 3 | SPP3 `OZP_PLAN` MapServer (layers 1000, 1001, 1004, 1010–1015, 1019), "
      "referenced by the portal's own code | Folder `SPP3` returns **HTTP 499 “Token "
      "Required”**. Not publicly queryable. |")
    A("| 4 | SPP3 API (`/api/Plan/*`) | Only answers POST with an undocumented body; "
      "`GetPlanMoreInfor` returned an empty result for `S/STT/2`. The per-plan GeoJSON "
      "links the UI uses (`dlGeoJSONLink`) sit behind `proxyAPI` plus authorisation. |")
    A("| 5 | Town Planning Board website | Delegates all OZP content to SPP3 "
      "(`https://www.ozp.tpb.gov.hk/?lang=en`); no separate OZP GIS page. |")
    A("| 6 | Gazetted statutory plans XML "
      "(`https://www.ozp.tpb.gov.hk/api/OZPStatistic?year=YYYY&quarter=N&type=xml`) | "
      "**Public and readable.** Confirms both plan numbers, official names and gazette "
      "dates — but contains no geometry. |")
    A("")
    A("### Verified plan metadata (from source 6)")
    A("")
    A("| Plan | Official name | Draft exhibited |")
    A("|---|---|---|")
    A("| `S/STT/2` | San Tin Technopole Outline Zoning Plan / 新田科技城分區計劃大綱圖 | "
      "20/09/2024 (2024 Q3) |")
    A("| `S/YL-NTM/15` | Ngau Tam Mei Outline Zoning Plan / 牛潭尾分區計劃大綱圖 | "
      "31/10/2025 (2025 Q4) |")
    A("")
    A("The exhibition date is the s.5/s.7 gazette date of the draft plan. It is **not** a "
      "final approval date and **not** a geometry-version date.")
    A("")
    A("### What could not be verified")
    A("")
    A("- **Geometry:** no Polygon or MultiPolygon, therefore no geometry type, vertex count "
      "or topology to report.")
    A("- **CRS:** unknown. The SPP3 map uses HK80 basemaps, but that is a display choice, "
      "not a declaration about the data.")
    A("- **Schema / data dictionary:** referenced by the dataset but not retrievable.")
    A("- **Licence:** the dataset requires acceptance of Terms and Conditions of Use "
      "“enclosed in the downloaded data”. Since no download succeeded, the licence text is "
      "**unverified**, not assumed permissive.")
    A("")
    A("### Consequence")
    A("")
    A("- `reports.json` is **unchanged**: `report_areas[]` stays empty and `label_lat/lng` "
      "stay null. Validation remains incomplete, deliberately.")
    A("- No mapping to the `report_areas[]` schema is proposed, because a proposal without "
      "verified geometry would only invite it to be treated as approved.")
    A("- An OZP boundary is a **planning-scheme boundary**, not the EIA project footprint. "
      "Even once obtained it must be recorded as `area_type: \"planning_scheme_area\"` and "
      "must never be described as the project footprint.")
    A("- **Decision (2026-10-18):** official public data only; no approach to TPB or CSDI. "
      "Project-area highlighting is **deferred**. `report_areas_status` is now "
      "`deferred_no_public_geometry` and the map will use the district context layer plus "
      "an accessible report list/card instead of a highlighted area.")
    A("")
    A("## Stage 0 exit criteria — status")
    A("")
    A("| Criterion (PRD §9) | Status | Evidence |")
    A("|---|---|---|")
    A("| Both reports downloaded | **Met** | 38 files, 27.0 MB, checksums re-verified |")
    A("| Page-numbering mode verified and recorded | **Met** | `printed` for both; "
      "`page_numbering.json`. Counts re-derived with the corrected matcher (v2c) and "
      "diffed against the superseded output in `PAGE_NUMBERING_RECONCILIATION.md` |")
    A("| Executive-summary availability recorded | **Met** | EN + TC PDFs for both; "
      "`reports.json` |")
    A("| District IDs resolved against the boundary source | **Met** | M = Yuen Long, "
      "N = North, read from the HAD file |")
    A("| `reports.json` created per the registry schema | **NOT met** | "
      "`validation_status: incomplete` — `report_areas[]` and label coordinates missing |")
    A("")
    A("**Stage 0 is therefore blocked on exactly one item: report-area geometry.** "
      "Everything else is complete and evidenced.")
    A("")

    out = os.path.join(ROOT, "stage0", "STAGE0_INVENTORY.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("written:", out)
    print("written:", csv_path)


if __name__ == "__main__":
    main()
