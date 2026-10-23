#!/usr/bin/env python3
"""NORTHWISE MVP backend — evidence-first Q&A over EIA reports.

Standard library only. No packages, no LLM, no embeddings.
Serves a minimal HTML frontend and a POST /ask endpoint that returns
up to 3 evidence cards grounded in official report passages.

Run:
    python3 app.py              # starts on http://localhost:8080
    python3 app.py --port 9000  # custom port

Test:
    python3 test_app.py
    curl -X POST http://localhost:8080/ask \
         -H "Content-Type: application/json" \
         -d '{"question":"noise barrier"}'
"""
import argparse
import http.server
import json
import mimetypes
import os
import re
import socket
import socketserver
import sys
import time
import unittest
import urllib.error
import urllib.request

# stage1/ is a sibling directory; add it to the path.
STAGE1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stage1")
sys.path.insert(0, STAGE1)
import passages as P  # noqa: E402
import retrieve as R  # noqa: E402
import answerability as A  # noqa: E402

# Claim-level evaluator (optional — import may fail if file is missing)
try:
    import claim_evaluator as CE  # noqa: E402
    _CLAIM_EVAL_AVAILABLE = True
except ImportError:
    _CLAIM_EVAL_AVAILABLE = False

ROOT = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ load once

# Two indexes, deliberately separate.
#
#   CORPUS / IDX        English chapter text. `lang="en"` excludes the Chinese
#                       records, so this index keeps the exact token counts, df
#                       and avgdl that every recorded ranking was measured on.
#   CORPUS_ZH / IDX_ZH  the Traditional Chinese executive summaries only, built
#                       with CJK bigrams. Kept apart so a Chinese BM25 score is
#                       never compared with an English one, and so Chinese
#                       support cannot move an English result.
_ALL_RECORDS = R.load_all_records()
_RECORDS_BY_PAGE = {(r["report_id"], r.get("chapter"), r["pdf_page_index"]): r
                    for r in _ALL_RECORDS}
CORPUS = R.Corpus(lang="en", records=_ALL_RECORDS)
IDX = P.PassageIndex(CORPUS, records=_RECORDS_BY_PAGE)
CORPUS_ZH = R.Corpus(lang="zh-Hant", records=_ALL_RECORDS)
IDX_ZH = (P.PassageIndex(CORPUS_ZH, records=_RECORDS_BY_PAGE)
          if CORPUS_ZH.N else None)

with open(os.path.join(ROOT, "stage0", "reports.json"), "r", encoding="utf-8") as f:
    _REPORTS_DATA = json.load(f)

# Map (report_id, chapter_number) -> official EPD file_url
CHAPTER_URLS = {}
REPORTS_BY_ID = {}
for r in _REPORTS_DATA["reports"]:
    rid = r["report_id"]
    REPORTS_BY_ID[rid] = r
    CHAPTER_URLS[rid] = {}
    for ch in r.get("chapters", []):
        CHAPTER_URLS[rid][ch["number"]] = ch["file_url"]

# ------------------------------------------------------------------ Chinese topic mapping

# Explicit Traditional Chinese -> English term mapping for the six topic
# shortcuts.  This is NOT general Chinese NLP; only these exact phrases
# are recognised.  Longest match wins to avoid duplicate terms.
_TC_TOPIC_MAP = [
    # --- Water & hydrology ---
    ("水文評估", ["hydrological", "assessment"]),
    ("水文", ["hydrological"]),
    ("水質", ["water", "quality"]),
    ("排水", ["drainage"]),
    ("污水", ["sewage"]),
    ("雨水", ["stormwater"]),
    ("河流", ["river"]),
    ("渠道", ["channel"]),
    # --- Noise ---
    ("噪音屏障", ["noise", "barrier"]),
    ("噪音", ["noise"]),
    ("聲音", ["noise"]),
    # --- Ecology ---
    ("生態影響", ["ecology"]),
    ("生態", ["ecology"]),
    ("魚類", ["fish"]),
    ("生境", ["habitat"]),
    ("物種", ["species"]),
    ("植被", ["vegetation"]),
    ("濕地", ["wetland"]),
    ("林地", ["woodland"]),
    ("農地", ["agricultural", "land"]),
    ("復耕", ["rehabilitation"]),
    ("植樹", ["planting"]),
    ("園景", ["landscaping"]),
    ("綠化", ["landscaping"]),
    # --- Waste ---
    ("廢物管理", ["waste", "management"]),
    ("廢物", ["waste"]),
    # --- Cultural heritage ---
    ("文化遺產", ["cultural", "heritage"]),
    ("風水", ["feng", "shui"]),
    ("考古", ["archaeological"]),
    # --- Landscape / visual ---
    ("視覺影響", ["landscape"]),
    ("景觀", ["landscape"]),
    ("景觀影響", ["landscape"]),
    # --- Air quality ---
    ("空氣質素", ["air", "quality"]),
    ("空氣", ["air"]),
    ("空氣污染", ["air", "pollution"]),
    ("污染", ["pollution"]),
    ("粉塵", ["dust"]),
    ("臭氣", ["odour"]),
    # --- Traffic ---
    ("交通", ["traffic"]),
    ("運輸", ["transport"]),
    ("道路", ["road"]),
    ("車輛", ["vehicle"]),
    # --- Construction ---
    ("施工", ["construction"]),
    ("工地", ["construction", "site"]),
    ("建築", ["building"]),
    ("建造", ["construction"]),
    # --- Community / socio-economic ---
    ("村落", ["village", "settlement"]),
    ("居民", ["resident", "population"]),
    ("人口", ["population"]),
    ("社會", ["social"]),
    ("經濟", ["economic"]),
    ("健康", ["health"]),
    ("安全", ["safety"]),
    ("風險", ["risk"]),
    # --- EIA process ---
    ("環境影響", ["environmental", "impact"]),
    ("環評", ["environmental", "impact", "assessment"]),
    ("評估", ["assessment"]),
    ("報告", ["report"]),
    ("緩解措施", ["mitigation", "measures"]),
    ("補償", ["compensation"]),
    ("監測", ["monitoring"]),
    ("基線", ["baseline"]),
    ("累積", ["cumulative"]),
    ("殘餘", ["residual"]),
    ("替代方案", ["alternative"]),
    ("敏感度", ["sensitivity"]),
    ("敏感受體", ["sensitive", "receptor"]),
    # --- General EIA ---
    ("發展項目", ["development", "project"]),
]


# ------------------------------------------------------------------ Bilingual EIA glossary
# The full bilingual EIA terminology inventory lives in
# ``stage1/glossary_data.py`` (54 unique canonical terms as of 2026-10-18).
# This module provides the lookup function used by ``/ask`` to answer
# definition-style questions and to enrich synthesis when the user asks
# about a technical term.
from stage1.glossary_data import (
    get_glossary_entries,
    lookup_entry_by_alias,
    find_entry_in_text,
    total_entries as _glossary_total_entries,
)


# Regex patterns that suggest the user is asking for a definition.
# Extended to support common HK Cantonese question forms and to ignore
# punctuation that might follow the term.
_DEFINITION_PATTERNS = [
    re.compile(r"what(?:'s| is) (?:a |an |the )?(.+?)\??$", re.I),
    re.compile(r"^explain (.+?)\??$", re.I),
    re.compile(r"用簡單中文解釋(?:甚麼是)?(.+?)[？?]?$"),
    re.compile(r"甚麼[係是]?(.+?)[？?]?$"),
    re.compile(r"^告訴我(?:關於)?(.+?)$"),
    re.compile(r"^解釋(.+?)$"),  # bare "解釋X" (explain X)
    re.compile(r"^何謂(.+?)[？?]?$"),  # 何謂 = what is
    re.compile(r"^講解(.+?)$"),  # 講解 = describe
]


# Project-specific question triggers.  When ANY of these appear in the
# question we suppress the glossary result so the user gets report
# evidence first (the glossary is general knowledge, not project findings).
_PROJECT_TRIGGERS = [
    "this project", "the project", "that project", "the scheme", "this scheme",
    "the san tin", "san tin", "ngau tam mei", "牛潭尾",
    "the report", "this report", "the reports", "the chapter", "the page",
    "in the eia", "in the report", "what does the report say",
    "what do the reports say", "according to the report",
]


def _is_project_specific(question: str) -> bool:
    """True if the question is about a specific project's findings.

    Detects mentions of named projects, the word 'report', or page/chapter
    references.  When True, we skip generic glossary-only answers.
    """
    q = question.lower()
    return any(t in q for t in _PROJECT_TRIGGERS)


def _pick_display_alias(entry: dict, lang: str, fallback: str) -> str:
    """Choose the best display term from an entry's aliases.

    Picks an English alias for ``lang == 'en'`` and a Chinese alias for
    ``lang == 'zh-Hant'``.  Falls back to the canonical phrase or the
    original fallback term.
    """
    target_is_cjk = lang == "zh-Hant"
    for alias in entry["aliases"]:
        has_cjk = any("\u4e00" <= c <= "\u9fff" for c in alias)
        if target_is_cjk and has_cjk:
            return alias
        if not target_is_cjk and not has_cjk:
            return alias
    return fallback


def _format_glossary_entry(entry: dict, lang: str, matched_term: str) -> dict:
    """Convert an internal glossary entry into the API response shape.

    ``term`` and ``canonical_term`` are both the stable English canonical
    phrase derived from the entry key (backward-compatible with the
    earlier API).  ``display_term`` is the language-appropriate alias
    for user-facing presentation.  ``matched_alias`` records what the
    user actually wrote.
    """
    text = entry.get(lang) or entry.get("en", "")
    canonical = entry.get("key", "").replace("_", " ")
    display = _pick_display_alias(entry, lang, matched_term)
    return {
        "term": canonical,
        "canonical_term": canonical,
        "display_term": display,
        "matched_alias": matched_term,
        "key": entry.get("key", ""),
        "definition": text,
        "category": entry.get("category", ""),
        "source": "glossary",
        "source_name": entry.get("source_name", ""),
        "source_url": entry.get("source_url", ""),
        "source_section": entry.get("source_section", ""),
        "lang": lang,
        # Optional rich fields (omitted when not provided)
        **({k: entry[k] for k in (
            "why_it_matters_en", "why_it_matters_zh",
            "example_en", "example_zh",
            "interpreting_numbers_en", "interpreting_numbers_zh",
            "common_misunderstanding_en", "common_misunderstanding_zh",
        ) if entry.get(k)}),
    }


def _lookup_glossary(question: str, lang: str) -> dict | None:
    """Return a glossary entry if the question asks for a known term's definition.

    Lookup strategy:
        1. Pattern-based extraction: try each definition pattern, extract
           the term phrase, resolve via the alias index.
        2. Conservative fallback: ONLY for very short definition questions
           (≤8 words, ending with '?'), use alias-in-text matching.

    Refuses to return a generic glossary answer if the question is
    clearly project-specific — project evidence must come from
    reports, not from generic definitions.
    """
    if _is_project_specific(question):
        return None

    # Strategy 1: pattern-based extraction
    for pat in _DEFINITION_PATTERNS:
        m = pat.search(question)
        if not m:
            continue
        raw_term = m.group(1).strip().lower()
        # Strip leading articles and trailing punctuation
        raw_term = re.sub(r"^(a|an|the)\s+", "", raw_term).strip().rstrip("?？.,;:!。，；：、")
        entry = lookup_entry_by_alias(raw_term)
        if entry:
            return _format_glossary_entry(entry, lang, raw_term)

    # Strategy 2: short bare question fallback ONLY
    # (e.g. "wetland?" — short, ends with '?', clearly asking for definition)
    q = question.strip()
    if q.endswith("?") or q.endswith("？"):
        if len(q.split()) <= 8:
            entry = find_entry_in_text(question)
            if entry:
                matched = next(
                    (a for a in entry["aliases"] if a.lower() in question.lower()),
                    entry["key"].replace("_", " "),
                )
                return _format_glossary_entry(entry, lang, matched)

    return None


def _map_chinese_terms(text: str) -> list[str] | None:
    """Extract English search terms from known Chinese topic phrases.

    Returns a deduplicated list of English terms if any known Chinese
    phrases are found as substrings, or None if no known phrases match.
    """
    terms = []
    for cn, en in _TC_TOPIC_MAP:
        if cn in text:
            terms.extend(en)
    # deduplicate while preserving order
    seen = set()
    out = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out if out else None


# ------------------------------------------------------------------ i18n

_STRINGS = {
    "evidence_intro": {
        "en": (
            "Here are the most relevant passages from the official EIA reports. "
            "These excerpts are evidence, not a synthesized answer."
        ),
        "zh-Hant": (
            "以下是官方環評報告中最相關的段落。"
            "這些是原始證據，並非綜合答案。"
        ),
    },
    "refused_all_oov": {
        "en": "Sorry, I cannot answer this question",
        "zh-Hant": "抱歉，我無法回答此問題。",
    },
    "refused_chinese_unsupported": {
        "en": "Sorry, I cannot answer this question",
        "zh-Hant": "抱歉，我無法回答此問題。",
    },
    "refused_empty": {
        "en": "Please enter a question.",
        "zh-Hant": "請輸入問題。",
    },
    "refused_no_results": {
        "en": "Sorry, I cannot answer this question",
        "zh-Hant": "抱歉，我無法回答此問題。",
    },
    "refused_low_relevance": {
        "en": "Sorry, I cannot answer this question",
        "zh-Hant": "抱歉，我無法回答此問題。",
    },
    # The report may contain the words of the question without containing the
    # information it asks for. Same fallback text: the user needs one honest
    # answer, not a taxonomy of failure reasons.
    "refused_not_answerable": {
        "en": "Sorry, I cannot answer this question",
        "zh-Hant": "抱歉，我無法回答此問題。",
    },
    "disclaimer": {
        "en": "AI-generated excerpt. The official report prevails.",
        "zh-Hant": "AI 整理的摘要，請以官方報告為準。",
    },
    "page_verified": {
        "en": "verified",
        "zh-Hant": "已核實",
    },
    "page_absent": {
        "en": "no printed folio",
        "zh-Hant": "無印刷頁碼",
    },
    "page_unverified": {
        "en": "unverified",
        "zh-Hant": "未核實",
    },
}


def _t(key: str, lang: str) -> str:
    """Localized string lookup with English fallback."""
    s = _STRINGS.get(key, {})
    return s.get(lang, s.get("en", key))


def detect_lang(text: str) -> str:
    """Simple CJK detection -> zh-Hant, otherwise en."""
    if any("\u4e00" <= c <= "\u9fff" for c in text):
        return "zh-Hant"
    return "en"


# ------------------------------------------------------------------ core ask

MIN_SCORE = 1.0  # below this, top hit is treated as noise
MAX_EVIDENCE = 3

# Chinese-original retrieval gate. Both numbers were set by running real
# Traditional Chinese questions against the two executive summaries:
#   - score floor: below 2.5 the top hit was incidental (e.g. a land-use table
#     matched a question about tomorrow's weather because the page contains 天氣).
#   - coverage: the top hit must contain at least 2 distinct query bigrams, or
#     all of them for a 1-2 bigram query. A question about a species the summary
#     never mentions otherwise matched on a single character pair.
ZH_MIN_SCORE = 2.5
ZH_MIN_MATCHED = 2
# These bigrams describe almost any project question and cannot, by themselves,
# establish topic relevance. This closes the measured false-positive where
# "這個項目會不會影響房價" matched only 項目/會影/影響 in an EIA summary.
ZH_GENERIC_GATE_BIGRAMS = frozenset({"項目", "會影", "影響"})


def _zh_evidence_hits(question: str, report_id: str | None):
    """Search the ORIGINAL Chinese executive summaries.

    Returns (query_terms, hits). `hits` is empty when nothing clears the gate,
    in which case the caller falls back to the English corpus unchanged.

    This searches original Chinese documents only — it never translates an
    English passage and presents the translation as a Chinese source.
    """
    if IDX_ZH is None:
        return [], []
    terms = R.zh_query_terms(question)
    if not terms:
        return terms, []

    hits = IDX_ZH.search(terms, k=MAX_EVIDENCE * 2, report=report_id)
    # Contents pages and lists of tables/figures are navigation, not evidence.
    hits = [h for h in hits
            if IDX_ZH.passages[h[3]]["passage_type"] != "list"]
    if not hits:
        return terms, []

    top = hits[0]
    if top[0] < ZH_MIN_SCORE:
        return terms, []
    if len(top[4]) < min(ZH_MIN_MATCHED, len(terms)):
        return terms, []
    # Known EIA topic phrases are already controlled by _TC_TOPIC_MAP. For a
    # free-form phrase outside that map, require at least one matched bigram that
    # carries more information than the generic "project / will affect / impact"
    # frame; otherwise unrelated subjects such as property prices can slip in.
    if not _map_chinese_terms(question):
        topical_matches = [t for t in top[4] if t not in ZH_GENERIC_GATE_BIGRAMS]
        if not topical_matches:
            return terms, []
    return terms, hits[:MAX_EVIDENCE]


def _source_url(passage: dict) -> str | None:
    """Official EPD source URL for this passage, or None.

    A Chinese executive summary is its own PDF published alongside the report,
    so it links to `exec_summary_zh_url` rather than to a chapter file. Nothing
    is guessed: the URL comes from the report registry.
    """
    if (passage.get("doc_kind") or "chapter") == "executive_summary":
        report = REPORTS_BY_ID.get(passage["report_id"], {})
        return report.get("exec_summary_zh_url")
    return CHAPTER_URLS.get(passage["report_id"], {}).get(passage["chapter"])


# The card shows a short window so the page stays readable. The model needs the
# whole passage: on `aeiar-276-2026` Ch.0 p.24 the 300-character window ended
# mid-list of dust measures ("透過定期灑水來減少外露的工地表面和無鋪築的道路所產…"),
# and the model filled the gap with measures the report never proposed
# (防風屏, 封閉式搬運設備). The same page is 655 characters; the rest of it names
# the hoarding heights and watering regime that were being invented.
#
# Tables get a smaller budget than prose. A table row does not become more
# useful the more of it is pasted — it becomes a longer dump, and three of them
# pushed the Chinese prompt to 2050 tokens, where this model abandoned the
# format and answered in English. 500 characters reaches the mitigation column
# of that row without swallowing the whole table.
SYNTHESIS_EXCERPT_WIDTH = 2000
TABLE_SYNTHESIS_WIDTH = 500

_PROSE_TYPES = {"prose_page", "prose_paragraph", "prose_continuation"}
# Cells split across lines. A card may omit passage_type (hand-built fixtures),
# and an unknown type is treated as prose: only a known table is quoted short.
_TABLE_TYPES = {"table_fragmented", "table_row"}


def _make_card(p: dict, rank: int, search_terms: list[str],
               excerpt_width: int = 300) -> dict:
    """The one shape every evidence card has, whichever index it came from."""
    return {
        "rank": rank,
        "passage_id": p["passage_id"],
        "passage_type": p["passage_type"],
        "report_id": p["report_id"],
        "report_title": p["report_title"],
        "chapter": p["chapter"],
        "chapter_title": p["chapter_title"],
        "doc_kind": p.get("doc_kind") or "chapter",
        "excerpt_lang": p.get("doc_lang") or "en",
        "section_ref": p["section_ref"],
        "section_ref_status": p["section_ref_status"],
        "page_label": p["page_label"],
        "page_label_status": p["page_label_status"],
        "pdf_page_index": p["pdf_page_index"],
        "viewer_page": p["pdf_page_index"] + 1,
        "source_url": _source_url(p),
        "citation": P.passage_citation(p),
        "excerpt": P.passage_excerpt(p, search_terms, width=excerpt_width),
        # What the model reads. Never shown in the UI: the card above is the
        # reader-facing window, this is the evidence the summary may rely on.
        "synthesis_excerpt": P.passage_excerpt(
            p, search_terms,
            width=max(
                excerpt_width,
                SYNTHESIS_EXCERPT_WIDTH
                if p["passage_type"] in _PROSE_TYPES
                else TABLE_SYNTHESIS_WIDTH,
            ),
        ),
        "quality_flags": p["quality_flags"],
        "matched_terms": [],
        "query_terms_total": len(search_terms),
    }


def _citation_token(card: dict) -> str:
    """The citation the model is told to use for this card.

    A page with no printed folio cannot be cited by page number — writing
    `p.None` is how the model previously produced answers that failed
    validation and vanished. Chapter-only is the honest form for those pages.
    """
    pl = str(card.get("page_label") or "").strip()
    if pl and pl.lower() != "none":
        return f"[{card['report_id']}, Ch.{card['chapter']}, p.{pl}]"
    return f"[{card['report_id']}, Ch.{card['chapter']}]"


# ------------------------------------------------------------------ measure re-rank
# "What noise mitigation measures are proposed?" was answered from the residual
# impact conclusion — "with the implementation of the proposed mitigation
# measures" — which restates the question without naming a single measure. The
# passages that DO name them (low-noise surfacing, noise barriers, silencers)
# were ranked just below it. When the question asks for measures, prose that
# names one moves ahead of prose that only refers to them.
#
# This changes ORDER only: no card is added or dropped, so citation validation
# and the answerability coverage check see exactly the same evidence as before.

_MEASURE_INTENT = re.compile(
    r"\b(?:measures?|mitigat\w*|remed\w*|actions?|controls?|recommend\w*)\b", re.I)
_MEASURE_NOUN = re.compile(
    r"\b(?:noise barriers?|silencers?|enclosures?|enclosed|low[- ]noise|"
    r"acoustic|absorpt\w*|canop(?:y|ies)|resurfac\w*|perforated|louvres?|"
    r"water spray\w*|dust suppression|wheel wash\w*|hydroseed\w*|"
    r"transplant\w*|sheet pil\w*|quiet plant|screening)\b", re.I)


def _prefer_named_measures(evidence: list[dict], question: str) -> list[dict]:
    if len(evidence) < 2 or not _MEASURE_INTENT.search(question or ""):
        return evidence

    def names_one(card: dict) -> bool:
        # Prose only: a table row names plenty of measures but summarises badly.
        return (card.get("passage_type") == "prose_paragraph"
                and bool(_MEASURE_NOUN.search(card.get("excerpt") or "")))

    if not any(names_one(c) for c in evidence):
        return evidence
    return [c for c in evidence if names_one(c)] + [c for c in evidence
                                                    if not names_one(c)]


# ------------------------------------------------------------------ overview mode
# "Summarise this report" is not a keyword query. Measured before this change:
# retrieval answered it with three DIFFERENT reports' Chapter 1 introductions,
# because those pages share the words "report" and "findings". A report overview
# has to be assembled from the report's own summary chapters instead.

PRIMARY_REPORT_ID = "aeiar-276-2026"
OVERVIEW_LIMIT = 5
OVERVIEW_EXCERPT = 420

_OVERVIEW_EN = re.compile(
    r"\b(?:summari[sz]e|summary|overview|key findings|main findings|"
    r"main conclusions?|what (?:does|is) (?:the|this) (?:eia )?report "
    r"(?:say|cover|about|conclude))\b",
    re.I,
)
_OVERVIEW_ZH = re.compile(r"總結|概述|摘要|主要發現|重點|這份報告|該報告|報告的結論|整體而言")

_SUMMARY_CHAPTER = re.compile(r"CONCLUSION|SUMMARY OF ENVIRONMENTAL", re.I)

# Passages about the report itself, not about the environment. "Structure of
# this Report" (1.6.1.1) was being picked as an overview passage and pushed the
# model to describe the document's contents instead of its findings — the exact
# failure this task set out to remove.
_META_PASSAGE = re.compile(
    r"structure of this report|this report is (?:organi[sz]ed|structured)|"
    r"(?:is|are) organi[sz]ed as follows|table of contents|"
    r"this (?:chapter|section) (?:presents|introduces) the (?:background|structure)",
    re.I,
)


def _is_overview_question(question: str) -> bool:
    return bool(_OVERVIEW_EN.search(question) or _OVERVIEW_ZH.search(question))


def _prose_passages(items: list[dict], min_chars: int = 200) -> list[dict]:
    return [p for p in items
            if p.get("passage_type") == "prose_paragraph"
            and len(p.get("text") or "") >= min_chars
            and not _META_PASSAGE.search(p.get("text") or "")]


def _major_section(ref) -> int:
    """`4.9.2.1` -> 9, so a chapter's last major section can be found."""
    try:
        return int(str(ref).split(".")[1])
    except (IndexError, ValueError):
        return -1


def _overview_passages(report_id: str | None) -> list[dict]:
    """Representative passages from ONE report: its conclusion, its statement of
    environmental outcomes, what the project is, and why it exists."""
    rid = report_id or PRIMARY_REPORT_ID
    passages = [p for p in IDX.passages if p.get("report_id") == rid]
    if not passages:
        return []

    groups: dict = {}
    for p in passages:
        groups.setdefault(p.get("chapter"), []).append(p)
    picked: list[dict] = []

    def add(p):
        if p and all(p["passage_id"] != q["passage_id"] for q in picked):
            picked.append(p)

    def chapter_matching(pattern: str):
        for ch in sorted(c for c in groups if c is not None):
            if re.search(pattern, groups[ch][0].get("chapter_title") or "", re.I):
                return ch
        return None

    # The report's own verdict first, then its statement of outcomes.
    ch = chapter_matching(r"CONCLUSION")
    if ch is not None:
        prose = _prose_passages(groups[ch])
        if prose:
            add(prose[0])
    ch = chapter_matching(r"SUMMARY OF ENVIRONMENTAL")
    if ch is not None:
        prose = _prose_passages(groups[ch])
        if prose:
            add(prose[-1])

    # What the project is, and why it exists.
    for pattern in (r"INTRODUCTION", r"PROJECT DESCRIPTION"):
        ch = chapter_matching(pattern)
        if ch is None:
            continue
        prose = _prose_passages(groups[ch])
        if prose:
            add(prose[0])

    # Reports without a summary chapter: each impact chapter's concluding section.
    # Chapters already represented above are skipped, so the remaining slots add
    # a new impact area (air, noise, ecology...) instead of a second passage from
    # a chapter the reader has already seen.
    used_chapters = {p.get("chapter") for p in picked}
    for ch in sorted(c for c in groups if c is not None):
        if len(picked) >= OVERVIEW_LIMIT:
            break
        if ch in used_chapters:
            continue
        prose = [p for p in _prose_passages(groups[ch]) if p.get("section_ref")]
        if not prose:
            continue
        top = max(_major_section(p["section_ref"]) for p in prose)
        for p in prose:
            if _major_section(p["section_ref"]) == top:
                add(p)
                break
    return picked[:OVERVIEW_LIMIT]


def _overview_passages_zh(report_id: str | None) -> list[dict]:
    """The Chinese executive summary is itself the report's summary, so a Chinese
    overview request is answered from its own 總結 / 引言 pages."""
    rid = report_id or PRIMARY_REPORT_ID
    passages = [p for p in IDX_ZH.passages if p.get("report_id") == rid] if IDX_ZH else []
    if not passages:
        return []
    picked: list[dict] = []

    def add(p):
        if p and all(p["passage_id"] != q["passage_id"] for q in picked):
            picked.append(p)

    def first_with(needle: str):
        for p in passages:
            if needle in (p.get("text") or ""):
                return p
        return None

    for needle in ("總結", "結論", "引言", "影響"):
        if len(picked) >= 3:
            break
        add(first_with(needle))
    return picked


# ------------------------------------------------------------------ LLM synthesis

# Two providers behind one interface. The local model stays the default so the
# project runs with no account and no key; OpenRouter is used when a key is
# present, which is what the hosted deployment does.
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "granite4.1:3b"
OLLAMA_TIMEOUT = 100  # seconds. A 700-token Chinese answer measures ~75 s here.

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Configurable default; override with OPENROUTER_MODEL.
OPENROUTER_DEFAULT_MODEL = "google/gemma-4-26b-a4b-it:free"
OPENROUTER_TIMEOUT = 90  # seconds. Hosted latency varies far more than localhost.

# When a provider fails in a way that retrying cannot fix (bad key, rate limit),
# stop calling it for a while. Without this the caller's one retry — and the next
# reader's question — would hammer an endpoint that is already refusing us.
_PROVIDER_COOLDOWN_UNTIL = 0.0
_COOLDOWN_AUTH = 300.0
_COOLDOWN_RATE_LIMIT = 30.0


def _openrouter_key() -> str:
    """The API key, read from the server environment on every call.

    Never stored in a module constant, so it cannot be captured at import time
    and cannot end up in a pickled object, a response body or a test fixture.
    """
    return (os.environ.get("OPENROUTER_API_KEY") or "").strip()


def _openrouter_model() -> str:
    return (os.environ.get("OPENROUTER_MODEL") or "").strip() or OPENROUTER_DEFAULT_MODEL


def _llm_provider() -> str:
    """Which provider to use: "openrouter" or "ollama".

    LLM_PROVIDER forces a choice ("ollama" is useful for tests and for a laptop
    that happens to have a key exported). "auto" prefers OpenRouter when a key
    is configured and otherwise uses the local model.
    """
    forced = (os.environ.get("LLM_PROVIDER") or "auto").strip().lower()
    if forced in ("openrouter", "ollama"):
        return forced
    return "openrouter" if _openrouter_key() else "ollama"


def _in_cooldown() -> bool:
    return time.monotonic() < _PROVIDER_COOLDOWN_UNTIL


def _start_cooldown(seconds: float) -> None:
    global _PROVIDER_COOLDOWN_UNTIL
    _PROVIDER_COOLDOWN_UNTIL = time.monotonic() + seconds


def _clear_cooldown() -> None:
    global _PROVIDER_COOLDOWN_UNTIL
    _PROVIDER_COOLDOWN_UNTIL = 0.0


def _build_synthesis_prompt(question: str, lang: str, evidence: list[dict],
                            overview: bool = False) -> list[dict]:
    """Build the chat messages for the LLM.

    The output shape is fixed — Summary, Key findings, What this means — because
    a summary that narrates its own sources ("the report states that...") tells
    the reader nothing, and a summary that concatenates headings and fragments
    is not a summary at all. The Sources section is the evidence cards the UI
    already renders; the model's job is the substance above them.
    """
    zh = lang == "zh-Hant"
    lang_instruction = (
        "以繁體中文書寫摘要，即使證據段落是英文。介面語言決定摘要語言，與來源語言無關。"
        if zh else
        "Write the summary in English, even if the evidence is in Chinese."
    )

    # Added only when the evidence really is Chinese, so an English question
    # keeps exactly the prompt it had before.
    has_zh = any(c.get("excerpt_lang") == "zh-Hant" for c in evidence)
    zh_rule = (
        "\n\nEVIDENCE LANGUAGE: the passages below are in TRADITIONAL CHINESE and "
        "come from the official Chinese executive summary. It is the original "
        "source, not a translation. Never translate an English passage and present "
        "it as a Chinese quotation, and never quote wording that is not in the evidence."
        if has_zh else ""
    )

    # Traditional Chinese costs ~1.3 tokens per character on this model, so an
    # English-length answer does not fit the token budget and was being cut off
    # mid-sentence. Ask for a compact answer that finishes, rather than a long
    # one that does not. English prompts are untouched.
    zh_length = (
        "\n\nLENGTH: write compact Traditional Chinese — 摘要約 150-250 字，"
        "主要發現最多 3 點，「這代表甚麼」1-2 句。每句都要寫完。"
        if zh else ""
    )

    if zh:
        sections = ("**摘要**\n（3-5 句連貫段落，說明報告涵蓋甚麼、結論是甚麼；不含數字與措施名稱）\n\n"
                    "**主要發現**\n- （具體發現，含數字／地點／措施，附引註）\n"
                    "- （另一項具體發現，附引註）\n\n"
                    "**這代表甚麼**\n（一句話：對附近居民有甚麼後果）")
    else:
        sections = ("**Summary**\n(one paragraph of 3-5 connected sentences: what "
                    "was assessed and what it concluded; no figures or measure names)\n\n"
                    "**Key findings**\n- (specific finding with its figure, location "
                    "or measure, with citation)\n- (a different specific finding, with citation)\n\n"
                    "**What this means**\n(ONE sentence: the consequence for someone "
                    "living nearby)")

    overview_rule = (
        "\n\n9. THIS IS A WHOLE-REPORT OVERVIEW. The passages span the report's "
        "purpose, its main impacts, its mitigation approach and its conclusion. "
        "Summarise the report as a whole: what the project is, which environmental "
        "impacts were assessed, what the report concludes, and any conditions "
        "attached. Do not walk through the passages one by one."
        if overview else ""
    )

    plain_rule = (
        "\n\n10. WRITE FOR A RESIDENT, NOT AN ENGINEER. Explain a technical term the "
        "first time it appears, in the same sentence and in brackets — e.g. 'noise "
        "barrier (a wall built to block sound)', 'residual impact (the effect left "
        "after the measures are in place)'. Do not stack abbreviations, section "
        "numbers or report titles into a sentence. Never start a sentence with a "
        "section number. Never paste a heading, a document title or a raw fragment "
        "into the text."
        if not zh else
        "\n\n10. 以居民看得懂的語言書寫。技術術語首次出現時，在同一句內用括號解釋，"
        "例如「隔音屏障（阻擋聲音的牆）」、「剩餘影響（措施實施後仍存在的影響）」。"
        "專有名詞（地名、項目名稱、機構名稱）保留英文原文，不要自行音譯；可在後面用"
        "括號補充中文說明。沒有公認中文譯名的，直接寫英文原名，不要造出中英夾雜的寫法"
        "（寫 Northern Metropolis Highway，不要寫「北 metropolis」）。"
        "證據寫 Ramsar Site、Mai Po、San Tin，就直接寫這些英文名，不要自創中文譯名"
        "（不要寫「蘭嶇國家公園」「南沙瀨濕地保護公園」這類憑空拼出來的名稱）。"
        "不要以章節編號（例如 14.6.1.1）開頭，也不要把縮寫、章節編號或報告名稱堆進句子，"
        "或直接貼上標題、文件名稱或零碎片段。引註放在句末，不要放在句首。"
    )

    dedupe_rule = (
        "\n\n11. EACH SECTION DOES A DIFFERENT JOB — do not repeat a finding across "
        "them.\n"
        "   Summary: the overview. What the assessment covers and what it concluded, "
        "in plain words. Do NOT put figures, standards, or the names of specific "
        "measures here — those belong in the bullets. Do not enumerate the impacts "
        "either: one phrase ('air quality, noise and ecology') is enough, the "
        "bullets carry the detail.\n"
        "   Key findings: the specifics. Each bullet is a different fact, with its "
        "number, location or measure named. Nothing already stated in the Summary.\n"
        "   What this means: ONE sentence about the consequence for someone living "
        "nearby. No new facts, no measure names, no numbers, and no restating the "
        "findings."
        if not zh else
        "\n\n11. 三段各有分工，不可重複同一項發現。\n"
        "   摘要：整體概述，用平實語言說明評估涵蓋甚麼、結論是甚麼。不要放數字、標準或"
        "具體措施名稱，那些留給主要發現。\n"
        "   主要發現：具體事實，每點不同，寫出數字、地點或措施名稱。不要重述摘要已有的內容。\n"
        "   這代表甚麼：只用一句話說明對附近居民的後果。不加新事實、不提措施名稱、不寫數字，"
        "也不要重述發現。"
    )

    meaning_rule = (
        "\n\n12. SEPARATE THE REPORT FROM YOUR READING OF IT. 'What this means' is "
        "where interpretation is allowed, and it must be visible as interpretation: "
        "write 'This suggests…', 'In practice…'. Never present an interpretation as "
        "something the report concluded. Keep it to ONE sentence built only from "
        "the findings already stated above — no new fact, no number, no measure "
        "name. If the evidence does not support any practical reading, say so in "
        "one sentence instead of inventing one. The heading is MANDATORY: all "
        "three sections must appear every time, even when a section can only say "
        "what the evidence does not establish."
        if not zh else
        "\n\n12. 分清報告內容與你的解讀。「這代表甚麼」可以解讀，但必須看得出是解讀："
        "用「這意味著…」「實際上…」。不可把解讀寫成報告的結論。只用一句話，內容只根據"
        "上文已述的發現，不加新事實、數字或措施名稱。若證據不足以支持任何實際含義，"
        "用一句話說明，不要憑空推論。三個段落標題都是必須的：每次都要寫齊三段，"
        "即使某一段只能說明證據未能確立甚麼。"
    )

    quote_rule = (
        "\n\n13. ENGLISH STAYS ENGLISH. When you quote an English passage inside a "
        "Chinese summary, reproduce the English wording unchanged in quotation "
        "marks, then explain it in Chinese. Do not translate a quotation and present "
        "the translation as if it were the report's wording."
        if zh else ""
    )

    fragment_rule = (
        "\n\n14. TABLES AND FRAGMENTS. Some passages are table rows split into "
        "short cells ('施 工期間 對空氣 質素 造成的潛 在影響'). Read them for what "
        "the cells literally say. Do not reconstruct a cell that is missing, and do "
        "not name a measure the cells do not name. If a passage shows the problem "
        "but not the response, say what the evidence does establish and stop there."
    )

    system = (
        "You are NORTHWISE, an assistant that explains official Hong Kong "
        "Environmental Impact Assessment (EIA) reports to residents. Using ONLY "
        "the evidence passages provided, write a summary of what they actually say.\n\n"
        "OUTPUT FORMAT — exactly these three sections, no preamble, no closing offer:\n\n"
        f"{sections}\n\n"
        "RULES:\n"
        "1. STATE THE FINDING, NOT THE SOURCE. Never write 'the report states "
        "that...', 'the report says...', 'the report describes...', 'this passage "
        "shows...', 'the executive summary provides...'. Write the finding itself; "
        "the citation at the end of the sentence shows where it came from. A reader "
        "must learn something before opening any source. BANNED OPENERS: any "
        "sentence that begins with 'The report', 'The study states', 'The document', "
        "'This passage' or 'According to' is wrong — start with the subject matter.\n\n"
        "2. BE SPECIFIC. Use the actual measures, standards, limits, locations, "
        "receptors, quantities and conclusions in the evidence. 'Mitigation "
        "measures were proposed' says nothing; name them.\n\n"
        "3. KEEP QUALIFICATIONS. If the report says 'no residual impact is "
        "anticipated' or 'subject to implementation of the measures', keep that "
        "condition. Do not upgrade a prediction into a certainty.\n\n"
        "4. CITE. End every sentence or bullet that makes a factual claim with the "
        "citation given beside its passage, e.g. [report_id, Ch.X, p.Y]. Where a "
        "passage has no printed page number, cite [report_id, Ch.X] instead. Never "
        "invent a page number, and never cite a passage that is not below.\n\n"
        "5. DO NOT INVENT. No figures, standards, measures or conclusions that are "
        "not in the evidence. If the evidence does not address part of the question, "
        "leave that part out rather than filling it.\n\n"
        "6. ATTRIBUTE FIGURES TO THE RIGHT THING. A quantity that belongs to a wider "
        "programme is not this project's own: if a passage says the whole highway is "
        "24 km and this project is one of its sections, do not call this project a "
        "24 km road. Keep the scope word the passage used.\n\n"
        "7. LENGTH: the Summary is one paragraph; Key findings is 2-4 bullets; "
        "'What this means' is 1-2 sentences. Short sentences. No bullet lists "
        "inside the Summary.\n\n"
        "8. WRITE CONNECTED PROSE. The Summary is sentences that follow from one "
        "another, not a list of excerpts joined by full stops. If the evidence is "
        "too thin for a section, write what it does establish and say plainly what "
        "it does not — never pad with generic wording."
        + "\n\n9. " + lang_instruction
        + zh_rule
        + zh_length
        + overview_rule
        + plain_rule
        + dedupe_rule
        + meaning_rule
        + quote_rule
        + fragment_rule
    )

    evidence_blocks = []
    for card in evidence:
        # The full passage, not the card's display window — see
        # SYNTHESIS_EXCERPT_WIDTH for the case that motivated this.
        body = card.get("synthesis_excerpt") or card["excerpt"]
        evidence_blocks.append(f"{_citation_token(card)}\n{body}")

    user = (
        f"Question: {question}\n\n"
        "Evidence passages (use ONLY these; do not add outside knowledge):\n\n"
        + "\n\n---\n\n".join(evidence_blocks)
        + "\n\nWrite the Summary, Key findings and What this means now, in the "
        "format specified. Cite each factual claim with the token shown beside "
        "its passage."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _validate_synthesis(answer: str, evidence: list[dict]) -> bool:
    """Check that every citation in the answer refers to a retrieved evidence card.

    Handles:
      - Compound page citations: [r, Ch.X, p.Y, p.Z]
      - Semicolon-separated multi-report citations: [r1, Ch.X, p.Y; r2, Ch.X, p.Z]
    Returns True if all detected citations are valid, False otherwise.
    """
    if not answer or not evidence:
        return False

    def _norm_dashes(s: str) -> str:
        # Models sometimes output non-ASCII dashes (en-dash, em-dash,
        # non-breaking hyphen, minus sign). Normalise to ASCII hyphen.
        return s.replace("\u2010", "-").replace("\u2011", "-").replace(
            "\u2012", "-"
        ).replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")

    # Build the keys a citation may legitimately use.
    #   page_keys    "report_id|chapter|page_label" — only for pages that really
    #                carry a printed folio. A card with no folio must not be
    #                citable as "p.None", which the model produced before and
    #                which used to slip through validation.
    #   chapter_keys "report_id|chapter" — the honest form for those cards.
    page_keys = set()
    chapter_keys = set()
    for card in evidence:
        rid = card.get("report_id", "")
        ch = str(card.get("chapter", ""))
        chapter_keys.add(f"{rid}|{ch}")
        pl = _norm_dashes(str(card.get("page_label") or "")).strip()
        if pl and pl.lower() != "none":
            page_keys.add(f"{rid}|{ch}|{pl}")

    # [report_id, Ch.N, p.X] — a page-level citation.
    pattern = re.compile(r"\[([^\]]+?),\s*Ch\.\s*(\d+),\s*p\.\s*([^\]]+?)\]")
    # [report_id, Ch.N] — a chapter-level citation, for pages without a folio.
    chapter_pattern = re.compile(r"\[([^\[\],]+?),\s*Ch\.\s*(\d+)\s*\]")

    citations = list(pattern.finditer(answer))
    chapter_citations = list(chapter_pattern.finditer(answer))
    if not citations and not chapter_citations:
        # An evidence-based answer must contain at least one citation.
        return False

    for m in chapter_citations:
        key = f"{m.group(1).strip()}|{m.group(2).strip()}"
        if key not in chapter_keys:
            return False

    for m in citations:
        rid = m.group(1).strip()
        ch = m.group(2).strip()
        pl_raw = _norm_dashes(m.group(3).strip())

        # Check if this is a semicolon-separated multi-report citation
        if ";" in pl_raw:
            parts = [p.strip() for p in pl_raw.split(";")]
            for part in parts:
                # Each part should be like "r2, Ch.X, p.Y" or just "r2, Ch.X, p.Y"
                # Try to extract report_id, chapter, page from each part
                sub_match = re.match(r"(.+?),\s*Ch\.\s*(\d+),\s*p\.\s*(.+)", part)
                if sub_match:
                    sub_rid = sub_match.group(1).strip()
                    sub_ch = sub_match.group(2).strip()
                    sub_pl = _norm_dashes(sub_match.group(3).strip())
                    key = f"{sub_rid}|{sub_ch}|{sub_pl}"
                    if key not in page_keys:
                        return False
                else:
                    # If we can't parse a part, be lenient and skip it
                    # (the model may have partial formatting)
                    continue
        else:
            # Handle compound page citations: "4-81, p.4-24" → ["4-81", "4-24"]
            pages = [p.strip() for p in re.split(r",\s*p\.\s*", pl_raw)]
            for pl in pages:
                pl = _norm_dashes(pl)
                key = f"{rid}|{ch}|{pl}"
                if key not in page_keys:
                    return False
    return True


class SynthesisUnavailable(Exception):
    """Raised when Ollama is unreachable or returns a non-OK response."""
    pass


def _trim_incomplete_tail(answer: str) -> str:
    """Drop a trailing partial sentence left by the token cap.

    A Traditional Chinese answer costs roughly 1.3 tokens per character on this
    model, so a long one can still reach `num_predict` mid-sentence. Cutting
    back to the last sentence-ending mark is the one repair that invents
    nothing: the text kept is exactly what the model wrote.

    Only applied to Chinese answers. English behaviour is left as it was.
    """
    if not answer:
        return answer
    stripped = answer.rstrip()
    if not stripped:
        return answer
    if stripped[-1] in "。！？；：":
        return stripped
    cut = max(stripped.rfind(ch) for ch in "。！？")
    if cut <= 0:
        return stripped
    return stripped[:cut + 1]


def _call_ollama(messages: list[dict], num_predict: int) -> tuple[str, dict]:
    """One local Ollama call. Returns (answer_text, raw_response)."""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": num_predict,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        resp = urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT)
        data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, socket.timeout, json.JSONDecodeError, OSError):
        raise SynthesisUnavailable("Ollama request failed")

    if not data.get("done"):
        raise SynthesisUnavailable("Ollama response incomplete")

    return ((data.get("message", {}).get("content") or "").strip(), data)


def _call_openrouter(messages: list[dict], num_predict: int) -> tuple[str, dict]:
    """One OpenRouter chat-completions call. Returns (answer_text, raw_response).

    The key is read from the environment, used only in the Authorization header,
    and never returned, logged or placed in an exception message. Failures are
    classified by HTTP status alone — the response body is provider prose and
    the request headers carry the key, so neither is echoed anywhere.
    """
    key = _openrouter_key()
    if not key:
        raise SynthesisUnavailable("OPENROUTER_API_KEY is not set")
    if _in_cooldown():
        raise SynthesisUnavailable("provider cooling down after an error")

    payload = json.dumps({
        "model": _openrouter_model(),
        "messages": messages,
        "stream": False,
        "temperature": 0.1,
        "max_tokens": num_predict,
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
            "X-Title": "NORTHWISE",
        },
    )

    try:
        resp = urllib.request.urlopen(req, timeout=OPENROUTER_TIMEOUT)
        raw = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            # A bad key will not fix itself inside a request; stop asking.
            _start_cooldown(_COOLDOWN_AUTH)
            raise SynthesisUnavailable("openrouter rejected the credentials") from None
        if exc.code == 429:
            # Retrying immediately is the opposite of graceful under a rate
            # limit. Answer from the evidence instead, and stand down briefly.
            _start_cooldown(_COOLDOWN_RATE_LIMIT)
            raise SynthesisUnavailable("openrouter rate limited") from None
        raise SynthesisUnavailable(f"openrouter http {exc.code}") from None
    except (urllib.error.URLError, socket.timeout, OSError):
        raise SynthesisUnavailable("openrouter request failed") from None

    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise SynthesisUnavailable("openrouter returned invalid JSON") from None

    choices = data.get("choices") or []
    content = ""
    if choices and isinstance(choices[0], dict):
        content = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not content:
        raise SynthesisUnavailable("openrouter returned no content")

    usage = data.get("usage") or {}
    data["_tokens"] = usage.get("completion_tokens")
    return content, data


def _call_model(messages: list[dict], num_predict: int) -> tuple[str, dict]:
    """Dispatch to the configured provider and normalise its metadata.

    Every caller gets the same (text, data) shape whichever provider ran, so the
    synthesis and validation code below is untouched. ``data`` carries
    ``_provider``, ``_model`` and ``_tokens`` for reporting back to the reader.
    """
    provider = _llm_provider()
    if provider == "openrouter":
        text, data = _call_openrouter(messages, num_predict)
        data["_model"] = data.get("model") or _openrouter_model()
    else:
        text, data = _call_ollama(messages, num_predict)
        data["_model"] = OLLAMA_MODEL
        data["_tokens"] = data.get("eval_count")
    data["_provider"] = provider
    return text, data


# Sentences that describe the document instead of its content. The system prompt
# forbids them; this model still writes them maybe one time in three, so one
# rewrite is requested when they appear.
_SOURCE_NARRATION = re.compile(
    r"(?im)(?:"
    r"(?:^|\s)(?:the|this)\s+(?:report|study|document|passage|assessment|executive summary)\s+"
    r"(?:states?|says?|describes?|highlights?|notes?|mentions?|outlines?|"
    r"presents?|lists?|details?)\b"
    r"|^\s*(?:[-•*]\s*)?it\s+(?:states?|says?|notes?|highlights?|mentions?|adds?)\b"
    r"|(?:本報告|該報告|報告|訊息|資料|原文)(?:指出|提到|說明|闡述|列出|講述)"
    # "第 3 節（引用 [...]）指出…" — citing a section instead of stating the finding.
    r"|第\s*\d+\s*[節章][^。！？]{0,24}?(?:指出|說明|提到|詳述|列出|講述)"
    r"|\d+(?:\.\d+){2,}\s"          # a pasted section number: "14.6.1.1 …"
    r")"
)

_RETRY_EN = (
    "Your answer still contains sentences that begin by describing the document "
    "('The report states...', 'It notes that...'). Rewrite it so every sentence "
    "starts with the subject matter — the impact, the measure, the figure or the "
    "finding — not with the report. Keep the same citations and the same three "
    "sections."
)
_RETRY_ZH = (
    "你的答案仍有句子以「本報告指出」「報告提到」開頭。請重寫：每句直接從主題"
    "（影響、措施、數字或發現）開始，不要以報告為主語。保留原有引註及三個段落。"
)

_RETRY_REPEAT_EN = (
    "Your Key findings repeat what the Summary already says. Rewrite the answer: "
    "the Summary keeps the overview, and each bullet must give a DIFFERENT specific "
    "fact — a number, place, measure, condition or conclusion — that the Summary "
    "does not already state. Keep the citations and the three sections."
)
_RETRY_REPEAT_ZH = (
    "你的「主要發現」重複了「摘要」已有的內容。請重寫：摘要保留整體概述，每點須為"
    "摘要沒有提到的具體事實（數字、地點、措施、條件或結論）。保留引註及三個段落。"
)

_RETRY_SIMPLIFIED_ZH = (
    "你的答案混入了簡體字。請全部改用繁體字重寫（例如 場／區／時／間／發／會／"
    "影響 不變），保留原有引註及三個段落。"
)

# Given a Chinese prompt and Chinese evidence, this model sometimes answers in
# English — measured once the evidence grew to three 655-character table dumps
# (2050 prompt tokens), where it also abandoned the three sections for a
# numbered list. The reader would see English prose under 摘要.
_RETRY_LANGUAGE_ZH = (
    "你用了英文作答。請用繁體中文重寫全文（摘要、主要發現、這代表甚麼），"
    "專有名詞可保留英文並在括號內附註，保留原有引註。"
)

# A bullet that reproduces a whole paragraph is not a finding — it is the
# report pasted back, which is what the reader was complaining about.
_RETRY_DUMP_EN = (
    "One of your bullets is a whole paragraph copied from the report, not a "
    "finding. Rewrite it as one short finding of your own words (under 25 "
    "words) naming the specific measure or conclusion, and keep its citation."
)
_RETRY_DUMP_ZH = (
    "「主要發現」中有一點是整段照抄報告原文，並非一項發現。請用自己的話改寫為"
    "一句簡短發現（25 字以內），寫出具體措施或結論，並保留引註。"
)

# Measured: on a Chinese request this model omits the citations about one time in
# three — not a wrong page, no citation at all — and the answer was then thrown
# away. Asking it to add them is a repair, not a rewrite.
_RETRY_CITE_EN = (
    "Your answer is missing citations. Add the citation token shown beside each "
    "passage, in square brackets, at the end of every sentence or bullet that makes "
    "a factual claim. Keep everything else exactly as it is."
)
_RETRY_CITE_ZH = (
    "你的答案缺少引註。請在每項事實陳述的句末補上該段落旁的引註（方括號格式，例如 "
    "[aeiar-276-2026, Ch.14, p.14-13]），其餘內容保持不變。"
)

# Words that carry no finding on their own, so they must not be counted when
# asking "does this bullet say the same thing as the summary?".
_STOPWORDS = set("""
a an the and or but if of to in on at by for with from as is are was were be been
being this that these those it its their there here which who whom whose what when
where how not no nor so than then also such can could would should may might must
has have had do does did will shall about into over under between during after
before more most other some any all both each few many own same very just only
""".split())


def _content_words(text: str) -> set:
    words = re.findall(r"[a-z0-9][a-z0-9\-']+", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _split_sections(answer: str) -> dict:
    """Split a model answer into its three sections by heading."""
    out = {"summary": "", "points": [], "meaning": ""}
    mode = None
    for raw in (answer or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(?:\*\*|__)?\s*(summary|摘要|總結|key points?|key findings?|"
                     r"主要發現|重點|要點|what (?:this|it) means|這代表甚麼|"
                     r"這代表什麼|這意味著甚麼)\s*(?:\*\*|__)?\s*[:：]?\s*(.*)$",
                     line, re.I)
        if m:
            head = m.group(1).lower()
            if re.search(r"what (?:this|it) means|代表甚麼|代表什麼|意味", head):
                mode = "meaning"
            elif re.search(r"key|重點|要點|發現", head):
                mode = "points"
            else:
                mode = "summary"
            if m.group(2).strip():
                if mode == "points":
                    out["points"].append(m.group(2).strip())
                else:
                    out[mode] += " " + m.group(2).strip()
            continue
        if mode == "points" and re.match(r"^[-•*]\s+", line):
            out["points"].append(re.sub(r"^[-•*]\s+", "", line))
        elif mode == "points":
            out["points"].append(line)
        elif mode == "meaning":
            out["meaning"] += " " + line
        elif mode == "summary":
            out["summary"] += " " + line
    return out


# The third section is the one this model drops most often: measured across
# runs of the same San Tin overview, it returned two headings about a third of
# the time. The structure is part of the specification, and the honest way to
# fill a missing section is to say what the evidence does not establish rather
# than to invent a consequence.
_NO_MEANING = {
    "en": ("Beyond the findings above, the evidence retrieved does not "
           "establish any further practical consequence for nearby residents."),
    "zh-Hant": ("除上述發現外，檢索所得的證據未能確立對附近居民的其他實際後果。"),
}


def _ensure_three_sections(answer: str, lang: str) -> str:
    """Add the missing heading when the model omits a section.

    Never adds a finding — only the heading and a statement of what the
    evidence does not establish.
    """
    if not answer:
        return answer
    parts = _split_sections(answer)
    zh = lang == "zh-Hant"
    if not parts["summary"].strip():
        return answer                     # nothing usable; leave it alone
    out = answer.rstrip()
    if not parts["meaning"].strip():
        head = "**這代表甚麼**" if zh else "**What this means**"
        out += f"\n\n{head}\n{_NO_MEANING[lang]}"
    return out


def _repeats_itself(answer: str) -> bool:
    """True when a bullet only restates the Summary.

    Deliberately narrow. Measured on this 3B model: three sections over the same
    four passages will always share vocabulary, and a loose threshold fired on
    every answer without improving it. What is worth catching is the bullet that
    re-says a summary sentence with the same content words — the case that made
    the output read as the same paragraph three times.
    """
    parts = _split_sections(answer)
    summary = _content_words(parts["summary"])
    if not summary:
        return False

    for bullet in parts["points"]:
        words = _content_words(bullet)
        if len(words) >= 5 and len(words & summary) / len(words) > 0.75:
            return True
    return False


# Simplified characters that have no Traditional use. Deliberately limited to
# characters where the two forms differ and the simplified form is unambiguous,
# so a Traditional answer is never flagged for a character that is the same in
# both scripts (影響, 環境, 評估 are shared or Traditional-only). Characters that
# also exist in Traditional (表, 里, 面, 干, 松, 云, 后, 台, 只, 布, 制) are left
# out on purpose — a false positive would trigger a pointless rewrite.
_SIMPLIFIED_CHARS = set(
    "场湿区锁挣尽关门问间时东车马鸟龙万与专业丝两严个丰临为丽举义乌乐习乡书买"
    "乱争亚产亲亿仅从仓仪们价众优会伟传伤体余侧债儿兰兴养兽冈册写军农冲决况"
    "冻净凉减凑几凤凭凯击刘则刚创删别动务势医华单卖卫厂厅历压县发变号听员响"
    "团园围图圆坏块坚处备复够头夹夺奖妇学宁宝实审对导将尔层属岁岛币师带帮广庆"
    "库应废开异弃张弹归当录径忆怀态总恋恶悦悬惊惧惨愿战户执扩扫扬扰抚抛抢护报"
    "担拟拥择挂挤挥损换据数断无旧显术机杀杂权条来极构枪标树样档桥检楼欢欧残毁"
    "气汇汉汤沟没沥沦泪泼泽洁洒涂涌润涨渐渔渗温湾满滤滨灭灯灵灾炉点炼烂烟烦"
    "烧热爱爷状独狭狱猎猪猫献环现电画畅疗疮疯痴盐监盖盘睁矿码砖础确碍礼祸离积"
    "称稳穷窃竞笔笼筑签简篮类粮紧纠红纤约级纪纯纱纲纳纵纷纸纹纺线练组细织终绍"
    "经绑结绕绘给络绝统绣继续绳维绵综绿缓编缘缩网罗罚罢耻职联聪肠肤肿胁胆胜胶"
    "脉脏脑脚脸腾舰舱艰艳艺节芦苍苏苹茧荐荣药莱莲获营萧蓝虏虑虫虽蚀蚁蚕蛮蜡蝇"
    "蝉衔补衬袄袜袭装见观规视览觉触誉计订认讨让训议讯记讲许论设访证评识诉诊词"
    "译试诗诚话询该详语误诱说诵请诸诺读课谁调谅谈谊谋谐谓谢谣谦谱贝负贡财责贤"
    "败账货质贩贪贫购贯贱贴贵贷贸费贺贼资赋赌赏赐赔赖赚赛赞赠赢赵赶趋趟轨转轮"
    "软轰轴轻载轿较辅辆辈辉辐输辖边达迁过迈运还这进远违连迟适选递逻遗遥邓邮邻"
    "郑释针钉钓钞钟钠钢钥钩钮钱钳钻铁铃铅铜铝银铸铺链销锅锋锐错锡锣锤锦键锯镇"
    "镜长闪闭闯闲闷闸闹闻阀阁阅阐阔队阳阴阵阶际陆陈险随隐难雏雕雾静韦韧韩页顶"
    "项顺须顽顾顿颁颂预领颇颈颊频颗题颜额颠颤风飘飞饥饮饭饰饱饲饶饼饿馆馈馒驭"
    "驮驯驰驱驳驴驶驻驼驾骂骄骆验骏骑骗骚骤鱼鲁鲍鲜鲨鳄鸠鸡鸣鸥鸦鸭鸳鸽鸿鹅鹏"
    "鹤鹰麦黄齐齿龄龚"
)
# 黑 鼠 鼻 趟 雕 痴 are written the same way in both scripts. They were in the
# set above and made a perfectly good Traditional answer look simplified
# ("黑夜裡的老鼠" was flagged), which triggered a pointless rewrite. Removed by
# subtraction rather than by editing the list, because several of them appear in
# more than one place in it.
_SHARED_CHARS = set("黑鼠鼻趟雕痴")
_SIMPLIFIED_CHARS -= _SHARED_CHARS

_SECTION_REF_LEAD = re.compile(r"(?m)^(\s*(?:[-•*]\s*)?)\d+(?:\.\d+){2,}\s+")


def _strip_section_numbers(answer: str) -> str:
    """Remove a pasted section reference from the start of a line.

    The model copies "14.6.1.1 " from the passage it is reading. A section number
    is metadata, not prose, and the citation at the end already says where the
    sentence came from. Deterministic because the model ignores the instruction.
    """
    return _SECTION_REF_LEAD.sub(r"\1", answer or "")


# "引用[aeiar-276-2026, Ch.14, p.14-13]：項目避免了…" — the model sometimes opens
# a bullet with the citation. The citation belongs at the end of the claim.
_LEADING_CITATION = re.compile(
    r"(?m)^(\s*(?:[-•*]\s*)?)(?:引用|根據|來源)?\s*(\[[^\]]+\])\s*[:：]\s*")


def _move_leading_citations(answer: str) -> str:
    out = []
    for line in (answer or "").splitlines():
        m = _LEADING_CITATION.match(line)
        if m and m.end() < len(line):
            out.append(f"{m.group(1)}{line[m.end():].rstrip()} {m.group(2)}")
        else:
            out.append(line)
    return "\n".join(out)


def _has_simplified(text: str) -> bool:
    return any(ch in _SIMPLIFIED_CHARS for ch in (text or ""))


def _problem_score(answer: str, evidence: list[dict], lang: str) -> int:
    """How badly an answer breaks the rules. Lower is better.

    The rewrite used to be accepted only if it cleared every check at once, so a
    rewrite that fixed the script but introduced one stylistic flaw was thrown
    away and the contaminated original was shown instead. That is how
    "南沙瀨湿地保護公園" reached the page after a retry had already produced a
    clean answer. Script and language are hard requirements from the spec, so
    they weigh more than style.
    """
    score = 0
    if _SOURCE_NARRATION.search(answer):
        score += 1
    if _repeats_itself(answer):
        score += 1
    if _pastes_a_passage(answer, evidence):
        score += 1
    if lang == "zh-Hant":
        if _has_simplified(answer):
            score += 2
        if _answered_in_english(answer):
            score += 2
    return score



_HAN = re.compile(r"[\u4e00-\u9fff]")


def _answered_in_english(text: str) -> bool:
    """True when a Chinese request came back as English prose.

    Measured on the dust question: the model wrote a numbered English list
    under the Chinese headings. Counting Han characters is enough — a real
    Chinese answer of this length has dozens; this one had none.
    """
    return len(_HAN.findall(text or "")) < 20


def _pastes_a_passage(answer: str, evidence: list[dict]) -> bool:
    """True when a bullet is a retrieved paragraph pasted back verbatim.

    Measured on the English dust answer: the seventh bullet was 300 characters
    of the report's own paragraph, trailing off mid-sentence ("Handling, and
    exposed areas. Stockpile areas should be covered…"). That is the
    concatenated-fragments failure the summary exists to avoid. Quoting the
    report is fine; reproducing it as a "finding" is not.
    """
    def norm(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").lower()).strip()

    bodies = [norm(c.get("synthesis_excerpt") or c.get("excerpt") or "")
              for c in evidence]
    for line in (answer or "").splitlines():
        line = line.strip()
        if not line.startswith(("-", "•", "*")):
            continue
        body = re.sub(r"\[[^\]]+\]\s*$", "", line.lstrip("-•* ")).strip()
        if len(body) < 220:
            continue
        probe = norm(body)[:180]
        if probe and any(probe in b for b in bodies):
            return True
    return False


def _synthesize(question: str, lang: str, evidence: list[dict],
                overview: bool = False) -> dict | None:
    """Call the local Ollama model to synthesize an evidence-grounded answer.

    Returns {"answer": str, "model": str, "tokens_used": int | None}
    or None if the answer fails citation/claim validation.

    Raises SynthesisUnavailable if Ollama is unreachable, times out, or
    returns an empty/unparseable response.  The caller can catch this and
    fall back to an evidence summary.
    """
    if not evidence:
        return None

    messages = _build_synthesis_prompt(question, lang, evidence, overview=overview)
    # Chinese needs a larger token budget for the same amount of text: measured
    # on this model, a Chinese answer costs ~1.3 tokens per character against
    # ~0.2 for English, so 400 tokens cut a Traditional Chinese summary off
    # mid-sentence at ~310 characters. Both budgets were raised again when the
    # third section ("What this means") was added.
    #
    # 700, not 900: this model writes at ~9.3 tokens/second here, so a full 900
    # budget is 96 seconds — past the request timeout, which turned a merely
    # rambling answer into "no answer at all".
    num_predict = 700 if lang == "zh-Hant" else 620

    answer, data = _call_model(messages, num_predict)
    if not answer:
        return None

    # If the token cap was reached, the last sentence is probably incomplete.
    if lang == "zh-Hant" and (data.get("_tokens") or 0) >= num_predict:
        answer = _trim_incomplete_tail(answer)

    # Validate citations (format check). A missing citation is repaired once
    # before the answer is discarded — the model drops them, it does not usually
    # invent them, so asking again works.
    if not _validate_synthesis(answer, evidence):
        repair_ask = _RETRY_CITE_ZH if lang == "zh-Hant" else _RETRY_CITE_EN
        if lang == "zh-Hant" and _answered_in_english(answer):
            # One repair, two faults: it answered in English AND dropped the
            # citations. Asking twice would cost two more model calls.
            repair_ask = _RETRY_LANGUAGE_ZH + "\n\n" + repair_ask
        repair = messages + [
            {"role": "assistant", "content": answer},
            {"role": "user", "content": repair_ask},
        ]
        try:
            repaired, data_r = _call_model(repair, num_predict)
        except SynthesisUnavailable:
            return None
        if lang == "zh-Hant" and (data_r.get("_tokens") or 0) >= num_predict:
            repaired = _trim_incomplete_tail(repaired)
        if not repaired or not _validate_synthesis(repaired, evidence):
            return None
        answer, data = repaired, data_r

    # Deterministic cleanup first: a pasted "14.6.1.1 " is removed whether or not
    # the model cooperates.
    answer = _limit_points(_normalise_bullets(
        _move_leading_citations(_strip_section_numbers(answer))))

    # One consolidated rewrite. Three separate retries would stack into four
    # model calls; naming every problem at once costs one, and the first answer
    # is kept as a fallback so a failed rewrite can never lose a valid answer.
    problems = []
    if _SOURCE_NARRATION.search(answer):
        problems.append("narration")
    if _repeats_itself(answer):
        problems.append("repetition")
    if lang == "zh-Hant" and _has_simplified(answer):
        problems.append("simplified")
    if lang == "zh-Hant" and _answered_in_english(answer):
        problems.append("language")
    if _pastes_a_passage(answer, evidence):
        problems.append("dump")

    if problems:
        parts = []
        if "narration" in problems:
            parts.append(_RETRY_ZH if lang == "zh-Hant" else _RETRY_EN)
        if "repetition" in problems:
            parts.append(_RETRY_REPEAT_ZH if lang == "zh-Hant" else _RETRY_REPEAT_EN)
        if "simplified" in problems:
            parts.append(_RETRY_SIMPLIFIED_ZH)
        if "language" in problems:
            parts.append(_RETRY_LANGUAGE_ZH)
        if "dump" in problems:
            parts.append(_RETRY_DUMP_ZH if lang == "zh-Hant" else _RETRY_DUMP_EN)
        retry = messages + [
            {"role": "assistant", "content": answer},
            {"role": "user", "content": "\n\n".join(parts)},
        ]
        try:
            second, data2 = _call_model(retry, num_predict)
        except SynthesisUnavailable:
            second = ""
        if second:
            if lang == "zh-Hant" and (data2.get("_tokens") or 0) >= num_predict:
                second = _trim_incomplete_tail(second)
            second = _limit_points(_normalise_bullets(
                _move_leading_citations(_strip_section_numbers(second))))
            # Keep the rewrite when it is better, not only when it is perfect.
            # A clean script with one stylistic flaw beats a contaminated
            # original; a rewrite that is worse in every respect is discarded.
            if (_validate_synthesis(second, evidence)
                    and _problem_score(second, evidence, lang)
                    < _problem_score(answer, evidence, lang)):
                answer, data = second, data2

    # The structure is part of the contract with the reader, so it is enforced
    # here rather than left to whether the model remembered the third heading.
    answer = _ensure_three_sections(answer, lang)

    # Claim-level semantic validation (if available)
    if _CLAIM_EVAL_AVAILABLE:
        eval_result = CE.evaluate_answer(answer, evidence)
        if eval_result["overall_outcome"] == "rejected":
            # Return the answer with a warning rather than discarding it.
            # The explanation is still valuable to users; transparency
            # about verification level is handled by the frontend.
            return {
                "answer": answer,
                "model": data.get("_model") or OLLAMA_MODEL,
                "tokens_used": data.get("_tokens"),
                "evaluation": {
                    "status": "rejected",
                    "total_claims": eval_result["metrics"]["total_claims"],
                },
            }
        if eval_result["overall_outcome"] == "flagged":
            # Attach warning but keep the answer
            return {
                "answer": answer,
                "model": data.get("_model") or OLLAMA_MODEL,
                "tokens_used": data.get("_tokens"),
                "evaluation": {
                    "status": "flagged",
                    "flagged_claims": eval_result["metrics"]["human_review"],
                    "total_claims": eval_result["metrics"]["total_claims"],
                },
            }

    return {
        "answer": answer,
        "model": data.get("_model") or OLLAMA_MODEL,
        "tokens_used": data.get("_tokens"),
    }


def _first_sentences(text: str, limit: int = 2, max_chars: int = 260) -> str:
    """The opening sentence(s) of a passage, for the extractive fallback.

    The wording is the report's own, so nothing is invented when no model is
    available. Two things have to be cleaned off first, or the fallback reads
    like a machine dump:

      - the section heading that precedes the number — "Conclusion of EIA Study
        15.1.1.1 This EIA Report has provided…" is one sentence, but the heading
        belongs to the chapter, not to the answer;
      - a hard character cut, which used to end mid-word ("…course of EIA stu").
        Cut on a sentence boundary, and on a word boundary if there is none.
    """
    t = (text or "").strip()
    # Heading + number, only when the prefix has no sentence punctuation in it,
    # so an ordinary sentence containing "15.1.1" is left alone.
    t = re.sub(r"^[^\n.!?]{0,80}?\b\d+(?:\.\d+)+\s+", "", t, count=1)
    t = re.sub(r"^\s*(?:[-•·])\s*", "", t).lstrip("…").strip()

    # A windowed excerpt starts mid-sentence ("…程項目施工期間潛在的空氣質素影響…").
    # Quoting from there is the broken fragment the summary must not contain, so
    # skip forward to the first sentence end — but only when the window cut is
    # what put us there, which the leading ellipsis records.
    if (text or "").strip().startswith("…"):
        first_end = re.search(r"[.!?。！？]\s*", t)
        if first_end:
            rest = t[first_end.end():].lstrip()
            if len(rest) >= 20:      # long enough to be a sentence of its own
                t = rest

    out = []
    for chunk in re.split(r"(?<=[.!?。！？])\s+", t):
        if not chunk:
            continue
        out.append(chunk.strip())
        if len(out) >= limit or len(" ".join(out)) >= max_chars:
            break

    joined = " ".join(out).strip()
    if len(joined) <= max_chars:
        return joined

    # Longest sentence boundary that still fits.
    end = 0
    for m in re.finditer(r"[.!?。！？]", joined[:max_chars]):
        end = m.end()
    if end >= 80:
        return joined[:end]
    cut = joined.rfind(" ", 0, max_chars)
    return joined[:cut if cut > 80 else max_chars].rstrip(" ,;:") + "…"


_NUMBERED_LINE = re.compile(r"(?m)^([ \t]*)\d{1,2}[.)][ \t]+(?=\S)")


def _normalise_bullets(answer: str) -> str:
    """Turn "1. …" / "2) …" into "- …".

    The prompt asks for bullets and the model still returns a numbered list
    about one time in three, which the reader sees as a different structure
    from every other answer. A section number is not affected: "2.4 米的圍擋"
    has no space after the point.
    """
    return _NUMBERED_LINE.sub(r"\1- ", answer or "")


def _limit_points(answer: str, limit: int = 4) -> str:
    """Keep at most `limit` bullets under Key findings.

    The prompt asks for 2-4 and the model routinely returns six or seven when
    the evidence is rich. The extra bullets are real findings, but a summary
    with seven of them is a list, not a summary.
    """
    out, kept, in_points = [], 0, False
    for line in (answer or "").splitlines():
        # "**Key findings**" starts with "*", so the heading must be classified
        # before bullets or it consumes one of the four slots.
        heading = re.match(r"^\s*\*\*", line)
        if heading and re.match(r"^\s*\*\*\s*(?:Key findings|主要發現)", line):
            in_points = True
        elif heading:
            in_points = False
        is_bullet = (not heading) and line.lstrip().startswith(("-", "•", "*"))
        if is_bullet and in_points:
            if kept >= limit:
                continue
            kept += 1
        out.append(line)
    return "\n".join(out)


def _sentence_key(sentence: str) -> set:
    """Word set used to spot the same finding twice."""
    return set(re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", sentence.lower()).split())


def _assemble_evidence_summary(question: str, lang: str, evidence: list[dict]) -> dict:
    """Extractive fallback when LLM synthesis is unavailable.

    Every sentence is the report's own wording — no synthesis happens without a
    model, and none is pretended. What it must NOT do is concatenate whatever
    came back: retrieval often returns the same paragraph from two pages, a
    heading that repeats across chapters, or a table fragment, and gluing those
    together is what made the old output unreadable.

    So: one topic sentence per card, duplicates dropped, fragments dropped, and
    no "What this means" section — an interpretation cannot be extracted from a
    source, so it is not produced at all.
    """
    if not evidence:
        return None

    zh = lang == "zh-Hant"
    prose = []             # (sentence, citation) — real sentences
    extracts = []          # (fragment, citation) — table rows, quoted not summarised
    seen = []
    for card in evidence:
        # A table row has no sentences. Cutting it to 300 characters produced
        # the wall of cells the reader complained about ("環境影響摘要 敏感受體 /
        # 評估點 … 影響避免措施 / 緩解措施"), so it is quoted short and labelled.
        table = card.get("passage_type") in _TABLE_TYPES
        sentence = _first_sentences(card.get("excerpt", ""), limit=1,
                                    max_chars=120 if table else 300)
        if len(sentence) < 40:
            continue                      # a fragment, not a finding
        key = _sentence_key(sentence)
        if len(key) < 5:
            continue
        if any(len(key & prev) / max(1, len(key | prev)) > 0.75 for prev in seen):
            continue                      # same passage retrieved twice
        seen.append(key)
        (extracts if table else prose).append((sentence, _citation_token(card)))

    if not prose and not extracts:
        return None

    # The summary carries the first two distinct findings; the bullets carry the
    # rest. Splitting this way is what keeps a finding from appearing twice.
    if prose:
        summary = " ".join(s for s, _ in prose[:2])
        rest = ([(s, c, False) for s, c in prose[2:]]
                + [(s, c, True) for s, c in extracts])
    else:
        # Nothing but tables: say so rather than presenting cells as a summary.
        summary = ("檢索到的證據為報告表格，未能整理為敘述摘要；以下節錄原文。"
                   if zh else
                   "The retrieved evidence is tabular, so no narrative summary "
                   "was produced. The extracts are quoted below as they appear.")
        rest = [(s, c, True) for s, c in extracts]

    quote = (lambda s: f"「{s}」") if zh else (lambda s: f"“{s}”")
    extract_label = "（表格節錄）" if zh else " (table extract)"

    def bullet(sentence: str, cite: str, is_extract: bool) -> str:
        body = quote(sentence) + extract_label if is_extract else sentence
        return f"- {body} {cite}"

    if zh:
        parts = [f"**摘要**\n{summary}"]
        if rest:
            parts.append("**主要發現**\n" + "\n".join(
                bullet(s, c, is_ex) for s, c, is_ex in rest))
        if not any(card.get("excerpt_lang") == "zh-Hant" for card in evidence):
            # The report is English-only. Quotations stay in the report's own
            # wording (rule 3); saying so is better than passing English off as
            # a Chinese summary.
            parts.append("**這代表甚麼**\n未能提供中文改寫：以下引述報告英文原文，"
                         "請以上方「資料來源」對照。")
        answer = "\n\n".join(parts)
    else:
        parts = [f"**Summary**\n{summary}"]
        if rest:
            parts.append("**Key findings**\n" + "\n".join(
                bullet(s, c, is_ex) for s, c, is_ex in rest))
        answer = "\n\n".join(parts)

    return {
        "answer": _ensure_three_sections(answer, lang),
        "model": "evidence-summary",
        "tokens_used": None,
    }


# ------------------------------------------------------------------ core ask

def ask(question: str, lang: str = "en", report_id: str | None = None) -> dict:
    """Run retrieval and format evidence cards.

    Args:
        question: user query (displayed unchanged in response)
        lang: interface language — "en" or "zh-Hant".  This controls the
              response language (glossary definitions, i18n strings) but
              does NOT restrict the language of the question itself.
        report_id: optional scope filter (e.g. "aeiar-276-2026")

    Returns a dict with keys:
        question, lang, report_id, gate{...}, translation_applied,
        refused (bool), message (str), evidence (list).
    """
    if not lang:
        lang = detect_lang(question)

    # Detect the ACTUAL language of the question text independently of
    # the interface language.  This lets users write in any language
    # regardless of which UI language is selected.
    query_lang = detect_lang(question)

    result = {
        "question": question,
        "lang": lang,
        "report_id": report_id,
        "evidence": [],
        "translation_applied": False,
        "query_lang": query_lang,
    }

    stripped = question.strip()
    if not stripped:
        result["refused"] = True
        result["message"] = _t("refused_empty", lang)
        result["gate"] = {"status": "empty_query", "message": "empty query"}
        return result

    # ------------------------------------------------------------------
    # Glossary lookup (definition queries) — runs FIRST so definitional
    # queries can answer without requiring topic mapping.
    # ------------------------------------------------------------------
    glossary_entry = _lookup_glossary(stripped, lang)

    # ------------------------------------------------------------------
    # Whole-report overview
    # ------------------------------------------------------------------
    # "Summarise this report" cannot be answered by keyword retrieval: measured
    # before this branch existed, it returned three different reports' Chapter 1
    # introductions. A report overview is assembled from that report's own
    # conclusion, outcomes, purpose and description instead.
    if _is_overview_question(stripped):
        picked = (_overview_passages_zh(report_id) if query_lang == "zh-Hant"
                  else _overview_passages(report_id))
        if picked:
            overview_cards = [
                _make_card(p, i, [], excerpt_width=OVERVIEW_EXCERPT)
                for i, p in enumerate(picked, 1)
            ]
            result["refused"] = False
            result["message"] = _t("evidence_intro", lang)
            result["evidence"] = overview_cards
            result["evidence_lang"] = ("zh-Hant" if query_lang == "zh-Hant" else "en")
            result["query_lang"] = query_lang
            result["disclaimer"] = _t("disclaimer", lang)
            result["gate"] = {
                "status": "overview",
                "message": (f"report overview: {len(overview_cards)} passages "
                            f"from {overview_cards[0]['report_id']}"),
                "blocked": False,
                "oov_terms": [],
                "present_terms": [],
                "substitutions": {},
            }
            result["answerability"] = {"answerable": True, "reason": "overview",
                                       "intent": None, "checks": {}}
            try:
                synth = _synthesize(question, lang, overview_cards, overview=True)
            except SynthesisUnavailable:
                synth = None
            # A model answer that fails citation validation returns None. Falling
            # back to the report's own sentences keeps a summary on screen instead
            # of leaving the reader with a bare list of sources.
            if not synth:
                synth = _assemble_evidence_summary(question, lang, overview_cards)
            result["synthesis"] = synth
            return result

    # ------------------------------------------------------------------
    # Determine search terms and run gate
    # ------------------------------------------------------------------
    # CRITICAL: use query_lang (detected from question text), NOT lang
    # (interface language).  This allows mixed-language input:
    #   - zh-Hant interface + English question → English BM25 gate
    #   - en interface + Chinese question → Chinese topic mapping
    # ------------------------------------------------------------------
    search_terms = None
    gate_info = {}
    zh_hits = []

    if query_lang == "zh-Hant":
        # ---------------------------------------------------------------
        # 1. ORIGINAL CHINESE SOURCES FIRST.
        # The reports publish Traditional Chinese executive summaries. When a
        # Chinese question can be answered from those originals, they are the
        # evidence — not an English passage, and not a translation of one.
        # ---------------------------------------------------------------
        zh_terms, zh_hits = _zh_evidence_hits(stripped, report_id)

        if zh_hits:
            search_terms = zh_terms
            gate_info = {
                "status": "zh_original",
                "message": ("matched the Chinese executive summary "
                            f"({len(zh_hits)} passages)"),
                "blocked": False,
                "oov_terms": [],
                "present_terms": sorted({t for h in zh_hits for t in h[4]}),
                "substitutions": {},
            }
            result["translation_applied"] = False
            result["evidence_lang"] = "zh-Hant"
        else:
            mapped = _map_chinese_terms(stripped)
            if mapped:
                search_terms = mapped
                result["translation_applied"] = True
                result["mapped_terms"] = mapped
                gate_info = {
                    "status": "mapped",
                    "message": f"Chinese terms mapped to English: {mapped}",
                    "blocked": False,
                    "oov_terms": [],
                    "present_terms": mapped,
                    "substitutions": {},
                }
            else:
                # No Chinese topic-map match.  The question may still contain
                # English technical terms (e.g. "NSR", "PM2.5") mixed with
                # Chinese text.  Run the English BM25 gate to extract them.
                gate = CORPUS.gate(stripped)
                if gate["status"] not in ("empty_query", "all_oov"):
                    search_terms = gate["search_terms"]
                    gate_info = {
                        "status": gate["status"],
                        "message": gate["message"],
                        "blocked": gate["blocked"],
                        "oov_terms": gate.get("oov_terms", []),
                        "present_terms": gate.get("present_terms", []),
                        "substitutions": gate.get("substitutions", {}),
                    }
                elif glossary_entry:
                    # Glossary-only fallback
                    search_terms = []
                    gate_info = {
                        "status": "glossary_only",
                        "message": "Definition answered from glossary only",
                        "blocked": False,
                        "oov_terms": [],
                        "present_terms": [],
                        "substitutions": {},
                    }
                else:
                    # Genuinely unsupported Chinese query
                    result["refused"] = True
                    result["message"] = _t("refused_chinese_unsupported", lang)
                    result["gate"] = {
                        "status": "chinese_unsupported",
                        "message": "Chinese retrieval is limited to supported topic terms",
                        "blocked": False,
                        "oov_terms": [],
                        "present_terms": [],
                        "substitutions": {},
                    }
                    return result
    else:
        # English path: normal OOV gate
        gate = CORPUS.gate(stripped)
        gate_info = {
            "status": gate["status"],
            "message": gate["message"],
            "blocked": gate["blocked"],
            "oov_terms": gate.get("oov_terms", []),
            "present_terms": gate.get("present_terms", []),
            "substitutions": gate.get("substitutions", {}),
        }
        if gate["blocked"]:
            result["refused"] = True
            terms = ", ".join(f'"{t}"' for t in gate.get("oov_terms", []))
            result["message"] = _t("refused_all_oov", lang).format(terms=terms)
            result["gate"] = gate_info
            return result
        if gate["status"] == "empty_query":
            result["refused"] = True
            result["message"] = _t("refused_empty", lang)
            result["gate"] = gate_info
            return result
        search_terms = gate["search_terms"]

    result["gate"] = gate_info
    result["query_lang"] = query_lang

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    # A question that asks for measures needs a wider net: the passages that
    # NAME a measure sit just below the ones that merely refer to "the proposed
    # measures", so a top-3 cut loses them before they can be preferred.
    wants_measures = bool(_MEASURE_INTENT.search(stripped))
    pool = MAX_EVIDENCE * 2 if wants_measures else MAX_EVIDENCE

    if zh_hits:
        # Already gated against the Chinese index. The chapter-relevance
        # filter below is skipped: it reads chapter titles and idf from the
        # ENGLISH corpus, neither of which describes an executive summary.
        index = IDX_ZH
        hits = zh_hits
    else:
        index = IDX
        hits = IDX.search(search_terms, k=pool, report=report_id)

    if not hits:
        # If we have a glossary entry but no evidence, return the glossary alone
        if glossary_entry:
            result["refused"] = False
            result["message"] = _t("evidence_intro", lang)
            result["evidence"] = []
            result["glossary"] = glossary_entry
            result["disclaimer"] = _t("disclaimer", lang)
            return result
        result["refused"] = True
        result["message"] = _t("refused_no_results", lang)
        return result

    top_score = hits[0][0]
    if not zh_hits and top_score < MIN_SCORE:
        if glossary_entry:
            result["refused"] = False
            result["message"] = _t("evidence_intro", lang)
            result["evidence"] = []
            result["glossary"] = glossary_entry
            result["disclaimer"] = _t("disclaimer", lang)
            return result
        result["refused"] = True
        result["message"] = _t("refused_low_relevance", lang)
        result["top_score"] = round(top_score, 4)
        return result

    if not zh_hits:
        # Chapter-relevance filter: if a passage is from a chapter whose title
        # shares zero keywords with the query, and the passage does not match
        # at least one high-idf query term, deprioritise it.
        # This is a conservative post-filter: we collect up to 2×MAX_EVIDENCE
        # and then filter, so genuinely relevant cross-chapter hits survive.
        query_keywords = set(search_terms)
        filtered_hits = []
        for h in hits:
            w, raw, weight, i, matched = h
            p = IDX.passages[i]
            ch_title = (p.get("chapter_title") or "").lower()
            # Check if chapter title shares any keyword with query
            ch_has_keyword = any(kw in ch_title for kw in query_keywords)
            # Check if passage matched a high-idf term (idf > 3.0)
            high_idf_matched = any(CORPUS.idf(t) > 3.0 for t in matched)
            # Keep if chapter is relevant OR passage matched a rare term
            if ch_has_keyword or high_idf_matched:
                filtered_hits.append(h)
            else:
                # Deprioritise: only drop if we have enough better hits
                if len(filtered_hits) < MAX_EVIDENCE:
                    filtered_hits.append(h)

        # Use filtered hits if we still have enough; otherwise fall back to raw
        if len(filtered_hits) >= MAX_EVIDENCE:
            hits = filtered_hits[:pool]
        elif len(filtered_hits) > 0:
            hits = filtered_hits
        # else: keep original hits (should not happen since hits was non-empty)

    evidence = []
    for rank, (w, raw, weight, i, matched) in enumerate(hits, 1):
        p = index.passages[i]
        card = _make_card(p, rank, search_terms)
        card["score"] = round(w, 4)
        card["score_unweighted"] = round(raw, 4)
        card["matched_terms"] = matched
        evidence.append(card)

    # ------------------------------------------------------------------
    # Answerability gate
    # ------------------------------------------------------------------
    # Retrieval has returned passages that share vocabulary with the question.
    # That is not evidence that they answer it: "How much does the project
    # cost?" matched "much ... construction cost" in a comparison of piling
    # methods, and "What is the capital of France?" matched "Capital Works"
    # and a hazard table that happens to list France. Neither passage states
    # what was asked. Decide here, before anything is shown or synthesised.
    verdict = A.assess(
        stripped,
        evidence,
        list(search_terms or []),
        query_lang=query_lang,
        lang=lang,
        definitional=glossary_entry is not None,
    )
    result["answerability"] = {
        "answerable": verdict["answerable"],
        "reason": verdict["reason"],
        "intent": verdict["intent"],
        "checks": verdict["checks"],
    }
    if not verdict["answerable"]:
        result["refused"] = True
        result["message"] = _t("refused_not_answerable", lang)
        result["evidence"] = []
        result["gate"] = dict(gate_info, status="not_answerable",
                              reason=verdict["reason"])
        return result

    # Keep only the cards that carry the requested information, so an
    # unrelated passage is never shown beside a real answer just to fill the
    # card list. Ranks are renumbered to stay contiguous.
    # Named-measure passages first, then the usual three cards. The wider pool
    # exists only to find those passages; the reader still sees MAX_EVIDENCE.
    evidence = _prefer_named_measures(verdict["kept"], stripped)[:MAX_EVIDENCE]
    for new_rank, card in enumerate(evidence, 1):
        card["rank"] = new_rank

    result["refused"] = False
    result["message"] = _t("evidence_intro", lang)
    result["evidence"] = evidence
    # Which language the evidence itself is in. The UI labels the excerpt from
    # this, so a Chinese question that had to fall back to English says so
    # instead of implying the English text is a Chinese original.
    result.setdefault("evidence_lang", "en")
    result["disclaimer"] = _t("disclaimer", lang)
    if glossary_entry:
        result["glossary"] = glossary_entry
    try:
        synth = _synthesize(question, lang, evidence)
    except SynthesisUnavailable:
        # Ollama unreachable or returned an error — use extractive fallback
        synth = None
    if not synth and evidence:
        # A citation-validation failure is stochastic on this model: the same
        # request often succeeds on a second attempt. One retry is cheaper than
        # showing the reader English text under a Chinese heading.
        try:
            synth = _synthesize(question, lang, evidence)
        except SynthesisUnavailable:
            synth = None
    if not synth and evidence:
        # Validation failure or empty answer: fall back to the report's own
        # sentences rather than showing cards with no summary above them.
        synth = _assemble_evidence_summary(question, lang, evidence)
    result["synthesis"] = synth
    return result


# ------------------------------------------------------------------ HTTP server

def _health_payload() -> dict:
    """Cheap readiness check: no model call, no corpus rebuild.

    Reports only booleans and counts, so the response is safe to serve publicly.
    The API key never appears here — not even a prefix of it.
    """
    provider = _llm_provider()
    data_dir = os.path.join(ROOT, "stage1", "data")
    try:
        page_files = sum(1 for n in os.listdir(data_dir) if n.endswith(".pages.jsonl"))
    except OSError:
        page_files = 0
    return {
        "status": "ok" if (page_files and REPORTS_BY_ID) else "degraded",
        "provider": provider,
        "model": _openrouter_model() if provider == "openrouter" else OLLAMA_MODEL,
        "provider_ready": bool(_openrouter_key()) if provider == "openrouter" else True,
        "reports": len(REPORTS_BY_ID),
        "page_files": page_files,
        "static": os.path.isfile(os.path.join(ROOT, "static", "index.html")),
        "registry": os.path.isfile(os.path.join(ROOT, "stage0", "reports.json")),
    }


class AskHandler(http.server.BaseHTTPRequestHandler):
    """Minimal JSON API handler using stdlib only."""

    def _send_json(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: str, content_type: str):
        if not os.path.exists(path):
            self._send_json(404, {"error": "not found"})
            return
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        from urllib.parse import urlparse, unquote
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path in ("/", "/index.html"):
            self._serve_file(
                os.path.join(ROOT, "static", "index.html"), "text/html; charset=utf-8"
            )
        elif path == "/reports":
            self._send_json(200, _REPORTS_DATA)
        elif path == "/health":
            # Always 200 so a platform health check does not restart a service
            # that is up but has missing data; "status" carries the detail.
            self._send_json(200, _health_payload())
        else:
            # Serve any file under ROOT (e.g. stage0/source-data/.../boundary.json).
            # The path is normalised and confined to ROOT; anything outside returns 404.
            rel = path.lstrip("/")
            full = os.path.normpath(os.path.join(ROOT, rel))
            if not full.startswith(ROOT) or not os.path.isfile(full):
                self._send_json(404, {"error": "not found"})
                return
            ctype, _ = mimetypes.guess_type(full)
            self._serve_file(full, ctype or "application/octet-stream")

    def do_POST(self):
        if self.path != "/ask":
            self._send_json(404, {"error": "not found"})
            return
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "invalid JSON body"})
            return

        question = str(data.get("question", "")).strip()
        lang = data.get("lang", "")
        report_id = data.get("report_id") or None
        if report_id and report_id not in REPORTS_BY_ID:
            self._send_json(400, {"error": f"unknown report_id: {report_id}"})
            return
        if not lang:
            lang = detect_lang(question)
        result = ask(question, lang, report_id=report_id)
        self._send_json(200, result)

    def log_message(self, fmt, *args):
        pass  # keep stdout clean


# ------------------------------------------------------------------ tests

class AskTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = CORPUS
        cls.idx = IDX

    # -- English queries -------------------------------------------------
    def test_english_supported_query_returns_evidence(self):
        r = ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        self.assertGreaterEqual(len(r["evidence"]), 1)
        self.assertFalse(r["translation_applied"])
        card = r["evidence"][0]
        self.assertIn("report_id", card)
        self.assertIn("source_url", card)
        self.assertTrue(card["citation"].startswith("["))

    def test_english_all_oov_query_is_refused(self):
        r = ask("geothermal", "en")
        self.assertTrue(r["refused"])
        self.assertEqual(r["gate"]["status"], "all_oov")
        self.assertFalse(r["translation_applied"])
        self.assertEqual(len(r["evidence"]), 0)
        self.assertEqual(r["message"], "Sorry, I cannot answer this question")

    def test_english_empty_query_is_refused(self):
        r = ask("   ", "en")
        self.assertTrue(r["refused"])
        self.assertEqual(r["gate"]["status"], "empty_query")
        self.assertEqual(len(r["evidence"]), 0)

    def test_citation_includes_page_label_when_verified(self):
        r = ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        for card in r["evidence"]:
            if card["page_label_status"] == "verified":
                self.assertIsNotNone(card["page_label"])
                self.assertIn(str(card["page_label"]), card["citation"])

    def test_source_url_is_official_epd(self):
        r = ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        for card in r["evidence"]:
            url = card.get("source_url")
            if url:
                self.assertTrue(url.startswith("https://www.epd.gov.hk/"))

    def test_evidence_is_labeled_not_answer(self):
        r = ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        self.assertIn("evidence", r["message"].lower())
        self.assertIn("not a synthesized", r["message"].lower())

    def test_gate_exposed_in_response(self):
        r = ask("noise barrier", "en")
        self.assertIn("gate", r)
        self.assertIn("status", r["gate"])
        self.assertIn("blocked", r["gate"])

    def test_report_scoping_limits_results(self):
        r_all = ask("noise barrier", "en")
        r_scoped = ask("noise barrier", "en", report_id="aeiar-271-2025")
        self.assertFalse(r_all["refused"])
        self.assertFalse(r_scoped["refused"])
        for card in r_scoped["evidence"]:
            self.assertEqual(card["report_id"], "aeiar-271-2025")
        report_ids_all = {c["report_id"] for c in r_all["evidence"]}
        self.assertIn("aeiar-276-2026", report_ids_all)

    # -- Chinese: original Chinese sources come first ---------------------
    def _assert_chinese_original_ok(self, zh_query, report_id=None):
        """A Chinese question the executive summary can answer must return the
        ORIGINAL Chinese passage — never an English passage or a translation."""
        r = ask(zh_query, "zh-Hant", report_id=report_id)
        self.assertFalse(r["refused"],
                         f"{zh_query} should not be refused: {r.get('message')}")
        self.assertEqual(r["gate"]["status"], "zh_original")
        self.assertFalse(r["translation_applied"])
        self.assertEqual(r["evidence_lang"], "zh-Hant")
        self.assertGreaterEqual(len(r["evidence"]), 1)
        self.assertEqual(r["question"], zh_query)
        for card in r["evidence"]:
            self.assertEqual(card["excerpt_lang"], "zh-Hant")
            self.assertEqual(card["doc_kind"], "executive_summary")
            # the excerpt is the original: it must contain Han characters
            self.assertTrue(any("\u4e00" <= ch <= "\u9fff"
                                for ch in card["excerpt"]))
            # provenance survives: report, page, link
            self.assertIn(card["page_label"], card["citation"])
            self.assertIsNotNone(card["page_label"])
            self.assertTrue(card["source_url"].endswith(
                ("es_chi_out.pdf", "es_tc.pdf")),
                f"source_url must be the Chinese PDF, got {card['source_url']}")
            if report_id:
                self.assertEqual(card["report_id"], report_id)
        return r

    def test_chinese_noise_returns_chinese_original(self):
        self._assert_chinese_original_ok("噪音會唔會影響附近居民？")

    def test_chinese_ecology_returns_chinese_original(self):
        self._assert_chinese_original_ok("工程會唔會影響生態？")

    def test_chinese_water_quality_returns_chinese_original(self):
        self._assert_chinese_original_ok("水質會唔會受污染？")

    def test_chinese_waste_returns_chinese_original(self):
        self._assert_chinese_original_ok("廢物管理有咩措施？")

    def test_chinese_air_quality_returns_chinese_original(self):
        self._assert_chinese_original_ok("空氣質素影響")

    def test_chinese_cultural_heritage_returns_chinese_original(self):
        self._assert_chinese_original_ok("文化遺產有冇影響？")

    def test_chinese_landfill_gas_returns_chinese_original(self):
        self._assert_chinese_original_ok("堆填區氣體風險")

    def test_chinese_scoped_search_respects_report_id(self):
        self._assert_chinese_original_ok("堆填區氣體風險",
                                         report_id="aeiar-271-2025")

    def test_chinese_citation_token_is_numeric(self):
        """The executive summary keeps a numeric chapter token (0) so the
        existing citation validator and claim evaluator need no special case."""
        r = self._assert_chinese_original_ok("堆填區氣體風險")
        card = r["evidence"][0]
        self.assertEqual(card["chapter"], 0)
        ok = _validate_synthesis(
            f"風險很低 [{card['report_id']}, Ch.0, p.{card['page_label']}].",
            r["evidence"])
        self.assertTrue(ok)
        # ... and a wrong page still fails
        bad = _validate_synthesis(
            f"風險很低 [{card['report_id']}, Ch.0, p.999].", r["evidence"])
        self.assertFalse(bad)


class FallbackSummaryTest(unittest.TestCase):
    """The offline summary must not concatenate whatever retrieval returned.

    Fixture mirrors the real failure: the same paragraph retrieved from two
    pages, a heading that repeats the chapter title, a table fragment, and one
    genuine second finding.
    """

    def setUp(self):
        self.evidence = [
            {"report_id": "aeiar-276-2026", "chapter": 4, "page_label": "4-1",
             "excerpt_lang": "en",
             "excerpt": "Noise 4.6.1.1 Construction noise would be controlled by "
                        "noise barriers and silencers at the site boundary, and no "
                        "residual impact is anticipated after these measures."},
            {"report_id": "aeiar-276-2026", "chapter": 4, "page_label": "4-2",
             "excerpt_lang": "en",
             "excerpt": "4.6.1.1 Construction noise would be controlled by noise "
                        "barriers and silencers at the site boundary, and no "
                        "residual impact is anticipated after these measures."},
            {"report_id": "aeiar-276-2026", "chapter": 4, "page_label": "4-3",
             "excerpt_lang": "en", "excerpt": "Table 4.2"},
            {"report_id": "aeiar-276-2026", "chapter": 4, "page_label": "4-4",
             "excerpt_lang": "en",
             "excerpt": "Road Traffic Noise 4.6.6.1 With the implementation of all "
                        "proposed direct noise mitigation measures, road noise "
                        "contributions at all noise sensitive receivers would "
                        "comply with the relevant criteria."},
            {"report_id": "aeiar-276-2026", "chapter": 3, "page_label": "3-60",
             "excerpt_lang": "en",
             "excerpt": "Air Quality 3.11.1.1 Dust from site formation and material "
                        "handling would be suppressed by water spraying on active "
                        "works areas and wheel washing at every site exit."},
        ]

    def test_duplicates_are_collapsed(self):
        s = _assemble_evidence_summary("noise mitigation measures", "en",
                                       self.evidence)
        self.assertEqual(s["answer"].lower().count("noise barriers and silencers"), 1)

    def test_fragments_and_section_numbers_are_dropped(self):
        s = _assemble_evidence_summary("noise mitigation measures", "en",
                                       self.evidence)
        self.assertNotIn("Table 4.2", s["answer"])
        self.assertNotIn("4.6.1.1", s["answer"])
        self.assertNotIn("Road Traffic Noise 4.6.6.1", s["answer"])

    def test_sections_do_not_repeat_each_other(self):
        s = _assemble_evidence_summary("noise mitigation measures", "en",
                                       self.evidence)
        self.assertIn("**Summary**", s["answer"])
        self.assertIn("**Key findings**", s["answer"])
        # A finding appears in the summary OR in the bullets, never both.
        head, _, rest = s["answer"].partition("**Key findings**")
        bullets = rest.split("**What this means**")[0]
        for line in bullets.strip().splitlines():
            text = line.strip("- ").split("[")[0].strip()
            if not text:
                continue
            self.assertNotIn(text[:40], head)

    def test_chinese_labels_with_english_evidence_says_so(self):
        s = _assemble_evidence_summary("noise mitigation measures", "zh-Hant",
                                       self.evidence)
        self.assertIn("**摘要**", s["answer"])
        # the quotation stays English, and the note admits the limitation
        self.assertIn("noise barriers", s["answer"].lower())
        self.assertIn("未能提供中文改寫", s["answer"])

    def test_no_interpretation_without_a_model(self):
        """'What this means' is an interpretation; the fallback must not invent one.

        The heading is now always emitted, so the check is on the content: the
        only thing allowed under it is the statement that the evidence does not
        establish a consequence.
        """
        s = _assemble_evidence_summary("noise mitigation measures", "en",
                                       self.evidence)
        parts = _split_sections(s["answer"])
        self.assertEqual(parts["meaning"].strip(), _NO_MEANING["en"])

    def test_missing_third_section_is_filled_honestly(self):
        """The model drops 'What this means' about a third of the time."""
        two = ("**Summary**\nNoise barriers and silencers would be used.\n\n"
               "**Key findings**\n- Barriers on the site boundary [r, Ch.3, p.3-1]")
        out = _ensure_three_sections(two, "en")
        self.assertIn("**What this means**", out)
        self.assertIn(_NO_MEANING["en"], out)
        # A complete answer is left exactly as it was.
        three = two + "\n\n**What this means**\nQuieter nights for residents."
        self.assertEqual(_ensure_three_sections(three, "en"), three)
        # Chinese heading, Chinese sentence.
        zh = _ensure_three_sections(two.replace("**Summary**", "**摘要**")
                                    .replace("**Key findings**", "**主要發現**"),
                                    "zh-Hant")
        self.assertIn("**這代表甚麼**", zh)
        self.assertIn(_NO_MEANING["zh-Hant"], zh)

    def test_table_rows_are_quoted_short_and_labelled(self):
        """A table row is not a sentence. It must not be pasted as a finding.

        The real output this reproduces: a 300-character wall of cells
        ("環境影響摘要 敏感受體 / 評估點 … 影響避免措施 / 緩解措施") presented as
        the answer to a question about dust.
        """
        cells = ("環境影響摘要 敏感受體 / 評估點 預計的影響結果 （未實施緩解措施） "
                 "主要相關標準/準則 預測超標範圍 影響避免措施 / 緩解措施 剩餘影響 "
                 "空氣質素影響 施工影響 在本工程項目工地界線外 500 米範圍內具代表性 "
                 "住宅、商業發展和政府用地 施工期間對空氣質素造成的潛在影響")
        s = _assemble_evidence_summary("施工期間如何控制塵埃？", "zh-Hant", [
            {"report_id": "aeiar-276-2026", "chapter": 0, "page_label": "24",
             "excerpt_lang": "zh-Hant", "passage_type": "table_fragmented",
             "excerpt": cells}])
        self.assertIn("檢索到的證據為報告表格", s["answer"])
        self.assertIn("（表格節錄）", s["answer"])
        # quoted, and short — not the whole row dumped as a sentence
        self.assertIn("「", s["answer"])
        self.assertLess(len(s["answer"]), len(cells) + 200)

    def test_prose_still_carries_the_summary_when_a_table_is_also_retrieved(self):
        table = {"report_id": "aeiar-276-2026", "chapter": 0, "page_label": "24",
                 "excerpt_lang": "zh-Hant", "passage_type": "table_fragmented",
                 "excerpt": "環境影響摘要 敏感受體 / 評估點 預計的影響結果 "
                            "主要相關標準/準則 預測超標範圍 影響避免措施 / 緩解措施"}
        s = _assemble_evidence_summary("noise mitigation measures", "en",
                                       self.evidence + [table])
        self.assertNotIn("tabular", s["answer"])
        self.assertIn("noise barriers", s["answer"].lower())


class SummaryPromptTest(unittest.TestCase):
    def test_prompt_has_three_sections(self):
        msgs = _build_synthesis_prompt("q", "en", [
            {"report_id": "r", "chapter": 1, "page_label": "1-1",
             "excerpt": "Excerpt", "excerpt_lang": "en"}])
        system = msgs[0]["content"]
        for head in ("**Summary**", "**Key findings**", "**What this means**"):
            self.assertIn(head, system)

    def test_prompt_feeds_the_whole_passage_not_the_card_window(self):
        """The model must not be asked to summarise a passage it cannot see.

        A 300-character window on a table page ended mid-list of dust measures,
        and the model invented the rest of the list.
        """
        msgs = _build_synthesis_prompt("q", "en", [
            {"report_id": "r", "chapter": 1, "page_label": "1-1",
             "excerpt": "SHORT CARD WINDOW",
             "synthesis_excerpt": "FULL PASSAGE naming the measures",
             "excerpt_lang": "en"}])
        user = msgs[1]["content"]
        self.assertIn("FULL PASSAGE naming the measures", user)
        self.assertNotIn("SHORT CARD WINDOW", user)

    def test_card_carries_a_wider_excerpt_for_synthesis(self):
        page = next(p for p in IDX_ZH.passages
                    if p["report_id"] == "aeiar-276-2026"
                    and str(p["page_label"]) == "24")
        card = _make_card(page, 1, ["塵埃"])
        self.assertLessEqual(len(card["excerpt"]), 320)
        self.assertGreater(len(card["synthesis_excerpt"]), len(card["excerpt"]))

    def test_table_synthesis_excerpt_stays_short(self):
        """Three full table dumps pushed the Chinese prompt to 2050 tokens."""
        page = next(p for p in IDX_ZH.passages
                    if p["report_id"] == "aeiar-276-2026"
                    and str(p["page_label"]) == "24")
        card = _make_card(page, 1, ["塵埃"])
        self.assertLessEqual(len(card["synthesis_excerpt"]), TABLE_SYNTHESIS_WIDTH + 20)

    def test_english_answer_to_chinese_request_is_flagged(self):
        self.assertTrue(_answered_in_english(
            "The EIA identifies construction dust as a potential air quality "
            "issue. Mitigation includes watering and wheel washing."))
        self.assertFalse(_answered_in_english(
            "本環評報告指出施工期間的塵埃可透過灑水及車輪清洗設施控制，"
            "剩餘影響預計不會超標。"))

    def test_a_pasted_paragraph_bullet_is_flagged(self):
        """The seventh bullet of the dust answer was the report's own paragraph."""
        para = ("Stockpile areas should be covered with impervious sheets as far "
                "as practicable. Haul roads should be paved and regularly wetted "
                "to suppress the fugitive dust emission caused by travelling "
                "construction vehicles. Vehicles transporting dusty materials "
                "should be properly covered.")
        ev = [{"report_id": "r", "chapter": 3, "page_label": "3-1",
               "excerpt": para, "excerpt_lang": "en"}]
        self.assertTrue(_pastes_a_passage(f"- {para} [r, Ch.3, p.3-1]", ev))
        # A short finding in the model's own words is not a paste.
        self.assertFalse(_pastes_a_passage(
            "- Haul roads would be paved and wetted to suppress dust "
            "[r, Ch.3, p.3-1]", ev))

    def test_key_findings_are_capped_at_four(self):
        """The model returned seven bullets when the prompt asked for 2-4."""
        answer = ("**Summary**\nSomething.\n\n**Key findings**\n"
                  + "".join(f"- finding {i} [r, Ch.3, p.3-1]\n" for i in range(1, 8))
                  + "\n**What this means**\nOne sentence.")
        out = _limit_points(answer)
        self.assertEqual(out.count("- finding"), 4)
        self.assertIn("**What this means**", out)

    def test_numbered_list_becomes_bullets(self):
        """The Chinese noise answer came back as 1./2./3. instead of bullets."""
        answer = ("**主要發現**\n\n1. **預期噪音水平**：最高 84 dB(A)。\n"
                  "2. **緩解措施**：隔音屏障。\n")
        out = _normalise_bullets(answer)
        self.assertNotIn("1. **", out)
        self.assertIn("- **預期噪音水平**", out)
        self.assertIn("- **緩解措施**", out)

    def test_section_numbers_are_not_mistaken_for_list_numbers(self):
        out = _normalise_bullets("工地邊界設置高於地面 2.4 米的圍擋")
        self.assertIn("2.4 米", out)

    def test_narration_mid_sentence_is_caught(self):
        """'The report states that…' was the third sentence, so the line anchor missed it."""
        self.assertTrue(_SOURCE_NARRATION.search(
            "The project avoids sensitive areas. The report states that with "
            "proper mitigation no adverse impacts are anticipated."))
        self.assertTrue(_SOURCE_NARRATION.search(
            "- 第 3 節（引用 [r, Ch.0, p.2]）指出該項目已進行環境影響評估。"))
        # A plain finding is not narration.
        self.assertFalse(_SOURCE_NARRATION.search(
            "Dust would be suppressed by water spraying at every site exit."))

    def test_quote_starts_at_a_sentence_boundary(self):
        """A windowed excerpt begins mid-sentence; the quote must not.

        Real case: "…程項目施工期間潛在的空氣質素影響…" — the reader was shown a
        fragment starting with the tail of "本工程項目".
        """
        text = ("…程項目施工期間潛在的空氣質素影響主要源自各類施工活動，包括工地平整、"
                "工地清理、挖掘、斜坡工程、建造行政辦公大樓和附屬控制站。"
                "項目 500 米評估範圍內的其他同期工程項目之施工活動亦可能造成累積影響。")
        out = _first_sentences(text, limit=1, max_chars=300)
        self.assertFalse(out.startswith("程項目"), out)
        self.assertTrue(out.startswith("項目 500 米"), out)

    def test_chinese_prompt_asks_for_traditional_even_from_english(self):
        msgs = _build_synthesis_prompt("q", "zh-Hant", [
            {"report_id": "r", "chapter": 1, "page_label": "1-1",
             "excerpt": "Excerpt", "excerpt_lang": "en"}])
        system = msgs[0]["content"]
        self.assertIn("**摘要**", system)
        self.assertIn("**主要發現**", system)
        self.assertIn("**這代表甚麼**", system)
        self.assertIn("即使證據段落是英文", system)

    def test_simplified_detector_misses_official_traditional(self):
        """No false positive on the official Chinese executive summaries."""
        for p in IDX_ZH.passages:
            text = p.get("text") or ""
            self.assertFalse(_has_simplified(text),
                             f"{p['report_id']} p.{p.get('page_label')} flagged")

    def test_shared_characters_are_not_flagged(self):
        """黑 鼠 鼻 趟 雕 痴 are identical in both scripts.

        They were in the detector set, so a clean Traditional answer mentioning
        老鼠 or 黑夜 was treated as simplified and rewritten for nothing.
        """
        for text in ("黑夜裡的老鼠", "老鼠在鼻子上", "這是一趟旅程", "雕像"):
            self.assertFalse(_has_simplified(text), text)
        # ...while the characters actually produced by the model still are.
        for text in ("南沙瀨湿地保護公園", "地基作業、掘挣、物料處理"):
            self.assertTrue(_has_simplified(text), text)

    def test_a_better_rewrite_is_kept_even_with_one_flaw(self):
        """A clean script with one stylistic flaw beats a contaminated original.

        Measured on the San Tin overview: the rewrite dropped the simplified
        characters but added a "the report states" opener, so the old
        all-or-nothing rule kept the original — and 湿地 reached the page.
        """
        ev = [{"report_id": "r", "chapter": 14, "page_label": "14-13",
               "excerpt": "The project avoids the Ramsar Site.",
               "excerpt_lang": "en"}]
        original = ("**摘要**\n該項目避免了入侵生態敏感地區，包括蘭嶇國家公園一帶。"
                    "[r, Ch.14, p.14-13]\n\n"
                    "**主要發現**\n- 項目避免了該湿地，亦避開附近的生態敏感地區。"
                    "[r, Ch.14, p.14-13]")
        rewrite = ("**摘要**\n報告指出，該項目避免了入侵拉姆薩爾濕地及周邊生態敏感地區，"
                   "因此不會造成影響。[r, Ch.14, p.14-13]\n\n"
                   "**主要發現**\n- 項目避免了該濕地，亦避開了附近的生態敏感地區。"
                   "[r, Ch.14, p.14-13]")
        self.assertGreater(_problem_score(original, ev, "zh-Hant"),
                           _problem_score(rewrite, ev, "zh-Hant"))
        # A rewrite that is worse is still rejected.
        worse = ("**摘要**\n報告指出，該項目避免了入侵生態敏感地區，報告亦指出項目"
                 "避開了附近的生態敏感地區。[r, Ch.14, p.14-13]\n\n"
                 "**主要發現**\n- 項目避免了該湿地，亦避開附近的生態敏感地區。"
                 "[r, Ch.14, p.14-13]")
        self.assertGreaterEqual(_problem_score(worse, ev, "zh-Hant"),
                                _problem_score(original, ev, "zh-Hant"))

    def test_section_number_and_leading_citation_cleanup(self):
        raw = "- 14.6.1.1 引用[aeiar-276-2026, Ch.14, p.14-13]：項目避免了入侵。"
        cleaned = _move_leading_citations(_strip_section_numbers(raw))
        self.assertTrue(cleaned.startswith("- 項目避免了"))
        self.assertTrue(cleaned.rstrip().endswith("[aeiar-276-2026, Ch.14, p.14-13]"))

    def test_chinese_mapping_is_now_the_fallback(self):
        """When the Chinese summaries cannot answer, the English topic map still
        applies and the English ORIGINAL is returned, labelled as English."""
        r = ask("復耕安排係點？", "zh-Hant")
        self.assertFalse(r["refused"])
        self.assertEqual(r["gate"]["status"], "mapped")
        self.assertTrue(r["translation_applied"])
        self.assertEqual(r["evidence_lang"], "en")
        self.assertGreaterEqual(len(r["evidence"]), 1)
        for card in r["evidence"]:
            self.assertEqual(card["excerpt_lang"], "en")
            self.assertEqual(card["doc_kind"], "chapter")

    def test_chinese_unsupported_query_is_refused(self):
        """Questions with no passage in either language are refused rather than
        answered from absent or generic word overlap."""
        for query in ["股票市場走勢", "房價", "這個項目會不會影響房價"]:
            with self.subTest(query=query):
                r = ask(query, "zh-Hant")
                self.assertTrue(r["refused"])
                self.assertEqual(r["gate"]["status"], "chinese_unsupported")
                self.assertFalse(r["translation_applied"])
                self.assertEqual(len(r["evidence"]), 0)
                self.assertEqual(r["message"], "抱歉，我無法回答此問題。")

    # -- Synthesis -------------------------------------------------------
    def test_synthesis_success_with_valid_citations(self):
        """A mocked Ollama response with valid citations is accepted."""
        from unittest.mock import patch, MagicMock
        mock_answer = (
            "The report recommends temporary noise barriers [aeiar-276-2026, Ch.4, p.4-28]."
        )
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "done": True,
            "message": {"content": mock_answer},
            "eval_count": 45,
        }).encode()
        # Force the local provider so an exported OPENROUTER_API_KEY in the
        # developer's shell cannot change which code path this test exercises.
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}), \
                patch("urllib.request.urlopen", return_value=mock_resp):
            r = ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        self.assertIsNotNone(r["synthesis"])
        self.assertEqual(r["synthesis"]["answer"], mock_answer)
        self.assertEqual(r["synthesis"]["model"], OLLAMA_MODEL)
        self.assertEqual(r["synthesis"]["tokens_used"], 45)
        # Evidence must still be present unchanged
        self.assertGreaterEqual(len(r["evidence"]), 1)

    def test_synthesis_rejected_when_citations_invalid(self):
        """A response citing evidence not in the retrieved set is discarded.

        The invented citation must not reach the reader, but the answer must not
        vanish either: with no valid model answer the extractive fallback still
        puts a summary above the sources.
        """
        from unittest.mock import patch, MagicMock
        mock_answer = (
            "The report says something [aeiar-999-9999, Ch.99, p.99-99]."
        )
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "done": True,
            "message": {"content": mock_answer},
            "eval_count": 30,
        }).encode()
        with patch("urllib.request.urlopen", return_value=mock_resp):
            r = ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        self.assertEqual(r["synthesis"]["model"], "evidence-summary")
        self.assertNotIn("aeiar-999-9999", r["synthesis"]["answer"])
        self.assertGreaterEqual(len(r["evidence"]), 1)

    def test_synthesis_fallback_on_ollama_failure(self):
        """When Ollama is unreachable, an evidence-summary fallback is provided."""
        from unittest.mock import patch
        with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
            r = ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        self.assertIsNotNone(r["synthesis"])
        self.assertEqual(r["synthesis"]["model"], "evidence-summary")
        self.assertGreaterEqual(len(r["evidence"]), 1)

    def test_synthesis_falls_back_on_empty_response(self):
        """An empty model response yields the extractive summary, not a blank."""
        from unittest.mock import patch, MagicMock
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "done": True,
            "message": {"content": "  "},
            "eval_count": 0,
        }).encode()
        with patch("urllib.request.urlopen", return_value=mock_resp):
            r = ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        self.assertEqual(r["synthesis"]["model"], "evidence-summary")

    def test_synthesis_skipped_when_refused(self):
        """Retrieval refusal must not call the LLM at all."""
        from unittest.mock import patch
        with patch("urllib.request.urlopen") as mock_urlopen:
            r = ask("geothermal", "en")
        self.assertTrue(r["refused"])
        self.assertEqual(len(r["evidence"]), 0)
        self.assertIsNone(r.get("synthesis"))
        mock_urlopen.assert_not_called()

    def test_synthesis_prompt_building(self):
        """_build_synthesis_prompt produces messages with evidence and lang directive."""
        evidence = [
            {"report_id": "r1", "chapter": 1, "page_label": "1-1", "excerpt": "Excerpt A"},
            {"report_id": "r2", "chapter": 2, "page_label": "2-2", "excerpt": "Excerpt B"},
        ]
        msgs = _build_synthesis_prompt("What is X?", "zh-Hant", evidence)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertIn("Traditional Chinese", msgs[0]["content"])
        self.assertIn("Excerpt A", msgs[1]["content"])
        self.assertIn("Excerpt B", msgs[1]["content"])
        self.assertIn("[r1, Ch.1, p.1-1]", msgs[1]["content"])

    def test_validate_synthesis_accepts_valid_citations(self):
        """Citations that match retrieved evidence pass validation."""
        evidence = [
            {"report_id": "r1", "chapter": 1, "page_label": "1-1"},
        ]
        ok = _validate_synthesis("See [r1, Ch.1, p.1-1] for details.", evidence)
        self.assertTrue(ok)

    def test_validate_synthesis_rejects_invalid_citations(self):
        """Citations not in the evidence set fail validation."""
        evidence = [
            {"report_id": "r1", "chapter": 1, "page_label": "1-1"},
        ]
        bad = _validate_synthesis("See [r99, Ch.9, p.9-9] for details.", evidence)
        self.assertFalse(bad)

    # -- Catalogue / Report expansion ------------------------------------
    def test_all_8_reports_in_registry(self):
        """All 8 core_nm reports are present in REPORTS_BY_ID."""
        expected = {
            "aeiar-276-2026", "aeiar-271-2025", "aeiar-274-2026",
            "aeiar-261-2024", "aeiar-175-2013", "aeiar-176-2013",
            "aeiar-203-2016", "aeiar-215-2017",
        }
        self.assertEqual(set(REPORTS_BY_ID.keys()), expected)

    def test_reports_have_audit_decision(self):
        """Every report has an audit_decision field."""
        for rid, r in REPORTS_BY_ID.items():
            self.assertIn("audit_decision", r, f"{rid} missing audit_decision")

    def test_aeiar_274_is_needs_review(self):
        """AEIAR-274/2026 is correctly marked needs_review."""
        r = REPORTS_BY_ID["aeiar-274-2026"]
        self.assertEqual(r["audit_decision"], "needs_review")

    def test_other_7_are_verified_core_nm(self):
        """The other 7 reports are verified_core_nm."""
        for rid, r in REPORTS_BY_ID.items():
            if rid == "aeiar-274-2026":
                continue
            self.assertEqual(r["audit_decision"], "verified_core_nm", f"{rid} should be verified_core_nm")

    def test_new_reports_are_searchable(self):
        """Queries retrieve evidence from newly added reports."""
        r = ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        report_ids = {c["report_id"] for c in r["evidence"]}
        # Should include at least one of the new reports
        new_reports = {"aeiar-261-2024", "aeiar-215-2017"}
        self.assertTrue(
            bool(report_ids & new_reports),
            f"Expected evidence from new reports, got {report_ids}"
        )

    def test_scoped_search_on_new_report(self):
        """Scoped search works on newly added reports."""
        r = ask("ecology", "en", report_id="aeiar-261-2024")
        self.assertFalse(r["refused"])
        for card in r["evidence"]:
            self.assertEqual(card["report_id"], "aeiar-261-2024")

    def test_chapter_urls_cover_all_reports(self):
        """CHAPTER_URLS contains entries for all 8 reports."""
        self.assertEqual(len(CHAPTER_URLS), 8)
        for rid in REPORTS_BY_ID:
            self.assertIn(rid, CHAPTER_URLS)

    # -- Glossary --------------------------------------------------------
    def test_glossary_noise_contour_map_en(self):
        """A definitional query in English returns the glossary entry."""
        r = ask("What is a noise contour map?", "en")
        self.assertFalse(r["refused"])
        self.assertIn("glossary", r)
        self.assertEqual(r["glossary"]["term"], "noise contour map")
        self.assertEqual(r["glossary"]["source"], "glossary")
        self.assertIn("diagram", r["glossary"]["definition"].lower())
        # Evidence should also be present (report-specific context)
        self.assertGreaterEqual(len(r["evidence"]), 1)

    def test_glossary_noise_barrier_zh(self):
        """A definitional query in Chinese returns the glossary entry."""
        r = ask("甚麼是噪音屏障？", "zh-Hant")
        self.assertFalse(r["refused"])
        self.assertIn("glossary", r)
        self.assertEqual(r["glossary"]["term"], "noise barrier")
        self.assertIn("屏障", r["glossary"]["definition"])

    def test_glossary_hydrological_assessment_en(self):
        """A definitional query for hydrological assessment returns glossary."""
        r = ask("Explain hydrological assessment", "en")
        self.assertFalse(r["refused"])
        self.assertIn("glossary", r)
        self.assertEqual(r["glossary"]["term"], "hydrological assessment")

    def test_glossary_not_returned_for_non_definition_query(self):
        """A non-definition query does not include a glossary entry."""
        r = ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        self.assertNotIn("glossary", r)

    def test_glossary_unknown_term_returns_evidence_only(self):
        """A definition query for an unknown term falls back to evidence-only."""
        r = ask("What is a geotechnical survey?", "en")
        # Should not be refused (geotechnical is not in glossary but may have evidence)
        # If no evidence, it may be refused — that's acceptable
        if not r["refused"]:
            self.assertNotIn("glossary", r)

    # -- Chinese hydrological retrieval ----------------------------------
    def test_chinese_hydrological_assessment(self):
        """水文評估 prefers original Chinese evidence when it is indexed."""
        r = ask("水文評估", "zh-Hant")
        self.assertFalse(r["refused"], f"Should not be refused: {r.get('message')}")
        self.assertFalse(r["translation_applied"])
        self.assertEqual(r["gate"]["status"], "zh_original")
        self.assertEqual(r["evidence_lang"], "zh-Hant")
        self.assertGreaterEqual(len(r["evidence"]), 1)
        self.assertTrue(all(c["excerpt_lang"] == "zh-Hant" for c in r["evidence"]))

    # -- Retrieval filtering ---------------------------------------------
    def test_noise_contour_map_no_cultural_heritage_false_positive(self):
        """A noise-contour-map query should not return cultural-heritage passages
        as top evidence.  The chapter-relevance filter should deprioritise them."""
        r = ask("What is a noise contour map?", "en")
        self.assertFalse(r["refused"])
        for card in r["evidence"]:
            ch_title = (card.get("chapter_title") or "").lower()
            # Cultural heritage chapter should not appear in top evidence
            self.assertNotIn("cultural", ch_title,
                f"Cultural heritage passage returned for noise query: {card['citation']}")

    def test_noise_query_retains_noise_chapter_evidence(self):
        """A noise query must still return genuine noise-chapter evidence."""
        r = ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        noise_chapters = [c for c in r["evidence"]
                          if "noise" in (c.get("chapter_title") or "").lower()]
        self.assertGreaterEqual(len(noise_chapters), 1,
            "Noise query should return at least one noise-chapter evidence card")

    # -- Expanded 54-term glossary -----------------------------------------
    def test_glossary_total_inventory_size(self):
        """Inventory should contain 54 unique canonical terms (40-60 target)."""
        self.assertEqual(_glossary_total_entries(), 54)

    def test_glossary_acronyms_en(self):
        """Common EIA acronyms (NSR, ASR, EM&A, PM2.5, LVIA) return glossary entries."""
        acronym_to_canonical = {
            "NSR": "noise sensitive receiver",
            "ASR": "air sensitive receiver",
            "EM&A": "ema",
            "PM2.5": "pm",
            "LVIA": "lvia",
            "dB(A)": "db a",
        }
        for acronym, expected_canonical in acronym_to_canonical.items():
            r = ask(f"What is {acronym}?", "en")
            self.assertIn("glossary", r,
                f"What is {acronym}? should return a glossary entry")
            self.assertEqual(r["glossary"]["source"], "glossary")
            # canonical_term is derived from the entry key
            self.assertEqual(
                r["glossary"].get("canonical_term", "").lower(),
                expected_canonical.lower(),
                f"What is {acronym}? canonical_term mismatch",
            )
            # Source metadata should be present
            self.assertTrue(r["glossary"].get("source_url", "").startswith("http"))

    def test_glossary_traditional_chinese(self):
        """Traditional Chinese queries for known terms return Chinese glossary."""
        for q, expected_canonical_key in [
            ("甚麼是噪音敏感受體？", "noise_sensitive_receiver"),
            ("用簡單中文解釋空氣質素指標", "air_quality_objective"),
            ("解釋風水", "fung_shui"),
            ("甚麼是環境監察及審核？", "ema"),
            ("甚麼是緩解措施？", "mitigation_measures"),
        ]:
            r = ask(q, "zh-Hant")
            self.assertIn("glossary", r, f"{q!r} should return a glossary entry")
            self.assertEqual(r["glossary"]["key"], expected_canonical_key,
                f"{q!r} returned key={r['glossary']['key']}")
            # Definition text should contain Chinese
            defn = r["glossary"]["definition"]
            self.assertTrue(any("\u4e00" <= c <= "\u9fff" for c in defn),
                f"zh-Hant definition should contain Chinese: {defn!r}")
            # display_term should be a Chinese alias
            self.assertTrue(
                any("\u4e00" <= c <= "\u9fff" for c in r["glossary"]["display_term"]),
                f"display_term should be Chinese: {r['glossary']['display_term']!r}",
            )

    def test_glossary_category_and_source_metadata(self):
        """Glossary entries expose category, source_name, source_url, source_section."""
        r = ask("What is a noise barrier?", "en")
        self.assertIn("glossary", r)
        g = r["glossary"]
        self.assertEqual(g["category"], "noise")
        self.assertIn("source_name", g)
        self.assertIn("source_url", g)
        self.assertIn("source_section", g)
        self.assertTrue(g["source_url"].startswith("https://"))

    def test_glossary_distinct_from_evidence(self):
        """Glossary (source='glossary') is clearly distinct from evidence cards."""
        r = ask("What is an NSR?", "en")
        self.assertIn("glossary", r)
        self.assertIn("evidence", r)
        # Glossary has source='glossary' and a 'key' field
        self.assertEqual(r["glossary"]["source"], "glossary")
        self.assertIn("key", r["glossary"])
        # Evidence cards have 'citation' field, not 'key'
        if r["evidence"]:
            self.assertIn("citation", r["evidence"][0])
            self.assertNotIn("key", r["evidence"][0])

    def test_project_specific_question_bypasses_glossary(self):
        """A project-specific question does NOT get a generic glossary answer."""
        r = ask("What NSRs are affected by this project?", "en")
        # Glossary should NOT be auto-returned for project-specific queries
        if "glossary" in r:
            # If glossary is present, evidence should also be present
            self.assertGreaterEqual(len(r.get("evidence", [])), 1,
                "Project-specific question should always show evidence alongside glossary")

    def test_glossary_unsupported_term_refused(self):
        """A question about a term not in the glossary is not refused just
        because the term is unsupported; the corpus may still have evidence."""
        # "carbon footprint" is not in glossary but is in EIA corpora
        r = ask("What is a carbon footprint?", "en")
        # Should not be refused for glossary reasons; either refused by
        # retrieval (all_oov) or by no-results — but no glossary returned
        self.assertNotIn("glossary", r)

    def test_glossary_no_fabricated_citation(self):
        """Glossary entries NEVER include a 'citation' field; only evidence cards do."""
        r = ask("What is LVIA?", "en")
        self.assertIn("glossary", r)
        g = r["glossary"]
        # Glossary must NOT carry a report-style citation
        self.assertNotIn("citation", g,
            "Glossary must not fabricate report citations")
        # Glossary must NOT carry a 'pdf_page_index' (that's evidence-only)
        self.assertNotIn("pdf_page_index", g)
        # Glossary must have source='glossary'
        self.assertEqual(g["source"], "glossary")

    # -- Mixed-language input with interface-based output ------------------
    def test_mixed_lang_zh_interface_zh_question(self):
        """zh-Hant interface + zh-Hant question → zh-Hant response."""
        r = ask("甚麼是噪音敏感受體？", "zh-Hant")
        self.assertFalse(r["refused"])
        self.assertIn("glossary", r)
        self.assertEqual(r["lang"], "zh-Hant")
        # Definition should be in Traditional Chinese
        defn = r["glossary"]["definition"]
        self.assertTrue(any("\u4e00" <= c <= "\u9fff" for c in defn))

    def test_mixed_lang_zh_interface_en_term_question(self):
        """zh-Hant interface + English terminology question → zh-Hant response."""
        r = ask("What is an NSR?", "zh-Hant")
        self.assertFalse(r["refused"])
        self.assertIn("glossary", r)
        self.assertEqual(r["lang"], "zh-Hant")
        # Definition should be in Traditional Chinese (interface language)
        defn = r["glossary"]["definition"]
        self.assertTrue(any("\u4e00" <= c <= "\u9fff" for c in defn),
            f"Expected zh-Hant definition, got: {defn!r}")
        # Evidence should also be present (English question went through BM25)
        self.assertGreaterEqual(len(r["evidence"]), 1)

    def test_mixed_lang_zh_interface_en_project_question(self):
        """zh-Hant interface + English project question → zh-Hant response with evidence."""
        r = ask("What NSRs are affected by this project?", "zh-Hant")
        self.assertFalse(r["refused"])
        self.assertEqual(r["lang"], "zh-Hant")
        # Should get evidence, not just glossary (project-specific bypass)
        self.assertGreaterEqual(len(r["evidence"]), 1)
        # Message should be in zh-Hant
        self.assertIn("以下是", r["message"])

    def test_mixed_lang_en_interface_en_question(self):
        """en interface + English question → en response."""
        r = ask("What is PM2.5?", "en")
        self.assertFalse(r["refused"])
        self.assertIn("glossary", r)
        self.assertEqual(r["lang"], "en")
        # Definition should be in English (no Chinese characters)
        defn = r["glossary"]["definition"]
        self.assertFalse(any("\u4e00" <= c <= "\u9fff" for c in defn),
            f"Expected English definition, got Chinese: {defn!r}")

    def test_mixed_lang_en_interface_zh_term_question(self):
        """en interface + Traditional Chinese terminology question → en response."""
        r = ask("甚麼是噪音敏感受體？", "en")
        self.assertFalse(r["refused"])
        self.assertIn("glossary", r)
        self.assertEqual(r["lang"], "en")
        # Definition should be in English (interface language)
        defn = r["glossary"]["definition"]
        self.assertFalse(any("\u4e00" <= c <= "\u9fff" for c in defn),
            f"Expected English definition, got Chinese: {defn!r}")
        # Evidence should also be present (Chinese question mapped to English terms)
        self.assertGreaterEqual(len(r["evidence"]), 1)

    def test_mixed_lang_en_interface_zh_project_question(self):
        """en interface + Traditional Chinese project question → en response with evidence."""
        r = ask("這個項目對噪音敏感受體有什麼影響？", "en")
        self.assertFalse(r["refused"])
        self.assertEqual(r["lang"], "en")
        # Should get evidence (Chinese question mapped to English terms)
        self.assertGreaterEqual(len(r["evidence"]), 1)
        # Message should be in English
        self.assertIn("Here are", r["message"])

    def test_mixed_lang_mixed_input(self):
        """Mixed-language input (English acronyms + Chinese text) works."""
        r = ask("NSR 是甚麼？", "zh-Hant")
        self.assertFalse(r["refused"])
        self.assertIn("glossary", r)
        # Response language follows interface
        defn = r["glossary"]["definition"]
        self.assertTrue(any("\u4e00" <= c <= "\u9fff" for c in defn))

    def test_mixed_lang_cjk_en_project_retrieval(self):
        """Mixed CJK+EN project question with English technical terms must
        retrieve EIA evidence, not fall back to glossary-only."""
        r = ask("這個項目的NSR有哪些？", "en")
        self.assertFalse(r["refused"])
        self.assertEqual(r["lang"], "en")
        # Must have evidence (the English BM25 gate extracts 'nsr')
        self.assertGreaterEqual(len(r["evidence"]), 1,
            "Mixed CJK+EN project question should retrieve evidence")
        # Glossary may also be present (NSR is in glossary)
        self.assertIn("glossary", r)

    def test_mixed_lang_cjk_en_project_retrieval_pm25(self):
        """Mixed CJK+EN project question with PM2.5 must retrieve evidence."""
        r = ask("這個項目對PM2.5有什麼影響？", "en")
        self.assertFalse(r["refused"])
        self.assertEqual(r["lang"], "en")
        self.assertGreaterEqual(len(r["evidence"]), 1,
            "Mixed CJK+EN project question should retrieve evidence")
        self.assertIn("glossary", r)

    def test_mixed_lang_unsupported_still_refused(self):
        """Unsupported questions still follow existing refusal regardless of interface lang."""
        # English OOV term
        r = ask("geothermal", "zh-Hant")
        self.assertTrue(r["refused"], f"Expected refusal for OOV term, got: {r['gate']['status']}")
        self.assertEqual(r["gate"]["status"], "all_oov")
        # Chinese-only question with no topic map match and no glossary entry
        r = ask("甚麼是地質？", "en")
        self.assertTrue(r["refused"], f"Expected refusal for unsupported Chinese, got: {r['gate']['status']}")
        self.assertEqual(r["gate"]["status"], "chinese_unsupported")


# ------------------------------------------------------------------ main

EXACT_REFUSAL_EN = "Sorry, I cannot answer this question"
EXACT_REFUSAL_ZH = "抱歉，我無法回答此問題。"


class AnswerabilityTest(unittest.TestCase):
    """The report may contain the words of a question without the answer.

    Each case below is a measured failure of keyword retrieval, not a
    hypothetical: "How much does the project cost?" returned three passages
    about piling methods, and "What is the capital of France?" returned
    "Capital Works" plus a hazard table listing France.
    """

    def _ask_offline(self, question, lang="en"):
        """ask() without the LLM, so the suite stays fast and deterministic."""
        from unittest.mock import patch
        with patch.object(sys.modules[__name__], "_synthesize", return_value=None):
            return ask(question, lang)

    # -- required case 1: project cost is not stated -----------------------
    def test_cost_question_is_refused(self):
        r = self._ask_offline("How much does the project cost?")
        self.assertTrue(r["refused"])
        self.assertEqual(r["message"], EXACT_REFUSAL_EN)
        self.assertEqual(r["evidence"], [])
        self.assertEqual(r["answerability"]["intent"], "money")
        self.assertEqual(r["answerability"]["reason"], "no_money_in_evidence")

    def test_cost_question_refused_in_chinese(self):
        r = self._ask_offline("這個項目造價多少？", "zh-Hant")
        self.assertTrue(r["refused"])
        self.assertEqual(r["message"], EXACT_REFUSAL_ZH)
        self.assertEqual(r["evidence"], [])

    # -- required case 2: unrelated question -------------------------------
    def test_unrelated_question_is_refused(self):
        r = self._ask_offline("What is the capital of France?")
        self.assertTrue(r["refused"])
        self.assertEqual(r["message"], EXACT_REFUSAL_EN)
        self.assertEqual(r["evidence"], [])
        self.assertEqual(r["answerability"]["reason"],
                         "evidence_does_not_cover_question")

    def test_unrelated_question_refused_in_chinese(self):
        r = self._ask_offline("法國首都是哪裡？", "zh-Hant")
        self.assertTrue(r["refused"])
        self.assertEqual(r["message"], EXACT_REFUSAL_ZH)
        self.assertEqual(r["evidence"], [])

    # -- required case 3: answerable question still answered ----------------
    def test_answerable_question_is_not_refused(self):
        r = self._ask_offline("What noise mitigation measures are proposed?")
        self.assertFalse(r["refused"])
        self.assertGreaterEqual(len(r["evidence"]), 1)
        card = r["evidence"][0]
        self.assertIn(card["page_label"], card["citation"])
        self.assertTrue(card["source_url"].startswith("https://www.epd.gov.hk/"))

    def test_answerable_question_answered_in_chinese(self):
        r = self._ask_offline("噪音會唔會影響附近居民？", "zh-Hant")
        self.assertFalse(r["refused"])
        self.assertGreaterEqual(len(r["evidence"]), 1)
        for card in r["evidence"]:
            self.assertEqual(card["excerpt_lang"], "zh-Hant")

    # -- required case 4: generic "project" without the requested fact -----
    def test_generic_project_word_does_not_imply_an_answer(self):
        # Every retrieved page contains "project" and "cost"; none states what
        # the project costs.
        r = self._ask_offline("How much does the project cost?")
        self.assertTrue(r["refused"])
        self.assertEqual(r["evidence"], [])

    def test_duration_question_refused_when_no_duration_stated(self):
        for q in ("What is the project duration?", "How long will construction take?"):
            with self.subTest(q=q):
                r = self._ask_offline(q)
                self.assertTrue(r["refused"])
                self.assertEqual(r["message"], EXACT_REFUSAL_EN)

    def test_duration_question_refused_in_chinese(self):
        r = self._ask_offline("工程為期多久？", "zh-Hant")
        self.assertTrue(r["refused"])
        self.assertEqual(r["message"], EXACT_REFUSAL_ZH)

    # -- the gate must not become a topic filter ---------------------------
    def test_valid_topic_questions_are_not_refused(self):
        """A regression guard: the gate must only reject, never over-reject."""
        for q in ("noise barrier", "wetland compensation", "air quality impact",
                  "spoonbill", "dissolved oxygen", "EM&A programme",
                  "landfill gas", "cultural heritage",
                  "What is the black-faced spoonbill?",
                  "When will construction commence?",
                  "How much noise will the project generate?"):
            with self.subTest(q=q):
                self.assertFalse(self._ask_offline(q)["refused"])

    def test_valid_chinese_topic_questions_are_not_refused(self):
        for q in ("噪音", "生態", "水質", "廢物", "景觀", "文化遺產",
                  "施工期間的監測安排"):
            with self.subTest(q=q):
                self.assertFalse(self._ask_offline(q, "zh-Hant")["refused"])

    # -- module-level unit tests -------------------------------------------
    def test_intent_detection(self):
        cases = [
            ("How much does the project cost?", "en", "money"),
            ("What is the total budget?", "en", "money"),
            ("How long will construction take?", "en", "duration"),
            ("What is the project duration?", "en", "duration"),
            ("When will construction commence?", "en", "date"),
            ("What noise mitigation measures are proposed?", "en", None),
            ("How much noise will the project generate?", "en", None),
            ("這個項目造價多少？", "zh-Hant", "money"),
            ("工程為期多久？", "zh-Hant", "duration"),
            # 「施工期間」 (during construction) is not a duration question
            ("施工期間的監測安排", "zh-Hant", None),
        ]
        for q, lang, want in cases:
            with self.subTest(q=q):
                self.assertEqual(A.detect_intent(q, lang), want)

    def test_datum_check(self):
        # A cost clause with no amount is not an answer.
        self.assertFalse(A.has_datum(
            "piling works will incur much higher construction cost", "money"))
        # A currency amount next to a cost word is.
        self.assertTrue(A.has_datum(
            "the estimated construction cost is HK$1,200 million", "money"))
        # A bare population figure is not a sum of money.
        self.assertFalse(A.has_datum("a population of 8.4 million by 2030", "money"))
        self.assertFalse(A.has_datum(
            "these are long-term operational impacts", "duration"))
        self.assertTrue(A.has_datum(
            "the construction phase will last 48 months", "duration"))
        # 2024 年 is a calendar year, not a duration of 2024 years.
        self.assertFalse(A.has_datum(
            "本研究於 2024 年展開", "duration", "zh-Hant"))

    def test_evidence_coverage(self):
        cards = [{"matched_terms": ["capital"]},
                 {"matched_terms": ["france"]}]
        # No single card carries both words of "capital of France".
        self.assertEqual(A.evidence_coverage(cards, ["capital", "france"]), 1)
        self.assertEqual(A.required_coverage(2), 2)
        self.assertLess(A.evidence_coverage(cards, ["capital", "france"]),
                        A.required_coverage(2))
        # One card that does carry them together passes.
        cards = [{"matched_terms": ["noise", "barrier"]}]
        self.assertGreaterEqual(A.evidence_coverage(cards, ["noise", "barrier"]),
                                A.required_coverage(2))
        # A long question needs half its terms, never fewer than two.
        self.assertEqual(A.required_coverage(7), 4)
        self.assertEqual(A.required_coverage(3), 2)
        self.assertEqual(A.required_coverage(1), 1)

    def test_gate_record_is_attached_to_every_answer(self):
        r = self._ask_offline("noise barrier")
        self.assertIn("answerability", r)
        self.assertTrue(r["answerability"]["answerable"])


def main():
    # argparse only for non-test invocations
    if "--test" in sys.argv:
        sys.argv = [sys.argv[0]]
        unittest.main(module=sys.modules[__name__], exit=True, verbosity=2)

    ap = argparse.ArgumentParser(description="NORTHWISE MVP backend")
    ap.add_argument("--port", type=int,
                    default=int(os.environ.get("PORT", "8080")))
    ap.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    args = ap.parse_args()

    class ReusableTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with ReusableTCPServer((args.host, args.port), AskHandler) as httpd:
        print(f"NORTHWISE MVP running at http://{args.host}:{args.port}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
