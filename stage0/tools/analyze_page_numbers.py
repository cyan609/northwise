#!/usr/bin/env python3
"""Stage 0: determine page-numbering mode per report from the PDFs.

REVISED 2026-10-18 (v2). The v1 matcher required the footer to be the last thing
on the page (`...$`). Two failure modes were found while building the Stage 1
extractor:

  * false negatives - some pages carry a stray character AFTER the footer
    (e.g. a trailing "4" on eia_ch04_out.pdf pp.49/52/55), so a real folio was
    reported as missing;
  * false positives - without a left boundary, "S/STT/2 March 2026" in body text
    was read as folio "2" on eia_ch01_out.pdf p.4.

v2 reuses the corrected footer logic from stage1/extract_pages.py (no end anchor,
240-character footer window, last match wins, `(?<![\\w/\\-.])` left boundary) and
the full-text bridge stage1/pdf_text.js. What stays Stage 0's own job, and is NOT
taken from the Stage 1 extractor: per-chapter aggregation, folio-form counts,
viewer-index offsets, the /PageLabels check and the report-level mode decision.

Method:
  1. Read every page's full text via macOS PDFKit (no packages installed).
  2. The footer ends with "<folio> <Month> <Year>"; the folio is the token
     immediately before the month-year, inside the last 240 characters.
  3. Folio forms: chapter-page ("4-12"), chapter-sec-page ("1-1-i"),
     chapter-roman ("15-i"), plain ("12"), roman ("iv").
  4. Classify each page: verified / absent / unverified. No inference, and no
     label is ever computed from the page index or a neighbouring page.
  5. Check the raw PDF for a /PageLabels tree.
  6. Compare the folio with the 1-based viewer index and report the offset.

Writes stage0/source-data/page_numbering.json. Prints a summary.
"""
import json
import os
import re
import subprocess

ROOT = "/Users/chloeyan/workbuddy-ai/NORTHWISE"
SRC = os.path.join(ROOT, "stage0", "source-data")
# full page text, shared with the Stage 1 extractor
JXA = os.path.join(ROOT, "stage1", "pdf_text.js")

MONTHS = (r"(?:January|February|March|April|May|June|July|August|September|"
          r"October|November|December)")

# folio immediately before the month-year footer; no end anchor; left boundary.
# Forms:
#   chapter-page       4-12
#   chapter-sec-page   1-1-i
#   chapter-roman      15-i      (front matter of a chapter, observed on ch.15)
#   plain              12
#   roman              iv
# The chapter-roman form was missing in v1 and v2a: v1 matched only the trailing
# "i" (losing the chapter part), v2a rejected it entirely because the left
# boundary now blocks a token preceded by "-".
#
# chapter-roman is a SEPARATE named group, listed first, so the form histogram
# does not merge "15-i" (chapter front matter) with "4-12" (chapter body page).
# Both are "compound" in the loose sense, but they are different label systems
# and must stay countable apart in the audit record.
FOOTER = re.compile(
    r"(?<![\w/\-.])"
    r"(?:(?P<chapter_roman>\d{1,2}-[ivxlcdm]{1,7})"
    r"|(?P<compound>\d{1,2}-\d{1,4}(?:-[0-9]{1,4}|-[ivxlcdm]+)?)"
    r"|(?P<plain>\d{1,4})"
    r"|(?P<roman>[ivxlcdm]{1,7}))"
    r"\s+" + MONTHS + r"\s+20\d\d",
    re.IGNORECASE)
DATE_END = re.compile(MONTHS + r"\s+20\d\d", re.IGNORECASE)
FOOTER_WINDOW = 240

MATCHER_NOTE = ("v2c: token before '<Month> <Year>' in the last 240 chars, no end "
                "anchor, last match wins, left boundary (?<![\\w/\\-.]) or a "
                "chapter-roman folio (15-i) that is itself preceded by '-'; "
                "chapter-roman kept as its own form; compound page part allows "
                "1-4 digits (8-100)")


def probe(path):
    out = subprocess.run(["osascript", "-l", "JavaScript", JXA, path],
                         capture_output=True, text=True, timeout=900)
    if out.returncode != 0 or not out.stdout.strip():
        return {"error": out.stderr.strip()[:200] or "no output"}
    return json.loads(out.stdout)


def classify(text):
    """Return (folio, form, status, evidence). Never infers a label."""
    norm = re.sub(r"\s+", " ", text).strip()
    if not norm:
        return None, None, "unverified", None
    evidence = norm[-140:] if len(norm) > 140 else norm
    window = norm[-FOOTER_WINDOW:]

    matches = list(FOOTER.finditer(window))
    if matches:
        m = matches[-1]
        for form in ("chapter_roman", "compound", "plain", "roman"):
            if m.group(form):
                return m.group(form), form.replace("_", "-"), "verified", evidence

    if DATE_END.search(window):
        return None, None, "absent", evidence
    return None, None, "unverified", evidence


def has_page_labels(path):
    with open(path, "rb") as fh:
        return b"/PageLabels" in fh.read()


def analyse_report(reg, files):
    per_file = []
    for f in files:
        path = os.path.join(SRC, reg, "chapters", f["filename"])
        d = probe(path)
        if "error" in d:
            per_file.append({"filename": f["filename"], "error": d["error"]})
            continue

        rows = []
        for p in d["page_data"]:
            folio, form, status, evidence = classify(p["text"])
            rows.append({"i": p["i"], "folio": folio, "form": form,
                         "status": status, "chars": p["chars"],
                         "evidence": evidence})

        verified = [r for r in rows if r["status"] == "verified"]
        forms = {}
        for r in verified:
            forms[r["form"]] = forms.get(r["form"], 0) + 1

        # offsets: viewer index (1-based) minus the last numeric part of the folio
        offsets = []
        for r in verified:
            last = re.split(r"-", r["folio"])[-1]
            if last.isdigit():
                offsets.append((r["i"] + 1) - int(last))

        n_pages = int(d["pages"])

        # Sequence integrity of the printed folios. Two source-side anomalies
        # were found by diffing against v1 and are worth recording per chapter
        # rather than rediscovering later:
        #   duplicate labels - two pages print the same folio (ch.10: 10-119)
        #   missing numbers  - a folio in the range is printed on no page
        #                      (s12: 12-23)
        # A duplicate label means a printed folio is NOT a unique page
        # identifier, which is why citations must also carry pdf_page_index.
        labels = [r["folio"] for r in verified]
        dupes = sorted({l for l in labels if labels.count(l) > 1})
        nums = []
        for r in verified:
            last = re.split(r"-", r["folio"])[-1]
            if last.isdigit():
                nums.append(int(last))
        missing = (sorted(set(range(min(nums), max(nums) + 1)) - set(nums))
                   if nums else [])

        per_file.append({
            "filename": f["filename"],
            "pages": n_pages,
            "pages_with_folio": len(verified),
            "coverage": round(len(verified) / n_pages, 3) if n_pages else 0,
            "status_counts": {
                "verified": len(verified),
                "absent": sum(1 for r in rows if r["status"] == "absent"),
                "unverified": sum(1 for r in rows if r["status"] == "unverified"),
            },
            "forms": forms,
            "offset_min": min(offsets) if offsets else None,
            "offset_max": max(offsets) if offsets else None,
            "duplicate_labels": dupes,
            "missing_page_numbers": missing,
            "page_labels_tree": has_page_labels(path),
            "samples": [{"viewer_index_1based": r["i"] + 1, "folio": r["folio"],
                         "form": r["form"], "status": r["status"]}
                        for r in rows[:3]] +
                       [{"viewer_index_1based": r["i"] + 1, "folio": r["folio"],
                         "form": r["form"], "status": r["status"]}
                        for r in rows[-2:]],
            "pages_without_folio": [r["i"] + 1 for r in rows
                                    if r["status"] != "verified"],
        })
    return per_file


def decide(per_file):
    """Report-level mode.

    v2b uses PAGE-WEIGHTED coverage (total verified / total pages) rather than
    the mean of per-chapter coverage. The mean-of-means let small chapters
    dominate: San Tin ch.15 (11 pages, 2 folios) and ch.13 (7 pages) pulled the
    average below the threshold even though 86% of the report's pages are
    numbered. Both figures are recorded so the choice stays auditable.
    """
    good = [f for f in per_file if "error" not in f and f["pages"]]
    if not good:
        return "unverified", "no chapter PDF could be read", {}, None, None
    total_pages = sum(f["pages"] for f in good)
    total_folios = sum(f["pages_with_folio"] for f in good)
    agg_cov = total_folios / total_pages if total_pages else 0
    mean_cov = sum(f["coverage"] for f in good) / len(good)
    forms = {}
    for f in good:
        for k, v in f["forms"].items():
            forms[k] = forms.get(k, 0) + v

    if agg_cov >= 0.8 and forms:
        dominant = max(forms, key=forms.get)
        if dominant == "compound":
            note = ("Printed folios are compound chapter-page labels "
                    "(e.g. 2-1, 1-1-i) and are NOT the PDF viewer page index. "
                    f"{total_folios}/{total_pages} pages numbered "
                    f"({agg_cov:.1%}); some pages are genuinely unnumbered.")
            return "printed", note, forms, agg_cov, mean_cov
        note = ("Printed folios are plain/roman numbers and are NOT the PDF "
                f"viewer page index. {total_folios}/{total_pages} pages numbered "
                f"({agg_cov:.1%}).")
        return "printed", note, forms, agg_cov, mean_cov
    if agg_cov > 0:
        return ("unverified",
                f"folios found on only {agg_cov:.0%} of pages", forms,
                agg_cov, mean_cov)
    return "none", "no printed folio detected in page text", forms, agg_cov, mean_cov


def main():
    manifest = json.load(open(os.path.join(SRC, "download_manifest.json")))
    result = {"matcher": MATCHER_NOTE,
              "method": "footer token before '<Month> <Year>' via PDFKit full page text",
              "reports": {}}
    for reg in ("AEIAR-276-2026", "AEIAR-271-2025"):
        files = [m for m in manifest
                 if m["register_no"] == reg and m["group"] == "chapters" and m["ok"]]
        files.sort(key=lambda m: m["filename"])
        per_file = analyse_report(reg, files)
        mode, note, forms, agg_cov, mean_cov = decide(per_file)
        result["reports"][reg] = {"page_numbering": mode, "note": note,
                                  "folio_forms": forms,
                                  "coverage_page_weighted": round(agg_cov, 3),
                                  "coverage_mean_of_chapters": round(mean_cov, 3),
                                  "chapters": per_file}
        print(f"\n=== {reg} -> {mode}")
        print(f"    {note}")
        print(f"    coverage: page-weighted {agg_cov:.3f} | "
              f"mean-of-chapters {mean_cov:.3f}")
        for f in per_file:
            if "error" in f:
                print(f"    ERROR {f['filename']}: {f['error']}")
                continue
            print(f"    {f['filename']:26s} pages={f['pages']:3d} "
                  f"cov={f['coverage']:.2f} {f['status_counts']} "
                  f"offset={f['offset_min']}..{f['offset_max']} "
                  f"PageLabels={f['page_labels_tree']}")
            if f["duplicate_labels"]:
                print(f"      DUPLICATE folios: {f['duplicate_labels']}")
            if f["missing_page_numbers"]:
                print(f"      folio numbers printed on no page: "
                      f"{f['missing_page_numbers']}")
    out = os.path.join(SRC, "page_numbering.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
