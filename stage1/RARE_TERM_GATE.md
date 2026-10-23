# Stage 1 — Rare-term / Out-of-Vocabulary Gate

**Status:** implemented, tested, awaiting review.
**Date:** 2026-10-18
**Corpus:** 1,293 pages / 34 chapters / 2 reports — unchanged.
**Runtime:** Python 3.13 standard library only. No packages, no embeddings, no model, no network.

This is a **retrieval safeguard**, not an answer-refusal mechanism. It reports what
the corpus does and does not contain. It makes no claim about whether an answer
exists, and no claim about answer accuracy.

---

## 1. What changed

| File | Change |
|---|---|
| `stage1/retrieve.py` | 367 → 537 lines. Added `FUNCTION_WORDS`, `fold_candidates()`, `Corpus.resolve_query()`, `Corpus.gate()`, `--strict-oov`, gate output in text and JSON. `search()` now takes resolved terms instead of a raw string. Two unclosed-file warnings fixed. |
| `stage1/test_rare_term_gate.py` | New. 19 deterministic tests, stdlib `unittest`. |
| `stage1/RARE_TERM_GATE.md` | This report. |

Nothing else was touched. Verified after all work:

- 34/34 `stage1/data/*.pages.jsonl` byte-identical (`shasum -a 256`, 0 changes).
- The five previously validated outputs still hash to
  `2b7559b2…` (ch04), `f73e5f3c…` (ch08), `6b2f72d1…` (ch10),
  `baf96e18…` (ch15), `b89f7e91…` (s9_eco).
- `stage0/reports.json` still `incomplete`; geometry still deferred.
- `PRD_EIA_Map_Assistant.md`, `DESIGN.md`, `stage1/extract_pages.py` untouched
  (mtimes predate this task).

**The gate does not re-rank.** For all six test queries the ranked results are
byte-identical to the baseline captured before the change (§4). The gate adds a
verdict and can suppress output; it never changes a score or an order.

---

## 2. The rule

Three inputs, all from the existing corpus: document frequency, a function-word
list, and a suffix folder.

**Step 1 — content terms.** Tokenise as before, then drop function words.
`FUNCTION_WORDS` is `STOPWORDS` plus pronouns, auxiliaries and question words
(`my`, `our`, `will`, `how`, `why`, `please`, `tell`…). This list is used by the
gate **only**; the BM25 stopword list is untouched so earlier rankings stay
reproducible. Without it, "will my flat shake" reports `my` as an absent content
term.

**Step 2 — presence.** A term is present if `df > 0`. If absent, try
`fold_candidates()`: `-ies→y`, `-es`, `-s` (not `-ss`), `-ing`, `-ed`. If a
candidate is present, the term counts as present **and the folded form replaces
it in the search terms**, so the gate's verdict and the ranking cannot disagree.

**Step 3 — classify.**

| Condition | Status | Behaviour | Exit |
|---|---|---|---|
| no content terms | `empty_query` | message, no search | 1 |
| **every** content term absent | `all_oov` | **blocked** | 2 |
| some absent, some present | `partial_oov` | results returned + warning naming the absent terms | 0 |
| none absent | `ok` | normal | 0 |

`--strict-oov` also blocks `partial_oov`. It is opt-in and §6 shows why.

**Why `all_oov` is the only blocking tier.** It rests on a fact that needs no
threshold: no term in the query occurs on any of 1,293 pages, so no ranking can
be meaningful. Every other judgement would need a threshold, and §3 shows the
threshold does not exist in this corpus.

---

## 3. The design I rejected, and the measurement that rejected it

My earlier recommendation (`RETRIEVAL_PROTOTYPE.md` §8.1) was to block whenever
the query's highest-IDF term is absent. That would block `geothermal power
generation`. I tried to generalise it: treat an absent term as decisive when the
*remaining* terms are all "generic", with generic defined by a df threshold.

That fails on this corpus. At a candidate threshold of 26 pages (2% of corpus):

| Term | df | Intuition | Threshold verdict |
|---|---|---|---|
| `avifauna` | 89 | topical — a technical ecology term | "generic" ✗ |
| `egret` | 52 | topical — a species | "generic" ✗ |
| `heron` | 61 | topical — a species | "generic" ✗ |
| `barrier` | 47 | topical for this report | "generic" ✗ |
| `power` | 26 | ordinary | "generic" ✓ (exactly on the boundary) |
| `free` | 21 | ordinary | "specific" ✗ |
| `help` | 16 | ordinary | "specific" ✗ |
| `many` | 18 | ordinary | "specific" ✗ |
| `safe` | 18 | ordinary | "specific" ✗ |

The split fails in both directions, and `power` lands exactly on the boundary —
a knife-edge that would flip with any corpus change. **Document frequency
measures how often a word is used, not whether it carries the topic.** So the
threshold was not shipped, and blocking was restricted to the threshold-free
case.

This is the limitation the task asked to be documented rather than papered over:
**the gate cannot tell whether an absent term is the query's subject or
incidental wording.** `geothermal` is the subject in "geothermal power
generation"; `my` would have been incidental. Only the first is detectable, and
only because it is absent from every page.

---

## 4. Baseline vs. after — the six existing queries

Baseline captured with the pre-change script, compared on the `results` array.

| Query | Gate | Results identical to baseline? |
|---|---|---|
| `black-faced spoonbill` | `ok` | YES |
| `predicted mitigated noise level` | `ok` | YES |
| `geothermal power generation` | `partial_oov` | YES |
| `long viewing distance` | `ok` | YES |
| `noise barrier` | `ok` | YES |
| `wetland habitat enhancement` | `ok` | YES |

(The task said five queries; the report contains six. All six are re-run here so
nothing is dropped. The five that map to the original requirement categories are
narrative, table, weak-match, duplicate-folio and null-folio; `noise barrier` is
the second table query.)

**No regressions.** No previously relevant query is now blocked, because only
`geothermal` has an absent term and it lands in `partial_oov`, which does not
block by default. No score or ordering changed anywhere.

---

## 5. The `geothermal power generation` case, explicitly

- `df("geothermal")` = **0**. It occurs on 0 of 1,293 pages.
- `df("power")` = 26 (exact token; the 51 I reported earlier was substring
  matching, which also counted "powerful"). `df("generation")` = 66.
- Gate status: **`partial_oov`**, `oov_terms = ["geothermal"]`, not blocked.

Default output:

```
gate: partial_oov — "geothermal" occurs on 0 of 1293 pages; the other terms do occur
gate: WARNING — the results below do not address "geothermal"
```

The three hits (CLP power cables, the duplicated summary paragraph, backup pump
power supply) are still returned, now under an explicit statement that the query's
distinctive term is absent from the whole corpus. With `--strict-oov` the query is
blocked (exit 2) and nothing is returned.

**Honest assessment:** the default does not suppress the misleading hit, it labels
it. That is a real reduction in misleadingness — a reader can no longer mistake
the CLP page for an answer about geothermal — but it is not the hard block the
word "gate" suggests. The hard block exists, and §6 shows what it costs.

---

## 6. False-block audit — 32 realistic queries

Queries written as a resident might ask, covering noise, air, water, ecology,
landscape, heritage, waste, hazards, traffic, EMF, plus off-topic controls.

**Default mode blocks 1 of 32:** `quantum entanglement` — correct (neither term
occurs anywhere).

**`--strict-oov` blocks 6 of 32.** Judged individually:

| Query | Absent term | Verdict | Why |
|---|---|---|---|
| `quantum entanglement` | quantum, entanglement | **correct** | concept absent |
| `geothermal power generation` | geothermal | **correct** | concept absent (`renewable` also df=0) |
| `nuclear power station` | nuclear | **correct** | concept absent |
| `solar panel` | solar | **correct** | concept absent (`photovoltaic` df=0) |
| `smelly river water quality` | smelly | **WRONG** | corpus says `odour` (df=67) — content exists |
| `property price` | price | **WRONG** | corpus says `value` (df=138), `compensation` (df=70) |

So strict mode is 4/6 correct, and both failures share one cause: **register
mismatch**. The resident uses an everyday word, the report uses the technical
one. A document-frequency gate cannot see that `smelly` and `odour` are the same
concern — they share no characters and no vocabulary entry.

That is the measured reason strict mode is opt-in and not the default. On this
set it would wrongly refuse a question the corpus can answer.

---

## 7. The blind spot in the other direction

Presence of individual words does not mean the corpus addresses the combination.

`offshore wind` → gate `ok` (`offshore` df=3, `wind` df=22). The actual hits:

- rank 1, `§12.6.19 p.12-37` — "**Former Offshore Area** … previously submerged"
  (marine geology, matched 1/2 terms)
- rank 2, `§5.6.1.4 p.5-19` — "**Wind**-blown dust would be generated" (air
  quality, matched 1/2 terms)

No page contains both terms; the words appear in unrelated senses. The corpus
says nothing about offshore wind energy, and the gate does not notice. The output
does expose `matched 1/2` on each hit, but the gate does not act on it.

A co-occurrence rule ("no page contains all query terms") would catch this, but it
would also flag legitimate questions whose answer spans pages. That is a passage
problem, not a gate problem, and it belongs with paragraph-level retrieval.

---

## 8. Regression tests

`stage1/test_rare_term_gate.py` — **19 tests, all pass** (`OK`, 4.6 s).

| Requirement | Test |
|---|---|
| (a) genuinely out-of-vocabulary term | `test_a_all_oov_blocks`, `test_a_all_oov_multiple_terms_blocks` |
| (b) present terms return relevant passages | `test_b_present_terms_not_blocked`, `test_b_present_terms_return_results_with_citations` |
| (c) common words must not trigger | `test_c_question_wording_not_blocked`, `test_c_pronouns_are_not_content_terms`, `test_c_all_stopwords_is_empty_not_oov` |
| (d) mixed matched / unmatched | `test_d_mixed_is_partial_and_not_blocked`, `test_d_mixed_still_returns_results`, `test_d_mixed_blocks_only_in_strict_mode` |
| inflection folding | `test_inflection_fold_prevents_false_block`, `test_inflection_fold_matches_base_form_ranking`, `test_no_substitution_when_term_present` |
| traceability | `test_citation_resolves_to_the_source_record`, `test_duplicate_folio_is_not_deduplicated` |
| no re-ranking | `test_gate_does_not_change_ranking`, `test_ranking_is_deterministic`, `test_corpus_loads_every_record` |

The tests assert gate behaviour and citation traceability. They do **not** assert
retrieval relevance — there is no ground truth for "relevant", so such a test
would encode an opinion as a fact.

---

## 9. Limitations

1. **Role blindness.** df cannot tell a subject from a modifier. An absent term is
   reported, never interpreted.
2. **Register blindness.** Informal wording for a present concept reads as absent
   (`smelly` vs `odour`, `price` vs `value`). Measured: 2 of 6 strict blocks.
3. **Combination blindness.** All words present but the proposition absent reads
   as `ok` (`offshore wind`). The gate has no notion of co-occurrence.
4. **Inflection only.** `spoonbills→spoonbill` is folded; `noisy→noise` and
   `mitigate→mitigation` are not. Both happen to exist in this corpus (`noisy`
   df=10, `mitigate` df=48) so the gap is currently invisible, but it is real.
5. **Typo = absent.** A misspelling produces `all_oov` and a hard block if it is
   the only content term. No spell correction, by design.
6. **Corpus-relative.** Every verdict is relative to these 1,293 pages. Adding a
   report changes verdicts without any code change. That is correct behaviour but
   means the audit numbers in §6 do not transfer to a larger corpus.
7. **Not calibrated, not definitive.** The gate decides absence, not relevance.
   `ok` does not mean an answer exists.

---

## 10. Recommendation for the next step

**Keep the default as it is.** Blocking only on `all_oov` is the only rule here
that rests on a fact rather than a threshold, and it blocked 1 of 32 realistic
queries, correctly.

**If hard blocking of `partial_oov` is a product requirement**, the missing piece
is a small curated **register/synonym glossary** (`smelly→odour`, `price→value`,
`rubbish→waste`, `smoke→emission`…), consulted by the gate before declaring a term
absent. That is the only measured cause of strict-mode false blocks (2 of 6). It
would take strict mode from 4/6 to ~6/6 on this set and make it defensible as a
default. It is deterministic and standard-library. I recommend it as the next
scoped task **only if** hard blocking is wanted; it is not needed for the current
advisory behaviour.

**Otherwise**, proceed to paragraph-level passages as previously planned
(`RETRIEVAL_PROTOTYPE.md` §8.2). It addresses the two problems the gate cannot:
run-on excerpts and the `offshore wind` co-occurrence blind spot.

**Do not** build answer generation on top of this yet. The gate removes one
failure mode (confident citations for absent concepts) and leaves three
(§9.1–9.3). Answer generation needs the passage work first.

---

## 11. Reproduce

```bash
cd /Users/chloeyan/workbuddy-ai/NORTHWISE

# tests
python3 stage1/test_rare_term_gate.py

# the geothermal case: warning, results still returned
python3 stage1/retrieve.py "geothermal power generation" --k 3

# the same query hard-blocked (exit 2)
python3 stage1/retrieve.py "geothermal power generation" --k 3 --strict-oov

# total absence (exit 2)
python3 stage1/retrieve.py "geothermal"
python3 stage1/retrieve.py "quantum entanglement"

# inflection folding: spoonbills -> spoonbill, results identical to "spoonbill"
python3 stage1/retrieve.py "spoonbills" --k 3

# gate state in machine-readable form
python3 stage1/retrieve.py "geothermal" --json
```

Exit codes: `0` results returned, `1` no hits or empty query, `2` blocked.
