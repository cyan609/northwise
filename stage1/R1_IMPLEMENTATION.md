# R1 Implementation: Section Ref Recovery for `table_fragmented` Passages

## Changes

### `stage1/passages.py`

1. **Added `TOC_RE` regex** (line ~92) and **`looks_like_toc_line()`** helper:
   - Detects dot leaders (`...`), lines ending with a 1–3 digit page/folio number, or roman-numeral folios.
   - Does NOT reject short lines or headings — a genuine `2.1 Introduction` on a table page is accepted.

2. **Extended ref-computation block** in `build_page_passages` to cover `table_fragmented`:
   - Same logic as `prose_paragraph`/`heading` (first anchor in the passage, `MULTI_REF` guard for ambiguous sequences).
   - Additional `looks_like_toc_line` guard prevents assigning a ref from a TOC entry.

### `stage1/test_passages.py`

Three new regression tests:
- `test_table_fragmented_with_anchor_gets_section_ref` — sample #9 (`aeiar-276-2026|c2|p14|s0`) now gets `§2.6.5.1`.
- `test_toc_list_does_not_get_section_ref` — sample #15 (`aeiar-271-2025|c15|p0|s0`) remains `None`.
- `test_table_fragmented_multi_ref_is_ambiguous` — merged refs (e.g. `aeiar-271-2025|c4|p20|s0`) stay `ambiguous_multiple_refs`.

---

## Counts

| Passage type | Total | With `section_ref` (after) | Without | Change |
|--------------|-------|---------------------------|---------|--------|
| `table_fragmented` | 343 | **46** | 297 | **+46** |
| `prose_paragraph` | 2,941 | 2,941 | 0 | 0 |
| `heading` | 233 | 233 | 0 | 0 |
| `prose_continuation` | 383 | 0 | 383 | 0 |
| `prose_page` | 191 | 0 | 191 | 0 |
| `list` | 65 | 0 | 65 | 0 |

Of the 46 newly assigned refs:
- **43** have status `own` (single, unambiguous anchor).
- **3** have status `ambiguous_multiple_refs` (merged paragraph starts in the extraction; correctly flagged).

**No passage text, IDs, line ranges, or page-level provenance changed.** Verified by `test_passage_ids_are_stable_across_rebuilds` and zero mismatches in 200-page spot check.

---

## Remaining Citation Risks (not addressed by R1)

1. **`prose_page` passages with table content** (16 passages contain `"Table "` + 4-digit numbers; 11 pages fuse multiple tables). These remain typed as `prose_page` with no `fragmented` flag. No section ref is computed because they lack numbered paragraph anchors. **Mitigation:** R2 (search-time `likely_table` caution) is still pending.

2. **Table header scrambling** persists in both `table_fragmented` and `prose_page` tables. Row data is usually intact; column-specific claims remain unreliable without visual confirmation.

3. **`prose_continuation` passages cannot inherit section refs** because inheritance is page-scoped. 383 passages (8.4%) have no ref.

4. **Plain-numeric folios** (e.g., chapter 11 page `8`) create citation ambiguity across chapters.

---

## Test Results

```
python3 test_passages.py  → 26/26 OK  (8.5s)
python3 test_rare_term_gate.py → 19/19 OK  (5.7s)
```

---

## Diff Summary

```diff
+# TOC guard
+TOC_RE = re.compile(r'\.\s*\.\s*\.')
+def looks_like_toc_line(line): ...

# In build_page_passages:
 elif ptype == "table_fragmented":
     ref_line = None
     for line in seg_lines:
         r = anchor_ref(line, chapter)
         if r and not looks_like_toc_line(line):
             ref, ref_line = r, line
             break
     if ref and MULTI_REF.match(ref_line):
         ref_status = "ambiguous_multiple_refs"
     else:
         ref_status = "own" if ref else "not_detected"
```
