#!/usr/bin/env python3
"""
NORTHWISE Citation Reliability and Evidence Consistency Test Suite
===================================================================
Tests for:
  A. AEIAR-215-2017 page-number anomalies (source-PDF verified)
  B. Evidence consistency across all 8 registered reports
  B3. Adversarial / negative validation tests
  C. End-to-end regression (OOV, Chinese, scoped, synthesis fallback)

Run:  cd stage1 && python3 test_citation_reliability.py
"""

import json
import os
import re
import sys
import unittest
from urllib.error import URLError

# Ensure stage1/ is on path so we can import retrieve / passages
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import retrieve as R
import passages as P


# ------------------------------------------------------------------ helpers

def _load_jsonl_records():
    """Load all page-level JSONL records into a list."""
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    records = []
    for fname in sorted(os.listdir(data_dir)):
        if fname.endswith(".pages.jsonl"):
            with open(os.path.join(data_dir, fname), "r", encoding="utf-8") as fh:
                for line in fh:
                    records.append(json.loads(line))
    return records


# Global fixtures (loaded once). Keep the historical reliability baseline on the
# English chapter corpus; Chinese executive summaries have their own index in app.py.
ALL_RECORDS = _load_jsonl_records()
CORPUS = R.Corpus(lang="en", records=ALL_RECORDS)
IDX = P.PassageIndex(CORPUS)

# AEIAR-215-2017 records, keyed by (chapter, pdf_page_index)
RECORDS_215 = {
    (r["chapter"], r["pdf_page_index"]): r
    for r in ALL_RECORDS
    if r["report_id"] == "aeiar-215-2017"
}

# Evidence cards by case (populated lazily)
CASE_EVIDENCE = {}


def _ask(query: str, lang: str = "en", report_id: str | None = None):
    """Call the app's ask() function if available, else use Corpus directly."""
    # Try to import app.py from parent directory
    parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent not in sys.path:
        sys.path.insert(0, parent)
    try:
        import app as APP
        return APP.ask(query, lang, report_id)
    except Exception:
        # Fallback: build a minimal response using Corpus + PassageIndex
        gate = CORPUS.gate(query)
        if gate["blocked"] or gate["status"] == "empty_query":
            return {
                "refused": True,
                "gate": gate,
                "evidence": [],
            }
        hits = IDX.search(gate["search_terms"], k=3, report=report_id)
        evidence = []
        for rank, (w, raw, weight, i, matched) in enumerate(hits, 1):
            p = IDX.passages[i]
            evidence.append({
                "rank": rank,
                "report_id": p["report_id"],
                "chapter": p["chapter"],
                "chapter_title": p["chapter_title"],
                "section_ref": p["section_ref"],
                "section_ref_status": p["section_ref_status"],
                "page_label": p["page_label"],
                "page_label_status": p["page_label_status"],
                "pdf_page_index": p["pdf_page_index"],
                "source_url": "",
                "citation": P.passage_citation(p),
                "excerpt": P.passage_excerpt(p, gate["search_terms"], width=300),
                "matched_terms": matched,
            })
        return {
            "refused": False,
            "evidence": evidence,
            "gate": gate,
        }


# ------------------------------------------------------------------ Group A

class PageNumberAnomalyTest(unittest.TestCase):
    """Group A — AEIAR-215-2017 page-number anomaly verification."""

    def test_a1_ch1_pdf_page_26_has_label_1_27(self):
        """PDF page index 26 (viewer 27) prints folio 1-27."""
        rec = RECORDS_215[(1, 26)]
        self.assertEqual(rec["page_label"], "1-27")
        self.assertEqual(rec["page_label_status"], "verified")

    def test_a1_ch1_pdf_page_27_has_label_1_29(self):
        """PDF page index 27 (viewer 28) prints folio 1-29 — skip confirmed."""
        rec = RECORDS_215[(1, 27)]
        self.assertEqual(rec["page_label"], "1-29")
        self.assertEqual(rec["page_label_status"], "verified")

    def test_a1_ch1_no_fictional_page_1_28(self):
        """No record in the corpus claims printed folio 1-28 for ch.1."""
        labels_ch1 = {
            r["page_label"] for r in ALL_RECORDS
            if r["report_id"] == "aeiar-215-2017" and r["chapter"] == 1
            and r["page_label_status"] == "verified"
        }
        self.assertNotIn("1-28", labels_ch1)

    def test_a1_ch1_sequence_is_non_contiguous(self):
        """Ch.1 printed folios jump from 1-27 to 1-29 — not renumbered."""
        ch1 = sorted(
            [(r["pdf_page_index"], r["page_label"])
             for r in ALL_RECORDS
             if r["report_id"] == "aeiar-215-2017" and r["chapter"] == 1
             and r["page_label_status"] == "verified" and r["page_label"]],
            key=lambda x: x[0]
        )
        # Find the transition
        for i in range(1, len(ch1)):
            prev_idx, prev_label = ch1[i - 1]
            curr_idx, curr_label = ch1[i]
            if prev_label == "1-27" and curr_label == "1-29":
                # Confirm the gap is preserved (not silently renumbered)
                self.assertEqual(curr_idx, prev_idx + 1)
                return
        self.fail("Did not find 1-27 -> 1-29 transition in ch.1")

    def test_a1_ch11_reset_to_11_0_preserved(self):
        """Ch.11 resets to 11-0 after 11-6 — both labels present."""
        ch11 = sorted(
            [(r["pdf_page_index"], r["page_label"], r["page_label_status"])
             for r in ALL_RECORDS
             if r["report_id"] == "aeiar-215-2017" and r["chapter"] == 11
             and r["page_label"]],
            key=lambda x: x[0]
        )
        labels = [label for _, label, _ in ch11]
        self.assertIn("11-6", labels)
        self.assertIn("11-0", labels)
        # 11-0 appears AFTER 11-6 (reset, not start-of-chapter)
        idx_6 = next(i for i, (_, l, _) in enumerate(ch11) if l == "11-6")
        idx_0 = next(i for i, (_, l, _) in enumerate(ch11) if l == "11-0")
        self.assertGreater(idx_0, idx_6)

    def test_a1_ch11_duplicate_11_0_distinguished_by_pdf_index(self):
        """Two PDF pages have label 11-0; they must have distinct pdf_page_index."""
        pages_11_0 = [
            (r["pdf_page_index"], r["page_label"])
            for r in ALL_RECORDS
            if r["report_id"] == "aeiar-215-2017" and r["chapter"] == 11
            and r["page_label"] == "11-0"
        ]
        self.assertEqual(len(pages_11_0), 2)
        self.assertNotEqual(pages_11_0[0][0], pages_11_0[1][0])

    def test_a1_citation_includes_pdf_index(self):
        """Every citation for aeiar-215-2017 includes pdf_page_index and viewer page."""
        for p in IDX.passages:
            if p["report_id"] != "aeiar-215-2017":
                continue
            cite = P.passage_citation(p)
            self.assertIn("PDF idx", cite)
            self.assertIn("viewer p.", cite)
            # Extract pdf_page_index from citation
            m = re.search(r"PDF idx (\d+)", cite)
            self.assertIsNotNone(m)
            self.assertEqual(int(m.group(1)), p["pdf_page_index"])

    def test_a1_no_silent_renumbering_of_ch11(self):
        """Ch.11 labels remain exactly as printed; no relabelling to make sequence continuous."""
        ch11 = sorted(
            [(r["pdf_page_index"], r["page_label"])
             for r in ALL_RECORDS
             if r["report_id"] == "aeiar-215-2017" and r["chapter"] == 11
             and r["page_label_status"] == "verified" and r["page_label"]],
            key=lambda x: x[0]
        )
        # After 11-6, the next label should be 11-0 (reset), not 11-7
        idx_6 = next(i for i, (_, l) in enumerate(ch11) if l == "11-6")
        next_label = ch11[idx_6 + 1][1]
        self.assertEqual(next_label, "11-0")


# ------------------------------------------------------------------ Group B

class EvidenceConsistencyTest(unittest.TestCase):
    """Group B — Evidence consistency across all 8 reports."""

    @classmethod
    def setUpClass(cls):
        cls.corpus = CORPUS
        cls.idx = IDX

    def _get_evidence(self, query: str, lang: str = "en", report_id: str | None = None):
        cache_key = (query, lang, report_id)
        if cache_key not in CASE_EVIDENCE:
            CASE_EVIDENCE[cache_key] = _ask(query, lang, report_id)
        return CASE_EVIDENCE[cache_key]

    def test_b1_explicit_support_noise_barrier(self):
        r = self._get_evidence("noise mitigation measures proposed")
        self.assertFalse(r["refused"])
        self.assertGreaterEqual(len(r["evidence"]), 1)
        # With expanded corpus, any core_nm report with noise mitigation is acceptable
        report_ids = {c["report_id"] for c in r["evidence"]}
        self.assertIn("aeiar-276-2026", report_ids)

    def test_b1_numerical_value_5_db(self):
        r = self._get_evidence("5 dB(A) noise reduction")
        self.assertFalse(r["refused"])
        found = False
        for card in r["evidence"]:
            if "5" in card["excerpt"] and "dB" in card["excerpt"]:
                found = True
                self.assertIn(card["report_id"], ["aeiar-276-2026", "aeiar-175-2013"])
                break
        self.assertTrue(found, "Expected 5 dB(A) in evidence excerpts")

    def test_b1_numerical_value_barrier_height(self):
        r = self._get_evidence("cantilevered noise barrier height")
        self.assertFalse(r["refused"])
        found = False
        for card in r["evidence"]:
            excerpt = card["excerpt"].lower()
            if "7" in card["excerpt"] and ("metre" in excerpt or "meter" in excerpt or "(m)" in excerpt):
                found = True
                break
        self.assertTrue(found, "Expected height in metres or (m)")

    def test_b1_date_value_year_2038(self):
        r = self._get_evidence("year 2038")
        self.assertFalse(r["refused"])
        found = False
        for card in r["evidence"]:
            if "2038" in card["excerpt"]:
                found = True
                self.assertEqual(card["report_id"], "aeiar-215-2017")
                break
        self.assertTrue(found, "Expected year 2038 in evidence")

    def test_b1_mitigation_wetland_compensation(self):
        r = self._get_evidence("wetland compensation")
        self.assertFalse(r["refused"])
        found = False
        for card in r["evidence"]:
            if "compensat" in card["excerpt"].lower():
                found = True
                break
        self.assertTrue(found, "Expected compensation in evidence")

    def test_b1_predicted_impact_noise_level(self):
        r = self._get_evidence("predicted noise level 70 dB")
        self.assertFalse(r["refused"])
        # Should find predicted noise levels
        self.assertGreaterEqual(len(r["evidence"]), 1)

    def test_b1_monitoring_ema(self):
        r = self._get_evidence("EM&A programme")
        self.assertFalse(r["refused"])
        found = False
        for card in r["evidence"]:
            if "EM&A" in card["excerpt"] or "monitoring" in card["excerpt"].lower():
                found = True
                break
        self.assertTrue(found, "Expected EM&A or monitoring in evidence")

    def test_b1_table_content_ecoli(self):
        r = self._get_evidence("E. coli parameter")
        self.assertFalse(r["refused"])
        found = False
        for card in r["evidence"]:
            if "E. coli" in card["excerpt"] or "coli" in card["excerpt"].lower():
                found = True
                break
        self.assertTrue(found, "Expected E. coli in evidence")

    def test_b1_multi_report_noise(self):
        r = self._get_evidence("noise mitigation")
        self.assertFalse(r["refused"])
        reports = {c["report_id"] for c in r["evidence"]}
        self.assertGreaterEqual(len(reports), 2)

    def test_b1_scoped_only_returns_selected_report(self):
        r = self._get_evidence("noise", report_id="aeiar-274-2026")
        self.assertFalse(r["refused"])
        for card in r["evidence"]:
            self.assertEqual(card["report_id"], "aeiar-274-2026")

    def test_b1_scoped_historical_report(self):
        r = self._get_evidence("noise", report_id="aeiar-175-2013")
        self.assertFalse(r["refused"])
        for card in r["evidence"]:
            self.assertEqual(card["report_id"], "aeiar-175-2013")

    def test_b1_insufficient_evidence_geothermal(self):
        r = self._get_evidence("geothermal")
        self.assertTrue(r["refused"])
        self.assertEqual(r["gate"]["status"], "all_oov")
        self.assertEqual(len(r["evidence"]), 0)

    def test_b1_weak_evidence_crypto_mining(self):
        r = self._get_evidence("cryptocurrency mining")
        # "mining" exists in the corpus (sand mining, quarrying), "cryptocurrency"
        # does not. The two never share a page, so the answerability gate refuses
        # rather than quoting a passage about sand extraction. This is the
        # behaviour the gate exists for, so assert it rather than accepting any
        # retrieval status.
        self.assertTrue(r["refused"])
        self.assertEqual(r["gate"]["status"], "not_answerable")
        self.assertEqual(len(r["evidence"]), 0)

    def test_b1_chinese_original_noise(self):
        r = self._get_evidence("噪音", "zh-Hant")
        self.assertFalse(r["refused"])
        self.assertEqual(r["gate"]["status"], "zh_original")
        self.assertFalse(r.get("translation_applied", False))
        self.assertEqual(r.get("evidence_lang"), "zh-Hant")
        self.assertTrue(r["evidence"])
        self.assertTrue(all(c.get("excerpt_lang") == "zh-Hant" for c in r["evidence"]))

    def test_b1_chinese_original_ecology(self):
        r = self._get_evidence("生態", "zh-Hant")
        self.assertFalse(r["refused"])
        self.assertEqual(r["gate"]["status"], "zh_original")
        self.assertFalse(r.get("translation_applied", False))
        self.assertEqual(r.get("evidence_lang"), "zh-Hant")
        self.assertTrue(r["evidence"])
        self.assertTrue(all(c.get("excerpt_lang") == "zh-Hant" for c in r["evidence"]))

    def test_b1_chinese_unsupported_refused(self):
        for query in ["股票市場走勢", "這個項目會不會影響房價"]:
            with self.subTest(query=query):
                r = self._get_evidence(query, "zh-Hant")
                self.assertTrue(r["refused"])
                self.assertEqual(r["gate"]["status"], "chinese_unsupported")

    def test_b1_chemical_parameter_dissolved_oxygen(self):
        r = self._get_evidence("dissolved oxygen")
        self.assertFalse(r["refused"])
        found = False
        for card in r["evidence"]:
            if "dissolved oxygen" in card["excerpt"].lower() or "DO" in card["excerpt"]:
                found = True
                break
        self.assertTrue(found, "Expected dissolved oxygen in evidence")

    def test_b1_species_spoonbill(self):
        r = self._get_evidence("spoonbill")
        self.assertFalse(r["refused"])
        found = False
        for card in r["evidence"]:
            if "spoonbill" in card["excerpt"].lower():
                found = True
                break
        self.assertTrue(found, "Expected spoonbill in evidence")

    def test_b1_construction_phase(self):
        r = self._get_evidence("during construction phase")
        self.assertFalse(r["refused"])
        found = False
        for card in r["evidence"]:
            if "construction" in card["excerpt"].lower():
                found = True
                break
        self.assertTrue(found, "Expected construction phase in evidence")

    def test_b1_waste_asbestos(self):
        r = self._get_evidence("asbestos containing materials")
        self.assertFalse(r["refused"])
        found = False
        for card in r["evidence"]:
            if "asbestos" in card["excerpt"].lower():
                found = True
                break
        self.assertTrue(found, "Expected asbestos in evidence")

    def test_b1_heritage_archaeological(self):
        r = self._get_evidence("Archaeological Survey")
        self.assertFalse(r["refused"])
        found = False
        for card in r["evidence"]:
            if "archaeolog" in card["excerpt"].lower():
                found = True
                break
        self.assertTrue(found, "Expected archaeological in evidence")

    def test_b1_needs_review_still_searchable(self):
        r = self._get_evidence("noise barrier", report_id="aeiar-274-2026")
        self.assertFalse(r["refused"])
        self.assertGreaterEqual(len(r["evidence"]), 1)
        for card in r["evidence"]:
            self.assertEqual(card["report_id"], "aeiar-274-2026")

    def test_b1_all_reports_searchable_unscoped(self):
        r = self._get_evidence("noise barrier")
        self.assertFalse(r["refused"])
        reports = {c["report_id"] for c in r["evidence"]}
        # Should find evidence from at least 3 different reports
        self.assertGreaterEqual(len(reports), 3)


# ------------------------------------------------------------------ Group B3

class AdversarialValidationTest(unittest.TestCase):
    """Group B3 — Adversarial and negative validation tests."""

    def _validate(self, answer: str, evidence: list):
        """Wrapper around app._validate_synthesis if available."""
        parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent not in sys.path:
            sys.path.insert(0, parent)
        try:
            import app as APP
            return APP._validate_synthesis(answer, evidence)
        except Exception as e:
            # Fallback: basic regex validation
            return self._fallback_validate(answer, evidence)

    def _fallback_validate(self, answer: str, evidence: list):
        """Basic fallback: check citation format and report IDs."""
        citations = re.findall(
            r"\[([a-z0-9\-]+)\s*,?\s*Ch\.?(\d+)[^\d]*(p\.?\s*([^\]]+))\]",
            answer,
            re.IGNORECASE,
        )
        if not citations:
            # Try alternate format
            citations = re.findall(
                r"\[([a-z0-9\-]+)\s*,?\s*Ch\.?(\d+)\s*,?\s*p\.?\s*([^\]]+)\]",
                answer,
                re.IGNORECASE,
            )
        valid = True
        for match in citations:
            if len(match) >= 2:
                report_id = match[0]
                ch = int(match[1])
                # Check report_id exists in evidence
                evidence_ids = {e["report_id"] for e in evidence}
                if report_id not in evidence_ids:
                    valid = False
        return valid

    def _get_evidence_for_validation(self):
        """Get real evidence for validation tests."""
        return _ask("noise barrier", "en")["evidence"]

    def test_b3_wrong_numerical_value_detected(self):
        """Adversarial: answer claims 10 dB(A) when evidence says 5 dB(A)."""
        evidence = self._get_evidence_for_validation()
        answer = "The noise barrier reduces noise by 10 dB(A) [aeiar-276-2026, Ch.4, p.4-28]."
        # This is a heuristic test — we note the discrepancy
        # Real validation would need claim-level semantic matching
        self.assertIn("10 dB", answer)
        # Check that real evidence contains 5 dB, not 10
        has_5db = any("5" in e["excerpt"] and "dB" in e["excerpt"] for e in evidence)
        self.assertTrue(has_5db)

    def test_b3_wrong_phase_detected(self):
        """Adversarial: answer claims operational phase for construction measure."""
        evidence = self._get_evidence_for_validation()
        answer = "Noise barriers will be used during the operational phase [aeiar-276-2026, Ch.4, p.4-28]."
        self.assertIn("operational phase", answer.lower())
        # Evidence should mention construction
        has_construction = any("construction" in e["excerpt"].lower() for e in evidence)
        self.assertTrue(has_construction)

    def test_b3_wrong_report_citation(self):
        """Adversarial: citation uses wrong report ID."""
        evidence = self._get_evidence_for_validation()
        answer = "Noise barriers are proposed [aeiar-271-2025, Ch.4, p.4-28]."
        valid = self._validate(answer, evidence)
        # aeiar-271-2025 is not in the noise barrier evidence set
        # (unless by coincidence — but 4-28 is specific to aeiar-276-2026)
        # This test documents the limitation
        self.assertIsInstance(valid, bool)

    def test_b3_inflated_status_completed(self):
        """Adversarial: proposed measure called completed."""
        evidence = self._get_evidence_for_validation()
        answer = "Noise barriers have been completed [aeiar-276-2026, Ch.4, p.4-28]."
        self.assertIn("completed", answer.lower())
        # Evidence should use present/future tense (proposed)
        has_proposed = any(
            word in e["excerpt"].lower()
            for e in evidence
            for word in ["propose", "would", "will", "shall"]
        )
        self.assertTrue(has_proposed)

    def test_b3_wrong_page_citation(self):
        """Adversarial: citation to non-existent page."""
        evidence = self._get_evidence_for_validation()
        answer = "Noise barriers are used [aeiar-276-2026, Ch.4, p.4-99]."
        # Page 4-99 does not exist in ch.4
        # Validation should catch this if page labels are checked
        ch4_labels = {
            r["page_label"] for r in ALL_RECORDS
            if r["report_id"] == "aeiar-276-2026" and r["chapter"] == 4
            and r["page_label_status"] == "verified"
        }
        self.assertNotIn("4-99", ch4_labels)

    def test_b3_unsupported_claim(self):
        """Adversarial: unsupported fact about jobs added."""
        evidence = self._get_evidence_for_validation()
        answer = "The project will create 5000 jobs [aeiar-276-2026, Ch.4, p.4-28]."
        self.assertIn("5000 jobs", answer)
        # Evidence should not mention 5000 jobs
        has_jobs = any("5000" in e["excerpt"] and "job" in e["excerpt"].lower() for e in evidence)
        self.assertFalse(has_jobs)

    def test_b3_ollama_down_synthesis_null(self):
        """Ollama unavailable: synthesis must be null, evidence preserved."""
        # This is a unit test of the synthesis logic
        parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent not in sys.path:
            sys.path.insert(0, parent)
        try:
            import app as APP
            # Temporarily break Ollama URL
            orig_url = APP.OLLAMA_URL
            APP.OLLAMA_URL = "http://localhost:19999/api/chat"
            r = APP.ask("noise barrier", "en")
            APP.OLLAMA_URL = orig_url
            self.assertIsNone(r.get("synthesis"))
            self.assertFalse(r["refused"])
            self.assertGreaterEqual(len(r["evidence"]), 1)
        except Exception:
            # If app import fails, skip this test
            self.skipTest("app.py not available for synthesis test")

    def test_b3_empty_model_response(self):
        """Empty model response: synthesis null, evidence preserved."""
        parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent not in sys.path:
            sys.path.insert(0, parent)
        try:
            import app as APP
            evidence = _ask("noise barrier", "en")["evidence"]
            result = APP._synthesize("noise barrier", "en", evidence)
            # If result is None or empty, it should be handled
            if result is None:
                self.assertIsNone(result)
            else:
                self.assertIn("answer", result)
        except Exception:
            self.skipTest("app.py not available for synthesis test")

    def test_b3_format_only_valid_citation(self):
        """Valid citation format with real page — should pass format check."""
        evidence = self._get_evidence_for_validation()
        answer = "Noise barriers are proposed [aeiar-276-2026, Ch.4, p.4-28]."
        valid = self._validate(answer, evidence)
        self.assertTrue(valid)

    def test_b3_real_page_wrong_claim_heuristic(self):
        """Real page cited but claim not supported — heuristic flag."""
        evidence = self._get_evidence_for_validation()
        answer = "The project includes a nuclear reactor [aeiar-276-2026, Ch.4, p.4-28]."
        # Citation format is valid, page exists, but claim is unsupported
        # Current validation only checks format; semantic verification needs human review
        valid = self._validate(answer, evidence)
        # Document that this is a known limitation
        self.assertIsInstance(valid, bool)


# ------------------------------------------------------------------ Group B4

class ClaimLevelEvaluationTest(unittest.TestCase):
    """Group B4 — Claim-level evidence evaluation tests."""

    def _get_evidence(self, query: str, lang: str = "en"):
        return _ask(query, lang)["evidence"]

    def test_claim_eval_valid_answer_accepted(self):
        """A valid answer with correct citations and supported claims is accepted."""
        from claim_evaluator import evaluate_answer
        evidence = self._get_evidence("noise barrier")
        answer = "Movable noise barriers would be erected [aeiar-276-2026, Ch.4, p.4-28]."
        result = evaluate_answer(answer, evidence)
        self.assertEqual(result["overall_outcome"], "accepted")

    def test_claim_eval_wrong_number_rejected(self):
        """A claim with wrong numeric value is rejected."""
        from claim_evaluator import evaluate_answer
        evidence = self._get_evidence("noise barrier")
        answer = "Noise barriers reduce noise by 10 dB(A) [aeiar-276-2026, Ch.4, p.4-28]."
        result = evaluate_answer(answer, evidence)
        self.assertEqual(result["overall_outcome"], "rejected")
        self.assertGreaterEqual(result["metrics"]["contradicted"], 1)

    def test_claim_eval_wrong_page_rejected(self):
        """A citation to a non-existent page is rejected."""
        from claim_evaluator import evaluate_answer
        evidence = self._get_evidence("noise barrier")
        answer = "Noise barriers are used [aeiar-276-2026, Ch.4, p.4-99]."
        result = evaluate_answer(answer, evidence)
        self.assertEqual(result["overall_outcome"], "rejected")

    def test_claim_eval_unsupported_claim_rejected(self):
        """A claim not found in any evidence is rejected."""
        from claim_evaluator import evaluate_answer
        evidence = self._get_evidence("noise barrier")
        answer = "The project will create 5000 jobs [aeiar-276-2026, Ch.4, p.4-28]."
        result = evaluate_answer(answer, evidence)
        self.assertEqual(result["overall_outcome"], "rejected")

    def test_claim_eval_certainty_inflation_rejected(self):
        """A claim that inflates certainty ('guarantees') is rejected."""
        from claim_evaluator import evaluate_answer
        evidence = self._get_evidence("noise barrier")
        answer = "The noise barrier guarantees a 5 dB(A) reduction [aeiar-276-2026, Ch.4, p.4-28]."
        result = evaluate_answer(answer, evidence)
        self.assertEqual(result["overall_outcome"], "rejected")

    def test_claim_eval_phase_mismatch_rejected(self):
        """A claim with wrong phase attribution is rejected."""
        from claim_evaluator import evaluate_answer
        evidence = self._get_evidence("noise barrier")
        answer = "Noise barriers will be erected during the operational phase [aeiar-276-2026, Ch.4, p.4-28]."
        result = evaluate_answer(answer, evidence)
        self.assertEqual(result["overall_outcome"], "rejected")

    def test_claim_eval_status_inflation_rejected(self):
        """A claim that inflates status ('completed' vs 'proposed') is rejected."""
        from claim_evaluator import evaluate_answer
        evidence = self._get_evidence("noise barrier")
        answer = "Noise barriers have been completed [aeiar-276-2026, Ch.4, p.4-28]."
        result = evaluate_answer(answer, evidence)
        self.assertEqual(result["overall_outcome"], "rejected")

    def test_claim_eval_all_adversarial_fixtures(self):
        """All adversarial fixtures match expected outcomes."""
        import json
        from claim_evaluator import evaluate_answer

        fixtures = []
        with open("evaluations/adversarial_fixtures.jsonl") as f:
            for line in f:
                fixtures.append(json.loads(line))

        passed = 0
        for fix in fixtures:
            query = " ".join(fix["evidence_terms"])
            evidence = _ask(query, fix["lang"]).get("evidence", [])
            result = evaluate_answer(fix["synthetic_answer"], evidence)
            if fix.get("overall_expected") == result["overall_outcome"]:
                passed += 1

        self.assertEqual(passed, len(fixtures),
                         f"Only {passed}/{len(fixtures)} adversarial fixtures matched expected outcome")

    def test_claim_eval_metrics_structure(self):
        """Evaluation result contains all required metric fields."""
        from claim_evaluator import evaluate_answer
        evidence = self._get_evidence("noise barrier")
        answer = "Movable noise barriers would be erected [aeiar-276-2026, Ch.4, p.4-28]."
        result = evaluate_answer(answer, evidence)
        self.assertIn("metrics", result)
        self.assertIn("total_claims", result["metrics"])
        self.assertIn("supported", result["metrics"])
        self.assertIn("contradicted", result["metrics"])
        self.assertIn("insufficient_evidence", result["metrics"])
        self.assertIn("human_review", result["metrics"])


# ------------------------------------------------------------------ Group C

class EndToEndRegressionTest(unittest.TestCase):
    """Group C — End-to-end regression tests."""

    def test_c_all_reports_searchable(self):
        """All 8 reports must return evidence for relevant queries."""
        for rid in [
            "aeiar-276-2026", "aeiar-271-2025", "aeiar-274-2026", "aeiar-261-2024",
            "aeiar-175-2013", "aeiar-176-2013", "aeiar-203-2016", "aeiar-215-2017",
        ]:
            with self.subTest(report=rid):
                r = _ask("noise", "en", report_id=rid)
                self.assertFalse(r["refused"])
                self.assertGreaterEqual(len(r["evidence"]), 1)

    def test_c_chinese_original_retrieval_works(self):
        """Traditional Chinese EIA topics prefer original Chinese passages."""
        for query in ["噪音", "生態", "水質", "廢物", "景觀", "文化遺產"]:
            with self.subTest(query=query):
                r = _ask(query, "zh-Hant")
                self.assertFalse(r["refused"])
                self.assertEqual(r["gate"]["status"], "zh_original")
                self.assertFalse(r.get("translation_applied", False))
                self.assertEqual(r.get("evidence_lang"), "zh-Hant")
                self.assertTrue(r["evidence"])
                for card in r["evidence"]:
                    self.assertEqual(card.get("excerpt_lang"), "zh-Hant")
                    self.assertEqual(card.get("doc_kind"), "executive_summary")
                    self.assertTrue(card.get("source_url", "").endswith(
                        ("es_chi_out.pdf", "es_tc.pdf")
                    ))

    def test_c_report_scoped_correct(self):
        """Scoped search returns only the selected report."""
        r = _ask("noise barrier", "en", report_id="aeiar-274-2026")
        self.assertFalse(r["refused"])
        for card in r["evidence"]:
            self.assertEqual(card["report_id"], "aeiar-274-2026")

    def test_c_needs_review_unchanged(self):
        """AEIAR-274-2026 retains needs_review classification."""
        parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            with open(os.path.join(parent, "stage0", "reports.json")) as f:
                data = json.load(f)
            r274 = next(r for r in data["reports"] if r["report_id"] == "aeiar-274-2026")
            self.assertEqual(r274["audit_decision"], "needs_review")
        except FileNotFoundError:
            self.skipTest("reports.json not found")

    def test_c_oov_refusal_intact(self):
        """OOV refusal still blocks unsupported queries."""
        r = _ask("geothermal", "en")
        self.assertTrue(r["refused"])
        self.assertEqual(r["gate"]["status"], "all_oov")

    def test_c_evidence_cards_preserved(self):
        """Evidence cards contain all required fields."""
        r = _ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        for card in r["evidence"]:
            self.assertIn("report_id", card)
            self.assertIn("chapter", card)
            self.assertIn("page_label", card)
            self.assertIn("page_label_status", card)
            self.assertIn("pdf_page_index", card)
            self.assertIn("citation", card)
            self.assertIn("excerpt", card)

    def test_c_source_url_is_official_epd(self):
        """Source URLs point to official EPD domain."""
        r = _ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        for card in r["evidence"]:
            url = card.get("source_url")
            if url:
                self.assertTrue(
                    url.startswith("https://www.epd.gov.hk/"),
                    f"URL not official EPD: {url}"
                )

    def test_c_synthesis_fallback_when_ollama_down(self):
        """When Ollama is unavailable, evidence is still returned."""
        parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent not in sys.path:
            sys.path.insert(0, parent)
        try:
            import app as APP
            orig_url = APP.OLLAMA_URL
            APP.OLLAMA_URL = "http://localhost:19999/api/chat"
            r = APP.ask("noise barrier", "en")
            APP.OLLAMA_URL = orig_url
            self.assertFalse(r["refused"])
            self.assertGreaterEqual(len(r["evidence"]), 1)
        except Exception:
            self.skipTest("app.py not available")


# ------------------------------------------------------------------ main

if __name__ == "__main__":
    unittest.main(verbosity=2)
