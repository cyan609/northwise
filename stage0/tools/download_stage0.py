#!/usr/bin/env python3
"""Stage 0 Step 1: download official EPD EIA report files and record provenance.

Stdlib only. Writes stage0/source-data/<register>/... and a manifest JSON with
URL, HTTP status, content type, byte size, SHA-256 and retrieval timestamp.
Nothing is invented: every URL comes from the EPD project/index/TOC pages that
were fetched and parsed first.
"""
import hashlib
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = "/Users/chloeyan/workbuddy-ai/NORTHWISE/stage0/source-data"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

ST = ("https://www.epd.gov.hk/eia/files/applications/en/pp_955/eia_6390/"
      "progress/action_180296/NMHST%20v3")
NTM = ("https://www.epd.gov.hk/eia/files/applications/en/pp_363/eia_6226/"
       "progress/action_176330")

# (register_no, subdir, url, local_filename)
FILES = []
for n in range(1, 16):
    FILES.append(("AEIAR-276-2026", "chapters", f"{ST}/eia/eia_ch{n:02d}_out.pdf",
                  f"eia_ch{n:02d}_out.pdf"))
FILES.append(("AEIAR-276-2026", "chapters", f"{ST}/eia/eia_text_sign_page.pdf",
              "eia_text_sign_page.pdf"))
FILES.append(("AEIAR-276-2026", "executive-summary", f"{ST}/es/es_eng_out.pdf",
              "es_eng_out.pdf"))
FILES.append(("AEIAR-276-2026", "executive-summary", f"{ST}/es/es_chi_out.pdf",
              "es_chi_out.pdf"))

NTM_CHAPTERS = [
    "s1_introduction.pdf", "s2_project_description.pdf", "s3_aq.pdf",
    "s4_noise.pdf", "s5_water_quality.pdf", "s6_sewerage.pdf", "s7_wast.pdf",
    "s8_land_con.pdf", "s9_eco.pdf", "s10_fisheries.pdf", "s11_lvia.pdf",
    "s12_cultural_heritage.pdf", "s13_hazard_to_life.pdf",
    "s14_landfill_gas.pdf", "S15_EMF.pdf", "s16_ema.pdf",
    "s17_summary_of_outcomes.pdf", "s18_conclusion.pdf",
]
for f in NTM_CHAPTERS:
    FILES.append(("AEIAR-271-2025", "chapters", f"{NTM}/{f}", f))
FILES.append(("AEIAR-271-2025", "executive-summary", f"{NTM}/es_e.pdf", "es_e.pdf"))
FILES.append(("AEIAR-271-2025", "executive-summary", f"{NTM}/es_tc.pdf", "es_tc.pdf"))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, "", b""
    except Exception as e:  # noqa: BLE001 - record, do not abort the batch
        return -1, f"ERROR: {type(e).__name__}: {e}", b""


def main():
    manifest = []
    for reg, sub, url, name in FILES:
        dest_dir = os.path.join(ROOT, reg, sub)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, name)
        status, ctype, body = fetch(url)
        rec = {
            "register_no": reg,
            "group": sub,
            "filename": name,
            "local_path": os.path.relpath(dest, os.path.dirname(ROOT)),
            "source_url": url,
            "http_status": status,
            "content_type": ctype,
            "bytes": len(body),
            "sha256": None,
            "retrieved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if status == 200 and body.startswith(b"%PDF"):
            with open(dest, "wb") as fh:
                fh.write(body)
            rec["sha256"] = hashlib.sha256(body).hexdigest()
            rec["ok"] = True
        else:
            rec["ok"] = False
            rec["problem"] = ("not a PDF" if status == 200 else "download failed")
        manifest.append(rec)
        print(f"{'OK ' if rec['ok'] else 'FAIL'} {reg:14s} {name:34s} "
              f"{status} {len(body)/1048576:7.2f} MB")
        time.sleep(0.3)

    out = os.path.join(ROOT, "download_manifest.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    ok = sum(1 for r in manifest if r["ok"])
    print(f"\n{ok}/{len(manifest)} downloaded -> {out}")
    total = sum(r["bytes"] for r in manifest if r["ok"])
    print(f"total {total/1048576:.1f} MB")


if __name__ == "__main__":
    main()
