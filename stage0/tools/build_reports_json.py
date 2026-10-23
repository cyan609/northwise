#!/usr/bin/env python3
"""Stage 0 Step 2: build stage0/reports.json (report registry) from verified data.

Only verified values are written. Fields that cannot yet be filled honestly are
set to null / [] and listed in `incomplete_reasons`, so the file fails the PRD
geometry validation rule on purpose rather than inventing geometry.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

ROOT = "/Users/chloeyan/workbuddy-ai/NORTHWISE"
SRC = os.path.join(ROOT, "stage0", "source-data")
sys.path.insert(0, os.path.join(ROOT, "stage0", "tools"))
from build_inventory import TITLES, META, chapter_num  # noqa: E402

NM_IT_ZONE_URL = "https://www.nm.gov.hk/en/four-zones/innovation-and-technology-zone"

# Verified from nm.gov.hk /api/zone/<id> (saved as provenance/nm_it_zone_api.json):
# subzones of the Innovation and Technology Zone are San Tin Technopole,
# Ngau Tam Mei New Development Area and Au Tau.
NM_SUBZONE = {
    "AEIAR-276-2026": {"zone": "Innovation and Technology Zone",
                       "area": "San Tin Technopole"},
    "AEIAR-271-2025": {"zone": "Innovation and Technology Zone",
                       "area": "Ngau Tam Mei New Development Area"},
}
PROJECT_AREA = {
    "AEIAR-276-2026": ("San Tin", "新田"),
    "AEIAR-271-2025": ("Ngau Tam Mei", "牛潭尾"),
}
APPROVAL = {
    "AEIAR-276-2026": "2026-08-12",
    "AEIAR-271-2025": "2025-12-18",
}
REPORT_ID = {"AEIAR-276-2026": "aeiar-276-2026", "AEIAR-271-2025": "aeiar-271-2025"}


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    manifest = json.load(open(os.path.join(SRC, "download_manifest.json")))
    pn = json.load(open(os.path.join(SRC, "page_numbering.json")))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    reports = []
    for reg in ("AEIAR-276-2026", "AEIAR-271-2025"):
        rows = [m for m in manifest if m["register_no"] == reg and m["ok"]]
        chs = sorted([m for m in rows if m["group"] == "chapters"],
                     key=lambda m: chapter_num(m["filename"]))
        es = {m["filename"]: m for m in rows if m["group"] == "executive-summary"}
        en = es.get("es_eng_out.pdf") or es.get("es_e.pdf")
        zh = es.get("es_chi_out.pdf") or es.get("es_tc.pdf")

        pn_ch = {c["filename"]: c for c in pn["reports"][reg]["chapters"]}
        chapters = []
        for m in chs:
            n = chapter_num(m["filename"])
            c = pn_ch.get(m["filename"], {})
            chapters.append({
                "number": None if n >= 900 else n,
                "title": TITLES[reg].get(m["filename"], None),
                "format": "pdf",
                "file_url": m["source_url"],
                "local_file": m["local_path"],
                "sha256": m["sha256"],
                "pages": c.get("pages"),
                "printed_folio_scheme": ("none" if c.get("pages_with_folio", 0) == 0
                                         else ("mixed" if len(c.get("forms", {})) > 1
                                               else next(iter(c.get("forms", {})), None))),
                "pages_without_folio": (c.get("pages", 0) - c.get("pages_with_folio", 0))
                                       if c.get("pages") else None,
            })

        area_en, area_zh = PROJECT_AREA[reg]
        reports.append({
            "report_id": REPORT_ID[reg],
            "register_no": reg,
            "status": "approved",
            "status_note": "conditionally approved (per EPD project page)",
            "approval_date": APPROVAL[reg],
            "title_en": META[reg]["title"],
            "title_zh": META[reg]["title_zh"],
            "project_area_en": area_en,
            "project_area_zh": area_zh,
            "districts": ["hk-district:M"],
            "districts_evidence": ("Yuen Long District (code M in the HAD 18-district "
                                   "GeoJSON). Derived from the OZP plan numbers cited in "
                                   "the reports, not from point-in-polygon: no project "
                                   "coordinates exist yet."),
            "report_areas": [],
            "report_areas_status": "deferred_no_public_geometry",
            "report_areas_decision": ("2026-10-18: official public data only. No verified "
                                      "project geometry is publicly obtainable (CSDI/SPP3 "
                                      "requires a token), so project-area highlighting is "
                                      "deferred. The map will use the district context layer "
                                      "plus an accessible report list/card instead."),
            "label_lat": None,
            "label_lng": None,
            "original_url": META[reg]["project_page"],
            "report_index_url": META[reg]["index_page"],
            "exec_summary_en_url": en["source_url"] if en else None,
            "exec_summary_zh_url": zh["source_url"] if zh else None,
            "exec_summary_status": {
                "en": "available" if en else "missing",
                "zh": "available" if zh else "missing",
                "note": ("PDFs verified to open; not linked from the project page, "
                         "only from the report index page."),
            },
            "page_numbering": pn["reports"][reg]["page_numbering"],
            "page_numbering_note": pn["reports"][reg]["note"],
            "nm_scope_evidence": {
                "zone": NM_SUBZONE[reg]["zone"],
                "area": NM_SUBZONE[reg]["area"],
                "url": NM_IT_ZONE_URL,
                "evidence_note": ("Subzone list read from the nm.gov.hk zone API "
                                  "(provenance/nm_it_zone_api.json). Area-level match; "
                                  "the project-to-area link rests on the project name."),
            },
            "chapters": chapters,
            "version": "1.0",
            "retrieved_at": max(m["retrieved_at_utc"] for m in rows),
            "checksum_manifest": "source-data/download_manifest.json",
        })

    out = {
        "schema_version": "stage0-draft-1",
        "generated_at_utc": now,
        "validation_status": "incomplete",
        "incomplete_reasons": [
            "report_areas[] is empty for both reports: no polygon could be traced to an "
            "official project layout or planning map, and no official coordinate source "
            "was found (report text contains no coordinates).",
            "label_lat/label_lng are null for the same reason.",
            "Consequence: the PRD geometry/status validation rule will reject both "
            "entries until geometry is resolved. Nothing was invented to pass it.",
        ],
        "reports": reports,
    }
    path = os.path.join(ROOT, "stage0", "reports.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print("written:", path)
    for r in reports:
        print(f"  {r['register_no']}: {len(r['chapters'])} chapters, "
              f"page_numbering={r['page_numbering']}, "
              f"areas={len(r['report_areas'])}, label=({r['label_lat']},{r['label_lng']})")


if __name__ == "__main__":
    main()
