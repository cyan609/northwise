#!/usr/bin/env python3
"""Regression tests for the Stage 0 page-number matcher (v2).

These two cases are the ones that broke v1, so they are asserted explicitly
before the Stage 0 analysis is allowed to run again.

Case A - eia_ch04_out.pdf (San Tin ch.4, 62 pages)
    v1 reported 59 folios and called pp.49/52/55 unnumbered. They are numbered
    (4-47, 4-50, 4-53) but carry a stray character after the footer.
    Expect: 62/62 verified, labels i, ii, iii then 4-1 ... 4-59, no gaps.

Case B - eia_ch01_out.pdf (San Tin ch.1, 7 pages)
    v1 read "S/STT/2 March 2026" as folio "2" on p.4, and counted 4 folios.
    Expect: exactly 2 folios (1-1-i, 1-1-ii); pages 3-7 absent, not labelled.

Case C - eia_ch15_out.pdf (San Tin ch.15, 11 pages)
    v2a reported 0 folios: the chapter-roman form "15-i"/"15-ii" was rejected
    because the token is preceded by "-" and the left boundary blocks it.
    Expect: 2 folios (15-i, 15-ii) classified as form "chapter-roman" - NOT as
    "compound", which is the chapter-page form (4-12) - and pages 3-11 absent.

Case D - eia_ch08_out.pdf (San Tin ch.8, 124 pages)
    The page part of a compound folio can be THREE digits (8-100 .. 8-120) in
    chapters longer than 99 pages. With `\\d{1,2}` for the page part, v1 matched
    the "100" as a *plain* folio (right count, wrong label) and v2b's new left
    boundary rejected it, turning 21 real folios into `absent`.
    Expect: 124/124 verified, front matter 8-i..8-iv, body 8-1..8-120 with no
    gaps, and index 103/104/105 labelled 8-100/8-101/8-102 as compound.

Usage: python3 stage0/tools/regression_page_numbers.py
Exit code 0 = all assertions pass.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_page_numbers import classify, probe, SRC  # noqa: E402

CASES = {
    "AEIAR-276-2026/chapters/eia_ch04_out.pdf": "A",
    "AEIAR-276-2026/chapters/eia_ch01_out.pdf": "B",
    "AEIAR-276-2026/chapters/eia_ch15_out.pdf": "C",
    "AEIAR-276-2026/chapters/eia_ch08_out.pdf": "D",
}

results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    print(f"  [{'PASS' if condition else 'FAIL'}] {name}"
          + (f" - {detail}" if detail else ""))


def run_case(rel):
    path = os.path.join(SRC, rel)
    d = probe(path)
    if "error" in d:
        raise SystemExit(f"could not read {rel}: {d['error']}")
    pages = int(d["pages"])
    rows = []
    for p in d["page_data"]:
        folio, form, status, evidence = classify(p["text"])
        rows.append({"i": p["i"], "folio": folio, "form": form,
                     "status": status, "evidence": evidence})
    return pages, rows


def case_a():
    print("\nCase A - eia_ch04_out.pdf (62 pages, compound folios)")
    pages, rows = run_case("AEIAR-276-2026/chapters/eia_ch04_out.pdf")
    labels = [r["folio"] for r in rows]

    check("page count is 62", pages == 62, f"got {pages}")
    check("record count equals page count", len(rows) == pages, f"got {len(rows)}")
    check("all pages verified", all(r["status"] == "verified" for r in rows),
          f"statuses={ {s: sum(1 for r in rows if r['status'] == s) for s in ('verified','absent','unverified')} }")
    check("front matter is i, ii, iii", labels[:3] == ["i", "ii", "iii"],
          f"got {labels[:3]}")
    expected = [f"4-{n}" for n in range(1, 60)]
    check("body is 4-1 .. 4-59 with no gaps", labels[3:] == expected,
          f"got {len(labels[3:])} labels, last={labels[-1]!r}")
    check("no duplicate labels", len(set(labels)) == len(labels),
          f"{len(labels)} labels, {len(set(labels))} distinct")
    # the three pages v1 missed
    for idx, want in ((49, "4-47"), (52, "4-50"), (55, "4-53")):
        check(f"page index {idx} is {want} (v1 called it unnumbered)",
              rows[idx]["folio"] == want, f"got {rows[idx]['folio']!r}")
    check("every label appears in its own evidence",
          all(r["folio"] in (r["evidence"] or "") for r in rows))


def case_b():
    print("\nCase B - eia_ch01_out.pdf (7 pages, must not invent labels)")
    pages, rows = run_case("AEIAR-276-2026/chapters/eia_ch01_out.pdf")
    labels = [r["folio"] for r in rows]

    check("page count is 7", pages == 7, f"got {pages}")
    check("exactly two folios", sum(1 for l in labels if l) == 2,
          f"labels={labels}")
    check("folios are 1-1-i and 1-1-ii", labels[:2] == ["1-1-i", "1-1-ii"],
          f"got {labels[:2]}")
    check("no label taken from body text 'S/STT/2'", "2" not in labels,
          f"labels={labels}")
    check("pages 3-7 are absent, not labelled",
          all(r["status"] == "absent" for r in rows[2:]),
          f"statuses={[r['status'] for r in rows[2:]]}")
    check("absent pages carry evidence but no label",
          all(r["folio"] is None and r["evidence"] for r in rows[2:]))


def case_c():
    print("\nCase C - eia_ch15_out.pdf (11 pages, chapter-roman folios)")
    pages, rows = run_case("AEIAR-276-2026/chapters/eia_ch15_out.pdf")
    labels = [r["folio"] for r in rows]

    check("page count is 11", pages == 11, f"got {pages}")
    check("exactly two folios", sum(1 for l in labels if l) == 2,
          f"labels={labels}")
    check("folios are 15-i and 15-ii", labels[:2] == ["15-i", "15-ii"],
          f"got {labels[:2]}")
    check("form is chapter-roman, not compound",
          [r["form"] for r in rows[:2]] == ["chapter-roman", "chapter-roman"],
          f"got {[r['form'] for r in rows[:2]]}")
    check("pages 3-11 are absent, not labelled",
          all(r["status"] == "absent" for r in rows[2:]),
          f"statuses={[r['status'] for r in rows[2:]]}")


def case_d():
    print("\nCase D - eia_ch08_out.pdf (124 pages, three-digit folios)")
    pages, rows = run_case("AEIAR-276-2026/chapters/eia_ch08_out.pdf")
    labels = [r["folio"] for r in rows]

    check("page count is 124", pages == 124, f"got {pages}")
    check("all pages verified", all(r["status"] == "verified" for r in rows),
          f"statuses={ {s: sum(1 for r in rows if r['status'] == s) for s in ('verified','absent','unverified')} }")
    check("front matter is 8-i .. 8-iv",
          labels[:4] == ["8-i", "8-ii", "8-iii", "8-iv"], f"got {labels[:4]}")
    check("body is 8-1 .. 8-120 with no gaps",
          labels[4:] == [f"8-{n}" for n in range(1, 121)],
          f"got {len(labels[4:])} labels, last={labels[-1]!r}")
    for idx, want in ((103, "8-100"), (104, "8-101"), (105, "8-102")):
        check(f"page index {idx} is {want} (three-digit page part)",
              rows[idx]["folio"] == want, f"got {rows[idx]['folio']!r}")
    check("three-digit folios keep form compound",
          all(r["form"] == "compound" for r in rows[103:106]),
          f"got {[r['form'] for r in rows[103:106]]}")
    check("no duplicate labels", len(set(labels)) == len(labels),
          f"{len(labels)} labels, {len(set(labels))} distinct")


def main():
    print("Regression tests - Stage 0 page-number matcher v2")
    case_a()
    case_b()
    case_c()
    case_d()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} assertions passed")
    if failed:
        print("FAILED:")
        for name, _, detail in failed:
            print(f"  - {name} {detail}")
        sys.exit(1)
    print("ALL PASS - safe to re-run the Stage 0 analysis")


if __name__ == "__main__":
    main()
