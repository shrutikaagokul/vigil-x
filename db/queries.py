"""
Database query functions for Vigil-X investigation endpoints.
All queries return structured dictionaries or models with full provenance.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from contracts.investigation import (
    AuditLogEntry,
    CaseDetail,
    CaseEvidenceItem,
    CaseHeader,
    CaseStatus,
    PriorityLevel,
    QueueItem,
    SummaryFunnel,
    SummaryResponse,
    get_current_as_of,
)


def _parse_json_field(val: Any, default: Any = None) -> Any:
    """Parse JSON field stored in SQLite."""
    if default is None:
        default = []
    if val is None or val == "":
        return default
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default


def get_summary_metrics(conn: sqlite3.Connection) -> SummaryResponse:
    """Retrieve platform-wide summary and funnel metrics."""
    # Claims and paid total
    row_claims = conn.execute(
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(paid_amount), 0.0) AS total_paid FROM claims;"
    ).fetchone()
    claims_cnt = row_claims["cnt"] if row_claims else 0
    paid_total = round(row_claims["total_paid"], 2) if row_claims else 0.0

    # Claim lines
    row_lines = conn.execute("SELECT COUNT(*) AS cnt FROM claim_lines;").fetchone()
    lines_cnt = row_lines["cnt"] if (row_lines and row_lines["cnt"] > 0) else claims_cnt

    # Alerts
    row_alerts = conn.execute("SELECT COUNT(*) AS cnt FROM alerts;").fetchone()
    alerts_cnt = row_alerts["cnt"] if row_alerts else 0

    # Cases
    row_cases = conn.execute(
        """
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN entity_type = 'network' THEN 1 ELSE 0 END) AS net_cases,
            SUM(CASE WHEN entity_type != 'network' THEN 1 ELSE 0 END) AS ent_cases
        FROM cases;
        """
    ).fetchone()
    total_cases = row_cases["total"] if row_cases else 0
    net_cases = row_cases["net_cases"] if row_cases and row_cases["net_cases"] else 0
    ent_cases = row_cases["ent_cases"] if row_cases and row_cases["ent_cases"] else 0

    # Queue size
    row_q = conn.execute("SELECT COUNT(*) AS cnt FROM queue_items;").fetchone()
    queue_size = row_q["cnt"] if row_q else 0

    # Distinct rules fired
    row_rules = conn.execute("SELECT COUNT(DISTINCT rule_id) AS cnt FROM alerts;").fetchone()
    rules_fired = row_rules["cnt"] if row_rules else 0

    funnel = SummaryFunnel(
        claims_ingested=claims_cnt,
        rules_fired=rules_fired,
        alerts_produced=alerts_cnt,
        cases_formed=total_cases,
        queue_prioritized=queue_size,
    )

    return SummaryResponse(
        claims_analyzed=claims_cnt,
        lines_analyzed=lines_cnt,
        paid_total=paid_total,
        alerts_total=alerts_cnt,
        entity_cases=ent_cases,
        network_cases=net_cases,
        queue_size=queue_size,
        funnel=funnel,
        as_of=get_current_as_of(),
        synthetic=True,
    )


def get_queue_items(
    conn: sqlite3.Connection,
    capacity_hours: Optional[float] = None,
    horizon_days: Optional[int] = None,
    sort_by: str = "priority",
) -> List[QueueItem]:
    """
    Retrieve prioritized queue items with optional capacity and sorting.
    Supported sorts: 'priority', 'ev_per_hour', 'risk'.
    """
    order_clause = "rank ASC"
    if sort_by == "ev_per_hour":
        order_clause = "ev_per_hour DESC, risk DESC"
    elif sort_by == "risk":
        order_clause = "risk DESC, ev_per_hour DESC"

    cursor = conn.execute(
        f"""
        SELECT 
            case_id, rank, baseline_rank, entity_type, entity_id, entity_name,
            risk, priority, exposure_low, exposure_high, members_affected,
            severity, evidence_strength, confidence, effort_hours, ev_per_hour,
            slot, top_reasons
        FROM queue_items
        ORDER BY {order_clause};
        """
    )
    rows = cursor.fetchall()

    items: List[QueueItem] = []
    cumulative_hours = 0.0

    for r in rows:
        effort = float(r["effort_hours"] or 2.0)
        if capacity_hours is not None and (cumulative_hours + effort) > capacity_hours:
            break
        cumulative_hours += effort

        reasons = _parse_json_field(r["top_reasons"], [])

        items.append(QueueItem(
            case_id=r["case_id"],
            rank=r["rank"],
            baseline_rank=r["baseline_rank"],
            entity_type=r["entity_type"],
            entity_id=r["entity_id"],
            entity_name=r["entity_name"],
            risk=r["risk"],
            priority=PriorityLevel(r["priority"]) if r["priority"] in [p.value for p in PriorityLevel] else PriorityLevel.MEDIUM,
            exposure_low=r["exposure_low"],
            exposure_high=r["exposure_high"],
            members_affected=r["members_affected"],
            severity=r["severity"],
            evidence_strength=r["evidence_strength"],
            confidence=r["confidence"],
            effort_hours=effort,
            ev_per_hour=r["ev_per_hour"],
            slot=r["slot"],
            top_reasons=reasons,
        ))

    return items


def get_case_by_id(conn: sqlite3.Connection, case_id: str) -> Optional[CaseDetail]:
    """Retrieve full case details including evidence ledger, timeline, and claims."""
    c_row = conn.execute(
        """
        SELECT 
            case_id, entity_type, entity_id, entity_name, status, priority,
            risk_score, confidence, evidence_strength, exposure_low, exposure_high,
            members_affected, claims_count, why_flagged, top_reasons,
            benign_explanations, risk_components, future_risk, network_id,
            assigned_to, created_at, updated_at
        FROM cases
        WHERE case_id = ?;
        """,
        (case_id,),
    ).fetchone()

    if not c_row:
        return None

    # Retrieve case evidence items
    ev_cursor = conn.execute(
        """
        SELECT 
            evidence_id, rule_id, rule_name, claim_id, entity_id,
            field_name, field_value, plain_text, est_overpay, severity,
            source_table, source_artifact, timestamp, fp_notes
        FROM case_evidence
        WHERE case_id = ?
        ORDER BY est_overpay DESC;
        """,
        (case_id,),
    )
    evidence_items = [
        CaseEvidenceItem(
            evidence_id=e["evidence_id"],
            rule_id=e["rule_id"],
            rule_name=e["rule_name"],
            claim_id=e["claim_id"],
            entity_id=e["entity_id"],
            field_name=e["field_name"],
            field_value=e["field_value"],
            plain_text=e["plain_text"],
            est_overpay=e["est_overpay"],
            severity=e["severity"],
            source_table=e["source_table"],
            source_artifact=e["source_artifact"],
            timestamp=e["timestamp"],
            fp_notes=e["fp_notes"],
        )
        for e in ev_cursor.fetchall()
    ]

    # Retrieve associated alerts
    al_cursor = conn.execute(
        """
        SELECT alert_id, rule_id, rule_version, entity_type, entity_id, claim_ids, severity, est_dollars, fp_notes, metadata
        FROM alerts
        WHERE entity_id = ?;
        """,
        (c_row["entity_id"],),
    )
    alerts = []
    all_claim_ids = set()
    for al in al_cursor.fetchall():
        c_ids = _parse_json_field(al["claim_ids"], [])
        all_claim_ids.update(c_ids)
        alerts.append({
            "alert_id": al["alert_id"],
            "rule_id": al["rule_id"],
            "severity": al["severity"],
            "est_dollars": al["est_dollars"],
            "claim_ids": c_ids,
            "fp_notes": al["fp_notes"],
            "metadata": _parse_json_field(al["metadata"], {}),
        })

    # Retrieve relevant claims (up to 50)
    claims = []
    if all_claim_ids:
        placeholders = ", ".join(["?"] * min(len(all_claim_ids), 50))
        claim_sub = list(all_claim_ids)[:50]
        cl_cursor = conn.execute(
            f"""
            SELECT claim_id, member_id, provider_id, service_date, procedure_code, paid_amount, billed_amount, status
            FROM claims
            WHERE claim_id IN ({placeholders})
            ORDER BY service_date DESC;
            """,
            claim_sub,
        )
        claims = [dict(cl) for cl in cl_cursor.fetchall()]

    # Retrieve timeline events
    timeline = get_case_timeline(conn, case_id)

    # Network summary if attached
    network_summary = None
    if c_row["network_id"]:
        net_row = conn.execute(
            "SELECT * FROM networks WHERE network_id = ?;", (c_row["network_id"],)
        ).fetchone()
        if net_row:
            network_summary = dict(net_row)

    status_val = CaseStatus(c_row["status"]) if c_row["status"] in [s.value for s in CaseStatus] else CaseStatus.NEW
    prio_val = PriorityLevel(c_row["priority"]) if c_row["priority"] in [p.value for p in PriorityLevel] else PriorityLevel.MEDIUM

    return CaseDetail(
        case_id=c_row["case_id"],
        entity_type=c_row["entity_type"] or "provider",
        entity_id=c_row["entity_id"],
        entity_name=c_row["entity_name"] or f"Entity {c_row['entity_id']}",
        status=status_val,
        priority=prio_val,
        risk_score=float(c_row["risk_score"] or 0.0),
        confidence=float(c_row["confidence"] if c_row["confidence"] is not None else 0.85),
        evidence_strength=float(c_row["evidence_strength"] if c_row["evidence_strength"] is not None else 0.80),
        exposure_low=float(c_row["exposure_low"] or 0.0),
        exposure_high=float(c_row["exposure_high"] or 0.0),
        members_affected=int(c_row["members_affected"] or 0),
        claims_count=int(c_row["claims_count"] or 0),
        why_flagged=_parse_json_field(c_row["why_flagged"], []),
        top_reasons=_parse_json_field(c_row["top_reasons"], []),
        benign_explanations=_parse_json_field(c_row["benign_explanations"], []),
        risk_components=_parse_json_field(c_row["risk_components"], {}),
        future_risk=_parse_json_field(c_row["future_risk"], {}),
        network_id=c_row["network_id"],
        assigned_to=c_row["assigned_to"],
        created_at=c_row["created_at"] or get_current_as_of(),
        updated_at=c_row["updated_at"] or get_current_as_of(),
        alerts=alerts,
        evidence=evidence_items,
        timeline=timeline,
        network_summary=network_summary,
        claims=claims,
    )


def get_case_evidence_ledger(conn: sqlite3.Connection, case_id: str) -> List[CaseEvidenceItem]:
    """Return the evidence ledger for a given case with full provenance."""
    cursor = conn.execute(
        """
        SELECT 
            evidence_id, rule_id, rule_name, claim_id, entity_id,
            field_name, field_value, plain_text, est_overpay, severity,
            source_table, source_artifact, timestamp, fp_notes
        FROM case_evidence
        WHERE case_id = ?
        ORDER BY est_overpay DESC;
        """,
        (case_id,),
    )
    return [
        CaseEvidenceItem(
            evidence_id=e["evidence_id"],
            rule_id=e["rule_id"],
            rule_name=e["rule_name"],
            claim_id=e["claim_id"],
            entity_id=e["entity_id"],
            field_name=e["field_name"],
            field_value=e["field_value"],
            plain_text=e["plain_text"],
            est_overpay=e["est_overpay"],
            severity=e["severity"],
            source_table=e["source_table"],
            source_artifact=e["source_artifact"],
            timestamp=e["timestamp"],
            fp_notes=e["fp_notes"],
        )
        for e in cursor.fetchall()
    ]


def get_case_timeline(conn: sqlite3.Connection, case_id: str) -> List[Dict[str, Any]]:
    """Return chronological activity timeline for the case entity."""
    case_row = conn.execute("SELECT entity_id, entity_type FROM cases WHERE case_id = ?;", (case_id,)).fetchone()
    if not case_row:
        return []

    entity_id = case_row["entity_id"]
    timeline: List[Dict[str, Any]] = []

    # Get sample claim dates for this provider
    claim_cursor = conn.execute(
        """
        SELECT service_date, COUNT(*) as claim_count, SUM(paid_amount) as total_paid
        FROM claims
        WHERE provider_id = ?
        GROUP BY service_date
        ORDER BY service_date DESC
        LIMIT 20;
        """,
        (entity_id,),
    )
    for row in claim_cursor.fetchall():
        timeline.append({
            "event_type": "CLAIMS_BATCH",
            "date": row["service_date"],
            "description": f"Processed {row['claim_count']} claims totalling ${row['total_paid']:,.2f}.",
            "amount": row["total_paid"],
        })

    # Get alerts triggering dates
    ev_cursor = conn.execute(
        """
        SELECT rule_id, rule_name, plain_text, est_overpay, timestamp
        FROM case_evidence
        WHERE case_id = ?
        ORDER BY timestamp DESC;
        """,
        (case_id,),
    )
    for ev in ev_cursor.fetchall():
        timeline.append({
            "event_type": "ALERT_TRIGGERED",
            "date": ev["timestamp"][:10] if ev["timestamp"] else get_current_as_of()[:10],
            "description": f"Alert {ev['rule_id']} ({ev['rule_name']}): {ev['plain_text']}",
            "amount": ev["est_overpay"],
        })

    timeline.sort(key=lambda x: str(x.get("date", "")), reverse=True)
    return timeline


def get_case_network(conn: sqlite3.Connection, case_id: str) -> Dict[str, Any]:
    """Return the network/subgraph information for a case."""
    case_row = conn.execute(
        "SELECT entity_id, entity_type, network_id FROM cases WHERE case_id = ?;", (case_id,)
    ).fetchone()

    if not case_row:
        return {"nodes": [], "edges": [], "cohorts": [], "summary": {}}

    entity_id = case_row["entity_id"]
    nodes = [{"id": entity_id, "label": entity_id, "type": case_row["entity_type"], "is_focal": True}]
    edges = []

    # Find referrals
    ref_cursor = conn.execute(
        """
        SELECT referring_provider_id, target_provider_id, COUNT(*) as ref_count
        FROM referrals
        WHERE referring_provider_id = ? OR target_provider_id = ?
        GROUP BY referring_provider_id, target_provider_id
        LIMIT 15;
        """,
        (entity_id, entity_id),
    )
    for ref in ref_cursor.fetchall():
        other_id = ref["target_provider_id"] if ref["referring_provider_id"] == entity_id else ref["referring_provider_id"]
        if not any(n["id"] == other_id for n in nodes):
            nodes.append({"id": other_id, "label": other_id, "type": "provider", "is_focal": False})
        edges.append({
            "source": ref["referring_provider_id"],
            "target": ref["target_provider_id"],
            "edge_type": "refers_to",
            "weight": ref["ref_count"],
        })

    # Find network/community co-providers if part of a network
    if case_row["network_id"]:
        net_row = conn.execute("SELECT * FROM networks WHERE network_id = ?;", (case_row["network_id"],)).fetchone()
        if net_row and net_row["hub_provider_id"] != entity_id:
            hub = net_row["hub_provider_id"]
            if not any(n["id"] == hub for n in nodes):
                nodes.append({"id": hub, "label": hub, "type": "provider", "is_focal": False, "is_hub": True})
            edges.append({
                "source": entity_id,
                "target": hub,
                "edge_type": "shared_network",
                "weight": 1.0,
            })

    return {
        "nodes": nodes,
        "edges": edges,
        "cohorts": [],
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "network_id": case_row["network_id"],
        },
    }


def record_case_decision(
    conn: sqlite3.Connection,
    case_id: str,
    decision: str,
    notes: Optional[str] = "",
    actor: str = "investigator",
) -> Dict[str, Any]:
    """Record an investigator decision on a case and append an audit record."""
    status_map = {
        "accept": "ACCEPTED",
        "reject": "REJECTED",
        "escalate_for_review": "ESCALATED",
    }
    new_status = status_map.get(decision.lower(), "IN_REVIEW")
    now_iso = get_current_as_of()

    # Get previous case status
    prev_row = conn.execute("SELECT status FROM cases WHERE case_id = ?;", (case_id,)).fetchone()
    prev_status = prev_row["status"] if prev_row else "UNKNOWN"

    # Update case status
    conn.execute(
        "UPDATE cases SET status = ?, updated_at = ? WHERE case_id = ?;",
        (new_status, now_iso, case_id),
    )

    # Insert audit log with previous and new states
    audit_id = f"LOG-{uuid.uuid4().hex[:8]}"
    payload = {
        "previous_state": prev_status,
        "new_state": new_status,
        "action": f"DECISION_{decision.upper()}",
        "statement": "Prioritized for human investigation",
    }
    conn.execute(
        """
        INSERT INTO audit_log (log_id, case_id, action, decision, actor, notes, payload, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            audit_id,
            case_id,
            f"DECISION_{decision.upper()}",
            decision,
            actor,
            notes or "",
            json.dumps(payload),
            now_iso,
        ),
    )

    return {
        "case_id": case_id,
        "status": new_status,
        "decision": decision,
        "recorded_at": now_iso,
        "audit_id": audit_id,
        "message": f"Case decision '{decision}' recorded successfully.",
    }


def get_audit_records(
    conn: sqlite3.Connection, case_id: Optional[str] = None, limit: int = 50
) -> List[AuditLogEntry]:
    """Retrieve audit history entries."""
    if case_id:
        cursor = conn.execute(
            """
            SELECT log_id, case_id, action, decision, actor, notes, payload, timestamp
            FROM audit_log
            WHERE case_id = ?
            ORDER BY timestamp DESC
            LIMIT ?;
            """,
            (case_id, limit),
        )
    else:
        cursor = conn.execute(
            """
            SELECT log_id, case_id, action, decision, actor, notes, payload, timestamp
            FROM audit_log
            ORDER BY timestamp DESC
            LIMIT ?;
            """,
            (limit,),
        )

    records = []
    for r in cursor.fetchall():
        records.append(AuditLogEntry(
            log_id=r["log_id"],
            case_id=r["case_id"],
            action=r["action"],
            decision=r["decision"],
            actor=r["actor"],
            notes=r["notes"],
            payload=_parse_json_field(r["payload"], {}),
            timestamp=r["timestamp"],
        ))
    return records


def get_networks_list(
    conn: sqlite3.Connection, limit: int = 50, offset: int = 0
) -> List[Dict[str, Any]]:
    """Retrieve network/ring summaries."""
    cursor = conn.execute(
        """
        SELECT 
            network_id, community_id, n_providers, hub_provider_id,
            hard_link_score, referral_score, concentration_score, ownership_score,
            suspicious_claims, total_claims, total_exposure, triggered_rules,
            hub_centrality, documented_group, network_feature_version
        FROM networks
        ORDER BY total_exposure DESC, hard_link_score DESC
        LIMIT ? OFFSET ?;
        """,
        (limit, offset),
    )
    return [dict(r) for r in cursor.fetchall()]


def get_claims_list(
    conn: sqlite3.Connection,
    provider_id: Optional[str] = None,
    member_id: Optional[str] = None,
    procedure_code: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Retrieve claims with filtering."""
    query = "SELECT * FROM claims WHERE 1=1"
    params: List[Any] = []
    if provider_id:
        query += " AND provider_id = ?"
        params.append(provider_id)
    if member_id:
        query += " AND member_id = ?"
        params.append(member_id)
    if procedure_code:
        query += " AND procedure_code = ?"
        params.append(procedure_code)

    query += " ORDER BY service_date DESC LIMIT ? OFFSET ?;"
    params.extend([limit, offset])

    cursor = conn.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]


def get_providers_list(
    conn: sqlite3.Connection,
    provider_id: Optional[str] = None,
    specialty: Optional[str] = None,
    county: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Retrieve providers with lookup and filtering."""
    query = "SELECT * FROM providers WHERE 1=1"
    params: List[Any] = []
    if provider_id:
        query += " AND provider_id = ?"
        params.append(provider_id)
    if specialty:
        query += " AND LOWER(specialty) = LOWER(?)"
        params.append(specialty)
    if county:
        query += " AND LOWER(county) = LOWER(?)"
        params.append(county)

    query += " ORDER BY provider_id ASC LIMIT ? OFFSET ?;"
    params.extend([limit, offset])

    cursor = conn.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]


def get_risk_info(
    conn: sqlite3.Connection, entity_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Expose risk components from cases and risk tables."""
    if entity_id:
        cursor = conn.execute(
            """
            SELECT case_id, entity_type, entity_id, entity_name, risk_score, priority, confidence, evidence_strength, risk_components, future_risk
            FROM cases
            WHERE entity_id = ?;
            """,
            (entity_id,),
        )
    else:
        cursor = conn.execute(
            """
            SELECT case_id, entity_type, entity_id, entity_name, risk_score, priority, confidence, evidence_strength, risk_components, future_risk
            FROM cases
            ORDER BY risk_score DESC
            LIMIT 50;
            """
        )

    results = []
    for r in cursor.fetchall():
        d = dict(r)
        d["risk_components"] = _parse_json_field(d.get("risk_components"), {})
        d["future_risk"] = _parse_json_field(d.get("future_risk"), {})
        results.append(d)
    return results


def get_evaluation_metrics_data(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Retrieve stored evaluation/ablation metrics."""
    cursor = conn.execute("SELECT eval_type, metrics, created_at FROM evaluation_results ORDER BY created_at DESC LIMIT 5;")
    rows = cursor.fetchall()
    eval_list = []
    for r in rows:
        eval_list.append({
            "eval_type": r["eval_type"],
            "metrics": _parse_json_field(r["metrics"], {}),
            "created_at": r["created_at"],
        })
    return {"evaluations": eval_list, "total_evaluations": len(eval_list)}
