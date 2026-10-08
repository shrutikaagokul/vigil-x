"""
Data loader and ingestion pipeline for Vigil-X SQLite application database.

Enforces strict separation between:
1. REAL PIPELINE OUTPUT (from ML/Risk, Network, and Detection workstreams)
2. DEVELOPMENT FIXTURE (deterministic alerts-to-cases synthesis to unblock API/UI)

In REAL mode:
- Requires genuine upstream analytical artifacts (cases, queue, risk_scores).
- FAILS LOUDLY with MissingAnalyticalOutputError if required outputs are absent.
- Validates all records against strict Pydantic analytical contracts before insertion.
- Never silently invents fake risk scores or synthesizes queue priority.

In FIXTURE mode:
- Permits deterministic derivation of cases and queue items from alerts.
- Clearly flags and logs fixture generation for development and UI integration.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from config.backend_config import DataMode, get_data_mode
from contracts.alert import Alert, Evidence
from contracts.analytical import (
    AlertInput,
    CaseEvidenceInput,
    CaseInput,
    ClaimMLScoreInput,
    EvaluationResultInput,
    EvidenceInput,
    NetworkScoreInput,
    QueueItemInput,
    UnifiedRiskScoreInput,
)
from db.database import get_db_context, init_db
from db.schema import init_schema

logger = logging.getLogger("vigilx.loader")


class MissingAnalyticalOutputError(RuntimeError):
    """Raised when required upstream analytical outputs are missing in REAL mode."""
    pass


class AnalyticalValidationError(ValueError):
    """Raised when incoming analytical outputs violate schema, type, or range constraints."""
    pass


RULE_NAMES = {
    "R01": "Duplicate Billing",
    "R02": "Upcoding",
    "R03": "Unbundling",
    "R04": "Phantom Services",
    "R05": "Excessive Utilization",
    "R06": "Impossible Timing",
    "R07": "Referral Anomaly",
    "R08": "Geographic Anomaly",
    "R09": "Shared Identity Link",
    "R10": "Burst / Spike",
}


def _safe_json(val: Any) -> str:
    """Serialize value to JSON safely handling numpy and datetime types."""
    if isinstance(val, (dict, list)):
        return json.dumps(val, default=str)
    if pd.isna(val) or val is None:
        return "[]"
    if isinstance(val, str):
        return val
    return json.dumps(val, default=str)


def load_dataframe_to_table(
    conn: sqlite3.Connection,
    df: pd.DataFrame,
    table_name: str,
    column_mapping: Optional[Dict[str, str]] = None,
) -> int:
    """
    Insert or replace records from a DataFrame into an existing SQLite table.
    """
    if df is None or df.empty:
        return 0

    df_copy = df.copy()
    if column_mapping:
        df_copy = df_copy.rename(columns=column_mapping)

    cursor = conn.execute(f"PRAGMA table_info({table_name});")
    valid_cols = [row["name"] for row in cursor.fetchall()]
    cols_to_insert = [c for c in df_copy.columns if c in valid_cols]

    if not cols_to_insert:
        return 0

    sub_df = df_copy[cols_to_insert].copy()

    for col in sub_df.columns:
        if sub_df[col].dtype == "object":
            sub_df[col] = sub_df[col].apply(
                lambda x: _safe_json(x) if isinstance(x, (dict, list)) else (None if pd.isna(x) else str(x))
            )
        elif np.issubdtype(sub_df[col].dtype, np.floating):
            sub_df[col] = sub_df[col].apply(lambda x: None if pd.isna(x) else float(x))
        elif np.issubdtype(sub_df[col].dtype, np.integer):
            sub_df[col] = sub_df[col].apply(lambda x: None if pd.isna(x) else int(x))

    placeholders = ", ".join(["?"] * len(cols_to_insert))
    col_str = ", ".join(cols_to_insert)
    sql = f"INSERT OR REPLACE INTO {table_name} ({col_str}) VALUES ({placeholders})"

    records = [tuple(x) for x in sub_df.to_numpy()]
    conn.executemany(sql, records)
    return len(records)


# ── Validated Contract Ingestion Functions ──────────────────────────

def validate_and_load_cases(
    conn: sqlite3.Connection,
    cases: Union[List[Dict[str, Any]], pd.DataFrame],
) -> int:
    """
    Validate and insert upstream investigation cases.
    Verifies constraints using CaseInput contract.
    """
    if isinstance(cases, pd.DataFrame):
        case_records = cases.to_dict(orient="records")
    else:
        case_records = list(cases)

    if not case_records:
        return 0

    validated_rows = []
    seen_ids = set()
    now_iso = datetime.now(timezone.utc).isoformat()

    for idx, raw in enumerate(case_records):
        try:
            # Parse JSON fields if given as strings in dataframe
            d = dict(raw)
            for field in ["why_flagged", "top_reasons", "benign_explanations"]:
                if isinstance(d.get(field), str):
                    try:
                        d[field] = json.loads(d[field])
                    except Exception:
                        d[field] = [d[field]]
            for field in ["risk_components", "future_risk"]:
                if isinstance(d.get(field), str):
                    try:
                        d[field] = json.loads(d[field])
                    except Exception:
                        d[field] = {}

            item = CaseInput(**d)
        except Exception as e:
            raise AnalyticalValidationError(f"Invalid case record at index {idx} ({raw.get('case_id')}): {e}")

        if item.case_id in seen_ids:
            raise AnalyticalValidationError(f"Duplicate case_id found: '{item.case_id}'")
        seen_ids.add(item.case_id)

        validated_rows.append((
            item.case_id,
            item.entity_type,
            item.entity_id,
            item.entity_name,
            item.status,
            item.priority,
            float(item.risk_score),
            float(item.confidence),
            float(item.evidence_strength),
            float(item.exposure_low),
            float(item.exposure_high),
            int(item.members_affected),
            int(item.claims_count),
            json.dumps(item.why_flagged),
            json.dumps(item.top_reasons),
            json.dumps(item.benign_explanations),
            json.dumps(item.risk_components),
            json.dumps(item.future_risk) if item.future_risk else None,
            item.network_id,
            item.assigned_to,
            now_iso,
            now_iso,
        ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO cases (
            case_id, entity_type, entity_id, entity_name, status, priority,
            risk_score, confidence, evidence_strength, exposure_low, exposure_high,
            members_affected, claims_count, why_flagged, top_reasons,
            benign_explanations, risk_components, future_risk, network_id,
            assigned_to, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        validated_rows,
    )
    return len(validated_rows)


def validate_and_load_case_evidence(
    conn: sqlite3.Connection,
    evidence_items: Union[List[Dict[str, Any]], pd.DataFrame],
) -> int:
    """Validate and insert upstream case evidence ledger items."""
    if isinstance(evidence_items, pd.DataFrame):
        ev_records = evidence_items.to_dict(orient="records")
    else:
        ev_records = list(evidence_items)

    if not ev_records:
        return 0

    validated_rows = []
    seen_ids = set()

    for idx, raw in enumerate(ev_records):
        try:
            item = CaseEvidenceInput(**dict(raw))
        except Exception as e:
            raise AnalyticalValidationError(f"Invalid case evidence record at index {idx}: {e}")

        if item.evidence_id in seen_ids:
            raise AnalyticalValidationError(f"Duplicate evidence_id: '{item.evidence_id}'")
        seen_ids.add(item.evidence_id)

        validated_rows.append((
            item.evidence_id,
            item.case_id,
            item.rule_id,
            item.rule_name,
            item.claim_id,
            item.entity_id,
            item.field_name,
            item.field_value,
            item.plain_text,
            float(item.est_overpay),
            item.severity,
            item.source_table,
            item.source_artifact,
            item.timestamp,
            item.fp_notes,
        ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO case_evidence (
            evidence_id, case_id, rule_id, rule_name, claim_id, entity_id,
            field_name, field_value, plain_text, est_overpay, severity,
            source_table, source_artifact, timestamp, fp_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        validated_rows,
    )
    return len(validated_rows)


def validate_and_load_queue(
    conn: sqlite3.Connection,
    queue_items: Union[List[Dict[str, Any]], pd.DataFrame],
) -> int:
    """Validate and insert upstream prioritized queue items."""
    if isinstance(queue_items, pd.DataFrame):
        q_records = queue_items.to_dict(orient="records")
    else:
        q_records = list(queue_items)

    if not q_records:
        return 0

    validated_rows = []
    seen_cases = set()

    for idx, raw in enumerate(q_records):
        try:
            d = dict(raw)
            if isinstance(d.get("top_reasons"), str):
                try:
                    d["top_reasons"] = json.loads(d["top_reasons"])
                except Exception:
                    d["top_reasons"] = [d["top_reasons"]]
            item = QueueItemInput(**d)
        except Exception as e:
            raise AnalyticalValidationError(f"Invalid queue item at index {idx} ({raw.get('case_id')}): {e}")

        if item.case_id in seen_cases:
            raise AnalyticalValidationError(f"Duplicate case_id in queue items: '{item.case_id}'")
        seen_cases.add(item.case_id)

        validated_rows.append((
            item.case_id,
            item.rank,
            item.baseline_rank or item.rank,
            item.entity_type,
            item.entity_id,
            item.entity_name,
            float(item.risk),
            item.priority,
            float(item.exposure_low),
            float(item.exposure_high),
            int(item.members_affected),
            item.severity,
            float(item.evidence_strength),
            float(item.confidence),
            float(item.effort_hours),
            float(item.ev_per_hour),
            item.slot,
            json.dumps(item.top_reasons),
        ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO queue_items (
            case_id, rank, baseline_rank, entity_type, entity_id, entity_name,
            risk, priority, exposure_low, exposure_high, members_affected,
            severity, evidence_strength, confidence, effort_hours, ev_per_hour,
            slot, top_reasons
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        validated_rows,
    )
    return len(validated_rows)


def validate_and_load_risk_scores(
    conn: sqlite3.Connection,
    risk_scores: Union[List[Dict[str, Any]], pd.DataFrame],
) -> int:
    """Validate and insert upstream unified risk scores."""
    if isinstance(risk_scores, pd.DataFrame):
        records = risk_scores.to_dict(orient="records")
    else:
        records = list(risk_scores)

    if not records:
        return 0

    validated_rows = []
    for idx, raw in enumerate(records):
        try:
            item = UnifiedRiskScoreInput(**dict(raw))
        except Exception as e:
            raise AnalyticalValidationError(f"Invalid risk score record at index {idx}: {e}")

        validated_rows.append((
            item.entity_type,
            item.entity_id,
            float(item.risk_score),
            float(item.anomaly_score),
            float(item.rule_score),
            float(item.network_score),
            float(item.future_risk_score),
            float(item.confidence),
            float(item.evidence_strength),
        ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO risk_scores (
            entity_type, entity_id, risk_score, anomaly_score, rule_score,
            network_score, future_risk_score, confidence, evidence_strength
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        validated_rows,
    )
    return len(validated_rows)


def validate_and_load_claim_ml(
    conn: sqlite3.Connection,
    claim_ml_items: Union[List[Dict[str, Any]], pd.DataFrame],
) -> int:
    """Validate and insert claim ML anomaly scores."""
    if isinstance(claim_ml_items, pd.DataFrame):
        records = claim_ml_items.to_dict(orient="records")
    else:
        records = list(claim_ml_items)

    if not records:
        return 0

    validated_rows = []
    for idx, raw in enumerate(records):
        try:
            item = ClaimMLScoreInput(**dict(raw))
        except Exception as e:
            raise AnalyticalValidationError(f"Invalid claim ML record at index {idx}: {e}")

        validated_rows.append((
            item.claim_id,
            float(item.anomaly_score),
            item.ml_prediction,
            item.model_version,
        ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO claim_ml (
            claim_id, anomaly_score, ml_prediction, model_version
        ) VALUES (?, ?, ?, ?)
        """,
        validated_rows,
    )
    return len(validated_rows)


def validate_and_load_networks(
    conn: sqlite3.Connection,
    networks: Union[List[Dict[str, Any]], pd.DataFrame],
) -> int:
    """Validate and insert network intelligence features."""
    if isinstance(networks, pd.DataFrame):
        records = networks.to_dict(orient="records")
    else:
        records = list(networks)

    if not records:
        return 0

    validated_rows = []
    for idx, raw in enumerate(records):
        try:
            item = NetworkScoreInput(**dict(raw))
        except Exception as e:
            raise AnalyticalValidationError(f"Invalid network feature record at index {idx}: {e}")

        validated_rows.append((
            item.network_id,
            item.community_id,
            item.n_providers,
            item.hub_provider_id,
            float(item.hard_link_score),
            float(item.referral_score),
            float(item.concentration_score),
            float(item.ownership_score),
            item.suspicious_claims,
            item.total_claims,
            float(item.total_exposure),
            item.triggered_rules,
            float(item.hub_centrality),
            item.documented_group,
            item.network_feature_version,
        ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO networks (
            network_id, community_id, n_providers, hub_provider_id,
            hard_link_score, referral_score, concentration_score, ownership_score,
            suspicious_claims, total_claims, total_exposure, triggered_rules,
            hub_centrality, documented_group, network_feature_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        validated_rows,
    )
    return len(validated_rows)


# ── Development Fixture Synthesis (FIXTURE Mode Only) ───────────────

def ingest_alerts_and_form_cases(
    conn: sqlite3.Connection,
    alerts: List[Union[Alert, Dict[str, Any]]],
    claims_df: Optional[pd.DataFrame] = None,
    providers_df: Optional[pd.DataFrame] = None,
    networks_df: Optional[pd.DataFrame] = None,
) -> int:
    """
    Ingest Alert objects and derive deterministic development Cases/Queue items.
    
    NOTE: Used in FIXTURE mode only to unblock API and frontend development.
    In REAL mode, upstream cases and queue items MUST be supplied directly.
    """
    if not alerts:
        return 0

    now_iso = datetime.now(timezone.utc).isoformat()

    # Pre-index provider names
    provider_names: Dict[str, str] = {}
    if providers_df is not None and not providers_df.empty:
        for _, p in providers_df.iterrows():
            provider_names[str(p["provider_id"])] = str(p.get("name", f"Provider {p['provider_id']}"))

    # Normalize alert objects
    normalized_alerts: List[Dict[str, Any]] = []
    for a in alerts:
        if hasattr(a, "to_dict"):
            d = a.to_dict()
        elif isinstance(a, dict):
            d = dict(a)
        else:
            continue
        normalized_alerts.append(d)

    # 1. Insert into alerts table
    alert_rows = []
    for a in normalized_alerts:
        alert_rows.append((
            a.get("alert_id"),
            a.get("rule_id"),
            a.get("rule_version", "1.0.0"),
            a.get("entity_type", "provider"),
            a.get("entity_id"),
            json.dumps(a.get("claim_ids", []), default=str),
            str(a.get("severity", "MEDIUM")),
            float(a.get("est_dollars", 0.0) or 0.0),
            str(a.get("fp_notes", "") or ""),
            json.dumps(a.get("metadata", {}), default=str),
            now_iso,
        ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO alerts (
            alert_id, rule_id, rule_version, entity_type, entity_id,
            claim_ids, severity, est_dollars, fp_notes, metadata, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        alert_rows,
    )

    # 2. Group alerts by entity to form Cases
    by_entity: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
    for a in normalized_alerts:
        key = (a.get("entity_type", "provider"), str(a.get("entity_id", "")))
        by_entity.setdefault(key, []).append(a)

    case_rows = []
    evidence_rows = []

    network_by_hub: Dict[str, Dict[str, Any]] = {}
    if networks_df is not None and not networks_df.empty:
        for _, net in networks_df.iterrows():
            hub = str(net.get("hub_provider_id", ""))
            if hub:
                network_by_hub[hub] = net.to_dict()

    for (entity_type, entity_id), ent_alerts in by_entity.items():
        case_id = f"CASE-{entity_type[:3].upper()}-{entity_id}"
        entity_name = provider_names.get(entity_id, f"{entity_type.capitalize()} {entity_id}")

        all_claim_ids = set()
        why_flagged = []
        top_reasons = []
        benign_explanations = []
        total_exposure = 0.0
        severities = []

        for a in ent_alerts:
            rule_id = a.get("rule_id", "UNKNOWN")
            rule_name = RULE_NAMES.get(rule_id, rule_id)
            claim_ids = a.get("claim_ids", [])
            all_claim_ids.update(claim_ids)
            est = float(a.get("est_dollars", 0.0) or 0.0)
            total_exposure += est
            sev = str(a.get("severity", "MEDIUM"))
            severities.append(sev)

            why = f"Triggered {rule_id} ({rule_name})"
            if why not in why_flagged:
                why_flagged.append(why)

            raw_ev_list = a.get("evidence", [])
            for ev in raw_ev_list:
                ev_d = ev if isinstance(ev, dict) else (ev.to_dict() if hasattr(ev, "to_dict") else {})
                ev_id = ev_d.get("evidence_id") or f"E-{rule_id}-{uuid.uuid4().hex[:6]}"
                plain_text = ev_d.get("plain_text", why)
                fields_matched = ev_d.get("fields_matched", [])
                ev_claims = ev_d.get("claim_ids", claim_ids)
                ev_overpay = float(ev_d.get("est_overpay", 0.0) or 0.0)
                fp_note = ev_d.get("fp_notes")
                if fp_note and str(fp_note) not in benign_explanations:
                    benign_explanations.append(str(fp_note))

                primary_claim = ev_claims[0] if ev_claims else None

                evidence_rows.append((
                    ev_id,
                    case_id,
                    rule_id,
                    rule_name,
                    primary_claim,
                    entity_id,
                    ", ".join(fields_matched) if fields_matched else "multiple",
                    str(ev_d.get("matched_value", "")),
                    plain_text,
                    ev_overpay if ev_overpay > 0 else est,
                    ev_d.get("severity", sev),
                    "alerts",
                    f"rule_engine/{rule_id.lower()}",
                    now_iso,
                    str(fp_note) if fp_note else None,
                ))

                if plain_text not in top_reasons and len(top_reasons) < 4:
                    top_reasons.append(plain_text)

        sev_weights = {"CRITICAL": 35.0, "HIGH": 25.0, "MEDIUM": 15.0, "LOW": 8.0}
        max_sev = "LOW"
        if "CRITICAL" in severities:
            max_sev = "CRITICAL"
        elif "HIGH" in severities:
            max_sev = "HIGH"
        elif "MEDIUM" in severities:
            max_sev = "MEDIUM"

        base_score = sev_weights.get(max_sev, 15.0)
        multi_rule_boost = min(len(why_flagged) * 12.0, 35.0)
        volume_boost = min(len(all_claim_ids) * 1.5, 20.0)
        risk_score = round(min(base_score + multi_rule_boost + volume_boost, 99.0), 1)

        priority = "LOW"
        if risk_score >= 80.0:
            priority = "CRITICAL"
        elif risk_score >= 60.0:
            priority = "HIGH"
        elif risk_score >= 35.0:
            priority = "MEDIUM"

        net_info = network_by_hub.get(entity_id)
        net_id = net_info.get("network_id") if net_info else None
        network_risk = float(net_info.get("hard_link_score", 0.0) or 0.0) if net_info else 0.0

        risk_components = {
            "rule_risk": round(min(risk_score / 100.0, 1.0), 3),
            "network_risk": round(network_risk, 3),
            "anomaly_risk": round(min(len(why_flagged) * 0.25, 1.0), 3),
        }

        members_affected = 1
        if claims_df is not None and not claims_df.empty and all_claim_ids:
            matching_claims = claims_df[claims_df["claim_id"].isin(all_claim_ids)]
            if not matching_claims.empty and "member_id" in matching_claims.columns:
                members_affected = int(matching_claims["member_id"].nunique())

        exposure_low = round(total_exposure * 0.8, 2)
        exposure_high = round(max(total_exposure * 1.2, 500.0), 2)

        case_rows.append((
            case_id,
            entity_type,
            entity_id,
            entity_name,
            "NEW",
            priority,
            risk_score,
            0.88,
            0.85,
            exposure_low,
            exposure_high,
            members_affected,
            len(all_claim_ids),
            json.dumps(why_flagged),
            json.dumps(top_reasons if top_reasons else why_flagged),
            json.dumps(benign_explanations),
            json.dumps(risk_components),
            json.dumps({"future_velocity_risk": round(risk_score * 0.7, 1)}),
            net_id,
            None,
            now_iso,
            now_iso,
        ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO cases (
            case_id, entity_type, entity_id, entity_name, status, priority,
            risk_score, confidence, evidence_strength, exposure_low, exposure_high,
            members_affected, claims_count, why_flagged, top_reasons,
            benign_explanations, risk_components, future_risk, network_id,
            assigned_to, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        case_rows,
    )

    if evidence_rows:
        conn.executemany(
            """
            INSERT OR REPLACE INTO case_evidence (
                evidence_id, case_id, rule_id, rule_name, claim_id, entity_id,
                field_name, field_value, plain_text, est_overpay, severity,
                source_table, source_artifact, timestamp, fp_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            evidence_rows,
        )

    sorted_cases = sorted(case_rows, key=lambda c: c[6], reverse=True)
    queue_rows = []
    for rank, c in enumerate(sorted_cases, start=1):
        c_id = c[0]
        c_ent_type = c[1]
        c_ent_id = c[2]
        c_ent_name = c[3]
        c_priority = c[5]
        c_risk = c[6]
        c_conf = c[7]
        c_ev_str = c[8]
        c_exp_low = c[9]
        c_exp_high = c[10]
        c_members = c[11]
        c_top_reasons = c[14]

        claims_cnt = c[12]
        effort_hours = round(min(2.0 + (claims_cnt * 0.1), 8.0), 1)
        ev_per_hour = round(c_exp_high / max(effort_hours, 1.0), 2)
        slot = rank

        queue_rows.append((
            c_id,
            rank,
            rank,
            c_ent_type,
            c_ent_id,
            c_ent_name,
            c_risk,
            c_priority,
            c_exp_low,
            c_exp_high,
            c_members,
            c_priority,
            c_ev_str,
            c_conf,
            effort_hours,
            ev_per_hour,
            slot,
            c_top_reasons,
        ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO queue_items (
            case_id, rank, baseline_rank, entity_type, entity_id, entity_name,
            risk, priority, exposure_low, exposure_high, members_affected,
            severity, evidence_strength, confidence, effort_hours, ev_per_hour,
            slot, top_reasons
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        queue_rows,
    )

    conn.execute(
        """
        INSERT OR REPLACE INTO audit_log (
            log_id, case_id, action, decision, actor, notes, payload, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"LOG-{uuid.uuid4().hex[:8]}",
            "SYSTEM",
            "FIXTURE_INGESTION",
            "INITIALIZED",
            "system",
            f"[FIXTURE MODE] Synthesized {len(case_rows)} cases and {len(evidence_rows)} evidence items from {len(normalized_alerts)} alerts.",
            json.dumps({"cases_count": len(case_rows), "alerts_count": len(normalized_alerts), "mode": "fixture"}),
            now_iso,
        ),
    )

    return len(case_rows)


# ── Full Rebuild Entry Point ────────────────────────────────────────

def rebuild_database(
    db_path: Optional[str | Path] = None,
    data_dict: Optional[Dict[str, pd.DataFrame]] = None,
    alerts: Optional[List[Alert]] = None,
    networks_df: Optional[pd.DataFrame] = None,
    cases_data: Optional[Union[List[Dict[str, Any]], pd.DataFrame]] = None,
    case_evidence_data: Optional[Union[List[Dict[str, Any]], pd.DataFrame]] = None,
    queue_data: Optional[Union[List[Dict[str, Any]], pd.DataFrame]] = None,
    risk_scores_data: Optional[Union[List[Dict[str, Any]], pd.DataFrame]] = None,
    claim_ml_data: Optional[Union[List[Dict[str, Any]], pd.DataFrame]] = None,
    eval_results: Optional[Dict[str, Any]] = None,
    data_mode: Optional[Union[str, DataMode]] = None,
) -> Dict[str, int]:
    """
    Completely rebuild the SQLite application database.
    
    In REAL mode:
      Requires upstream `cases_data` and `queue_data`. Fails loudly if absent.
    In FIXTURE mode:
      Synthesizes deterministic development cases from alerts if upstream cases are absent.
    """
    mode = DataMode(data_mode) if data_mode else get_data_mode()
    target_path = str(db_path or "app.db")

    if target_path != ":memory:" and os.path.exists(target_path):
        os.remove(target_path)

    with get_db_context(target_path) as conn:
        init_schema(conn)

        stats: Dict[str, int] = {}
        claims_df = None
        providers_df = None

        # 1. Load domain tables
        if data_dict:
            col_maps = {
                "claims": {
                    "billing_provider_id": "provider_id",
                    "cpt_code": "procedure_code",
                    "service_from": "service_date",
                    "claim_status": "status",
                }
            }
            for table_name, df in data_dict.items():
                if table_name in ["providers", "members", "facilities", "claims", "claim_lines", "referrals"]:
                    mapping = col_maps.get(table_name)
                    cnt = load_dataframe_to_table(conn, df, table_name, column_mapping=mapping)
                    stats[table_name] = cnt
                    if table_name == "claims":
                        claims_df = df
                    elif table_name == "providers":
                        providers_df = df

        # 2. Networks
        if networks_df is not None and not networks_df.empty:
            validate_and_load_networks(conn, networks_df)
            stats["networks"] = len(networks_df)

        # 3. Alerts
        if alerts:
            # Load raw alerts into alerts table
            normalized_alerts = [a.to_dict() if hasattr(a, "to_dict") else a for a in alerts]
            now_iso = datetime.now(timezone.utc).isoformat()
            alert_rows = [
                (
                    a.get("alert_id"),
                    a.get("rule_id"),
                    a.get("rule_version", "1.0.0"),
                    a.get("entity_type", "provider"),
                    a.get("entity_id"),
                    json.dumps(a.get("claim_ids", []), default=str),
                    str(a.get("severity", "MEDIUM")),
                    float(a.get("est_dollars", 0.0) or 0.0),
                    str(a.get("fp_notes", "") or ""),
                    json.dumps(a.get("metadata", {}), default=str),
                    now_iso,
                )
                for a in normalized_alerts
            ]
            conn.executemany(
                """
                INSERT OR REPLACE INTO alerts (
                    alert_id, rule_id, rule_version, entity_type, entity_id,
                    claim_ids, severity, est_dollars, fp_notes, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                alert_rows,
            )
            stats["alerts"] = len(alert_rows)

        # 4. Mode-specific Cases & Queue handling
        if mode == DataMode.REAL:
            if cases_data is None or (isinstance(cases_data, (list, pd.DataFrame)) and len(cases_data) == 0):
                raise MissingAnalyticalOutputError(
                    "REAL mode enabled (VIGILX_DATA_MODE=real): Missing required upstream 'cases' output. "
                    "In real mode, cases must be supplied by the ML/Risk pipeline and cannot be synthesized."
                )
            if queue_data is None or (isinstance(queue_data, (list, pd.DataFrame)) and len(queue_data) == 0):
                raise MissingAnalyticalOutputError(
                    "REAL mode enabled (VIGILX_DATA_MODE=real): Missing required upstream 'queue_items' output. "
                    "In real mode, SIU queue must be supplied by the ML/Risk pipeline and cannot be synthesized."
                )

            cnt_cases = validate_and_load_cases(conn, cases_data)
            stats["cases"] = cnt_cases

            if case_evidence_data is not None:
                cnt_ev = validate_and_load_case_evidence(conn, case_evidence_data)
                stats["case_evidence"] = cnt_ev

            cnt_q = validate_and_load_queue(conn, queue_data)
            stats["queue_items"] = cnt_q

            if risk_scores_data is not None:
                cnt_risk = validate_and_load_risk_scores(conn, risk_scores_data)
                stats["risk_scores"] = cnt_risk

            if claim_ml_data is not None:
                cnt_ml = validate_and_load_claim_ml(conn, claim_ml_data)
                stats["claim_ml"] = cnt_ml

        else:
            # FIXTURE Mode
            if cases_data is not None and len(cases_data) > 0:
                # Upstream cases provided even in fixture mode
                cnt_cases = validate_and_load_cases(conn, cases_data)
                stats["cases"] = cnt_cases
                if queue_data is not None:
                    cnt_q = validate_and_load_queue(conn, queue_data)
                    stats["queue_items"] = cnt_q
                if case_evidence_data is not None:
                    cnt_ev = validate_and_load_case_evidence(conn, case_evidence_data)
                    stats["case_evidence"] = cnt_ev
            elif alerts:
                # Synthesize deterministic cases for dev/UI unblocking
                cases_formed = ingest_alerts_and_form_cases(
                    conn, alerts, claims_df=claims_df, providers_df=providers_df, networks_df=networks_df
                )
                stats["cases"] = cases_formed

            if risk_scores_data is not None:
                validate_and_load_risk_scores(conn, risk_scores_data)
            if claim_ml_data is not None:
                validate_and_load_claim_ml(conn, claim_ml_data)

        # 5. Evaluation metrics
        if eval_results:
            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO evaluation_results (eval_id, eval_type, metrics, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    f"EVAL-{uuid.uuid4().hex[:6]}",
                    "pipeline_evaluation",
                    json.dumps(eval_results, default=str),
                    now_iso,
                ),
            )
            stats["evaluation_results"] = 1

        return stats
