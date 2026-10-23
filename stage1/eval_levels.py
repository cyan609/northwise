#!/usr/bin/env python3
"""Compare page-level and passage-level retrieval on the same queries.

Read-only. Standard library only. Prints both levels side by side; it does not
judge relevance (that needs a human reading the text).

    python3 stage1/eval_levels.py
    python3 stage1/eval_levels.py --k 2 --width 200
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retrieve as R
import passages as P

# The six queries from stage1/RETRIEVAL_PROTOTYPE.md §5 / RARE_TERM_GATE.md §4,
# plus `offshore wind`, which was the blind-spot probe in RARE_TERM_GATE.md §7.
QUERIES = [
    "black-faced spoonbill",
    "predicted mitigated noise level",
    "geothermal power generation",
    "long viewing distance",
    "noise barrier",
    "wetland habitat enhancement",
    "offshore wind",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--width", type=int, default=200)
    args = ap.parse_args()

    pages = R.Corpus()
    idx = P.PassageIndex(pages)

    for q in QUERIES:
        gate = pages.gate(q)
        print("=" * 100)
        print(f'QUERY: {q!r}   terms={gate["search_terms"]}   gate={gate["status"]}')
        print("=" * 100)

        hits, _ = pages.search(gate["search_terms"], k=args.k)
        print(f'-- PAGE level ({pages.N} pages)')
        for rank, (w, raw, weight, i, matched) in enumerate(hits, 1):
            d = pages.docs[i]
            print(f'  {rank}. {w:.2f} (bm25 {raw:.2f} × {weight} {d["text_form"]}) '
                  f'matched {len(matched)}/{len(gate["search_terms"])}')
            print(f'     {R.format_citation(d)}')
            print(f'     {R.excerpt(d, gate["search_terms"], width=args.width)}')

        phits = idx.search(gate["search_terms"], k=args.k)
        print(f'-- PASSAGE level ({idx.N} passages)')
        for rank, (w, raw, weight, i, matched) in enumerate(phits, 1):
            p = idx.passages[i]
            print(f'  {rank}. {w:.2f} (bm25 {raw:.2f} × {weight} {p["passage_type"]}) '
                  f'matched {len(matched)}/{len(gate["search_terms"])}')
            print(f'     {P.passage_citation(p)}')
            if p["quality_flags"]:
                print(f'     flags: {", ".join(p["quality_flags"])}')
            print(f'     {P.passage_excerpt(p, gate["search_terms"], width=args.width)}')
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
