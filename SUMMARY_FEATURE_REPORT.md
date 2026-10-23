# NORTHWISE — Summary Feature Rework

Implementation report for the summary-quality task. Everything below was run in
this project; no separate application was created.

## 1. What was actually wrong

Four distinct causes, each confirmed against real output rather than guessed:

| Symptom seen in the output | Cause found |
|---|---|
| `"Conclusion of EIA Study 15.1.1.1 … EIA stu"` pasted as a summary | The extractive fallback took the first 300 characters of a page, which began with a heading and a section number and ended mid-word |
| `"Table 4.2"`, `4.6.1.1`, `12.3.2.1` inside bullets | The model copies section numbers from the passage it is reading |
| A dust answer naming `防風屏` and `封閉式搬運設備` that the report never proposed | The card excerpt was a 300-character window. On `aeiar-276-2026` p.24 the window stopped in the middle of the dust-measures list, *before* the mitigation column, so the model filled the gap |
| Chinese answers containing `湿地`, `掘挣`, and `北 metropolis` | No script check on the final answer; rule text alone was ignored |
| `蘭嶇國家公園`, `南沙瀨濕地保護公園`, `三鴻樓` | The model transliterates English place names instead of keeping them in English (see §7) |
| The same finding repeated in all three sections | Prompt rules alone did not stop it; a lexical check was needed |
| `這代表甚麼` sometimes missing | The model drops the third heading about a third of the time |

## 2. Genuine summaries

- **The model now reads the whole passage, not the card window.**
  `_make_card()` attaches a second field, `synthesis_excerpt`
  (`SYNTHESIS_EXCERPT_WIDTH = 2000`), while `excerpt` keeps the 300-character
  window the reader sees. Table passages get a shorter synthesis window because
  a 2 000-character table dump pushed a Chinese call past the model timeout.
  This is the fix for the invented dust measures: the measures were in the page
  all along, just outside the window.
- **The prompt was rewritten** from a single blob into three named sections plus
  14 numbered rules: state the finding not the source, be specific, keep
  qualifications, cite every claim, do not invent, attribute figures to the
  right thing, length limits, connected prose, plain language, section
  separation, report-vs-interpretation, English quotations stay English, and
  tables/fragments are not to be reconstructed.
- **`_first_sentences()`** now strips the heading *before* the section number
  and cuts on a sentence boundary, so a summary starts at `"Construction noise
  would be controlled…"` instead of `"Conclusion of EIA Study 15.1.1.1 …"`.
- **`_assemble_evidence_summary()`** (the no-model fallback) was rewritten:
  sentences shorter than 40 characters or with fewer than 5 content words are
  dropped, duplicates are collapsed by Jaccard similarity (> 0.75), prose
  passages carry the summary and table rows are quoted separately and
  labelled, and the first two distinct findings go in the summary while the
  rest become bullets, so no finding appears twice.
- **`_pastes_a_passage()`** catches a bullet that is a retrieved paragraph
  pasted back verbatim — the "seventh bullet" failure.

## 3. English and Traditional Chinese, independent of source language

- The interface language alone decides the summary language. The Chinese prompt
  asks for 繁體中文 **even when every evidence passage is English**, and states
  that a Chinese source document is not required.
- **Script enforcement.** `_has_simplified()` checks the final answer against a
  set of characters that are Simplified-only. Six characters that are written
  identically in both scripts (`黑 鼠 鼻 趟 雕 痴`) had been in the set and made
  a clean Traditional answer look Simplified — `黑夜裡的老鼠` was flagged. They
  are now subtracted (`_SHARED_CHARS`), and the remaining set is validated
  against the official Chinese corpus (95 395 characters): **0 false positives**.
- **`_answered_in_english()`** rejects an English answer returned for a Chinese
  request (measured: the model wrote a numbered English list under Chinese
  headings).
- **Retry selection changed from all-or-nothing to least-bad.**
  `_problem_score()` weighs script and language problems at 2 and style problems
  at 1, and a rewrite is kept when its score is *lower* than the original's.
  Previously a rewrite had to clear every check at once, so one that fixed the
  script but added a stylistic flaw was discarded and the contaminated original
  was displayed — that is how `湿地` reached the page after a retry had already
  produced a clean answer.
- Switching language regenerates stored answers (`refreshAnswersForLanguage()`)
  with a token so a slow response for the old language cannot overwrite the new
  one.
- **Two pre-existing gaps in the language switch were found by the UI test and
  fixed**: `renderReportList()` hard-coded the English search placeholder and
  ran *after* `setLang()` had set the Chinese one, so the search box stayed
  English in Chinese mode; and `UI[lang].askBtn` existed in both dictionaries
  but was never applied to the Ask button. The "no matching reports" message
  was hard-coded too and now has a `noResults` string.

## 4. Citations

- Citation format is unchanged: `[report_id, Ch.N, p.X]`, and `[report_id, Ch.N]`
  where the page carries no printed folio. `_citation_token()` never emits
  `p.None`.
- `_validate_synthesis()` checks every citation against the retrieved cards
  before an answer is accepted; a failing answer gets one citation-repair pass.
- The summary and the references are rendered as separate blocks: the
  `Sources / 資料來源` divider sits between the prose and the evidence cards.
- No page number, quotation or citation is generated by the code itself.

## 5. Structure

- `**Summary** / **Key findings** / **What this means**`, localised as
  `**摘要** / **主要發現** / **這代表甚麼**`.
- `_limit_points()` caps Key findings at four bullets and converts numbered
  lists to bullets.
- `_ensure_three_sections()` guarantees the third heading. When the model omits
  it, the section is filled with a statement of what the evidence does *not*
  establish — never with an invented consequence.
- "What this means" is capped to one sentence in the UI
  (`renderSummaryBody()`), because the model would not respect the length rule.

## 6. Files changed

| File | Change |
|---|---|
| `app.py` | Prompt rewrite; `synthesis_excerpt`; `_first_sentences`, `_assemble_evidence_summary`, `_problem_score`, `_ensure_three_sections`, `_split_sections`, `_repeats_itself`, `_has_simplified`, `_answered_in_english`, `_pastes_a_passage`, `_limit_points`, `_normalise_bullets`, `_strip_section_numbers`, `_move_leading_citations`; retry chain; new tests |
| `static/index.html` | `parseSummarySections()` returns three parts; `renderSummaryBody()` renders the third labelled paragraph and caps it to one sentence; i18n labels (`Key findings`, `What this means`, `資料來源`); `refreshAnswersForLanguage()`; `.summary-meaning`, `.lang-refreshing` CSS |

Nothing else in the project was modified: the map, report selection, retrieval
indexes and citation system are untouched apart from the extra
`synthesis_excerpt` field on evidence cards.

## 7. Tests performed

| Suite | Result |
|---|---|
| `python3 -m unittest app` | 99 tests, OK in 1 632 s |
| `app.FallbackSummaryTest` (new) | 8/8 |
| Summary prompt/guard tests (new) | 15/15 run individually; the file's remaining summary tests pass inside the full run |
| `stage1/test_passages.py` | 26 OK |
| `stage1/test_rare_term_gate.py` | 19 OK |
| `stage1/test_citation_reliability.py` | 58/58 covered, 0 failures — the other four classes passed in one run (42 tests), `EvidenceConsistencyTest` was re-run alone (23 tests, 434 s, OK) after the environment killed the first run on memory |
| Browser harness `/tmp/summary3.js` | 13/13 |
| Browser harness `/tmp/ui_regression.js` | 8/8 — map tiles, 8 reports, filter, report card, chat shell, map survives language switch, UI strings localised, no page errors |

### End-to-end cases (English-only report, both interface languages)

San Tin (`aeiar-276-2026`), English interface — three sections, 3 bullets, one-
sentence meaning, `Sources` divider, answer start at 12 px:

> **Summary** … Construction noise would be controlled by noise barriers and
> silencers at the site boundary … **Key findings** … **What this means** For
> residents living near the Project, there is no expected increase in noise …

Chinese interface, same stored answer regenerated in 18 s (49 s on an earlier
run; the same call has measured up to 96 s when the answer runs to the token cap):

> **摘要** 本報告評估了北邊大都會高速（Northern Metropolis Highway, NMH）一部分…
> **主要發現** … **這代表甚麼** … **資料來源**

Then switching back to English regenerated the English text again.

### Duplicated headings and fragmented text

`FallbackSummaryTest` builds evidence containing a duplicated noise passage, a
`Table 4.2` fragment, `4.6.1.1` and `Road Traffic Noise 4.6.6.1`, and asserts
that the output collapses the duplicate, drops the table label and the section
numbers, keeps a finding in either the summary or the bullets but never both,
and does not invent a meaning section.

## 8. Known limitations — stated plainly

1. **Place names are still transliterated.** Given English evidence, the model
   writes `蘭嶇國家公園` for `Ramsar Site` and `南沙瀨濕地保護公園` for the future
   park. The prompt now forbids it with these exact counter-examples and the
   claim itself is supported, but a 3B local model still does it
   intermittently. A larger model, or an official bilingual glossary of place
   names, would be the real fix.
2. **`24 km` can still be attributed to the section** rather than to the whole
   highway; rule 6 reduces but does not eliminate it.
3. **The published site uses the extractive fallback.** The sandbox has no
   Ollama, so the live deployment never calls the model and shows the
   `evidence-summary` path, which is grammatical but plainer than the model
   output.
4. **Chinese retrieval quality is uneven.** The Chinese index is dominated by
   `table_fragmented` passages, so a Chinese question about dust can retrieve
   off-topic prose. That is a retrieval issue, outside this task.
5. **The verification banner appears on most answers.** `claim_evaluator.py`
   returns `rejected` as soon as a single cited claim is classed
   `insufficient_evidence`, and with 11 claims from a 3B model that happens
   almost every time — so readers see "⚠ Some claims could not be fully
   verified" even on answers that are well grounded. Left unchanged here
   because it is a separate subsystem with its own 9 tests, but it is worth
   revisiting: the threshold, not the summary, is what makes the warning
   ubiquitous.
