#!/usr/bin/env python3
"""Stage 1: extract one EPD EIA chapter PDF into page-level JSONL records.

Scope of this step: extraction only. No chunking, no index, no LLM call.

Design rules (all deliberate, all from Stage 0 evidence):

1. One record per PDF page. `pdf_page_index` is **0-based**, matching PDFKit's
   `pageAtIndex(i)`, so index 0 is the first page of the chapter file.
2. `page_label` is the folio actually printed on that page, copied verbatim.
   It is NEVER computed from the index, the chapter number, or a neighbouring
   page. If no folio is printed, it is null.
3. `page_label_status` is one of:
     verified   - a folio was found immediately before the page's month-year footer
     absent     - the page has the month-year footer but no folio before it
     unverified - no recognisable footer (e.g. figure page) or no extractable text
4. `page_label_evidence` keeps the footer region of the page text so the label
   can be audited without reopening the PDF. null when there is no text at all.
5. The text itself is stored exactly as PDFKit returns it; whitespace is only
   normalised on a copy used for footer matching.

Usage:
    python3 stage1/extract_pages.py \
        --pdf stage0/source-data/AEIAR-276-2026/chapters/eia_ch04_out.pdf \
        --out stage1/data/eia_ch04_out.pages.jsonl
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = "/Users/chloeyan/workbuddy-ai/NORTHWISE"
REGISTRY = os.path.join(ROOT, "stage0", "reports.json")
PAGE_NUMBERING = os.path.join(ROOT, "stage0", "source-data", "page_numbering.json")
JXA = os.path.join(ROOT, "stage1", "pdf_text.js")

MONTHS = (r"(?:January|February|March|April|May|June|July|August|September|"
          r"October|November|December)")

# The folio is the token immediately before the "<Month> <Year>" footer.
# Accepted forms: chapter-page (4-12), chapter-sec-page (1-1-i),
# chapter-roman (15-i), plain (12), roman (iv).
# Anchoring on the footer is what keeps body numbers and the year out.
#
# NOTE: deliberately NOT anchored with "$" at the end of the page. Some pages
# carry a stray character AFTER the footer (observed: a trailing "4" on
# eia_ch04_out.pdf pages 49, 52 and 55), which made an end-anchored pattern
# report a printed folio as missing. The folio is still identified by being the
# token directly before the month-year, so the match stays footer-specific
# while tolerating trailing debris.
#
# The lookbehind is required: without it, "S/STT/2 March 2026" in body text was
# read as folio "2" on eia_ch01_out.pdf page 4. A real folio is never preceded
# by a word character, slash, hyphen or dot.
FOOTER = re.compile(
    r"(?<![\w/\-.])"
    r"(?:(?P<chapter_roman>\d{1,2}-[ivxlcdm]{1,7})"
    r"|(?P<compound>\d{1,2}-\d{1,4}(?:-[0-9]{1,4}|-[ivxlcdm]+)?)"
    r"|(?P<plain>\d{1,4})"
    r"|(?P<roman>[ivxlcdm]{1,7}))"
    r"\s+" + MONTHS + r"\s+20\d\d",
    re.IGNORECASE)
DATE_END = re.compile(MONTHS + r"\s+20\d\d", re.IGNORECASE)

# Footer matching is restricted to the tail of the page so a date mentioned in
# body text cannot be mistaken for the footer.
FOOTER_WINDOW = 240

EVIDENCE_CHARS = 140


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_pdf(path):
    """Full page text via the PDFKit bridge. Returns (page_count, [texts])."""
    out = subprocess.run(["osascript", "-l", "JavaScript", JXA, path],
                         capture_output=True, text=True, timeout=900)
    if out.returncode != 0 or not out.stdout.strip():
        raise RuntimeError(f"PDFKit bridge failed: {out.stderr.strip()[:300]}")
    data = json.loads(out.stdout)
    if "error" in data:
        raise RuntimeError(data["error"])
    return int(data["pages"]), [p["text"] for p in data["page_data"]]


def classify_page(raw_text):
    """Return (label, status, evidence) for one page. No inference."""
    norm = re.sub(r"\s+", " ", raw_text).strip()
    if not norm:
        return None, "unverified", None

    evidence = norm[-EVIDENCE_CHARS:] if len(norm) > EVIDENCE_CHARS else norm
    window = norm[-FOOTER_WINDOW:]

    # Take the LAST footer-shaped match in the tail: that is the page footer,
    # not a date quoted higher up the page.
    matches = list(FOOTER.finditer(window))
    if matches:
        m = matches[-1]
        label = (m.group("chapter_roman") or m.group("compound")
                 or m.group("plain") or m.group("roman"))
        return label, "verified", evidence

    if DATE_END.search(window):
        # Footer date is present but no folio precedes it: genuinely unnumbered.
        return None, "absent", evidence

    # No recognisable footer at all (figure page, cover, etc.).
    return None, "unverified", evidence


def find_chapter_in_registry(pdf_path, registry):
    """Match the PDF to a registry chapter by filename, to inherit ids."""
    name = os.path.basename(pdf_path)
    for report in registry["reports"]:
        for ch in report["chapters"]:
            if os.path.basename(ch.get("local_file", "")) == name:
                return report, ch
    return None, None


def baseline_for(filename, report_id):
    """Stage 0 expectation for this chapter, for cross-checking."""
    if not os.path.exists(PAGE_NUMBERING):
        return None
    data = json.load(open(PAGE_NUMBERING))
    for reg, payload in data["reports"].items():
        for ch in payload["chapters"]:
            if ch.get("filename") == filename:
                return reg, ch
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pdf_path = args.pdf if os.path.isabs(args.pdf) else os.path.join(ROOT, args.pdf)
    out_path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    if not os.path.exists(pdf_path):
        sys.exit(f"PDF not found: {pdf_path}")

    registry = json.load(open(REGISTRY))
    report, chapter = find_chapter_in_registry(pdf_path, registry)
    if not report:
        sys.exit(f"PDF is not listed in {REGISTRY}: {os.path.basename(pdf_path)}")

    digest = sha256_of(pdf_path)
    if chapter.get("sha256") and chapter["sha256"] != digest:
        sys.exit("SHA-256 does not match the registry entry - refusing to extract "
                 f"a file that has changed.\n  registry: {chapter['sha256']}\n"
                 f"  on disk : {digest}")

    page_count, texts = read_pdf(pdf_path)
    if len(texts) != page_count:
        sys.exit(f"PDFKit returned {len(texts)} pages, header says {page_count}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    records = []
    with open(out_path, "w", encoding="utf-8") as fh:
        for i, raw in enumerate(texts):
            label, status, evidence = classify_page(raw)
            rec = {
                "report_id": report["report_id"],
                "chapter": chapter.get("number"),
                "chapter_title": chapter.get("title"),
                "pdf_page_index": i,              # 0-based, PDFKit order
                "page_label": label,
                "page_label_status": status,
                "page_label_evidence": evidence,
                "text": raw,
                "source_pdf": os.path.relpath(pdf_path, ROOT),
                "source_sha256": digest,
            }
            records.append(rec)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---------------- validation ----------------
    counts = {}
    for r in records:
        counts[r["page_label_status"]] = counts.get(r["page_label_status"], 0) + 1
    labels = [r["page_label"] for r in records if r["page_label"]]

    print(f"file      : {os.path.relpath(pdf_path, ROOT)}")
    print(f"report    : {report['register_no']} ({report['report_id']}), "
          f"chapter {chapter.get('number')} - {chapter.get('title')}")
    print(f"sha256    : {digest}")
    print(f"pdf pages : {page_count}")
    print(f"records   : {len(records)}  -> {'OK' if len(records) == page_count else 'MISMATCH'}")
    print(f"statuses  : {counts}")
    print(f"labels    : {len(labels)} total, {len(set(labels))} distinct")

    dupes = {l for l in labels if labels.count(l) > 1}
    if dupes:
        print(f"DUPLICATE LABELS: {sorted(dupes)}")

    # every compound label's chapter part should match the chapter number
    bad_prefix = [l for l in labels if "-" in l and l.split("-")[0].isdigit()
                  and int(l.split("-")[0]) != (chapter.get("number") or -1)]
    if bad_prefix:
        print(f"LABEL/CHAPTER MISMATCH: {sorted(set(bad_prefix))}")

    base = baseline_for(os.path.basename(pdf_path), report["report_id"])
    if base:
        reg, ch = base
        expected_folios = ch.get("pages_with_folio")
        got = counts.get("verified", 0)
        print(f"stage0    : pages={ch.get('pages')} pages_with_folio={expected_folios}")
        print(f"delta     : verified {got} vs stage0 {expected_folios} -> "
              f"{'MATCH' if got == expected_folios else 'DIFFERS'}")
        if got != expected_folios:
            print("            investigate before trusting page labels.")

    print("\nsample records:")
    for idx in (0, len(records) // 2, len(records) - 1):
        r = records[idx]
        print(f"  idx {r['pdf_page_index']:>3} | label={r['page_label']!r} "
              f"| {r['page_label_status']:<10} | chars={len(r['text'])} "
              f"| evidence_tail={ (r['page_label_evidence'] or '')[-45:]!r}")

    unverified = [r["pdf_page_index"] for r in records
                  if r["page_label_status"] == "unverified"]
    absent = [r["pdf_page_index"] for r in records
              if r["page_label_status"] == "absent"]
    print(f"\npages without a verified label: absent={absent} unverified={unverified}")
    print(f"\nwrote {len(records)} records -> {os.path.relpath(out_path, ROOT)}")


if __name__ == "__main__":
    main()
