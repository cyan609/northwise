#!/usr/bin/env python3
"""
NORTHWISE Claim-Level Evidence Evaluator
========================================
Evaluates whether claims in a synthesized answer are supported by the
retrieved evidence passages.

Usage:
    from claim_evaluator import evaluate_answer
    result = evaluate_answer(answer, evidence)
    # result is a dict with claim-level outcomes and aggregate metrics

Deterministic checks:
- Citation metadata (report_id, chapter, page_label) exists in evidence
- Numeric values and units (heuristic — flags mismatches, does not block)
- Entity presence in evidence excerpts (heuristic)
- Phase/status terminology (heuristic)

Limitations:
- Semantic entailment is NOT fully automated. Claims with valid citations
  but unsupported content are flagged for human review.
- Numeric checks use regex extraction and may miss values in tables.
"""

import json
import re
from typing import Any


# ------------------------------------------------------------------ claim extraction

CLAIM_SPLIT_RE = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z])|\n+|\s*;\s*"
)

CITATION_RE = re.compile(
    r"\[([^\]]+?)\s*,\s*Ch\.?\s*(\d+)\s*,\s*p\.?\s*([^\]]+?)\]"
)

NUMERIC_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(dB\(A\)|dB|mg/L|mg/l|mg\s*/\s*L|m|metres?|meters?|%|percent|ha|hectares?|km|kilometres?|years?|year)"
)

STATUS_WORDS = {
    "proposed": ["proposed", "would", "will", "shall", "recommended", "suggested"],
    "completed": ["completed", "implemented", "finished", "done", "constructed"],
    "required": ["required", "shall", "must", "mandatory", "obligatory"],
    "operational": ["operational", "operation", "during operation"],
    "construction": ["construction", "during construction", "construct"],
}

CERTAINTY_STRONG = ["guarantee", "guarantees", "guaranteed", "will definitely", "certainly", "absolutely", "always"]
CERTAINTY_WEAK = ["can", "could", "may", "might", "would", "predicted", "expected", "estimated"]

STOPWORDS = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
             "have", "has", "had", "do", "does", "did", "will", "would", "could",
             "should", "may", "might", "can", "this", "that", "these", "those",
             "project", "report", "eia", "study", "assessment"}


def _check_certainty_inflation(claim: str, evidence_card: dict) -> dict:
    """Check if claim uses stronger certainty than evidence."""
    claim_lower = claim.lower()
    excerpt_lower = evidence_card.get("excerpt", "").lower()

    claim_strong = any(w in claim_lower for w in CERTAINTY_STRONG)
    evidence_weak = any(w in excerpt_lower for w in CERTAINTY_WEAK)

    if claim_strong and evidence_weak and not any(w in excerpt_lower for w in CERTAINTY_STRONG):
        return {
            "status": "flagged",
            "reason": "Claim uses strong certainty ('guarantee') but evidence uses weak certainty ('can/may')",
        }
    return {"status": "ok", "reason": ""}


def _check_global_entities(claim: str, all_evidence: list[dict]) -> dict:
    """Check if key noun phrases in claim appear anywhere in the evidence set."""
    phrases = re.findall(r'"([^"]{3,40})"', claim)
    phrases += re.findall(r"[A-Z][a-zA-Z\s]{2,25}[a-z]", claim)

    all_excerpt_text = " ".join(e.get("excerpt", "").lower() for e in all_evidence)

    missing = []
    for phrase in phrases:
        phrase_lower = phrase.lower().strip()
        words = phrase_lower.split()
        if len(words) >= 2 and not all(w in STOPWORDS for w in words):
            if phrase_lower not in all_excerpt_text:
                if not any(w in all_excerpt_text for w in words if w not in STOPWORDS and len(w) > 4):
                    missing.append(phrase)

    if missing:
        return {"status": "partial", "missing_phrases": missing}
    return {"status": "present", "missing_phrases": []}


def _split_claims(answer: str) -> list[str]:
    """Split an answer into atomic factual claims."""
    if not answer:
        return []
    # Remove citation markers for claim splitting, then restore
    raw_parts = CLAIM_SPLIT_RE.split(answer)
    claims = []
    for part in raw_parts:
        part = part.strip()
        if len(part) > 10:
            claims.append(part)
    return claims


def _extract_citations(claim: str) -> list[dict]:
    """Extract citations from a claim."""
    citations = []
    for m in CITATION_RE.finditer(claim):
        citations.append({
            "report_id": m.group(1).strip(),
            "chapter": int(m.group(2)),
            "page_label": m.group(3).strip(),
            "raw": m.group(0),
        })
    return citations


def _norm_dashes(s: str) -> str:
    return s.replace("\u2010", "-").replace("\u2011", "-").replace(
        "\u2012", "-"
    ).replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")


def _find_evidence_for_citation(
    citation: dict, evidence: list[dict]
) -> dict | None:
    """Find the matching evidence card for a citation."""
    cite_pl = _norm_dashes(citation["page_label"])
    for card in evidence:
        rid_match = card.get("report_id") == citation["report_id"]
        ch_match = str(card.get("chapter", "")) == str(citation["chapter"])
        pl_match = _norm_dashes(str(card.get("page_label") or "")) == cite_pl
        if rid_match and ch_match and pl_match:
            return card
    return None


def _extract_numerics(text: str) -> list[dict]:
    """Extract numeric values with units from text."""
    results = []
    for m in NUMERIC_RE.finditer(text):
        results.append({
            "value": float(m.group(1)),
            "unit": m.group(2).lower(),
            "raw": m.group(0),
        })
    return results


def _normalise_unit(unit: str) -> str:
    """Normalise unit strings for comparison."""
    u = unit.lower().strip()
    if u in ("metre", "metres", "meter", "meters", "m"):
        return "m"
    if u in ("db(a)", "dba"):
        return "db(a)"
    if u in ("mg/l", "mg / l", "mg l-1"):
        return "mg/l"
    if u in ("percent", "%"):
        return "%"
    if u in ("hectare", "hectares", "ha"):
        return "ha"
    if u in ("kilometre", "kilometres", "km"):
        return "km"
    if u in ("year", "years"):
        return "year"
    return u


def _check_numeric_consistency(
    claim: str, evidence_card: dict
) -> dict:
    """Check if numerics in claim are consistent with evidence."""
    claim_nums = _extract_numerics(claim)
    evidence_nums = _extract_numerics(evidence_card.get("excerpt", ""))

    if not claim_nums or not evidence_nums:
        return {"status": "no_numeric", "details": []}

    mismatches = []
    for cn in claim_nums:
        found_match = False
        for en in evidence_nums:
            if _normalise_unit(cn["unit"]) == _normalise_unit(en["unit"]):
                # Allow small tolerance for rounding
                if abs(cn["value"] - en["value"]) < 0.5:
                    found_match = True
                    break
        if not found_match:
            mismatches.append({
                "claim_value": cn["value"],
                "claim_unit": cn["unit"],
                "evidence_values": [
                    {"value": e["value"], "unit": e["unit"]}
                    for e in evidence_nums
                ],
            })

    if mismatches:
        return {"status": "mismatch", "details": mismatches}
    return {"status": "consistent", "details": []}


def _check_entity_presence(claim: str, evidence_card: dict) -> dict:
    """Heuristic: check if key entities from claim appear in evidence excerpt."""
    # Strip markdown bold markers so section headers like "**Prohibition**"
    # do not create false entity mismatches.
    claim_clean = claim.replace("**", "")
    # Extract capitalised phrases (potential named entities)
    entities = re.findall(r"[A-Z][a-zA-Z\s]{2,20}", claim_clean)
    entities = [e.strip() for e in entities if len(e.strip()) > 3]

    excerpt = evidence_card.get("excerpt", "").lower()
    missing = []
    for ent in entities[:3]:  # Check top 3 entities
        ent_lower = ent.lower()
        if ent_lower not in excerpt and ent_lower.split()[0] not in excerpt:
            missing.append(ent)

    if missing:
        return {"status": "partial", "missing_entities": missing}
    return {"status": "present", "missing_entities": []}


def _check_phase_status(claim: str, evidence_card: dict) -> dict:
    """Heuristic: check if phase/status claims match evidence wording."""
    claim_lower = claim.lower()
    excerpt_lower = evidence_card.get("excerpt", "").lower()

    # Check for status inflation
    if any(w in claim_lower for w in STATUS_WORDS["completed"]):
        if not any(w in excerpt_lower for w in STATUS_WORDS["completed"]):
            if any(w in excerpt_lower for w in STATUS_WORDS["proposed"]):
                return {
                    "status": "flagged",
                    "reason": "Claim says 'completed' but evidence says 'proposed'",
                }

    # Check for phase mismatch
    claim_has_construction = any(w in claim_lower for w in STATUS_WORDS["construction"])
    claim_has_operational = any(w in claim_lower for w in STATUS_WORDS["operational"])
    evidence_has_construction = any(w in excerpt_lower for w in STATUS_WORDS["construction"])
    evidence_has_operational = any(w in excerpt_lower for w in STATUS_WORDS["operational"])

    if claim_has_construction and not evidence_has_construction and evidence_has_operational:
        return {
            "status": "flagged",
            "reason": "Claim says construction but evidence says operational",
        }
    if claim_has_operational and not evidence_has_operational and evidence_has_construction:
        return {
            "status": "flagged",
            "reason": "Claim says operational but evidence says construction",
        }

    return {"status": "ok", "reason": ""}


# ------------------------------------------------------------------ public API


def evaluate_claim(claim: str, evidence: list[dict]) -> dict:
    """Evaluate a single claim against the evidence set.

    Returns:
        {
            "claim_text": str,
            "citations": list[dict],
            "citation_valid": bool,
            "matching_evidence": list[dict],
            "numeric_check": dict,
            "entity_check": dict,
            "phase_status_check": dict,
            "outcome": "supported" | "contradicted" | "insufficient_evidence" | "human_review",
            "reason": str,
        }
    """
    citations = _extract_citations(claim)

    if not citations:
        return {
            "claim_text": claim,
            "citations": [],
            "citation_valid": False,
            "matching_evidence": [],
            "numeric_check": {},
            "entity_check": {},
            "phase_status_check": {},
            "outcome": "no_citation",
            "reason": "No citation found in claim",
        }

    # Check all citations are valid
    matching_evidence = []
    all_valid = True
    for cite in citations:
        card = _find_evidence_for_citation(cite, evidence)
        if card:
            matching_evidence.append(card)
        else:
            all_valid = False

    if not all_valid:
        return {
            "claim_text": claim,
            "citations": citations,
            "citation_valid": False,
            "matching_evidence": matching_evidence,
            "numeric_check": {},
            "entity_check": {},
            "phase_status_check": {},
            "outcome": "insufficient_evidence",
            "reason": "Citation points to evidence not in retrieved set",
        }

    # Run heuristic checks on the first matching evidence card
    primary_card = matching_evidence[0]

    numeric_result = _check_numeric_consistency(claim, primary_card)
    entity_result = _check_entity_presence(claim, primary_card)
    phase_result = _check_phase_status(claim, primary_card)
    certainty_result = _check_certainty_inflation(claim, primary_card)
    global_entity_result = _check_global_entities(claim, evidence)

    # Determine outcome
    if numeric_result["status"] == "mismatch":
        outcome = "contradicted"
        reason = f"Numeric mismatch: {numeric_result['details']}"
    elif phase_result["status"] == "flagged":
        outcome = "contradicted"
        reason = phase_result["reason"]
    elif certainty_result["status"] == "flagged":
        outcome = "contradicted"
        reason = certainty_result["reason"]
    elif global_entity_result["status"] == "partial":
        # Key phrases missing from ALL evidence — strong signal of unsupported claim
        outcome = "insufficient_evidence"
        reason = f"Key phrases not found in any evidence: {global_entity_result['missing_phrases']}"
    elif entity_result["status"] == "partial":
        # Entities missing from primary excerpt — flag for human review
        outcome = "human_review"
        reason = f"Entities in claim not found in evidence excerpt: {entity_result['missing_entities']}"
    else:
        outcome = "supported"
        reason = "Citation valid and heuristic checks pass"

    return {
        "claim_text": claim,
        "citations": citations,
        "citation_valid": True,
        "matching_evidence": [
            {
                "report_id": c["report_id"],
                "chapter": c["chapter"],
                "page_label": c["page_label"],
            }
            for c in matching_evidence
        ],
        "numeric_check": numeric_result,
        "entity_check": entity_result,
        "phase_status_check": phase_result,
        "certainty_check": certainty_result,
        "global_entity_check": global_entity_result,
        "outcome": outcome,
        "reason": reason,
    }


def evaluate_answer(answer: str, evidence: list[dict]) -> dict:
    """Evaluate all claims in an answer.

    Returns:
        {
            "answer": str,
            "claims": list[dict],
            "metrics": {
                "total_claims": int,
                "supported": int,
                "contradicted": int,
                "insufficient_evidence": int,
                "human_review": int,
            },
            "overall_outcome": "accepted" | "flagged" | "rejected",
            "flagged_claims": list[dict],
        }
    """
    claims = _split_claims(answer)
    evaluated = [evaluate_claim(c, evidence) for c in claims]

    metrics = {
        "total_claims": len(evaluated),
        "supported": sum(1 for e in evaluated if e["outcome"] == "supported"),
        "contradicted": sum(1 for e in evaluated if e["outcome"] == "contradicted"),
        "insufficient_evidence": sum(1 for e in evaluated if e["outcome"] == "insufficient_evidence"),
        "human_review": sum(1 for e in evaluated if e["outcome"] == "human_review"),
        "no_citation": sum(1 for e in evaluated if e["outcome"] == "no_citation"),
    }

    cited_evaluated = [e for e in evaluated if e["outcome"] != "no_citation"]
    flagged = [e for e in evaluated if e["outcome"] in ("contradicted", "insufficient_evidence", "human_review")]

    # Overall outcome logic
    # Only cited claims can trigger rejection; structural sentences without
    # citations are expected in synthesis and are neutral.
    if metrics["contradicted"] > 0:
        overall = "rejected"
    elif metrics["insufficient_evidence"] > 0:
        overall = "rejected"
    elif metrics["human_review"] > 1 and (metrics["human_review"] / max(len(cited_evaluated), 1)) > 0.25:
        overall = "flagged"
    else:
        overall = "accepted"

    return {
        "answer": answer,
        "claims": evaluated,
        "metrics": metrics,
        "overall_outcome": overall,
        "flagged_claims": flagged,
    }


# ------------------------------------------------------------------ test helpers


def evaluate_adversarial_fixture(fixture: dict, evidence: list[dict]) -> dict:
    """Evaluate an adversarial fixture against expected outcomes."""
    result = evaluate_answer(fixture["synthetic_answer"], evidence)

    # Compare with expected
    expected = fixture.get("expected_claim_evaluations", [])
    checks = []
    for i, exp in enumerate(expected):
        if i < len(result["claims"]):
            actual = result["claims"][i]
            checks.append({
                "expected_outcome": exp["expected_outcome"],
                "actual_outcome": actual["outcome"],
                "match": exp["expected_outcome"] == actual["outcome"],
            })

    return {
        "fixture_id": fixture["fixture_id"],
        "result": result,
        "expected_overall": fixture.get("overall_expected"),
        "actual_overall": result["overall_outcome"],
        "claim_checks": checks,
        "overall_match": fixture.get("overall_expected") == result["overall_outcome"],
    }


if __name__ == "__main__":
    # Quick self-test
    test_evidence = [
        {
            "report_id": "aeiar-276-2026",
            "chapter": 4,
            "page_label": "4-28",
            "excerpt": "Movable noise barriers would be erected to provide screening from the construction plant. Noise barriers can reduce the noise level by 5 dB(A).",
        }
    ]

    # Test valid answer
    result = evaluate_answer(
        "Movable noise barriers would be erected [aeiar-276-2026, Ch.4, p.4-28].",
        test_evidence
    )
    print("Valid answer:", result["overall_outcome"])
    assert result["overall_outcome"] == "accepted"

    # Test wrong number
    result = evaluate_answer(
        "Noise barriers reduce noise by 10 dB(A) [aeiar-276-2026, Ch.4, p.4-28].",
        test_evidence
    )
    print("Wrong number:", result["overall_outcome"])
    assert result["overall_outcome"] == "rejected"

    # Test wrong page
    result = evaluate_answer(
        "Noise barriers reduce noise [aeiar-276-2026, Ch.4, p.4-99].",
        test_evidence
    )
    print("Wrong page:", result["overall_outcome"])
    assert result["overall_outcome"] == "rejected"

    print("All self-tests passed.")
