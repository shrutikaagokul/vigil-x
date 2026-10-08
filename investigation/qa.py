"""
Restricted Investigator Q&A Engine for Vigil-X.

Enforces a strict whitelist of structured retrieval operations.
NO arbitrary SQL, NO arbitrary Python execution, NO unrestricted database access.
Answers are generated strictly from the validated EvidencePacket.
"""
from __future__ import annotations

import re
import sqlite3
from typing import Any, Dict, List, Tuple

from contracts.investigation import (
    EvidencePacket,
    QuestionResponse,
    get_current_as_of,
)
from investigation.evidence_packet import build_evidence_packet


ALLOWED_INTENTS = {
    "WHY_FLAGGED": ["why", "flagged", "prioritized", "reasons", "score", "risk score"],
    "SUPPORTING_CLAIMS": ["claim", "supporting claims", "cpt", "procedure", "billed"],
    "RELATED_PROVIDERS": ["related providers", "providers", "doctor", "colleague", "partners"],
    "NETWORK_CONNECTIONS": ["network", "connections", "links", "hub", "ring", "graph", "subgraph"],
    "FINANCIAL_EXPOSURE": ["financial", "exposure", "money", "dollars", "amount", "overpayment", "cost"],
    "MEMBER_IMPACT": ["member", "patient", "impact", "affected", "beneficiary"],
    "TIMELINE": ["timeline", "chronology", "when", "history", "dates"],
    "RULE_EVIDENCE": ["rule", "evidence", "rules fired", "indicators", "matched"],
    "FUTURE_RISK": ["future", "velocity", "trajectory", "forward risk", "future risk"],
    "BENIGN_EXPLANATIONS": ["benign", "false positive", "explanation", "legitimate", "modifier"],
}


INJECTION_PATTERNS = [
    r"\bselect\b.*\bfrom\b",
    r"\bdrop\b\s+\btable\b",
    r"\bdelete\b\s+\bfrom\b",
    r"\bupdate\b.*\bset\b",
    r"\binsert\b\s+\binto\b",
    r"\bunion\b\s+\bselect\b",
    r"\bexec(?:ute)?\b",
    r"\bignore\b\s+.*\binstructions\b",
    r"\bsystem\s+prompt\b",
    r"__import__",
    r"\beval\s*\(",
    r"\bos\.system\b",
]


def _match_whitelist_intent(question: str) -> Tuple[str, List[str]]:
    """Match question text to allowed structured retrieval intents."""
    q_lower = question.lower()

    for pat in INJECTION_PATTERNS:
        if re.search(pat, q_lower):
            return "UNKNOWN", []

    for intent, keywords in ALLOWED_INTENTS.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", q_lower):
                return intent, keywords
    return "UNKNOWN", []


def answer_investigator_question(
    conn: sqlite3.Connection,
    case_id: str,
    question: str,
) -> QuestionResponse:
    """
    Answer an investigator's question using ONLY whitelisted structured retrieval.
    """
    packet = build_evidence_packet(conn, case_id)
    intent, _ = _match_whitelist_intent(question)

    grounded_facts: Dict[str, Any] = {}
    citations: List[str] = []

    if intent == "WHY_FLAGGED":
        reasons_text = "; ".join(packet.top_reasons) if packet.top_reasons else "Elevated anomaly indicators"
        answer = (
            f"Case {packet.case_id} was prioritized for human investigation due to an overall risk score of "
            f"{packet.risk_score:.1f}/100 (confidence: {packet.confidence * 100:.0f}%). "
            f"Key triggers: {reasons_text}."
        )
        grounded_facts = {
            "risk_score": packet.risk_score,
            "top_reasons": packet.top_reasons,
            "rules_triggered": packet.cited_rule_ids,
        }
        citations = packet.cited_rule_ids

    elif intent == "SUPPORTING_CLAIMS":
        claims_list = packet.relevant_claims[:5]
        if claims_list:
            c_summaries = [
                f"{c.get('claim_id')}: {c.get('procedure_code', 'N/A')} on {c.get('service_date', 'N/A')} (${float(c.get('paid_amount', 0.0)):,.2f})"
                for c in claims_list
            ]
            answer = f"Found {len(packet.cited_claim_ids)} total supporting claims. Top records:\n" + "\n".join(c_summaries)
        else:
            answer = f"Found {len(packet.cited_claim_ids)} cited claim IDs in case evidence ledger."
        grounded_facts = {"total_claims": len(packet.cited_claim_ids), "sample_claims": claims_list}
        citations = [str(c.get("claim_id")) for c in claims_list if c.get("claim_id")]

    elif intent == "RELATED_PROVIDERS":
        other_providers = [p for p in packet.cited_provider_ids if p != packet.entity_id]
        if other_providers:
            answer = f"Provider {packet.entity_name} ({packet.entity_id}) is connected to {len(other_providers)} other provider(s): {', '.join(other_providers)}."
        else:
            answer = f"Provider {packet.entity_name} ({packet.entity_id}) does not currently have documented co-conspirator or shared provider links."
        grounded_facts = {"focal_provider": packet.entity_id, "connected_providers": other_providers}
        citations = other_providers

    elif intent == "NETWORK_CONNECTIONS":
        net_summary = packet.network_evidence.get("summary", {})
        total_nodes = net_summary.get("total_nodes", len(packet.cited_provider_ids))
        total_edges = net_summary.get("total_edges", 0)
        answer = (
            f"Network subgraph for {packet.entity_id} contains {total_nodes} node(s) and {total_edges} edge(s). "
            f"Structural network risk component is {packet.risk_components.get('network_risk', 0.0):.2f}."
        )
        grounded_facts = packet.network_evidence.get("summary", {})
        citations = [f"Node-{n.get('id')}" for n in packet.network_evidence.get("nodes", [])[:5]]

    elif intent == "FINANCIAL_EXPOSURE":
        answer = (
            f"The estimated financial exposure is ${packet.exposure_high:,.2f} "
            f"(lower bound: ${packet.exposure_low:,.2f}, upper bound: ${packet.exposure_high:,.2f})."
        )
        grounded_facts = {
            "exposure_low": packet.exposure_low,
            "exposure_high": packet.exposure_high,
        }
        citations = [f"${packet.exposure_high:,.2f}"]

    elif intent == "MEMBER_IMPACT":
        answer = f"A total of {packet.members_affected} member(s)/patient(s) are associated with the flagged claims in this case."
        grounded_facts = {"members_affected": packet.members_affected}
        citations = [f"{packet.members_affected} members"]

    elif intent == "TIMELINE":
        t_items = packet.timeline[:5]
        t_str = "\n".join([f"• {t.get('date')}: {t.get('description')}" for t in t_items]) if t_items else "No activity recorded."
        answer = f"Chronological timeline of events:\n{t_str}"
        grounded_facts = {"timeline_events": t_items}
        citations = [str(t.get("date")) for t in t_items if t.get("date")]

    elif intent == "RULE_EVIDENCE":
        ev_items = [f"• {a.get('rule_id')}: {a.get('severity')} severity (${float(a.get('est_dollars', 0)):,.2f} exposure)" for a in packet.rule_alerts[:5]]
        answer = f"The following {len(packet.cited_rule_ids)} rule(s) fired on this entity:\n" + "\n".join(ev_items)
        grounded_facts = {"rules_fired": packet.cited_rule_ids, "rule_alerts": packet.rule_alerts}
        citations = packet.cited_rule_ids

    elif intent == "FUTURE_RISK":
        signals = packet.future_risk_signals or ["No compounding future velocity detected."]
        answer = "Future risk evaluation: " + " ".join(signals)
        grounded_facts = {"future_signals": signals}
        citations = ["future_risk"]

    elif intent == "BENIGN_EXPLANATIONS":
        benign_str = "\n".join([f"• {b}" for b in packet.benign_explanations])
        answer = f"Potential benign explanations or documentation considerations to verify:\n{benign_str}"
        grounded_facts = {"benign_explanations": packet.benign_explanations}
        citations = ["fp_notes"]

    else:
        allowed_list = ", ".join([k.lower().replace("_", " ") for k in ALLOWED_INTENTS.keys()])
        answer = (
            f"The query is outside the whitelisted investigation retrieval scope. "
            f"Allowed question topics include: {allowed_list}. "
            f"Free-form SQL or ungrounded queries are prohibited by system policy."
        )
        grounded_facts = {"allowed_intents": list(ALLOWED_INTENTS.keys())}
        citations = []

    return QuestionResponse(
        case_id=case_id,
        question=question,
        matched_intent=intent,
        answer=answer,
        grounded_facts=grounded_facts,
        citations=citations,
        as_of=get_current_as_of(),
        synthetic=True,
    )
