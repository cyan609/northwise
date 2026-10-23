#!/usr/bin/env python3
"""Stage 1: minimal lexical retrieval over the extracted EIA pages.

This is a RETRIEVAL prototype. It does not generate answers, call a model, or
judge relevance. It returns ranked passages with the fields needed to build a
citation, so a human can check every hit against the original PDF.

No packages, no embeddings, no vector database. Standard library only.

Method
------
1. Read every `stage1/data/*.pages.jsonl` record (read-only; never rewritten).
2. Build a *search copy* of the text with the running header and the page footer
   removed. The stored `text` field is untouched.
3. Classify the page's text form and down-weight non-prose forms.
4. Score with Okapi BM25 over the cleaned tokens.
5. Return the top-k pages with report, chapter, section ref, folio, PDF index and
   an excerpt.

Out-of-vocabulary gate
----------------------
Before ranking, every content term of the query is checked against the corpus
document frequency. A term with df=0 occurs on no page, so no ranking can be
meaningful for it.

- every content term absent  -> `all_oov`, blocked (exit 2). Definitive: nothing
  in the query occurs anywhere in 1,293 pages.
- some absent, some present  -> `partial_oov`, results returned with a warning
  that names the absent terms. NOT blocked by default, because document
  frequency cannot tell whether the absent term is the query's subject or
  incidental wording (see stage1/RARE_TERM_GATE.md §6).
- `--strict-oov` also blocks `partial_oov`. Measured to over-block on ordinary
  phrasing; opt-in only.

The gate decides nothing about answers. It only reports what the corpus does and
does not contain.

Why page-level: a page is the smallest unit that can always be cited exactly, and
the extracted text is already one record per page. Section-level chunking is a
later refinement, not a prerequisite.

Usage
-----
    python3 stage1/retrieve.py "black-faced spoonbill" --k 5
    python3 stage1/retrieve.py "noise barrier" --report AEIAR-271-2025
    python3 stage1/retrieve.py "long viewing distance" --json
"""
import argparse
import glob
import json
import math
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "stage1", "data")
REGISTRY = os.path.join(ROOT, "stage0", "reports.json")

# ---------------------------------------------------------------- boilerplate
# The running header is identical on 100% of San Tin pages and near-identical on
# Ngau Tam Mei pages; the footer carries the printed folio and the month-year.
# Left in, they match almost any query containing "environmental impact
# assessment" and would swamp the real content. They are removed from the SEARCH
# COPY only.
HEADER_PATTERNS = [
    re.compile(r"^Agreement No\. CE \d+/\d+ \((?:HY|CE)\)$"),
    re.compile(r"^Northern Metropolis Highway$"),
    re.compile(r"^[–\-] Investigation$"),
    re.compile(r"^Development at Ngau Tam Mei Area$"),
    re.compile(r"^Environmental Impact Assessment(?: Report)? [–\-] San Tin Section$"),
    re.compile(r"^Environmental Impact Assessment Report$"),
    re.compile(r"^Environmental Impact Assessment$"),
    # --- Traditional Chinese executive summaries (Stage 1b) ---
    # These can never match an English page, so adding them cannot change any
    # English ranking. They are listed here, next to the English rules they
    # mirror, because both sets describe the same running header.
    re.compile(r"^合約編號\.?\s*CE\s*\d+/\d+\s*\([A-Z]{2}\)$"),
    re.compile(r"^北都公路$"),
    re.compile(r"^[–\-]\s*勘查研究$"),
    re.compile(r"^北都公路\s*[–\-]\s*新田段\s*環境影響評估研究行政摘要$"),
    re.compile(r"^牛潭尾地區發展$"),
    re.compile(r"^行政摘要$"),
]

MONTHS = (r"(?:January|February|March|April|May|June|July|August|September|"
          r"October|November|December)")
# footer: "<folio> <Month> <Year>" as the last line
FOOTER = re.compile(
    r"^(?:\d{1,2}-\d{1,4}(?:-[0-9]{1,4}|-[ivxlcdm]+)?"
    r"|\d{1,2}-[ivxlcdm]{1,7}"
    r"|\d{1,4}"
    r"|[ivxlcdm]{1,7})"
    r"\s+" + MONTHS + r"\s+20\d\d$", re.IGNORECASE)

# The same footer in Chinese: "<folio> <year> 年 <month> 月", where the year and
# month may be Arabic or Chinese numerals.
#   "4 2026 年 3 月"    (San Tin ES)
#   "58 二零二五年八月"  (Ngau Tam Mei ES)
FOOTER_ZH = re.compile(
    r"^(?:\d{1,4}|[ivxlcdm]{1,7})"
    r"\s+(?:\d{4}|[〇零一二三四五六七八九]{4})\s*年\s*"
    r"(?:\d{1,2}|[一二三四五六七八九十]{1,3})\s*月$", re.IGNORECASE)

# A page that is a cover sheet or legal disclaimer. Kept searchable, but weighted
# far down: it is not evidence about environmental impacts.
NON_SUBSTANTIVE = re.compile(
    r"Disclaimer:|AAJV|forward-looking statements|免責聲明", re.I)

# Han characters. Used to (a) keep the English stopword heuristic away from
# Chinese text and (b) build bigrams for the Chinese index. English pages
# contain almost no Han characters, so this changes nothing for them.
CJK_RUN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")

# ---------------------------------------------------------------- text form
# Thresholds come from stage1/TEXT_QUALITY_AUDIT.md, which measured 132 of 1293
# pages at mean line length < 20 characters (table-cell fragmentation).
FRAGMENTED_MEAN_LINE = 20.0
LIST_CAPTION_SHARE = 0.40
LIST_DOTLEADER_SHARE = 0.30
# A second, independent signal: prose is built from function words, table cells
# are not. Measured on the audit sample: prose pages 32-46% stopwords, table
# pages 12-31%. 0.25 is deliberately conservative: it catches most tables and
# leaves a margin under the lowest prose page. It does NOT catch every table -
# a page whose cells contain long phrases (e.g. eia_ch04_out p.4-45, 31%
# stopwords) is still labelled prose. That is a known miss, not a silent one.
FRAGMENTED_STOPWORD_RATIO = 0.25
FRAGMENTED_MIN_LINES = 12

# Down-weighting for non-prose forms. A table page stays searchable: its terms
# are real, but it must not outrank narrative prose for a narrative question.
FORM_WEIGHT = {
    "prose": 1.00,
    "table_fragmented": 0.60,
    "list": 0.50,
    "non_substantive": 0.15,
}

STOPWORDS = set("""
a an and are as at be been being but by for from had has have if in into is it
its of on or that the their there these they this those to was were what when
where which who will with would should could may might must not no nor than then
than too very can also such any all both each more most other some only own same
so up out over under about after before between during through during
""".split())

# Used by the OOV gate only, never by BM25. The BM25 stopword list above is left
# exactly as it was so that the previously recorded rankings stay reproducible.
# These are function words that a resident's question contains but that carry no
# topic: without them "will my flat shake" reports `my` as an absent content term.
FUNCTION_WORDS = STOPWORDS | set("""
i me my myself we our ours us you your yours he him his she her hers it its
they them their theirs am is are was were be been being do does did doing done
have has had having will would shall should can could may might must
what which who whom whose when where why how whether
if then than because while although though unless until since
this that these those here there now just also very too quite rather
please tell show explain give find get want need know about regarding
""".split())


def fold_candidates(term):
    """Deterministic English inflection candidates, most conservative first.

    Purpose: stop a plural or participle from being reported as out-of-vocabulary
    when its base form is in the corpus. `spoonbills` (df=0) must not be treated
    as absent when `spoonbill` (df=11) is present.

    This handles inflection only. It does NOT handle derivation: `noisy` will not
    find `noise`, `mitigate` will not find `mitigation`. Both are measured and
    documented in stage1/RARE_TERM_GATE.md §6.
    """
    out = []
    if len(term) > 4 and term.endswith("ies"):
        out.append(term[:-3] + "y")
    if len(term) > 4 and term.endswith("es"):
        out.append(term[:-2])
    if len(term) > 3 and term.endswith("s") and not term.endswith("ss"):
        out.append(term[:-1])
    if len(term) > 5 and term.endswith("ing"):
        out += [term[:-3], term[:-3] + "e"]
    if len(term) > 4 and term.endswith("ed"):
        out += [term[:-2], term[:-1]]
    return out


def strip_boilerplate(text):
    """Return (clean_text, n_header_lines_removed, footer_removed)."""
    lines = text.split("\n")
    # leading header
    i = 0
    while i < len(lines) and i < 8:
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if any(p.match(s) for p in HEADER_PATTERNS):
            i += 1
            continue
        break
    header_removed = i

    body = lines[i:]
    # trailing footer
    footer_removed = False
    for j in range(len(body) - 1, max(len(body) - 5, -1), -1):
        s = body[j].strip()
        if not s:
            continue
        if FOOTER.match(s) or FOOTER_ZH.match(s):
            body = body[:j] + body[j + 1:]
            footer_removed = True
        break

    return "\n".join(body).strip(), header_removed, footer_removed


def classify_form(clean, page_label):
    """prose | table_fragmented | list | non_substantive. Evidence-based only."""
    if not clean.strip():
        return "non_substantive"
    if NON_SUBSTANTIVE.search(clean):
        return "non_substantive"

    lines = [x.strip() for x in clean.split("\n") if x.strip()]
    if not lines:
        return "non_substantive"

    caption = sum(1 for x in lines
                  if re.match(r"^(?:Figure|Table)\s+\d", x)) / len(lines)
    dotleader = sum(1 for x in lines if re.search(r"\.{4,}", x)) / len(lines)
    if caption >= LIST_CAPTION_SHARE or dotleader >= LIST_DOTLEADER_SHARE:
        return "list"

    # front matter carries roman folios (i, ii, iii, 15-i)
    if page_label and not re.search(r"\d$", page_label):
        return "list"

    mean_line = sum(len(x) for x in lines) / len(lines)
    if len(lines) >= 20 and mean_line < FRAGMENTED_MEAN_LINE:
        return "table_fragmented"

    words = re.findall(r"[a-z]+", clean.lower())
    cjk_chars = sum(len(m) for m in CJK_RUN.findall(clean))
    # The stopword ratio measures ENGLISH prose. Applied to Chinese text it
    # reads as "0% stopwords" on every page, because Chinese has no words in
    # this sense — measured on the two Chinese executive summaries, that
    # mislabelled 91 of 113 pages as fragmented tables and cut their weight to
    # 0.6. Only apply it when the page is mostly Latin script.
    if words and (cjk_chars / max(len(clean), 1)) < 0.30:
        stop_ratio = sum(1 for w in words if w in STOPWORDS) / len(words)
        if len(lines) >= FRAGMENTED_MIN_LINES and stop_ratio < FRAGMENTED_STOPWORD_RATIO:
            return "table_fragmented"

    return "prose"


SECTION_RE = re.compile(r"^(\d{1,2}\.\d{1,2}(?:\.\d{1,2}){0,2})\s+\S")


def extract_section(clean, form, chapter):
    """First numbered section reference that starts a line. Never invented.

    A section reference must belong to the chapter it sits in: chapter 9's
    sections are 9.x. Without that check a measurement such as "1.88 ha" at the
    start of a line was accepted as section 1.88 on a chapter 9 page.
    """
    if form == "list":
        return None, "excluded_list_page"
    for line in clean.split("\n"):
        m = SECTION_RE.match(line.strip())
        if not m:
            continue
        ref = m.group(1)
        if isinstance(chapter, int) and not ref.startswith(f"{chapter}."):
            continue
        return ref, "detected"
    return None, "not_detected"


# Bigrams that carry no topic. Chinese has no spaces, so a bigram can straddle a
# word boundary ("的影", "響會"); these are the ones that showed up in every test
# query and matched nearly every page. Kept deliberately short: a bigram is only
# dropped when it is functional on its own.
ZH_STOP_BIGRAMS = set("""
的影 響會 是否 會否 有沒有 有冇 可否 怎樣 如何 哪些 甚麼 什麼 這個 那個 我們
你們 他們 以及 但是 因為 所以 如果 可以 需要 有關 對於 關於 有甚麼 有咩
會唔 唔會 會不 不會 係唔 係咪 咁樣 點樣 幾多 邊度 喺邊 請問 想問 我想 想知
""".split())


def tokenize(text, cjk=False):
    """English word tokens. With `cjk=True`, also Chinese character bigrams.

    The default (`cjk=False`) is byte-for-byte the tokenizer the English index
    and every recorded ranking were built with. Chinese support is opt-in per
    corpus, so adding the Chinese executive summaries cannot shift an English
    document's length, term frequencies, or df.

    Why bigrams: Chinese is not space-delimited and there is no segmenter in
    this project (standard library only). A character bigram is the smallest
    unit that still carries meaning — "噪音" (noise), "生態" (ecology) — and
    avoids the noise of single characters like 的 / 會.
    """
    toks = [t for t in re.findall(r"[a-z0-9]+", text.lower())
            if t not in STOPWORDS and len(t) > 1]
    if cjk:
        for run in CJK_RUN.findall(text):
            if len(run) == 1:
                toks.append(run)
                continue
            for i in range(len(run) - 1):
                bg = run[i:i + 2]
                if bg not in ZH_STOP_BIGRAMS:
                    toks.append(bg)
    return toks


def zh_query_terms(text):
    """Search terms for a Traditional Chinese question.

    Same bigram scheme as the Chinese index, but WITHOUT the English stopword
    filter (it would drop "in", "for" etc. from a mixed query, which is fine,
    yet Chinese bigrams never appear in that list anyway).

    ASCII words in a mixed question are kept, so "PM2.5 對健康有咩影響" searches
    both `pm2` / `5` and the Chinese bigrams.
    """
    return tokenize(text, cjk=True)


def load_all_records():
    """Every page record under stage1/data, in stable (sorted-path) order.

    Read once and shared between the English and Chinese corpora. Both indexes
    need the same pages, and re-reading ~7,000 records per corpus doubles
    start-up time for no benefit.
    """
    out = []
    for path in sorted(glob.glob(os.path.join(DATA, "*.pages.jsonl"))):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    return out


class Corpus:
    def __init__(self, lang=None, records=None, cjk=None):
        """BM25 index over page records.

        lang     None = every record (historical behaviour); "en" / "zh-Hant"
                 select by the record's `doc_lang` (absent means "en").
        records  pre-parsed records, to avoid reading stage1/data twice.
        cjk      whether to add Chinese bigrams. Defaults to True only for a
                 Chinese corpus, so the English index keeps the exact tokens it
                 was measured with.
        """
        with open(REGISTRY, encoding="utf-8") as fh:
            reg = json.load(fh)
        self.report_titles = {r["report_id"]: r.get("title_en") or r["report_id"]
                              for r in reg["reports"]}
        self.lang = lang
        self.cjk = (lang == "zh-Hant") if cjk is None else cjk
        self.docs = []
        self.tokens = []
        self.tf = []
        self.lengths = []
        self.df = Counter()

        for rec in (records if records is not None else load_all_records()):
            rec_lang = rec.get("doc_lang") or "en"
            if lang is not None and rec_lang != lang:
                continue
            clean, hdr, ftr = strip_boilerplate(rec.get("text") or "")
            form = classify_form(clean, rec.get("page_label"))
            section, section_status = extract_section(clean, form,
                                                      rec.get("chapter"))
            toks = tokenize(clean, cjk=self.cjk)
            doc = {
                "report_id": rec["report_id"],
                "report_title": self.report_titles.get(rec["report_id"], ""),
                "chapter": rec.get("chapter"),
                "chapter_title": rec.get("chapter_title"),
                "pdf_page_index": rec["pdf_page_index"],
                "page_label": rec.get("page_label"),
                "page_label_status": rec.get("page_label_status"),
                "source_pdf": os.path.basename(rec.get("source_pdf", "")),
                "text_form": form,
                "section_ref": section,
                "section_ref_status": section_status,
                "clean_text": clean,
                "chars_clean": len(clean),
                "boilerplate_lines_removed": hdr,
                "footer_removed": ftr,
                "doc_lang": rec_lang,
                "doc_kind": rec.get("doc_kind") or "chapter",
            }
            self.docs.append(doc)
            self.tokens.append(toks)
            self.tf.append(Counter(toks))
            self.lengths.append(len(toks))
            for t in set(toks):
                self.df[t] += 1

        self.N = len(self.docs)
        self.avgdl = sum(self.lengths) / self.N if self.N else 0

    def idf(self, term):
        df = self.df.get(term, 0)
        return math.log((self.N - df + 0.5) / (df + 0.5) + 1.0)

    # ------------------------------------------------------------ OOV gate
    def resolve_query(self, query):
        """Split query terms into present / out-of-vocabulary.

        Only document frequency is consulted. No threshold, no model, no
        scoring: a term is present if it occurs on at least one page, either
        literally or through an inflection fold.

        A folded term is substituted in the search terms, so the gate's verdict
        and the ranking cannot disagree: if the gate says `spoonbills` is
        present because `spoonbill` is, then `spoonbill` is what gets ranked.
        """
        raw = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 1]
        function_dropped = [t for t in raw if t in FUNCTION_WORDS]
        content = [t for t in raw if t not in FUNCTION_WORDS]

        search_terms, present, oov, subs = [], [], [], {}
        for t in content:
            if self.df.get(t, 0) > 0:
                search_terms.append(t)
                present.append(t)
                continue
            folded = next((c for c in fold_candidates(t)
                           if self.df.get(c, 0) > 0), None)
            if folded:
                search_terms.append(folded)
                present.append(t)      # report the term the user typed
                subs[t] = folded
            else:
                search_terms.append(t)
                oov.append(t)

        return {
            "query_terms": content,
            "search_terms": search_terms,
            "present_terms": present,
            "oov_terms": oov,
            "substitutions": subs,
            "function_words_dropped": function_dropped,
        }

    def gate(self, query, strict=False):
        """Classify the query. Blocking is decided by presence, not by score."""
        r = self.resolve_query(query)
        content, oov = r["query_terms"], r["oov_terms"]

        if not content:
            status = "empty_query"
            msg = "query has no content terms after removing function words"
        elif not r["present_terms"]:
            status = "all_oov"
            listed = ", ".join(f'"{t}"' for t in oov)
            msg = (f'no page in the corpus contains {listed} '
                   f'(0 of {self.N} pages)')
        elif oov:
            status = "partial_oov"
            listed = ", ".join(f'"{t}"' for t in oov)
            verb = "occurs" if len(oov) == 1 else "occur"
            msg = (f'{listed} {verb} on 0 of {self.N} pages; '
                   f'the other terms do occur')
        else:
            status = "ok"
            msg = f'all {len(content)} content terms occur in the corpus'

        r["status"] = status
        r["message"] = msg
        r["strict"] = strict
        r["blocked"] = (status == "all_oov"
                        or (strict and status == "partial_oov"))
        return r

    def search(self, terms, k=5, report=None, k1=1.5, b=0.75):
        q = terms
        if not q:
            return [], []
        scores = []
        for i, tf in enumerate(self.tf):
            if report and self.docs[i]["report_id"] != report:
                continue
            raw = 0.0
            matched = []
            for term in q:
                f = tf.get(term)
                if not f:
                    continue
                matched.append(term)
                dl = self.lengths[i]
                denom = f + k1 * (1 - b + b * dl / self.avgdl)
                raw += self.idf(term) * (f * (k1 + 1)) / denom
            if raw <= 0:
                continue
            weight = FORM_WEIGHT.get(self.docs[i]["text_form"], 1.0)
            scores.append((raw * weight, raw, weight, i, matched))
        scores.sort(key=lambda x: -x[0])
        return scores[:k], q


def excerpt(doc, query_tokens, width=260):
    """A window around the first query-term hit, from the CLEANED text."""
    text = re.sub(r"\s+", " ", doc["clean_text"])
    low = text.lower()
    pos = -1
    for t in query_tokens:
        p = low.find(t)
        if p != -1 and (pos == -1 or p < pos):
            pos = p
    if pos == -1:
        return text[:width]
    start = max(0, pos - width // 3)
    return ("…" if start else "") + text[start:start + width] + "…"


def format_citation(d):
    """One-line citation. A missing folio is stated, never guessed.

    `pdf_page_index` is 0-based (PDFKit order) and is printed as stored; the
    1-based viewer page is given too, because a PDF viewer's `#page=` anchor is
    1-based and the two numbers differ by one.
    """
    page = (f"p.{d['page_label']}" if d["page_label"]
            else "no printed folio")
    return (f"[{d['report_id']} · Ch.{d['chapter']} {d['chapter_title']} · "
            f"{('§' + d['section_ref']) if d['section_ref'] else '§not detected'} · "
            f"{page} · PDF idx {d['pdf_page_index']} "
            f"(viewer p.{d['pdf_page_index'] + 1}) · "
            f"{d['page_label_status']}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--report", default=None,
                    help="scope to one report_id, e.g. AEIAR-276-2026")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict-oov", action="store_true",
                    help="also block queries with only SOME absent terms "
                         "(measured to over-block ordinary phrasing)")
    args = ap.parse_args()

    corpus = Corpus()
    gate = corpus.gate(args.query, strict=args.strict_oov)
    q = gate["search_terms"]

    def emit_blocked():
        if args.json:
            print(json.dumps({"query": args.query,
                              "tokens": q,
                              "gate": gate,
                              "results": []},
                             indent=2, ensure_ascii=False))
        else:
            print(f'query: "{args.query}"')
            print(f'gate: {gate["status"]} — BLOCKED')
            print(f'  {gate["message"]}')
            if gate["status"] == "all_oov":
                print('  Nothing is returned: ranking absent terms would produce '
                      'citations to unrelated pages.')
            else:
                print('  Blocked by --strict-oov. Re-run without it to see '
                      'results for the remaining terms.')
        return 2

    if gate["status"] == "empty_query":
        print(gate["message"], file=sys.stderr)
        return 1
    if gate["blocked"]:
        return emit_blocked()

    hits, q = corpus.search(q, k=args.k, report=args.report)
    if not hits:
        print("no page matched any query term", file=sys.stderr)
        return 1

    results = []
    for rank, (weighted, raw, weight, i, matched) in enumerate(hits, 1):
        d = corpus.docs[i]
        results.append({
            "rank": rank,
            "score": round(weighted, 4),
            "score_unweighted": round(raw, 4),
            "form_weight": weight,
            "matched_terms": matched,
            "query_terms_total": len(q),
            "report_id": d["report_id"],
            "report_title": d["report_title"],
            "chapter": d["chapter"],
            "chapter_title": d["chapter_title"],
            "section_ref": d["section_ref"],
            "section_ref_status": d["section_ref_status"],
            "page_label": d["page_label"],
            "page_label_status": d["page_label_status"],
            "pdf_page_index": d["pdf_page_index"],
            "viewer_page": d["pdf_page_index"] + 1,
            "text_form": d["text_form"],
            "source_pdf": d["source_pdf"],
            "citation": format_citation(d),
            "excerpt": excerpt(d, q),
        })

    if args.json:
        print(json.dumps({"query": args.query, "tokens": q,
                          "gate": gate, "results": results},
                         indent=2, ensure_ascii=False))
        return 0

    print(f'query: "{args.query}"   tokens: {q}')
    print(f'corpus: {corpus.N} pages   shown: {len(results)}')
    print(f'gate: {gate["status"]} — {gate["message"]}')
    if gate["status"] == "partial_oov":
        listed = ", ".join(f'"{t}"' for t in gate["oov_terms"])
        print(f'gate: WARNING — the results below do not address {listed}')
    if gate["substitutions"]:
        subs = ", ".join(f'{k}→{v}' for k, v in gate["substitutions"].items())
        print(f'gate: inflected terms folded for matching: {subs}')
    for r in results:
        print()
        print(f'{r["rank"]}. score {r["score"]} '
              f'(bm25 {r["score_unweighted"]} × {r["form_weight"]} '
              f'{r["text_form"]})  '
              f'matched {len(r["matched_terms"])}/{r["query_terms_total"]}: '
              f'{r["matched_terms"]}')
        print(f'   {r["citation"]}')
        print(f'   {r["excerpt"]}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
