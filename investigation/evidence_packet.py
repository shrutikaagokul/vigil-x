"""
Evidence Packet Builder for Vigil-X.

Constructs structured, tamper-proof evidence packets from SQLite.
The LLM and verifier interact ONLY with this validated packet.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Set

from contracts.investigation import EvidencePacket, get_current_as_of
from db.queries import get_case_by_id, get_case_network, get_case_timeline


def build_evidence_packet(conn: sqlite3.Connection, case_id: str) -> EvidencePacket:
    """
    Construct a verified, structured EvidencePacket for a given case.

    Raises:
        ValueError: if case_id is not found in database.
    """
    case = get_case_by_id(conn, case_id)
    if not case:
        raise ValueError(f"Case '{case_id}' not found.")

    # Collect cited factual identifiers for verifier boundaries
    cited_claims: Set[str] = set()
    cited_providers: Set[str] = {case.entity_id}
    cited_members: Set[str] = set()
    cited_rules: Set[str] = set()
    cited_networks: Set[str] = set()
    if case.network_id:
        cited_networks.add(case.network_id)

    # Rule alerts
    rule_alerts_list = []
    for a in case.alerts:
        rule_id = str(a.get("rule_id", ""))
        if rule_id:
            cited_rules.add(rule_id)
        c_ids = a.get("claim_ids", [])
        for cid in c_ids:
            if cid:
                cited_claims.add(str(cid))
        rule_alerts_list.append(a)

    # Relevant claims
    relevant_claims = []
    for cl in case.claims:
        cid = str(cl.get("claim_id", ""))
        if cid:
            cited_claims.add(cid)
        pid = str(cl.get("provider_id", ""))
        if pid:
            cited_providers.add(pid)
        mid = str(cl.get("member_id", ""))
        if mid:
            cited_members.add(mid)
        relevant_claims.append(cl)

    # Evidence items
    for ev in case.evidence:
        if ev.rule_id:
            cited_rules.add(ev.rule_id)
        if ev.claim_id:
            cited_claims.add(ev.claim_id)
        if ev.entity_id:
            cited_providers.add(ev.entity_id)

    # Network context
    net_data = get_case_network(conn, case_id)
    if net_data.get("network_id"):
        cited_networks.add(str(net_data["network_id"]))
    for n in net_data.get("nodes", []):
        nid = str(n.get("id", ""))
        if nid:
            cited_providers.add(nid)

    # ML Evidence if available from claim_ml
    ml_evidence: List[Dict[str, Any]] = []
    if cited_claims:
        sub_claims = list(cited_claims)[:50]
        placeholders = ", ".join(["?"] * len(sub_claims))
        ml_rows = conn.execute(
            f"SELECT claim_id, anomaly_score, ml_prediction, model_version FROM claim_ml WHERE claim_id IN ({placeholders});",
            sub_claims,
        ).fetchall()
        for r in ml_rows:
            ml_evidence.append(dict(r))

    # Standard clinical/investigation limitations & benign explanations
    benign_notes = list(case.benign_explanations)
    if not benign_notes:
        benign_notes = [
            "Consider shared group practice NPI billing conventions.",
            "Verify whether clinical modifiers (59, 25, 50) were appropriately documented.",
            "Review patient rural residence and travel logs before formal action.",
        ]

    limitations = [
        "Analytical indicators are based on synthetic payer claims data.",
        "System does not confirm fraud; human SIU review is mandatory.",
        "Ground truth labels were strictly isolated from detection logic.",
    ]

    future_signals = []
    if case.future_risk and isinstance(case.future_risk, dict):
        vel = case.future_risk.get("future_velocity_risk")
        if vel:
            future_signals.append(f"Elevated billing velocity metric ({vel:.1f}/100) indicates compounding exposure if unchecked.")

    return EvidencePacket(
        case_id=case.case_id,
        entity_type=case.entity_type,
        entity_id=case.entity_id,
        entity_name=case.entity_name,
        risk_score=case.risk_score,
        risk_components=case.risk_components,
        evidence_strength=case.evidence_strength,
        confidence=case.confidence,
        exposure=case.exposure_high,
        exposure_low=case.exposure_low,
        exposure_high=case.exposure_high,
        members_affected=case.members_affected,
        top_reasons=case.top_reasons,
        rule_alerts=rule_alerts_list,
        ml_evidence=ml_evidence,
        network_evidence=net_data,
        timeline=case.timeline,
        relevant_claims=relevant_claims,
        benign_explanations=benign_notes,
        future_risk_signals=future_signals,
        limitations=limitations,
        cited_claim_ids=sorted(list(cited_claims)),
        cited_provider_ids=sorted(list(cited_providers)),
        cited_member_ids=sorted(list(cited_members)),
        cited_rule_ids=sorted(list(cited_rules)),
        cited_network_ids=sorted(list(cited_networks)),
        as_of=get_current_as_of(),
        synthetic=True,
    )
