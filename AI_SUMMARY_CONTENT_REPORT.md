# AI Summary — content summary instead of source description

**Task:** make the AI Summary explain what the EIA report found, not which
passages were quoted.

**Status:** implemented and verified. Files changed: `app.py`,
`static/index.html`. No new dependencies.

---

## 1. The problem, measured

Before any change, `Summarise this EIA report` was answered by keyword retrieval
with three **different reports'** Chapter 1 introductions, because those pages
share the words "report" and "findings". The model then wrote a sentence that
named its own sources and a citation that failed validation
(`[aeiar-276-2026, Ch.1, p.None]`), so the summary disappeared and the reader
was left with a bare card list — the exact failure being reported.

Two causes, two fixes:

| Cause | Fix |
|---|---|
| A whole-report request is not a keyword query | `overview` mode, assembled from that report's own conclusion / outcomes / purpose chapters |
| `p.None` citations failed validation and dropped the whole summary | `_citation_token` never emits `p.None`; validation accepts chapter-only citations |

## 2. What the summary now contains

**Prompt** (`_build_synthesis_prompt`). Fixed two-section output — `**Summary**`
then `**Key points**` — with rules that:

1. ban source narration, and name the banned openers explicitly
   ("The report states…", "It notes…", "According to…");
2. demand the actual measures, standards, locations, receptors and conclusions,
   not "mitigation measures were proposed";
3. preserve qualifications ("no residual impact is **anticipated**", "subject to
   implementation");
4. require a citation on every factual claim, using the token printed beside its
   passage;
5. forbid figures or conclusions absent from the evidence;
6. **attribute figures to the right thing** — added after the model called this
   project a "24 km road segment" when the evidence says the *whole highway* is
   24 km and this project is one of its four sections.

**One rewrite** (`_SOURCE_NARRATION`). The model reverts to "The report
highlights that…" roughly one time in three even with the rule in front of it.
When a sentence opens that way, one corrective rewrite is requested. The first
answer is kept as a fallback, so a failed rewrite can never lose a valid answer.

**Overview mode** (`_overview_passages`). For "summarise this report" / "key
findings" / 這份報告的主要發現, five passages are taken from **one** report:
its conclusion, its statement of environmental outcomes, what the project is,
its objective, and one impact chapter's concluding section. Two corrections
made during verification:

- passages *about the document* ("Structure of this Report", 1.6.1.1) are
  excluded — they were being selected and pushed the model into describing the
  table of contents;
- chapters already represented are skipped, so the fifth slot adds a new impact
  area (air quality) instead of a second passage from Chapter 1.

**Extractive fallback** (`_assemble_evidence_summary`). When the model is
unavailable *or* its answer fails citation validation, the same two-section
shape is produced from the report's own sentences, labelled
`model: evidence-summary`. Previously a validation failure produced no summary
at all.

## 3. Reading order

`static/index.html`: `renderSummaryBody()` splits the answer into a paragraph
and a bullet list (`Summary` / `Key points`, `摘要` / `重點`). The evidence
divider is labelled `Sources` / `資料來源`.

The glossary card was rendering **before** the summary, so a question like
"What noise mitigation measures are proposed?" opened on a definition. It now
sits between the summary and the sources. Verified order:
`summary → glossary → sources`.

## 4. Retrieval: naming the measures

"What noise mitigation measures are proposed?" was answered from the residual
impact conclusion — "with the implementation of the proposed mitigation
measures" — which restates the question without naming one. The passages that
do name them (low-noise surfacing, vertical/cantilevered barriers, silencers,
enclosures) ranked just below the top three.

`_prefer_named_measures()` re-orders prose passages that name a concrete
measure ahead of those that only refer to them. Ordering only: no card is added
or dropped, so citation validation and the answerability coverage check see the
same evidence. A wider candidate pool (6 instead of 3) is used **only** when the
question asks for measures, because the named passages sit just below the cut.

Effect, report-scoped question:

> At-source mitigation measures such as low noise road surfacing and
> vertical/cantilevered noise barriers are recommended… adoption of Impeded
> Stone Mastic Asphalt (PMSMA6) or an equivalent material on the slip roads.

## 5. Test results

### Content (live server, real model `granite4.1:3b`)

| Request | Result |
|---|---|
| `Summarise this EIA report` | `gate: overview`, 5 passages from `aeiar-276-2026`; summary opens on air-quality impacts, ecological avoidance and the "no residual impact anticipated" conclusion |
| `What are the key findings of this report?` | `gate: overview`, 5 passages; no source-narrating sentence after rewrite |
| `這份報告的主要發現是甚麼？` | `gate: overview`, 3 Chinese executive-summary pages, `**摘要**` / `**重點**` |
| `What noise mitigation measures are proposed?` (report selected) | names low-noise surfacing, vertical/cantilevered barriers, silencers, enclosures, PMSMA6 |
| `有哪些噪音緩解措施？` (report selected) | names 臨時隔音屏障、隔音罩、隔音布、消音器、隧道入口隔音屏障, cites 75 Leq(30min) |
| `What is the capital of France?` | `not_answerable`, 0 cards, `Sorry, I cannot answer this question` |

### Regression

| Suite | Result |
|---|---|
| `python3 -m unittest app` | **75 / 75 pass** |
| `stage1/test_citation_reliability.py` | **58 tests, OK** (1 skip) |
| `stage1/test_passages.py` | **26 / 26 pass** |
| `stage1/test_rare_term_gate.py` | **19 / 19 pass** |
| Answerability battery (50 valid EN, 12 valid ZH, 12 invalid EN, 5 invalid ZH) | **0 false refusals, 0 wrong refusals** |

Two tests changed with the behaviour they described:

- `test_synthesis_rejected_when_citations_invalid` — asserted `synthesis is None`
  when the model cites a report that is not in the retrieved set. It now asserts
  the invented citation is absent **and** an extractive summary is present.
- `test_synthesis_none_on_empty_response` → renamed
  `test_synthesis_falls_back_on_empty_response` for the same reason.

Both encoded the old outcome (no summary at all) that this task set out to
remove; the new assertions check the citation is still rejected, which is the
part that matters for honesty.

### Browser (Chrome, 1280×900, live page)

17 / 17 checks pass, covering:

- English overview: `Summary` + `Key points` labels, 734-character paragraph,
  4 bullets, 5 source cards, links present;
- no source-narrating sentence in the summary;
- report-scoped specific question names concrete measures;
- Chinese: `摘要` / `重點` labels, Chinese summary, 3 bullets;
- answer start visible at 12 px from the top of the chat in all three cases,
  `window.scrollY === 0`;
- no console errors other than the browser's automatic `/favicon.ico` request
  (the app has no favicon).

Screenshots: `screenshots/summary-en.png`, `summary-zh.png`,
`summary-specific.png`, `summary-order.png`.

## 6. Known limitations

- **Unscoped measure questions still read generically.** With eight reports in
  the corpus, a generic question takes one passage per report and the top three
  are all residual-impact conclusions. The re-rank helps when a report is
  selected (the normal path in the UI); it cannot help when six reports each
  contribute a near-identical conclusion.
- **The Chinese overview is drawn from the executive summary, which is itself a
  summary.** Its opening sentence therefore sometimes describes the assessment
  rather than stating a finding ("本報告主要評估…"). Chinese narration detection
  covers 指出／提到／說明 only — broadening it risks the shorter, tighter Chinese
  answer budget.
- **The rewrite costs one extra model call** (about 7 s) when it fires, roughly
  one answer in three.
- `Who is the project manager?` and `What is the population of Hong Kong?`
  remain answered rather than refused (carried over from the answerability
  work; catching them needs NER or a numeric-answer rule that over-refuses).
