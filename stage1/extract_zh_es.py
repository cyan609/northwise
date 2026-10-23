#!/usr/bin/env python3
"""Stage 1b: extract a CHINESE executive-summary PDF into page-level records.

Why this exists
---------------
Stage 1 (`extract_pages.py`) only handles chapter PDFs listed in
`stage0/reports.json -> chapters[]`. The Traditional Chinese executive
summaries are listed under `exec_summary_zh_url` instead, and their footers use
Chinese month-year forms (`4 2026 年 3 月`, `58 二零二五年八月`) that the English
footer regex cannot read. This script reuses the same PDFKit bridge and the same
record shape, and adds the Chinese footer rule.

It writes the SAME schema as extract_pages.py plus two fields:

    doc_kind   "executive_summary"  (so the UI can say "Executive Summary"
                                    instead of pretending this is a chapter)
    doc_lang   "zh-Hant"            (so retrieval can tell an ORIGINAL Chinese
                                    source from an English one)

`chapter` is 0. That is a deliberate placeholder, not a claim that the report
has a chapter zero: the executive summary is a separate document with its own
pagination, and 0 keeps the citation token numeric so the existing citation
validator and claim evaluator keep working unchanged.

Rules carried over from extract_pages.py, unchanged:
  - `page_label` is the folio actually printed on the page, copied verbatim.
    Never computed from the index.
  - `page_label_status` is verified | absent | unverified.
  - The text is stored exactly as PDFKit returns it.

Usage:
    python3 stage1/extract_zh_es.py \
        --pdf stage0/source-data/AEIAR-276-2026/executive-summary/es_chi_out.pdf \
        --out stage1/data/aeiar-276-2026_es_zh.pages.jsonl
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_pages import ROOT, REGISTRY, read_pdf, sha256_of

# The printed folio, then a month-year in either Arabic or Chinese numerals.
#   "4 2026 年 3 月"      -> 4
#   "58 二零二五年八月"    -> 58
#   "i 二零二五年八月"     -> i
ZH_YEAR = r"(?:\d{4}|[〇零一二三四五六七八九]{4})"
ZH_MONTH = r"(?:\d{1,2}|[一二三四五六七八九十]{1,3})"
FOOTER_ZH = re.compile(
    r"^(?P<folio>\d{1,4}|[ivxlcdm]{1,7})"
    r"\s+" + ZH_YEAR + r"\s*年\s*" + ZH_MONTH + r"\s*月$",
    re.IGNORECASE)
# A month-year with no folio before it: the page is genuinely unnumbered.
DATE_END_ZH = re.compile(ZH_YEAR + r"\s*年\s*" + ZH_MONTH + r"\s*月", re.IGNORECASE)

FOOTER_WINDOW = 240
EVIDENCE_CHARS = 140


def classify_page_zh(raw_text):
    """Return (label, status, evidence) for one Chinese page. No inference."""
    norm = re.sub(r"\s+", " ", raw_text).strip()
    if not norm:
        return None, "unverified", None

    evidence = norm[-EVIDENCE_CHARS:] if len(norm) > EVIDENCE_CHARS else norm
    window = norm[-FOOTER_WINDOW:]

    # The footer is the LAST line of the page, so match against the tail of the
    # page only. Taking the last match (not the first) keeps a date quoted in
    # body text from being read as the footer.
    tail_lines = [ln.strip() for ln in raw_text.strip().split("\n") if ln.strip()]
    for line in reversed(tail_lines[-4:]):
        m = FOOTER_ZH.match(line)
        if m:
            return m.group("folio"), "verified", evidence

    if DATE_END_ZH.search(window):
        return None, "absent", evidence
    return None, "unverified", evidence


def find_report(pdf_path, registry):
    """Locate the registry entry whose exec_summary_zh_url ends with this file."""
    name = os.path.basename(pdf_path)
    for report in registry["reports"]:
        url = report.get("exec_summary_zh_url") or ""
        if url and os.path.basename(url) == name:
            return report
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chapter-title", default=None)
    args = ap.parse_args()

    pdf_path = args.pdf if os.path.isabs(args.pdf) else os.path.join(ROOT, args.pdf)
    out_path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    if not os.path.exists(pdf_path):
        sys.exit(f"PDF not found: {pdf_path}")

    registry = json.load(open(REGISTRY))
    report = find_report(pdf_path, registry)
    if not report:
        sys.exit(f"PDF is not any report's exec_summary_zh_url in {REGISTRY}: "
                 f"{os.path.basename(pdf_path)}")

    digest = sha256_of(pdf_path)
    page_count, texts = read_pdf(pdf_path)
    if len(texts) != page_count:
        sys.exit(f"PDFKit returned {len(texts)} pages, header says {page_count}")

    chapter_title = args.chapter_title or "EXECUTIVE SUMMARY (CHINESE ORIGINAL)"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    records = []
    with open(out_path, "w", encoding="utf-8") as fh:
        for i, raw in enumerate(texts):
            label, status, evidence = classify_page_zh(raw)
            rec = {
                "report_id": report["report_id"],
                "chapter": 0,
                "chapter_title": chapter_title,
                "pdf_page_index": i,
                "page_label": label,
                "page_label_status": status,
                "page_label_evidence": evidence,
                "text": raw,
                "source_pdf": os.path.relpath(pdf_path, ROOT),
                "source_sha256": digest,
                "doc_kind": "executive_summary",
                "doc_lang": "zh-Hant",
            }
            records.append(rec)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    counts = {}
    for r in records:
        counts[r["page_label_status"]] = counts.get(r["page_label_status"], 0) + 1
    labels = [r["page_label"] for r in records if r["page_label"]]
    arabic = [int(l) for l in labels if l.isdigit()]

    print(f"file      : {os.path.relpath(pdf_path, ROOT)}")
    print(f"report    : {report['register_no']} ({report['report_id']})")
    print(f"sha256    : {digest}")
    print(f"pdf pages : {page_count}")
    print(f"records   : {len(records)}  -> "
          f"{'OK' if len(records) == page_count else 'MISMATCH'}")
    print(f"statuses  : {counts}")
    print(f"labels    : {len(labels)} total, {len(set(labels))} distinct")

    dupes = sorted({l for l in labels if labels.count(l) > 1})
    if dupes:
        print(f"DUPLICATE LABELS: {dupes}")

    # A contiguous 1..N run is the expected shape; report gaps rather than hide
    # them, because a gap means a folio was misread.
    if arabic:
        missing = sorted(set(range(1, max(arabic) + 1)) - set(arabic))
        print(f"arabic folios : {min(arabic)}..{max(arabic)} "
              f"({len(arabic)} pages)")
        if missing:
            print(f"GAPS in folio run: {missing}")
        if arabic != sorted(arabic):
            print("WARNING: folios are not in ascending page order")

    print("\nsample records:")
    for idx in (0, len(records) // 2, len(records) - 1):
        r = records[idx]
        print(f"  idx {r['pdf_page_index']:>3} | label={r['page_label']!r} "
              f"| {r['page_label_status']:<10} | chars={len(r['text'])}")
    print(f"\nwrote {len(records)} records -> {os.path.relpath(out_path, ROOT)}")


if __name__ == "__main__":
    main()
