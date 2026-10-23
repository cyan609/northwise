#!/usr/bin/env python3
"""Stage 1: paragraph-level passages over the extracted EIA pages.

This module is a LAYER ON TOP of stage1/retrieve.py. It does not modify it, and
the page-level retriever remains the baseline (`python3 stage1/retrieve.py`).

No packages, no embeddings, no model, no network. Standard library only.

Why passages
------------
A page is a safe citation unit but a poor evidence unit: the median page holds
2,475 characters and 51 lines, and a 260-character excerpt window cut from it is
often mid-sentence and mid-topic. A passage is the paragraph a claim actually
comes from, while the page remains the thing that gets cited.

Segmentation is deliberately conservative. It splits ONLY where the document
itself gives a literal marker. It never guesses at paragraph breaks from
punctuation, line length or layout.

Passage schema (one JSON object per passage)
--------------------------------------------
    passage_id          "<report_id>|c<chapter>|p<pdf_page_index>|s<ordinal>"
                        stable for a given page + segmentation rule set
    passage_ordinal     0-based within the page
    passage_type        prose_paragraph | prose_page | prose_continuation
                        table_fragmented | list | non_substantive | blank
    quality_flags       list; any of:
                          low_context        shorter than MIN_PASSAGE_CHARS
                          fragmented         table/list page kept whole
                          near_blank         page has < NEAR_BLANK_CHARS
                          no_verified_folio  page_label is null or unverified
                          page_start_continuation  starts mid-sentence
    text                passage text, page header/footer/banner removed
    char_len            len(text)
    line_count          non-empty lines in the passage
    section_ref         literal "N.N…" starting a line at or before the passage,
                        within this page only; null when none
    section_ref_status  own | inherited_within_page | not_detected
    report_id, report_title, chapter, chapter_title
    pdf_page_index      0-based, unchanged from the source record
    page_label          unchanged from the source record (may be null)
    page_label_status   verified | absent | unverified (unchanged)
    page_label_verified bool, derived: status == "verified"
    line_start, line_end  0-based line range within the cleaned page text
    source_pdf, source_sha256
    page_text_sha256    sha256 of the ORIGINAL record `text`, so the exact source
                        record can be verified without trusting this file

Nothing is invented: `page_label` and `section_ref` are copied or null, never
reconstructed. A passage on a page with no verified folio keeps
`page_label: null` and cites `pdf_page_index` instead.

Usage
-----
    python3 stage1/passages.py --stats
    python3 stage1/passages.py "black-faced spoonbill" --k 3
    python3 stage1/passages.py "noise barrier" --k 2 --expand
    python3 stage1/passages.py "noise barrier" --json
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retrieve as R  # reuse the page corpus, tokenizer and form classifier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- segmentation
# A paragraph begins with a literal section number at the start of a line.
# The reference must belong to its own chapter: chapter 3 is full of numeric
# table values like "1.5 - 10 54.5 - 54.6", which would otherwise split a table
# page into hundreds of 10-character "passages" (measured: 331 such lines).
PARA_START = re.compile(r"^(\d{1,2}\.\d{1,2}(?:\.\d{1,2}){0,2})\s+\S")

# A page with no folio still ends with a bare month-year footer. retrieve.py's
# footer rule requires a folio before the month, so these survive its cleaning.
MONTH_FOOTER = re.compile(r"^(?:" + R.MONTHS + r")\s+20\d\d$", re.IGNORECASE)

# Several paragraph numbers stacked in the left margin are emitted as one line:
# "4.2.1 4.2.2 4.2.3 The criteria of evaluating noise impacts...". Which of the
# three the following text belongs to is not recoverable, so the reference is
# recorded as ambiguous rather than asserted.
MULTI_REF = re.compile(r"^(?:\d{1,2}\.\d{1,2}(?:\.\d{1,2}){0,2}\s+){2,}")

# TOC entries carry dot leaders or end with a folio/page number.  These must
# not be treated as paragraph anchors when assigning section_ref to a
# table_fragmented passage.
TOC_RE = re.compile(r'\.\s*\.\s*\.')


def looks_like_toc_line(line):
    """True if the line is a table-of-contents entry rather than body text.

    A TOC line has dot leaders ("...") or ends with a standalone page/folio
    number such as "15-1", "8", or "iv".  Genuine paragraph anchors do not.
    """
    s = line.strip()
    if TOC_RE.search(s):
        return True
    # Ends with a standalone 1-3 digit number or simple folio (not a year).
    if re.search(r'\s+\d{1,3}(?:-\d{1,3})?$', s):
        return True
    # Ends with a roman-numeral folio.
    if re.search(r'\s+[ivxlc]+\.?$', s, re.I):
        return True
    return False


# Chapter banners at the top of a page ("NOISE", "4 NOISE", "AIR QUALITY").
BANNER_MAX_CHARS = 60

NEAR_BLANK_CHARS = 200      # <1% of pages (cleaned length p1 = 216)
MIN_PASSAGE_CHARS = 80      # below this a passage is a fragment, not evidence

# Weights mirror the page-level FORM_WEIGHT so the two levels stay consistent in
# spirit. Scores are still NOT comparable across levels (different df and avgdl).
PASSAGE_WEIGHT = {
    "prose_paragraph": 1.00,
    "prose_page": 1.00,
    "prose_continuation": 0.90,
    "heading": 0.20,
    "table_fragmented": 0.60,
    "list": 0.50,
    "non_substantive": 0.15,
    "blank": 0.00,
}

HEADING_MAX_CHARS = 120


def anchor_ref(line, chapter):
    """The literal section number that starts this line, or None.

    Chapter-scoped: a chapter 9 page cannot open a paragraph numbered 1.88.
    """
    m = PARA_START.match(line.strip())
    if not m:
        return None
    ref = m.group(1)
    if isinstance(chapter, int) and not ref.startswith(f"{chapter}."):
        return None
    return ref


def heading_like(line):
    """A short line with no terminal punctuation.

    On its own this is a weak signal — PDF lines break mid-sentence, so
    continuation lines look identical. It is only ever trusted in `segment()`
    when the NEXT line starts a numbered paragraph.
    """
    s = line.strip()
    if not s or len(s) > 80 or len(s.split()) > 12:
        return False
    if not s[0].isupper():
        return False
    if s.endswith((".", ",", ";", ":", "-", ")")) or s[-1].isdigit():
        return False
    if s.startswith(("•", "-", "*", "(")):
        return False
    if re.match(r"^(Table|Figure)\s+\d", s):
        return False
    return True


def strip_page_extras(text, chapter):
    """retrieve.strip_boilerplate plus two rules it does not cover.

    Returns (lines, notes) where notes records what was removed. Nothing is
    removed silently: the counts go into the passage's page-level provenance.
    """
    clean, hdr, ftr = R.strip_boilerplate(text)
    lines = [x.strip() for x in clean.split("\n") if x.strip()]
    notes = {"header_lines": hdr, "folio_footer": ftr,
             "month_footer": 0, "banner": 0, "repeated_header": 0}

    if lines and MONTH_FOOTER.match(lines[-1]):
        lines.pop()
        notes["month_footer"] = 1

    # A running header can also reappear in the MIDDLE of a page — the extracted
    # text puts "Agreement No. CE 33/2021 (CE)" between paragraph numbers and
    # body text on 70+ pages. strip_boilerplate only handles leading lines.
    kept = []
    for line in lines:
        if any(p.match(line) for p in R.HEADER_PATTERNS):
            notes["repeated_header"] += 1
            continue
        kept.append(line)
    lines = kept

    # a chapter banner only counts at the very top of the page, and never more
    # than 3 lines: a page that is entirely upper-case is not a banner run
    while (lines and notes["banner"] < 3
           and len(lines[0]) <= BANNER_MAX_CHARS and lines[0].isupper()):
        lines.pop(0)
        notes["banner"] += 1

    return lines, notes


def segment(lines, chapter):
    """Split one page's lines into (start, end, type) spans. Never crosses pages.

    - Every numbered paragraph starts a span.
    - A short line immediately before a numbered paragraph is that paragraph's
      heading and moves into it.
    - Lines before the first numbered paragraph are a continuation span.
    - A page with no numbered paragraph is a single `prose_page` span.
    """
    if not lines:
        return []
    anchors = [i for i, l in enumerate(lines) if anchor_ref(l, chapter)]
    if not anchors:
        return [(0, len(lines), "prose_page")]

    spans = []
    prev = 0
    for k, a in enumerate(anchors):
        start = a
        if a - 1 >= prev and heading_like(lines[a - 1]):
            start = a - 1
        end = anchors[k + 1] if k + 1 < len(anchors) else len(lines)
        # the line before the next anchor may be that anchor's heading
        if k + 1 < len(anchors) and end - 1 > a and heading_like(lines[end - 1]):
            end -= 1
        if start > prev:
            spans.append((prev, start, "prose_continuation"))
        spans.append((start, end, "prose_paragraph"))
        prev = end
    if prev < len(lines):
        spans.append((prev, len(lines), "prose_continuation"))
    return spans


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def looks_like_heading(seg_text):
    """A numbered line that carries a title and no sentence.

    Measured: 287 short passages are of the form "6.1 Introduction" or
    "16.14 Impact from Electric and Magnetic Field". Citing one as evidence would
    answer a query with a title and no content. A real short paragraph ends in a
    full stop ("8.6.2.29 No flora species ... within this habitat."), a heading
    does not.
    """
    t = seg_text.strip()
    if not t or len(t) > HEADING_MAX_CHARS:
        return False
    lines = [x for x in t.split("\n") if x.strip()]
    # the passage must itself start with a numbered heading. Without this, table
    # cells that happen to precede a numbered line ("Reversibility Direct impact
    # (habitat loss) on") were called headings.
    if not PARA_START.match(lines[0]):
        return False
    # a heading line is a title, not the first line of a sentence. A paragraph
    # cut mid-sentence at a page break ("14.6.8 Based on the timeline of historic
    # operations alone, gas production at NTML (Table") otherwise qualifies.
    if len(lines[0].split()) > 12:
        return False
    if any(x.rstrip().endswith((".", ";", ":")) for x in lines):
        return False
    return True


def load_records():
    """Raw JSONL records, keyed by the triple that identifies one page.

    retrieve.Corpus keeps only the cleaned text and the source PDF basename, so
    the original `text` and `source_sha256` are read here. This is read-only.
    """
    import glob
    out = {}
    pattern = os.path.join(ROOT, "stage1", "data", "*.pages.jsonl")
    for path in sorted(glob.glob(pattern)):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                out[(r["report_id"], r["chapter"], r["pdf_page_index"])] = r
    return out


def build_page_passages(doc, rec):
    """All passages for one page record. Always returns at least one passage."""
    text = rec.get("text") or ""
    chapter = doc.get("chapter")
    lines, notes = strip_page_extras(text, chapter)
    body = "\n".join(lines)

    flags = []
    if len(body) < NEAR_BLANK_CHARS:
        flags.append("near_blank")
    if not doc.get("page_label") or doc.get("page_label_status") != "verified":
        flags.append("no_verified_folio")

    form = doc["text_form"]

    # Non-prose pages are kept whole and flagged. Splitting a table page into
    # cell fragments would be reconstruction, which this stage does not do.
    if form in ("table_fragmented", "list", "non_substantive") or not lines:
        ptype = {"table_fragmented": "table_fragmented",
                 "list": "list",
                 "non_substantive": "non_substantive"}.get(form, "blank")
        if form in ("table_fragmented", "list"):
            flags.append("fragmented")
        spans = [(0, len(lines), ptype)] if lines else []
    else:
        spans = segment(lines, chapter)

    if not spans:
        spans = [(0, 0, "blank")]

    out = []
    for ordinal, (s, e, ptype) in enumerate(spans):
        seg_lines = lines[s:e]
        seg_text = "\n".join(seg_lines)
        flat = " ".join(seg_lines)

        if ptype == "prose_paragraph" and looks_like_heading(seg_text):
            ptype = "heading"

        ref, ref_status = None, "not_detected"
        if ptype in ("prose_paragraph", "heading"):
            # The anchor may not be the first line: a heading prepended to its
            # paragraph pushes the numbered line to line 1. Take the first
            # literal reference anywhere in the passage — there can only be one,
            # because the span ends at the next anchor.
            ref_line = None
            for line in seg_lines:
                r = anchor_ref(line, chapter)
                if r:
                    ref, ref_line = r, line
                    break
            if ref and MULTI_REF.match(ref_line):
                ref_status = "ambiguous_multiple_refs"
            else:
                ref_status = "own" if ref else "not_detected"
        elif ptype == "table_fragmented":
            # A table page may open with a genuine paragraph anchor (e.g.
            # "2.6.5.1 A comparison...").  Assign the ref only when the anchor
            # line is not a TOC entry (dot leaders or trailing folio).
            ref_line = None
            for line in seg_lines:
                r = anchor_ref(line, chapter)
                if r and not looks_like_toc_line(line):
                    ref, ref_line = r, line
                    break
            if ref and MULTI_REF.match(ref_line):
                ref_status = "ambiguous_multiple_refs"
            else:
                ref_status = "own" if ref else "not_detected"
        elif ptype == "prose_continuation":
            # a section number may appear earlier on this same page
            prior = [anchor_ref(l, chapter) for l in lines[:s]]
            prior = [x for x in prior if x]
            if prior:
                ref, ref_status = prior[-1], "inherited_within_page"

        pflags = list(flags)
        if ptype == "heading":
            pflags.append("heading_only")
        elif len(flat) < MIN_PASSAGE_CHARS:
            pflags.append("low_context")
        if ptype == "prose_continuation" and seg_lines:
            pflags.append("page_start_continuation")

        out.append({
            "passage_id": f'{doc["report_id"]}|c{chapter}|p{doc["pdf_page_index"]}|s{ordinal}',
            "passage_ordinal": ordinal,
            "passage_type": ptype,
            "quality_flags": pflags,
            "text": seg_text,
            "char_len": len(flat),
            "line_count": len(seg_lines),
            "section_ref": ref,
            "section_ref_status": ref_status,
            "report_id": doc["report_id"],
            "report_title": doc["report_title"],
            "chapter": chapter,
            "chapter_title": doc["chapter_title"],
            "pdf_page_index": doc["pdf_page_index"],
            "page_label": doc.get("page_label"),
            "page_label_status": doc.get("page_label_status"),
            "page_label_verified": doc.get("page_label_status") == "verified",
            "line_start": s,
            "line_end": e,
            "source_pdf": doc["source_pdf"],
            "source_sha256": rec.get("source_sha256"),
            "page_text_sha256": _sha(text),
            "page_boilerplate_removed": notes,
            "doc_lang": doc.get("doc_lang") or "en",
            "doc_kind": doc.get("doc_kind") or "chapter",
        })
    return out


def build_all(corpus, records=None):
    records = records if records is not None else load_records()
    passages = []
    missing = []
    for doc in corpus.docs:
        key = (doc["report_id"], doc["chapter"], doc["pdf_page_index"])
        rec = records.get(key)
        if rec is None:
            missing.append(key)
            continue
        passages.extend(build_page_passages(doc, rec))
    if missing:
        raise RuntimeError(f"{len(missing)} pages had no source record, "
                           f"first: {missing[0]}")
    return passages


def passage_citation(p):
    """One-line citation. Missing folio is stated, never guessed."""
    page = f"p.{p['page_label']}" if p["page_label"] else "no printed folio"
    if p["section_ref"]:
        ref = f"§{p['section_ref']}"
        if p["section_ref_status"] == "ambiguous_multiple_refs":
            ref += " (ambiguous)"
    else:
        ref = "§not detected"
    # The executive summary is not a chapter. It keeps chapter 0 internally so
    # the numeric citation token stays valid, but it is named for what it is.
    if p.get("doc_kind") == "executive_summary":
        head = f"{p['report_id']} · Executive Summary (Chinese original)"
    else:
        head = (f"{p['report_id']} · Ch.{p['chapter']} {p['chapter_title']}")
    return (f"[{head} · {ref} · "
            f"{page} · PDF idx {p['pdf_page_index']} "
            f"(viewer p.{p['pdf_page_index'] + 1}) · {p['page_label_status']} · "
            f"passage s{p['passage_ordinal']} {p['passage_type']}]")


def passage_excerpt(p, terms, width=300):
    """Window around the first matching term, so a long passage is judged fairly.

    The page-level retriever already centres its excerpt on the match. Taking the
    passage's first 300 characters instead would compare two different things and
    make long passages look worse than they are.
    """
    return R.excerpt({"clean_text": p["text"]}, terms, width=width)


class PassageIndex:
    """BM25 over passages. Same maths as the page index, different unit."""

    def __init__(self, corpus=None, records=None):
        self.corpus = corpus or R.Corpus()
        self.passages = build_all(self.corpus, records=records)
        self.cjk = getattr(self.corpus, "cjk", False)
        self.tokens, self.tf, self.lengths = [], [], []
        self.df = Counter()
        for p in self.passages:
            toks = R.tokenize(p["text"], cjk=self.cjk)
            self.tokens.append(toks)
            self.tf.append(Counter(toks))
            self.lengths.append(len(toks))
            for t in set(toks):
                self.df[t] += 1
        self.N = len(self.passages)
        self.avgdl = sum(self.lengths) / self.N if self.N else 0

    def idf(self, term):
        df = self.df.get(term, 0)
        return math.log((self.N - df + 0.5) / (df + 0.5) + 1.0)

    def search(self, terms, k=5, report=None, k1=1.5, b=0.75):
        if not terms:
            return []
        scored = []
        for i, tf in enumerate(self.tf):
            if report and self.passages[i]["report_id"] != report:
                continue
            raw, matched = 0.0, []
            for term in terms:
                f = tf.get(term)
                if not f:
                    continue
                matched.append(term)
                denom = f + k1 * (1 - b + b * self.lengths[i] / self.avgdl)
                raw += self.idf(term) * (f * (k1 + 1)) / denom
            if raw <= 0:
                continue
            w = PASSAGE_WEIGHT.get(self.passages[i]["passage_type"], 1.0)
            scored.append((raw * w, raw, w, i, matched))
        scored.sort(key=lambda x: -x[0])
        return scored[:k]

    def context(self, p):
        """Neighbouring pages, kept SEPARATE from the passage text.

        Each side carries its own page provenance. Nothing is joined.
        """
        out = {}
        for side, delta in (("prev", -1), ("next", 1)):
            idx = p["pdf_page_index"] + delta
            match = [d for d in self.corpus.docs
                     if d["report_id"] == p["report_id"]
                     and d["chapter"] == p["chapter"]
                     and d["pdf_page_index"] == idx]
            if match:
                d = match[0]
                # Corpus.docs stores the cleaned text under `clean_text`
                text = d.get("clean_text") or ""
                out[side] = {
                    "pdf_page_index": d["pdf_page_index"],
                    "page_label": d.get("page_label"),
                    "page_label_status": d.get("page_label_status"),
                    "text": " ".join(text.split())[:400],
                    "source_pdf": d["source_pdf"],
                }
            else:
                out[side] = None
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default=None)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--report", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--expand", action="store_true",
                    help="attach previous/next page context, kept separate")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    idx = PassageIndex()

    if args.stats or not args.query:
        types = Counter(p["passage_type"] for p in idx.passages)
        flags = Counter(f for p in idx.passages for f in p["quality_flags"])
        lens = sorted(p["char_len"] for p in idx.passages)
        print(f'pages: {idx.corpus.N}   passages: {idx.N}   '
              f'passages/page: {idx.N / idx.corpus.N:.2f}')
        for t, n in types.most_common():
            print(f'  {t:<22} {n:>5}')
        print('quality flags:')
        for f, n in flags.most_common():
            print(f'  {f:<24} {n:>5}')
        print(f'passage chars: min {lens[0]}  p10 {lens[len(lens)//10]}  '
              f'median {lens[len(lens)//2]}  p90 {lens[9*len(lens)//10]}  '
              f'max {lens[-1]}')
        return 0

    # The gate is applied exactly as in the page-level retriever: same function,
    # same defaults. Nothing here blocks a partial match.
    gate = idx.corpus.gate(args.query)
    if gate["status"] == "empty_query":
        print(gate["message"], file=sys.stderr)
        return 1
    if gate["blocked"]:
        print(f'gate: {gate["status"]} — BLOCKED', file=sys.stderr)
        print(f'  {gate["message"]}', file=sys.stderr)
        return 2

    hits = idx.search(gate["search_terms"], k=args.k, report=args.report)
    if not hits:
        print("no passage matched any query term", file=sys.stderr)
        return 1

    results = []
    for rank, (weighted, raw, w, i, matched) in enumerate(hits, 1):
        p = idx.passages[i]
        row = {
            "rank": rank,
            "score": round(weighted, 4),
            "score_unweighted": round(raw, 4),
            "form_weight": w,
            "matched_terms": matched,
            "query_terms_total": len(gate["search_terms"]),
            "passage_id": p["passage_id"],
            "passage_type": p["passage_type"],
            "quality_flags": p["quality_flags"],
            "section_ref": p["section_ref"],
            "section_ref_status": p["section_ref_status"],
            "page_label": p["page_label"],
            "page_label_status": p["page_label_status"],
            "pdf_page_index": p["pdf_page_index"],
            "viewer_page": p["pdf_page_index"] + 1,
            "citation": passage_citation(p),
            "text": p["text"],
        }
        if args.expand:
            row["context"] = idx.context(p)
        results.append(row)

    if args.json:
        print(json.dumps({"query": args.query, "gate": gate,
                          "level": "passage", "results": results},
                         indent=2, ensure_ascii=False))
        return 0

    print(f'query: "{args.query}"   tokens: {gate["search_terms"]}')
    print(f'corpus: {idx.N} passages from {idx.corpus.N} pages   shown: {len(results)}')
    print(f'gate: {gate["status"]} — {gate["message"]}')
    if gate["status"] == "partial_oov":
        listed = ", ".join(f'"{t}"' for t in gate["oov_terms"])
        print(f'gate: WARNING — the results below do not address {listed}')
    for r in results:
        print()
        print(f'{r["rank"]}. score {r["score"]} (bm25 {r["score_unweighted"]} × '
              f'{r["form_weight"]} {r["passage_type"]})  '
              f'matched {len(r["matched_terms"])}/{r["query_terms_total"]}: '
              f'{r["matched_terms"]}')
        print(f'   {r["citation"]}')
        if r["quality_flags"]:
            print(f'   flags: {", ".join(r["quality_flags"])}')
        print(f'   {passage_excerpt(idx.passages[hits[rank - 1][3]], gate["search_terms"])}')
        if args.expand and r.get("context"):
            c = r["context"]
            if c.get("prev"):
                print(f'   prev page p.{c["prev"]["page_label"]} '
                      f'(PDF idx {c["prev"]["pdf_page_index"]}): '
                      f'{c["prev"]["text"][:120]}…')
            if c.get("next"):
                print(f'   next page p.{c["next"]["page_label"]} '
                      f'(PDF idx {c["next"]["pdf_page_index"]}): '
                      f'{c["next"]["text"][:120]}…')
    return 0


if __name__ == "__main__":
    sys.exit(main())
