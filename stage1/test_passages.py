#!/usr/bin/env python3
"""Deterministic regression tests for paragraph-level passages.

Standard library only. No network, no model, no packages.

Run:
    python3 stage1/test_passages.py
    python3 stage1/test_passages.py -v

These assert segmentation, provenance and label handling. They do NOT assert
retrieval relevance: there is no ground truth for "relevant", so such a test
would encode an opinion as a fact.
"""
import hashlib
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import passages as P  # noqa: E402

ID_RE = re.compile(r"^[a-z0-9\-]+\|c(?:[A-Za-z0-9]+|None)\|p\d+\|s\d+$")


class PassageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = P.load_records()
        cls.corpus = P.R.Corpus()
        cls.idx = P.PassageIndex(cls.corpus)
        cls.ps = cls.idx.passages
        cls.by_page = {}
        for p in cls.ps:
            cls.by_page.setdefault(
                (p["report_id"], p["chapter"], p["pdf_page_index"]), []).append(p)

    # -- segmentation ------------------------------------------------------
    def test_every_page_yields_at_least_one_passage(self):
        self.assertEqual(len(self.by_page), len(self.records))
        self.assertGreater(len(self.by_page), 6000)  # 8 reports, ~6900 pages

    def test_numbered_anchors_split_a_page(self):
        # ch.8 idx 6 is a page with 8 numbered paragraphs and 3 headings
        got = self.by_page[("aeiar-276-2026", 8, 6)]
        self.assertEqual(len(got), 8)
        self.assertTrue(all(p["passage_type"] == "prose_paragraph" for p in got))
        self.assertTrue(all(p["section_ref"] for p in got))

    def test_passages_are_contiguous_slices_of_their_page(self):
        """The strongest provenance check: text == lines[start:end]."""
        checked = 0
        for (rid, ch, idx), group in list(self.by_page.items())[:200]:
            rec = self.records[(rid, ch, idx)]
            lines, _ = P.strip_page_extras(rec["text"], ch)
            for p in group:
                expected = "\n".join(lines[p["line_start"]:p["line_end"]])
                self.assertEqual(p["text"], expected, p["passage_id"])
                checked += 1
        self.assertGreater(checked, 300)  # first 200 pages from 8 reports

    def test_no_passage_crosses_a_page(self):
        for p in self.ps:
            rec = self.records[(p["report_id"], p["chapter"], p["pdf_page_index"])]
            lines, _ = P.strip_page_extras(rec["text"], p["chapter"])
            self.assertLessEqual(p["line_end"], len(lines), p["passage_id"])
            self.assertLessEqual(p["line_start"], p["line_end"], p["passage_id"])

    def test_table_page_is_one_flagged_passage(self):
        # a page the classifier already tags as a table must not be split
        group = self.by_page[("aeiar-276-2026", 3, 47)]
        self.assertEqual(len(group), 1)
        self.assertEqual(group[0]["passage_type"], "table_fragmented")
        self.assertIn("fragmented", group[0]["quality_flags"])

    def test_list_page_is_one_flagged_passage(self):
        group = self.by_page[("aeiar-276-2026", 1, 0)]   # TOC page
        self.assertEqual(len(group), 1)
        self.assertEqual(group[0]["passage_type"], "list")
        self.assertIn("fragmented", group[0]["quality_flags"])

    def test_heading_only_passages_are_typed_and_flagged(self):
        heads = [p for p in self.ps if p["passage_type"] == "heading"]
        self.assertGreater(len(heads), 100)
        for p in heads[:50]:
            self.assertIn("heading_only", p["quality_flags"])
            self.assertFalse(p["text"].rstrip().endswith("."))

    # -- provenance --------------------------------------------------------
    def test_passage_ids_are_unique_and_well_formed(self):
        ids = [p["passage_id"] for p in self.ps]
        self.assertEqual(len(ids), len(set(ids)))
        for i in ids[:500]:
            self.assertRegex(i, ID_RE)

    def test_passage_ids_are_stable_across_rebuilds(self):
        again = P.build_all(self.corpus, self.records)
        self.assertEqual([p["passage_id"] for p in again],
                         [p["passage_id"] for p in self.ps])
        self.assertEqual([p["text"] for p in again],
                         [p["text"] for p in self.ps])

    def test_page_text_hash_matches_source_record(self):
        for p in self.ps[:300]:
            rec = self.records[(p["report_id"], p["chapter"], p["pdf_page_index"])]
            want = hashlib.sha256((rec["text"] or "").encode("utf-8")).hexdigest()
            self.assertEqual(p["page_text_sha256"], want, p["passage_id"])
            self.assertEqual(p["source_sha256"], rec["source_sha256"])

    def test_required_provenance_fields_present(self):
        required = ("passage_id", "report_id", "report_title", "chapter",
                    "chapter_title", "section_ref", "page_label",
                    "page_label_status", "pdf_page_index", "passage_type",
                    "quality_flags", "text", "line_start", "line_end",
                    "source_pdf", "source_sha256", "page_text_sha256")
        for p in self.ps[:300]:
            for k in required:
                self.assertIn(k, p)
            self.assertIsInstance(p["pdf_page_index"], int)

    # -- labels ------------------------------------------------------------
    def test_unverified_labels_are_preserved_not_invented(self):
        null_pages = {(r["report_id"], r["chapter"], r["pdf_page_index"])
                      for r in self.records.values() if not r.get("page_label")}
        self.assertGreater(len(null_pages), 100)  # some pages genuinely lack printed folios
        for key in null_pages:
            for p in self.by_page[key]:
                self.assertIsNone(p["page_label"])
                self.assertIn("no_verified_folio", p["quality_flags"])
                self.assertFalse(p["page_label_verified"])

    def test_label_is_always_copied_from_source(self):
        for p in self.ps[:600]:
            rec = self.records[(p["report_id"], p["chapter"], p["pdf_page_index"])]
            self.assertEqual(p["page_label"], rec.get("page_label"))
            self.assertEqual(p["page_label_status"], rec.get("page_label_status"))

    def test_null_label_citation_states_the_gap(self):
        for p in self.by_page[("aeiar-276-2026", 15, 3)]:
            c = P.passage_citation(p)
            self.assertIn("no printed folio", c)
            self.assertIn("PDF idx 3", c)
            self.assertIn("absent", c)

    # -- boilerplate -------------------------------------------------------
    def test_repeated_headers_are_removed_and_recorded(self):
        pages_with_repeats = [p for p in self.ps
                              if p["page_boilerplate_removed"]["repeated_header"] > 0]
        self.assertGreater(len(pages_with_repeats), 0)
        for p in self.ps:
            for line in p["text"].split("\n"):
                self.assertFalse(
                    any(pat.match(line.strip()) for pat in P.R.HEADER_PATTERNS),
                    f'header survived in {p["passage_id"]}: {line!r}')

    def test_month_footer_does_not_become_a_passage(self):
        """A bare month-year footer must never survive as a passage of its own.

        The rule only removes the LAST line of a page, because a month-year can
        be legitimate content in the middle of one — the sign page carries
        "March 2026" and "16 March 2026" in its cover block.
        """
        for p in self.ps:
            self.assertIsNone(P.MONTH_FOOTER.match(p["text"].strip()),
                              f'footer became a passage: {p["passage_id"]}')
        # the page that previously produced a "March 2026" passage
        for p in self.by_page[("aeiar-276-2026", 5, 38)]:
            self.assertNotIn("March 2026", p["text"])
            self.assertEqual(p["page_boilerplate_removed"]["month_footer"], 1)

    def test_chapter_banner_removed(self):
        for key in [("aeiar-276-2026", 4, 3), ("aeiar-276-2026", 8, 4)]:
            for p in self.by_page[key]:
                self.assertFalse(p["text"].strip().isupper())

    # -- section references ------------------------------------------------
    def test_multi_ref_anchor_is_marked_ambiguous(self):
        group = self.by_page[("aeiar-276-2026", 10, 123)]
        self.assertEqual(group[0]["section_ref_status"], "ambiguous_multiple_refs")
        self.assertIn("(ambiguous)", P.passage_citation(group[0]))

    def test_table_fragmented_with_anchor_gets_section_ref(self):
        """R1: table_fragmented passages that open with a genuine paragraph
        anchor must receive a section_ref (sample #9 from visual validation)."""
        p = next(x for x in self.ps
                 if x["passage_id"] == "aeiar-276-2026|c2|p14|s0")
        self.assertEqual(p["passage_type"], "table_fragmented")
        self.assertEqual(p["section_ref"], "2.6.5.1")
        self.assertEqual(p["section_ref_status"], "own")
        self.assertIn("2.6.5.1", p["text"])

    def test_toc_list_does_not_get_section_ref(self):
        """R1 guard: TOC entries (dot leaders / trailing folio) must not be
        treated as paragraph anchors, even when they contain a section number
        (sample #15 from visual validation)."""
        p = next(x for x in self.ps
                 if x["passage_id"] == "aeiar-271-2025|c15|p0|s0")
        self.assertEqual(p["passage_type"], "list")
        self.assertIsNone(p["section_ref"])
        self.assertEqual(p["section_ref_status"], "not_detected")

    def test_table_fragmented_multi_ref_is_ambiguous(self):
        """R1: when a table_fragmented passage carries a merged multi-ref,
        it must be flagged ambiguous, not asserted as own."""
        p = next(x for x in self.ps
                 if x["passage_id"] == "aeiar-271-2025|c4|p20|s0")
        self.assertEqual(p["passage_type"], "table_fragmented")
        self.assertEqual(p["section_ref_status"], "ambiguous_multiple_refs")
        self.assertIn("(ambiguous)", P.passage_citation(p))

    def test_section_ref_is_literal(self):
        """A reference must appear verbatim at the start of a line."""
        for p in self.ps:
            if not p["section_ref"]:
                continue
            first = p["section_ref"].split(".")[0]
            self.assertEqual(str(p["chapter"]), first, p["passage_id"])
            self.assertTrue(
                any(line.strip().startswith(p["section_ref"] + " ")
                    for line in p["text"].split("\n")),
                p["passage_id"])

    def test_context_expansion_is_separate_and_provenanced(self):
        """Expansion must not be merged into the passage text."""
        p = next(x for x in self.ps
                 if x["passage_id"] == "aeiar-276-2026|c4|p30|s3")
        ctx = self.idx.context(p)
        self.assertEqual(ctx["prev"]["pdf_page_index"], p["pdf_page_index"] - 1)
        self.assertEqual(ctx["next"]["pdf_page_index"], p["pdf_page_index"] + 1)
        self.assertTrue(ctx["prev"]["text"])
        self.assertTrue(ctx["next"]["text"])
        # the passage itself is untouched, and the neighbours are not inside it
        self.assertNotIn(ctx["next"]["text"][:60], p["text"])
        self.assertNotIn("context", p)

    def test_context_is_absent_at_a_chapter_boundary(self):
        first = next(x for x in self.ps
                     if x["chapter"] == 4 and x["pdf_page_index"] == 0
                     and x["passage_type"] != "blank")
        ctx = self.idx.context(first)
        self.assertIsNone(ctx["prev"])
        self.assertIsNotNone(ctx["next"])

    # -- gate integration --------------------------------------------------
    def test_gate_is_unchanged_at_passage_level(self):
        self.assertEqual(self.idx.corpus.gate("geothermal")["status"], "all_oov")
        self.assertTrue(self.idx.corpus.gate("geothermal")["blocked"])
        partial = self.idx.corpus.gate("geothermal power generation")
        self.assertEqual(partial["status"], "partial_oov")
        self.assertFalse(partial["blocked"])          # no hard block by default
        self.assertTrue(self.idx.corpus.gate(
            "geothermal power generation", strict=True)["blocked"])

    def test_search_results_carry_full_provenance(self):
        gate = self.idx.corpus.gate("noise barrier")
        hits = self.idx.search(gate["search_terms"], k=3)
        self.assertEqual(len(hits), 3)
        for _, _, _, i, _ in hits:
            p = self.idx.passages[i]
            self.assertIn("PDF idx", P.passage_citation(p))
            self.assertIn("passage s", P.passage_citation(p))
            self.assertIsNotNone(p["page_text_sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
