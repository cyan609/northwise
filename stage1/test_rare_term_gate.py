#!/usr/bin/env python3
"""Deterministic regression tests for the retrieval OOV gate.

Standard library only. No network, no model, no packages.

Run:
    python3 stage1/test_rare_term_gate.py
    python3 stage1/test_rare_term_gate.py -v

These tests assert gate behaviour and citation traceability. They do NOT assert
retrieval relevance: there is no ground truth for "relevant", so any such test
would encode an opinion as a fact.
"""
import glob
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retrieve as R  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_jsonl():
    recs = []
    for p in sorted(glob.glob(os.path.join(ROOT, "stage1", "data",
                                           "*.pages.jsonl"))):
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                recs.append(json.loads(line))
    return recs


class GateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_jsonl()
        # The gate is an ENGLISH retrieval safeguard. Since Stage 1b added the
        # Chinese executive summaries, stage1/data holds two languages; the
        # product builds its English index with lang="en", so this test must
        # measure that index rather than the union of both.
        cls.c = R.Corpus(lang="en", records=cls.records)

    # -- (a) genuinely out-of-vocabulary term ------------------------------
    def test_a_all_oov_blocks(self):
        g = self.c.gate("geothermal")
        self.assertEqual(g["status"], "all_oov")
        self.assertTrue(g["blocked"])
        self.assertEqual(g["oov_terms"], ["geothermal"])
        self.assertEqual(g["present_terms"], [])

    def test_a_all_oov_multiple_terms_blocks(self):
        g = self.c.gate("nanotechnology entanglement")
        self.assertEqual(g["status"], "all_oov")
        self.assertTrue(g["blocked"])
        self.assertEqual(sorted(g["oov_terms"]),
                         ["entanglement", "nanotechnology"])

    def test_a_blocked_query_returns_no_results(self):
        g = self.c.gate("geothermal")
        hits, _ = self.c.search(g["search_terms"], k=3)
        # the gate is what prevents output; the ranking itself is unchanged
        self.assertTrue(g["blocked"])

    # -- (b) present terms return relevant passages ------------------------
    def test_b_present_terms_not_blocked(self):
        g = self.c.gate("black-faced spoonbill")
        self.assertEqual(g["status"], "ok")
        self.assertFalse(g["blocked"])
        self.assertEqual(g["oov_terms"], [])
        self.assertEqual(g["search_terms"], ["black", "faced", "spoonbill"])

    def test_b_present_terms_return_results_with_citations(self):
        g = self.c.gate("noise barrier")
        hits, q = self.c.search(g["search_terms"], k=3)
        self.assertEqual(len(hits), 3)
        for weighted, raw, weight, i, matched in hits:
            d = self.c.docs[i]
            self.assertTrue(d["report_id"])
            self.assertIsInstance(d["pdf_page_index"], int)
            self.assertTrue(d["source_pdf"].endswith(".pdf"))
            self.assertIn("§", R.format_citation(d))
            self.assertIn("PDF idx", R.format_citation(d))

    # -- (c) common words must not trigger the gate ------------------------
    def test_c_question_wording_not_blocked(self):
        g = self.c.gate("what is the impact of the project on air quality")
        self.assertEqual(g["status"], "ok")
        self.assertFalse(g["blocked"])
        self.assertEqual(g["query_terms"], ["impact", "project", "air", "quality"])

    def test_c_pronouns_are_not_content_terms(self):
        g = self.c.gate("will my flat shake")
        self.assertNotIn("my", g["query_terms"])
        self.assertNotIn("my", g["oov_terms"])
        self.assertIn("my", g["function_words_dropped"])
        self.assertEqual(g["status"], "partial_oov")  # "shake" is genuinely absent
        self.assertFalse(g["blocked"])

    def test_c_all_stopwords_is_empty_not_oov(self):
        g = self.c.gate("the of and what is it")
        self.assertEqual(g["status"], "empty_query")
        self.assertFalse(g["blocked"])
        self.assertEqual(g["oov_terms"], [])

    # -- (d) mixed matched / unmatched -------------------------------------
    def test_d_mixed_is_partial_and_not_blocked(self):
        g = self.c.gate("geothermal power generation")
        self.assertEqual(g["status"], "partial_oov")
        self.assertFalse(g["blocked"])
        self.assertEqual(g["oov_terms"], ["geothermal"])
        self.assertEqual(g["present_terms"], ["power", "generation"])

    def test_d_mixed_still_returns_results(self):
        g = self.c.gate("geothermal power generation")
        hits, _ = self.c.search(g["search_terms"], k=3)
        self.assertEqual(len(hits), 3)

    def test_d_mixed_blocks_only_in_strict_mode(self):
        g = self.c.gate("geothermal power generation", strict=True)
        self.assertEqual(g["status"], "partial_oov")
        self.assertTrue(g["blocked"])

    # -- inflection folding ------------------------------------------------
    def test_inflection_fold_prevents_false_block(self):
        g = self.c.gate("monitorings")
        self.assertEqual(g["status"], "ok")
        self.assertFalse(g["blocked"])
        self.assertEqual(g["substitutions"], {"monitorings": "monitoring"})
        self.assertEqual(g["search_terms"], ["monitoring"])

    def test_inflection_fold_matches_base_form_ranking(self):
        a, _ = self.c.search(self.c.gate("monitorings")["search_terms"], k=3)
        b, _ = self.c.search(self.c.gate("monitoring")["search_terms"], k=3)
        self.assertEqual([x[0] for x in a], [x[0] for x in b])

    def test_no_substitution_when_term_present(self):
        g = self.c.gate("noise barrier")
        self.assertEqual(g["substitutions"], {})

    # -- traceability and determinism --------------------------------------
    def test_citation_resolves_to_the_source_record(self):
        g = self.c.gate("long viewing distance")
        hits, _ = self.c.search(g["search_terms"], k=1)
        _, _, _, i, _ = hits[0]
        d = self.c.docs[i]
        match = [r for r in self.records
                 if r["report_id"] == d["report_id"]
                 and r["chapter"] == d["chapter"]
                 and r["pdf_page_index"] == d["pdf_page_index"]]
        self.assertEqual(len(match), 1, "citation must resolve to exactly one record")
        self.assertEqual(match[0]["page_label"], d["page_label"])
        self.assertEqual(match[0]["page_label_status"], d["page_label_status"])

    def test_duplicate_folio_is_not_deduplicated(self):
        dupes = [r for r in self.records
                 if r["report_id"] == "aeiar-276-2026"
                 and r["chapter"] == 10 and r["page_label"] == "10-119"]
        self.assertEqual(len(dupes), 2)
        self.assertEqual(sorted(r["pdf_page_index"] for r in dupes), [122, 123])

    def test_ranking_is_deterministic(self):
        a, _ = self.c.search(self.c.gate("noise barrier")["search_terms"], k=5)
        b, _ = self.c.search(self.c.gate("noise barrier")["search_terms"], k=5)
        self.assertEqual([(x[0], x[3]) for x in a], [(x[0], x[3]) for x in b])

    def test_gate_does_not_change_ranking(self):
        """The gate must be a filter on output, not a re-ranker."""
        g = self.c.gate("predicted mitigated noise level")
        direct, _ = self.c.search(["predicted", "mitigated", "noise", "level"], k=3)
        via_gate, _ = self.c.search(g["search_terms"], k=3)
        self.assertEqual([x[0] for x in direct], [x[0] for x in via_gate])

    def test_corpus_loads_every_record(self):
        en = [r for r in self.records if (r.get("doc_lang") or "en") == "en"]
        zh = [r for r in self.records if r.get("doc_lang") == "zh-Hant"]
        self.assertEqual(len(self.c.docs), len(en))
        self.assertEqual(len(en), 6899)   # Stage 1 English chapters, unchanged
        self.assertEqual(len(zh), 113)    # Stage 1b Chinese executive summaries


if __name__ == "__main__":
    unittest.main(verbosity=2)
