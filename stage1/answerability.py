#!/usr/bin/env python3
"""Answerability gate — can the retrieved evidence actually answer the question?

Retrieval answers "which passages share vocabulary with the question?". That is
not the same question as "which passages answer it". A page that mentions
"construction cost" while comparing piling methods does not state what the
project costs, and a hazard table that happens to list "France" does not make
the report a source on French geography. Both were measured failures: the
former returned three passages and the latter returned three passages, none of
which contained the requested information.

This module adds the missing step. Before anything is synthesised it decides
whether the evidence contains the *kind of information* the question asks for.

Three checks, each of which can only ever reduce confidence:

1. Intent detection
   What is being asked for — a monetary amount, a duration, a date, a count —
   or just a topic?

2. Datum verification
   If the question asks for an amount / duration / date, the evidence must
   actually contain one, and it must sit near the thing it describes. A bare
   "HK$1M" next to "billing account" is not a project cost.

3. Evidence coverage
   Does a single returned passage carry the question's words *together*? A
   card that matches one word out of four ("2022" from "Who won the 2022 World
   Cup?") shares vocabulary, not topic. Coverage is measured per passage, not
   across the corpus, because the corpus is not what gets shown.

Nothing here invents an answer, relaxes citation validation, or rewrites
retrieval scores. It is a filter on what may be shown, not a re-ranker.

Standard library only.
"""

import re

# --------------------------------------------------------------------- intents
# Question phrasing that asks for a specific *kind* of fact. Ordered: the first
# match wins, because "how much does construction cost" is a money question
# even though it mentions construction.

_EN_MONEY_Q = re.compile(
    r"\b(?:project|construction|capital|total|overall|estimated)\s+costs?\b"
    r"|\bcosts?\s+of\s+(?:the|this)\s+(?:project|works?|scheme)\b"
    r"|\bbudget(?:ed)?\b"
    r"|\bexpenditure\b"
    r"|\bhow\s+much\s+(?:money|funding|will\s+it\s+cost|does\s+it\s+cost)\b"
    r"|\bhow\s+much\s+(?:will|does|do|would|did)\b[^.?!]{0,40}?\bcosts?\b"
    r"|\bprice\s+of\s+(?:the|this)\b",
    re.I,
)

_EN_DURATION_Q = re.compile(
    r"\bhow\s+long\b"
    r"|\b(?:project|construction|works?|overall)\s+duration\b"
    r"|\bduration\s+of\s+(?:the\s+)?(?:project|construction|works?)\b"
    r"|\bconstruction\s+period\b"
    r"|\btime\s?frame\b"
    r"|\bhow\s+many\s+(?:months|years|weeks)\b",
    re.I,
)

_EN_DATE_Q = re.compile(
    r"\bwhen\s+(?:will|does|do|did|is|are|would)\b"
    r"|\bwhat\s+year\b"
    r"|\bwhich\s+year\b"
    r"|\b(?:start|commencement|completion)\s+date\b",
    re.I,
)

# "how many <noun>" — the noun is captured so the check can require a number
# near *that* noun rather than anywhere on the page.
_EN_COUNT_Q = re.compile(
    r"\bhow\s+many\s+([a-z][a-z\-]*(?:\s+[a-z][a-z\-]*){0,3})",
    re.I,
)

_ZH_MONEY_Q = re.compile(r"造價|成本|費用|預算|開支|經費|幾多錢|多少錢|幾錢|價格")
# Deliberately narrow. 「工期」 is a substring of 「施工期間」(during
# construction), which is a monitoring/arrangement question, not a duration
# question — measured false positive. The negative lookahead keeps the two
# apart.
_ZH_DURATION_Q = re.compile(r"為期|多久|多長|工期(?!間)|需時|幾耐")
_ZH_DATE_Q = re.compile(r"何時|幾時|哪一年|邊一年|年份|開始日期|完成日期")
_ZH_COUNT_Q = re.compile(r"幾多個|多少個|幾多|多少")

_INTENT_ORDER = ("money", "duration", "date", "count")

# ------------------------------------------------------------------ datum forms
# A monetary amount. The currency symbol is mandatory: bare "1.4 million" is a
# population or a volume in these reports, never a sum of money.
_EN_MONEY = re.compile(
    r"(?:HK|US|RMB|CNY)?\$\s?\d[\d,\.]*"
    r"|\bHKD\s?\d[\d,\.]*"
    r"|\b\d[\d,\.]*\s*(?:million|billion)\s+(?:dollars|HKD|Hong Kong dollars)\b",
    re.I,
)

# An explicit duration. "long-term" and "Long Valley" are not durations.
_EN_DURATION = re.compile(
    r"\b\d{1,3}(?:\.\d+)?\s*(?:calendar\s+)?(?:months?|years?|weeks?|days?)\b"
    r"|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
    r"|fifteen|eighteen|twenty|twenty-four|thirty|thirty-six)\s+"
    r"(?:months?|years?|weeks?)\b"
    r"|\b\d{1,3}\s*[-–]\s*\d{1,3}\s*(?:months?|years?)\b",
    re.I,
)

_EN_DATE = re.compile(r"\b(?:19|20)\d{2}\b")

_EN_COUNT = re.compile(r"\b\d[\d,\.]*\b")

_ZH_MONEY = re.compile(
    r"\d[\d,\.]*\s*(?:萬|億)?\s*(?:港元|元|圓)"
    r"|(?:港幣|港元|人民幣)\s*\d[\d,\.]*"
    r"|\$\s*\d",
)

_ZH_DURATION = re.compile(
    # 1-3 digits only: "2024 年" is a calendar year, not a duration of 2024
    # years. Chinese numerals are allowed ("兩個月", "一年").
    r"(?<![\d])(?:\d{1,3}|[一二三四五六七八九十兩]+)\s*個?\s*(?:月|年|星期)"
    r"|為期\s*(?:\d{1,3}|[一二三四五六七八九十兩]+)"
)

_ZH_DATE = re.compile(r"(?:19|20)\d{2}\s*年")

# Words that make a datum *about* the project rather than incidental. A money
# amount 300 characters away from any of these is not an answer to "what does
# the project cost".
_EN_MONEY_CONTEXT = re.compile(
    r"\b(?:cost|costs|budget|estimate|estimated|expenditure|price|works?|"
    r"construction|project|contract|scheme)\b",
    re.I,
)
_EN_DURATION_CONTEXT = re.compile(
    r"\b(?:construction|works?|phase|programme|program|project|commissioning|"
    r"operation|implementation|contract)\b",
    re.I,
)
_EN_DATE_CONTEXT = re.compile(
    r"\b(?:construction|works?|commence|commencement|start|complete|completion|"
    r"commission|project|implementation|schedule)\b",
    re.I,
)
_ZH_MONEY_CONTEXT = re.compile(r"成本|費用|造價|預算|開支|工程|項目|合約|建造")
_ZH_DURATION_CONTEXT = re.compile(r"工程|施工|建造|營運|合約|階段")
_ZH_DATE_CONTEXT = re.compile(r"工程|施工|建造|項目|展開|開始|完成|營運|時間")

_DATUM_WINDOW = 140  # characters, for money: a cost clause can be long
_DURATION_WINDOW = 60  # tighter: a duration belongs next to what it times
# Chinese is denser: 「工程」 appears in almost every sentence, so a wide
# window lets an unrelated "為期兩個月" borrow it. Require adjacency.
_ZH_DURATION_WINDOW = 15
_DATE_WINDOW = 100


# ------------------------------------------------------------------- detection

def detect_intent(question: str, query_lang: str = "en") -> str | None:
    """Return the kind of fact the question asks for, or None for a topic query.

    Only explicit fact-seeking phrasing counts. "How much noise" is a topic
    question about noise levels, not a question about money.
    """
    if query_lang == "zh-Hant":
        if _ZH_MONEY_Q.search(question):
            return "money"
        if _ZH_DURATION_Q.search(question):
            return "duration"
        if _ZH_DATE_Q.search(question):
            return "date"
        if _ZH_COUNT_Q.search(question):
            return "count"
        return None

    if _EN_MONEY_Q.search(question):
        return "money"
    if _EN_DURATION_Q.search(question):
        return "duration"
    if _EN_DATE_Q.search(question):
        return "date"
    if _EN_COUNT_Q.search(question):
        return "count"
    return None


def count_noun(question: str) -> str | None:
    """The noun phrase after 'how many', used to locate the counted thing."""
    m = _EN_COUNT_Q.search(question)
    if not m:
        return None
    phrase = m.group(1).strip().lower()
    # Drop trailing auxiliaries the regex may have swallowed.
    phrase = re.split(r"\s+(?:are|is|will|were|was|do|does|did|would|have|has)\b",
                      phrase)[0].strip()
    return phrase or None


# ----------------------------------------------------------------- datum checks

def _near(text: str, datum: re.Pattern, context: re.Pattern,
          window: int = _DATUM_WINDOW) -> bool:
    """True if some datum match has a context word within `window` chars."""
    for m in datum.finditer(text):
        lo = max(0, m.start() - window)
        hi = min(len(text), m.end() + window)
        if context.search(text[lo:hi]):
            return True
    return False


def has_datum(text: str, intent: str, query_lang: str = "en",
              question: str = "") -> bool:
    """Does this passage contain the kind of fact the question asks for?"""
    if not text:
        return False
    zh = query_lang == "zh-Hant"

    if intent == "money":
        return _near(text, _ZH_MONEY if zh else _EN_MONEY,
                     _ZH_MONEY_CONTEXT if zh else _EN_MONEY_CONTEXT,
                     _DATUM_WINDOW)
    if intent == "duration":
        return _near(text, _ZH_DURATION if zh else _EN_DURATION,
                     _ZH_DURATION_CONTEXT if zh else _EN_DURATION_CONTEXT,
                     _ZH_DURATION_WINDOW if zh else _DURATION_WINDOW)
    if intent == "date":
        return _near(text, _ZH_DATE if zh else _EN_DATE,
                     _ZH_DATE_CONTEXT if zh else _EN_DATE_CONTEXT,
                     _DATE_WINDOW)
    if intent == "count":
        noun = count_noun(question)
        if not noun:
            # Cannot tell what is being counted; do not use this to refuse.
            return True
        # A count is only verifiable up to a point. Requiring a number beside
        # the exact phrase over-refuses ("how many sensitive receivers" is
        # written "receivers" on the page), and accepting a number anywhere
        # would prove nothing. The honest test is whether the thing being
        # counted is mentioned at all.
        head = noun.split()[-1]
        return head in text.lower()
    return True


# ------------------------------------------------------------ evidence coverage

def evidence_coverage(evidence: list[dict], terms: list[str]) -> int:
    """The largest number of `terms` carried by any single returned passage.

    Uses the `matched_terms` recorded at retrieval time, intersected with the
    question's own terms so an expanded synonym cannot inflate the count.
    """
    want = set(terms)
    best = 0
    for card in evidence:
        got = want.intersection(card.get("matched_terms") or [])
        if len(got) > best:
            best = len(got)
    return best


def required_coverage(n_terms: int) -> int:
    """How many of `n_terms` one passage must carry to count as on-topic.

    Half the terms, but never fewer than two: a passage sharing a single word
    with the question is a coincidence. Measured on 50 valid queries (all
    reached full coverage) and 20 natural-language questions (all reached at
    least this threshold), against questions such as "Who won the 2022 World
    Cup?", whose best passage matched one word of four.
    """
    if n_terms < 2:
        return 1
    return max(2, (n_terms + 1) // 2)


def _ascii_terms(terms: list[str]) -> bool:
    """True when every term is written in Latin script (i.e. not a CJK bigram).

    Digits count: "2022" is a term like any other, and "Who won the 2022 World
    Cup?" must not escape the coverage test merely because it contains a year.
    """
    return bool(terms) and all(t.isascii() for t in terms)


# --------------------------------------------------------------------- verdict

def assess(question: str, evidence: list[dict], query_terms: list[str],
           query_lang: str = "en", lang: str = "en",
           definitional: bool = False) -> dict:
    """Decide whether `evidence` answers `question`.

    Returns:
        {
          "answerable": bool,
          "reason": str,            # machine-readable, for the gate record
          "intent": str | None,
          "kept": [evidence...],    # cards that survived; [] when refused
          "checks": {...},          # measurements, for tests and debugging
        }

    `kept` is a subset of `evidence`: cards that do not carry the requested
    datum are dropped, so an unrelated passage is never shown next to a real
    answer merely to fill the card list.

    `definitional` marks a question the glossary already answers with a curated
    definition. Such a question is not a claim about a report page, so the
    passage-coverage test does not apply to it — measured on "What is a noise
    contour map?", whose definition the app holds, while no single passage
    carries the words "noise", "contour" and "map" together (the map itself is
    a figure, and figure captions are stripped from the index).
    """
    intent = detect_intent(question, query_lang)
    verdict = {"answerable": True, "reason": "ok", "intent": intent,
               "kept": list(evidence), "checks": {}}

    if not evidence:
        verdict.update(answerable=False, reason="no_evidence", kept=[])
        return verdict

    # 1. Datum verification — the strongest, most specific check.
    if intent in ("money", "duration", "date", "count"):
        kept = [c for c in evidence
                if has_datum(c.get("excerpt", ""), intent, query_lang, question)]
        verdict["checks"]["datum"] = {"intent": intent,
                                      "passed": len(kept),
                                      "considered": len(evidence)}
        if not kept:
            verdict.update(answerable=False,
                           reason=f"no_{intent}_in_evidence",
                           kept=[])
            return verdict
        verdict["kept"] = kept

    # 2. Evidence coverage — only for Latin-script query terms. Chinese query
    #    terms are character bigrams that overlap by construction, so a
    #    coverage ratio means something different there; the Chinese gate
    #    already enforces term coverage before retrieval.
    terms = [t for t in query_terms if t]
    if not definitional and _ascii_terms(terms):
        got = evidence_coverage(evidence, terms)
        need = required_coverage(len(terms))
        verdict["checks"]["coverage"] = {"matched": got, "required": need,
                                         "terms": len(terms)}
        if got < need:
            verdict.update(answerable=False,
                           reason="evidence_does_not_cover_question",
                           kept=[])
            return verdict

    # A question with one known word and one unknown one is refused earlier by
    # the retrieval gate (all_oov) or by coverage, so no separate check is
    # needed here.

    return verdict