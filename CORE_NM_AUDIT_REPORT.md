# NORTHWISE `core_nm` EIA Report Audit Report

**Date:** 2026-10-18
**Auditor:** NORTHWISE agent
**Sources:** EPD EIA register (`epd.gov.hk/eia/en/register/`), nm.gov.hk Four Zones pages

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Proposed `core_nm` reports | 8 |
| **Verified `core_nm`** | **7** |
| `needs_review` | 1 |
| `exclude_from_core_nm` | 0 |
| Historical (pre-2021 NM concept) | 4 |

**All 8 EPD register entries were successfully accessed and verified.**

---

## Audit Method

1. **EPD verification:** Each report's `aspd.php` project page was fetched to confirm title, register number, approval status, and date.
2. **NM zone verification:** The four nm.gov.hk zone pages were fetched to confirm each project's development area is explicitly listed.
3. **Strict assessment:** Each project was evaluated against the `core_nm` definition: *"explicitly part of, or located within, a Northern Metropolis development area"*. A matching place name alone was not treated as sufficient; the project's nature (development vs. infrastructure) was also considered.
4. **Duplicate/overlap check:** Related projects were compared to determine whether they are distinct scopes or duplicate records.
5. **Historical flagging:** Projects approved before the 2021 NM Policy Address were flagged but not auto-excluded.

---

## Per-Record Audit Table

| Register No. | Project Title | NM Area | Decision | Historical | Rationale |
|-------------|---------------|---------|----------|------------|-----------|
| AEIAR-276/2026 | Northern Metropolis Highway – San Tin Section | San Tin Technopole | **verified_core_nm** | No | Title explicitly says "Northern Metropolis". Approved 2026 under NM programme. Unambiguous. |
| AEIAR-271/2025 | Development at Ngau Tam Mei Area | Ngau Tam Mei NDA | **verified_core_nm** | No | Title names Ngau Tam Mei, listed on nm.gov.hk. Approved 2025. Unambiguous. |
| AEIAR-274/2026 | Development of the Loop – Eastern Connection Road | HSITP in the Loop | **needs_review** | No | Road/infrastructure project within Loop area. Core development is AEIAR-176/2013. Under strict criteria, infrastructure may be `related_nm`. But it is explicitly part of the Loop programme and approved 2026. Requires human judgment. |
| AEIAR-261/2024 | San Tin / Lok Ma Chau Development Node | San Tin Technopole | **verified_core_nm** | No | Title names San Tin, listed on nm.gov.hk. Approved 2024. Unambiguous. |
| AEIAR-175/2013 | North East New Territories New Development Areas | Kwu Tung North / Fanling North NDA | **verified_core_nm** | Yes (2013) | Covers two NDAs now on nm.gov.hk Boundary Commerce & Industry Zone. Pre-dates NM concept (2021) but now formally incorporated. 2026 Policy Address references "all nine NDAs" as NM fruition. |
| AEIAR-176/2013 | Development of Lok Ma Chau Loop | HSITP in the Loop | **verified_core_nm** | Yes (2013) | Loop is on nm.gov.hk Innovation & Technology Zone. Pre-dates NM but now formally incorporated. Active EM&A confirms ongoing status. |
| AEIAR-203/2016 | Hung Shui Kiu New Development Area | HSK/HT NDA | **verified_core_nm** | Yes (2016) | HSK/HT NDA is on nm.gov.hk High-end Professional Services Hub. Pre-dates NM but now formally incorporated. |
| AEIAR-215/2017 | Housing Sites in Yuen Long South | YLS NDA | **verified_core_nm** | Yes (2017) | YLS NDA is on nm.gov.hk High-end Professional Services Hub. Pre-dates NM but now formally incorporated. |

---

## Duplicate / Overlap Assessment

| Relationship | Assessment |
|--------------|------------|
| AEIAR-276/2026 (highway) ↔ AEIAR-261/2024 (development node) | **Distinct, not duplicate.** The highway serves the node. Both are currently in the live app. |
| AEIAR-274/2026 (Loop road) ↔ AEIAR-176/2013 (Loop development) | **Distinct, not duplicate.** The road is infrastructure for the Loop development. Both are separate scopes. |
| AEIAR-175/2013 (NENT NDAs) | **Single report, two areas.** Covers Kwu Tung North AND Fanling North together. No separate EIA reports found for each NDA. Counts as **one report**. |
| AEIAR-176/2013 (Lok Ma Chau Loop) | **Single report.** Two study briefs existed (2008 and 2011) but only one EIA report. Counts as **one report**. |

---

## Historical Projects (Pre-2021 NM Concept)

The Northern Metropolis concept was announced in the **2021 Policy Address** (October 2021). Four of the verified reports pre-date this announcement:

| Report | Approval | Years pre-NM | Inclusion Rationale |
|--------|----------|-------------|---------------------|
| AEIAR-175/2013 | 2013 | 8 | KTN/FLN NDAs are now explicitly listed on nm.gov.hk as part of the Boundary Commerce & Industry Zone. The 2026 Policy Address describes "all nine New Development Areas" as NM fruition. |
| AEIAR-176/2013 | 2013 | 8 | Lok Ma Chau Loop is explicitly listed on nm.gov.hk as HSITP in the Loop. Active EM&A and project website confirm ongoing implementation under NM. |
| AEIAR-203/2016 | 2016 | 5 | HSK/HT NDA is explicitly listed on nm.gov.hk. Now formally part of NM. |
| AEIAR-215/2017 | 2017 | 4 | YLS NDA is explicitly listed on nm.gov.hk. Now formally part of NM. |

**Rationale for inclusion:** These projects were not originally conceived as "Northern Metropolis" projects, but they are now formally incorporated into the NM spatial plan as shown on the official nm.gov.hk website. Excluding them would under-represent the actual development footprint of the Northern Metropolis. Users searching for NM environmental impacts would expect these reports to be included.

---

## Approval Status Reality Check

**Important:** An approved EIA report does **not** mean the project is built or operational. It means the environmental impact has been assessed and approved (with conditions). Construction requires separate Environmental Permits and may proceed in phases.

| Report | Approval Date | Current Status from EPD |
|--------|--------------|------------------------|
| AEIAR-276/2026 | 2026-04-24 | Approved with conditions |
| AEIAR-271/2025 | 2025-06-27 | Approved with conditions |
| AEIAR-274/2026 | 2026-05-21 | Approved with conditions |
| AEIAR-261/2024 | 2024-05-17 | Approved with conditions; active EM&A submissions through 2026 |
| AEIAR-175/2013 | 2013-10-18 | Approved with conditions; active EM&A through 2026 |
| AEIAR-176/2013 | 2013-10-25 | Approved with conditions; active EM&A through 2026 |
| AEIAR-203/2016 | 2016-10-28 | Approved with conditions |
| AEIAR-215/2017 | 2017-11-24 | Approved with conditions |

---

## Limitations

1. **Title-based matching:** Projects were identified by scanning EIA report titles for NM-related place names. Reports with non-obvious titles may have been missed.
2. **No full-text review:** Project scope was not verified by reading the full EIA report text. Assessment relies on EPD project page metadata.
3. **NM source only:** Area membership was verified only against nm.gov.hk "Four Zones" pages. Statutory Outline Zoning Plans or gazettes were not checked.
4. **Register completeness:** Only the first 33 pages of the EPD EIA register were checked (324 reports). Additional pages may exist.
5. **Dynamic status:** EPD approval status and EM&A activity change over time. This audit reflects the status on 2026-10-18.

---

## Recommendation

**Import into live app:** The 7 `verified_core_nm` reports should be imported into NORTHWISE. The 1 `needs_review` report (AEIAR-274/2026) should be held pending a decision on whether infrastructure projects within NM areas count as `core_nm` or `related_nm`.

If the decision is to include infrastructure, all 8 reports become `core_nm`.
If the decision is to exclude infrastructure, AEIAR-274/2026 moves to `related_nm` and the count becomes 7 `core_nm` + 1 `related_nm`.

No reports were excluded from the proposed set.
