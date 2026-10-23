# NORTHWISE Semantic Evidence Consistency — Updated Test Plan

**Date:** 2026-10-18  
**Workspace:** `/Users/chloeyan/workbuddy-ai/NORTHWISE`

---

## 1. Objective

Implement claim-level evidence evaluation to address the highest-priority remaining defect: **semantic evidence consistency** — ensuring every factual claim in an AI-generated answer is actually supported by the retrieved official EIA report evidence.

---

## 2. Deliverables

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | `stage1/evaluations/gold_cases_verified.jsonl` — 30 manually verified gold cases | ✅ Complete |
| 2 | `stage1/evaluations/adversarial_fixtures.jsonl` — 10 adversarial test fixtures | ✅ Complete |
| 3 | `stage1/claim_evaluator.py` — Claim-level evidence evaluator | ✅ Complete |
| 4 | Integration into `app.py` `_synthesize()` | ✅ Complete |
| 5 | `stage1/test_citation_reliability.py` — New `ClaimLevelEvaluationTest` (9 tests) | ✅ Complete |
| 6 | Updated `CITATION_RELIABILITY_TEST_REPORT.md` | This file |
| 7 | Updated `CITATION_RELIABILITY_TEST_PLAN.md` | This file |

---

## 3. Gold Evaluation Set (Task 1)

### Coverage

| Category | Count | Examples |
|----------|-------|----------|
| Numeric claims (exact values) | 4 | 5 dB(A), barrier height, 900m length, PM10 |
| Date values | 2 | Year 2038, Year 2029 |
| Mitigation measures | 5 | Wetland compensation, dust control, compensatory planting, tree preservation, sediment control |
| Construction vs operational phase | 2 | Noise barrier construction, traffic noise operational |
| Predicted impacts | 3 | Noise exceedance, habitat loss, fisheries impact |
| Species/habitat | 3 | Spoonbill, bat roost, Archaeological Survey |
| Table content | 3 | E. coli, Total Phosphorus, BOD5 |
| Chemical parameters | 2 | Dissolved oxygen, PM10 |
| Scoped searches | 3 | needs_review report, historical report, scoped only |
| Chinese queries | 3 | Mapped (noise, ecology, water), unsupported (房價) |
| Refusal cases | 3 | Geothermal, Chinese unsupported, false premise |
| Multi-report | 2 | Unscoped noise, EM&A programme |
| **Total** | **30** | |

### Verification Method

Every gold case was verified by:
1. Running the query through `app.ask()`
2. Loading the actual source record from `stage1/data/*.pages.jsonl`
3. Checking that the claim text appears verbatim or by paraphrase in the source text
4. Recording the exact report_id, chapter, page_label, and pdf_page_index

Cases are labeled `verified: true` with `verification_method: source_text_check`.

---

## 4. Claim-Level Evaluation (Task 2)

### Implementation: `stage1/claim_evaluator.py`

The evaluator performs three layers of checks on each claim:

#### Layer 1: Citation Metadata Validation (deterministic)
- Extract bracket citations: `[report_id, Ch.N, p.X-Y]`
- Verify report_id exists in retrieved evidence
- Verify chapter number exists in retrieved evidence
- Verify page_label exists in retrieved evidence
- **Failure → `rejected`**

#### Layer 2: Heuristic Checks (rule-based)
- **Numeric consistency**: Extract numbers with units from claim and evidence; flag mismatches
- **Entity presence**: Check if key entities from claim appear in evidence excerpt
- **Phase/status correctness**: Check for phase words (construction/operational) and status words (proposed/completed/required)
- **Certainty inflation**: Flag words like "guarantees", "ensures", "proven" that overstate source confidence
- **Failure → `rejected` or `human_review`**

#### Layer 3: Overall Outcome
- `accepted`: All claims pass
- `rejected`: At least one claim fails deterministic or heuristic check
- `human_review`: At least one claim needs human review (entities missing but citation valid)

### Metrics Computed

| Metric | Description |
|--------|-------------|
| `total_claims` | Total claims in answer |
| `claims_accepted` | Claims passing all checks |
| `claims_rejected` | Claims failing checks |
| `claims_human_review` | Claims needing human review |
| `citations_valid` | Citations matching evidence metadata |
| `citations_invalid` | Citations not matching evidence |
| `citation_accuracy` | `citations_valid / (citations_valid + citations_invalid)` |
| `claim_support_rate` | `claims_accepted / total_claims` |
| `contradiction_rate` | `claims_rejected / total_claims` |
| `human_review_rate` | `claims_human_review / total_claims` |

---

## 5. Adversarial Tests (Task 3)

10 adversarial fixtures test the evaluator's ability to detect:

| Fixture | Attack | Expected |
|---------|--------|----------|
| `adv_numeric_wrong` | Claims 10 dB(A) instead of 5 dB(A) | rejected |
| `adv_phase_wrong` | Says operational when source says construction | rejected |
| `adv_wrong_report` | Cites wrong report ID | rejected |
| `adv_status_inflated` | Says "completed" when source says "proposed" | rejected |
| `adv_wrong_page` | Cites non-existent page label | rejected |
| `adv_unsupported_claim` | Adds unsupported fact about jobs | rejected |
| `adv_ollama_down` | Simulates Ollama unavailable | synthesis null |
| `adv_empty_response` | Empty model response | synthesis null |
| `adv_format_valid` | Valid citation, correct claim | accepted |
| `adv_real_page_unsupported` | Real page cited with unsupported claim | rejected |

All 10/10 match expected outcomes.

---

## 6. Production Safeguards (Task 5)

Implemented in `app.py`:

1. **Citation metadata validation** in `_validate_synthesis()` — rejects citations not in evidence
2. **Claim-level evaluation** in `_synthesize()` — if `claim_evaluator` is available, evaluates the model answer
3. **Synthesis rejection** — if claim evaluation returns `rejected`, synthesis is discarded
4. **Evidence preservation** — if synthesis fails or is rejected, evidence cards are still returned
5. **Refusal on no evidence** — if retrieval refuses, LLM is never called
6. **Ollama fallback** — if Ollama is down/times out, `synthesis: null` with evidence intact

---

## 7. What Is Verified vs. What Requires Human Review

| Check | Automation | Reliability |
|-------|-----------|-------------|
| Citation metadata (report_id, chapter, page_label) | Fully automated | High — deterministic |
| Citation existence in evidence set | Fully automated | High — deterministic |
| Numeric value + unit match | Heuristic | Medium — regex-based, may miss context |
| Entity presence in evidence | Heuristic | Medium — keyword matching |
| Phase/status correctness | Heuristic | Medium — keyword matching |
| Certainty inflation | Heuristic | Medium — keyword list |
| Semantic entailment | **Not automated** | Requires human review |
| Whether a claim is actually supported by the cited text | **Not automated** | Requires human review |

**Important:** The claim evaluator detects obvious errors (wrong numbers, wrong pages, wrong reports, status inflation) but cannot prove that a claim is semantically entailed by the source text. A claim can pass all automated checks and still be unsupported. Human review is required for high-stakes claims.

---

## 8. Remaining Risks

1. **Semantic gap**: The evaluator uses keyword heuristics, not semantic understanding. A cleverly worded unsupported claim may pass.
2. **Table extraction**: Tables are extracted as fragmented passages. Numeric claims from tables may be hard to verify.
3. **Paraphrased citations**: The evaluator only checks `[report_id, Ch.N, p.X-Y]` format. Paraphrased citations ("see page 4-28") are not validated.
4. **Unit normalization**: "5 dB(A)" and "five decibels" may not match.
5. **Contextual numbers**: A number may appear in the evidence but with a different meaning (e.g. "5 dB(A)" as a criterion vs. a reduction).

---

## 9. Test Commands

```bash
# Full suite (all 107 tests)
cd /Users/chloeyan/workbuddy-ai/NORTHWISE
python3 app.py --test
cd stage1
python3 test_passages.py
python3 test_rare_term_gate.py
python3 test_citation_reliability.py PageNumberAnomalyTest
python3 test_citation_reliability.py EvidenceConsistencyTest
python3 test_citation_reliability.py AdversarialValidationTest
python3 test_citation_reliability.py ClaimLevelEvaluationTest
python3 test_citation_reliability.py EndToEndRegressionTest

# Claim evaluator self-tests
python3 claim_evaluator.py

# Adversarial fixture evaluation
python3 -c "
import sys; sys.path.insert(0, 'stage1')
from claim_evaluator import evaluate_adversarial_fixture
evaluate_adversarial_fixture()
"
```

---

## 10. Files Changed

| File | Change |
|------|--------|
| `app.py` | Added `claim_evaluator` import; integrated claim evaluation into `_synthesize()` |
| `stage1/claim_evaluator.py` | New — claim-level evidence evaluator |
| `stage1/evaluations/gold_cases_verified.jsonl` | New — 30 verified gold cases |
| `stage1/evaluations/adversarial_fixtures.jsonl` | New — 10 adversarial fixtures |
| `stage1/test_citation_reliability.py` | Added `ClaimLevelEvaluationTest` (9 tests) |
| `stage1/CITATION_RELIABILITY_TEST_PLAN.md` | Updated (this file) |
| `stage1/CITATION_RELIABILITY_TEST_REPORT.md` | Updated |
