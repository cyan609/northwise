# Answerability gate — evidence-based abstention

**Status:** implemented and tested 2026-10-18. Measured behaviour, not intent.

## The problem it fixes

Retrieval answers "which passages share vocabulary with the question?". That is
not the same question as "which passages answer it". Measured before the change,
with the real application:

| Question | Passages returned | What they actually said |
|---|---|---|
| `How much does the project cost?` | 3 | piling-method comparisons containing "much ... construction cost"; no cost stated |
| `What is the capital of France?` | 3 | "Capital Works Contracts"; a hazard table that lists France as a country |
| `What is the project duration?` | 3 | a visual-impact table with a "SCHEDULE" column |
| `How long will construction take?` | 3 | "Long Valley" |

Every one of those is a keyword match, not an answer.

## The three checks

`stage1/answerability.py`, called from `ask()` after the evidence cards are
built and before anything is synthesised or shown. Each check can only reduce
confidence; none can invent an answer, relax citation validation, or rewrite a
retrieval score.

**1. Intent** — what kind of fact is being asked for: `money`, `duration`,
`date`, `count`, or nothing specific. English and Chinese patterns are separate
because the phrasings differ (`造價` / `成本` / `費用` / `預算` vs "project cost").

**2. Datum** — if the question asks for an amount, duration or date, a passage
must contain one, near the thing it describes. A bare "HK$1M" beside "billing
account" is not a project cost; "1.4 million" beside "population" is not money,
so a currency symbol is required. Windows: 140 chars for money (a cost clause
can be long), 60 for duration, 100 for a date, 15 for Chinese duration
(「工程」 appears in almost every Chinese sentence, so a wide window lets an
unrelated 「為期兩個月」 borrow it).

**3. Coverage** — the largest number of the question's terms carried by any
*single* returned passage. Required: half the terms, never fewer than two. A
passage sharing one word with the question is a coincidence. Measured on the
card list, not the corpus, because the corpus is not what gets shown.

If a check fails, `ask()` returns `refused: true`, `message` =
`Sorry, I cannot answer this question` (EN) / `抱歉，我無法回答此問題。` (ZH),
no evidence cards, and a `gate.status` of `not_answerable` with a
machine-readable `reason`.

Cards that fail the datum check are dropped from `kept`, so an unrelated
passage is never displayed beside a real answer just to fill the list.

## Why coverage, not corpus co-occurrence

The first implementation asked whether the question's terms ever co-occur on
one page of the corpus. It refused `noise contour map` — a term the app holds a
glossary definition for — because the map is a figure and figure captions are
stripped from the index, so no page carries "noise", "contour" and "map"
together. Coverage asks the narrower and more honest question: does the passage
we are about to show you carry the words of your question? It refuses the France
case (best card 1 of 2) and the World Cup case (1 of 4) for the same reason,
and keeps `noise contour map` (2 of 3).

Definitional questions the glossary answers are exempt: the curated definition
is the answer, and a page-level test does not apply to it.

## Measured results

Offline battery (model stubbed, deterministic):

| Group | Count | Result |
|---|---|---|
| Valid English questions | 50 | 0 false refusals |
| Valid Chinese questions | 12 | 0 false refusals |
| Invalid English questions | 12 | 12 refused, exact text, 0 cards |
| Invalid Chinese questions | 5 | 5 refused, exact text, 0 cards |

Twenty natural-language questions ("What mitigation measures are proposed to
reduce construction noise?") were used to set the coverage threshold; all
reached at least the required coverage, the tightest being 3 of 5.

End-to-end with the real model (`granite4.1:3b`), via the HTTP API:

| Case | Result |
|---|---|
| `How much does the project cost?` | refused — `no_money_in_evidence` |
| `What is the capital of France?` | refused — `evidence_does_not_cover_question` |
| `What noise mitigation measures are proposed?` | answered, 3 verified citations, model answer |
| `噪音屏障` | answered in Chinese, 3 Chinese-original citations |
| `工程費用是多少？` | refused — exact Chinese fallback |
| `法國的首都是哪裡？` | refused — exact Chinese fallback |

Test suites: `app.py` 75/75, `stage1/test_citation_reliability.py` 58/58
(2 pre-existing skips), `stage1/test_passages.py` + `test_rare_term_gate.py`
45/45.

## Known limitations

Both are answered today and are recorded here rather than hidden.

- **`Who is the project manager?`** — "Project Manager" is a real EIA role and
  appears on 14 pages, so coverage passes. The question asks *who*, and no
  person is named. A person-name check was considered and rejected: without
  named-entity recognition it would over-refuse.
- **`What is the population of Hong Kong?`** (and `香港的人口是多少？`) — the
  reports discuss the populations of species and of risk receptors, and all
  three words appear together on 252 pages. The figure asked for is not stated.
  Catching this needs a numeric-answer requirement for every "what is X"
  question, which would refuse valid qualitative questions such as "what is the
  noise impact".

Chinese species names (`中華白海豚`, `黑臉琵鷺`) are refused by the Chinese
retrieval gate, not by this gate: the Chinese executive summaries do not
mention them at all (0 of 113 pages). The English chapters do.

## Files

- `stage1/answerability.py` — new: intent, datum, coverage, `assess()`
- `app.py` — refusal strings, gate call in `ask()`, `AnswerabilityTest` (15 tests)
- `stage1/glossary_data.py` — acronym aliases must match in capitals; the alias
  `DO` was matching the ordinary word "do", so `How do I cook pasta?` returned
  a dissolved-oxygen definition
- `stage1/test_citation_reliability.py` — the weak-evidence test now asserts the
  refusal it was previously indifferent to
