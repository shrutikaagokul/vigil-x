"""
Standalone Case Builder for Vigil-X.

Consolidates existing multi-signal intelligence (Unified Risk scores, R01-R10 alerts,
evidence records, claim ML probabilities, provider anomaly percentiles, future risk forecasts,
and network relationships) into investigator-ready investigation cases for Special Investigation Units (SIU).

RESPONSIBILITY:
  signals → consolidated investigation case
  (NOT signals → new fraud score)
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd
import yaml

from cases.contracts import (
    CaseEvidenceRecord,
    CasePriority,
    CaseStatus,
    InvestigationCase,
)

DEFAULT_CONFIG_PATH = Path(__file__).parent / "case_config.yaml"


# ------------------------------------------------------------------------------
# Configuration Loader
# ------------------------------------------------------------------------------

def load_case_config(config_input: Optional[Union[Dict[str, Any], Path, str]] = None) -> Dict[str, Any]:
    """Load and return the Case Builder configuration."""
    if config_input is None:
        config_path = DEFAULT_CONFIG_PATH
        if not config_path.exists():
            raise FileNotFoundError(f"Case config not found: {config_path}")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    elif isinstance(config_input, (str, Path)):
        config_path = Path(config_input)
        if not config_path.exists():
            raise FileNotFoundError(f"Case config not found: {config_path}")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    elif isinstance(config_input, dict):
        return config_input.copy()
    else:
        raise TypeError(f"Unsupported config type: {type(config_input)}")


# ------------------------------------------------------------------------------
# Helper Utilities
# ------------------------------------------------------------------------------

def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (ValueError, TypeError):
        return default


def generate_case_id(index: int, prefix: str = "CASE") -> str:
    """Generate a deterministic case identifier (e.g. CASE-000001)."""
    return f"{prefix}-{index:06d}"


def _parse_list(val: Any) -> List[Any]:
    """Parse list or json-encoded list safely into a python list."""
    if val is None:
        return []
    if isinstance(val, list):
        return list(val)
    if isinstance(val, (set, tuple)):
        return list(val)
    if isinstance(val, str):
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            try:
                res = json.loads(val)
                return res if isinstance(res, list) else []
            except json.JSONDecodeError:
                pass
        if val:
            return [v.strip() for v in val.split(",") if v.strip()]
    return []


# ------------------------------------------------------------------------------
# Case Eligibility Logic
# ------------------------------------------------------------------------------

def is_provider_eligible(
    provider_row: Union[pd.Series, Dict[str, Any]],
    eligibility_cfg: Dict[str, Any],
) -> bool:
    """
    Evaluate whether a provider qualifies for investigation case creation.
    
    A provider is eligible if:
      - all_providers flag is true
      OR
      - (risk_score >= min_risk_score AND risk_tier in eligible_risk_tiers)
      OR
      - evidence_strength >= min_evidence_strength
    """
    if eligibility_cfg.get("all_providers", False):
        return True

    score = _safe_float(provider_row.get("risk_score", 0.0))
    tier = str(provider_row.get("risk_tier", "LOW")).upper()
    strength = _safe_float(provider_row.get("evidence_strength", 0.0))

    min_score = float(eligibility_cfg.get("min_risk_score", 0.25))
    min_strength = float(eligibility_cfg.get("min_evidence_strength", 0.50))
    eligible_tiers = [t.upper() for t in eligibility_cfg.get("eligible_risk_tiers", ["MODERATE", "HIGH", "CRITICAL"])]

    # Check score and tier
    score_eligible = (score >= min_score) and (tier in eligible_tiers)
    strength_eligible = (strength >= min_strength) and (tier in eligible_tiers)

    # Optional multiple signals requirement
    if eligibility_cfg.get("require_multiple_signals", False):
        n_families = 0
        for comp in ["rule_component", "ml_component", "anomaly_component", "network_component", "future_component"]:
            if _safe_float(provider_row.get(comp, 0.0)) >= 0.15:
                n_families += 1
        if n_families < 2:
            return False

    return score_eligible or strength_eligible


# ------------------------------------------------------------------------------
# Text Generation (Defensive Language & Deterministic Summaries)
# ------------------------------------------------------------------------------

def generate_case_title(
    provider_id: str,
    risk_tier: str,
    top_reasons: List[str],
    signal_families: List[str],
) -> str:
    """Generate deterministic, concise investigation case title."""
    if "network" in signal_families and "rules" in signal_families:
        topic = "Multi-Signal Network & Billing Anomaly"
    elif "rules" in signal_families and len(signal_families) > 1:
        topic = "Consolidated Billing Anomalies"
    elif "ml" in signal_families and "anomaly" in signal_families:
        topic = "Elevated Claim Risk & Behavioral Outlier"
    elif "anomaly" in signal_families:
        topic = "Macro Behavioral Billing Anomaly"
    elif "network" in signal_families:
        topic = "Affiliated Entity Network Anomaly"
    else:
        topic = "Prioritized Provider Billing Review"

    return f"Provider {provider_id} — {topic}"


def generate_case_summary(
    provider_id: str,
    risk_score: float,
    risk_tier: str,
    evidence_strength: float,
    evidence_tier: str,
    confidence_score: float,
    confidence_tier: str,
    estimated_exposure: float,
    rule_alert_count: int,
    claim_count: int,
    top_reasons: List[str],
    signal_families: List[str],
) -> str:
    """
    Generate deterministic, explainable human-readable case summary without LLM.
    
    Strictly uses compliant SIU defensive phrasing ("prioritized for human investigation").
    """
    fams_str = ", ".join(signal_families) if signal_families else "baseline metrics"
    
    summary_parts = [
        f"Provider {provider_id} was prioritized for human investigation based on consolidated signals across {fams_str}.",
        f"The unified risk engine assigned a risk score of {risk_score:.3f} ({risk_tier} tier) with {evidence_strength:.3f} evidence strength ({evidence_tier}) and {confidence_score:.3f} confidence ({confidence_tier}).",
    ]

    if estimated_exposure > 0:
        summary_parts.append(f"Estimated financial exposure identified from supporting evidence is ${estimated_exposure:,.2f}.")
    else:
        summary_parts.append("Direct rule-calculated financial exposure is currently unquantified.")

    if rule_alert_count > 0 or claim_count > 0:
        summary_parts.append(f"Investigation package includes {rule_alert_count} rule alert(s) and {claim_count} suspicious claim transaction(s).")

    if top_reasons:
        reasons_clean = [r.rstrip(".") for r in top_reasons[:3]]
        summary_parts.append("Primary investigation drivers: " + "; ".join(reasons_clean) + ".")

    return " ".join(summary_parts)


def generate_investigation_recommendations(
    distinct_rules: List[str],
    high_risk_claim_count: int,
    anomaly_flag: int,
    risk_30d: float,
    community_id: Optional[int],
    network_relationships: List[Dict[str, Any]],
    max_recommendations: int = 6,
) -> List[str]:
    """Generate deterministic, actionable investigation suggestions from actual signals."""
    recommendations: List[str] = []
    distinct_set = set(str(r).upper() for r in distinct_rules)

    if "R01" in distinct_set:
        recommendations.append("Review duplicate billing claims and clinical documentation for same-day service overlap.")
    if "R02" in distinct_set:
        recommendations.append("Review E/M coding level distribution against patient acuity and clinical notes.")
    if "R03" in distinct_set:
        recommendations.append("Examine mutually exclusive CPT procedure combinations against NCCI bundling edits.")
    if "R04" in distinct_set:
        recommendations.append("Verify patient attendance and provider presence for flagged service dates.")
    if "R05" in distinct_set:
        recommendations.append("Audit service frequencies and units per patient against specialty utilization baselines.")
    if "R06" in distinct_set:
        recommendations.append("Audit travel feasibility and 24-hour service-minute totals across overlapping claims.")
    if "R07" in distinct_set:
        recommendations.append("Examine referral reciprocity and concentration patterns with target diagnostic facilities.")
    if "R08" in distinct_set:
        recommendations.append("Verify physical facility locations and patient-provider travel distances.")
    if "R09" in distinct_set:
        recommendations.append("Investigate shared banking, TIN, or ownership ties with affiliated entities.")
    if "R10" in distinct_set:
        recommendations.append("Audit historical billing records to determine operational rationale for recent billing surge.")

    if high_risk_claim_count > 0:
        recommendations.append(f"Conduct detailed clinical audit on the {high_risk_claim_count} high-risk claims flagged by claim ML.")

    if anomaly_flag == 1:
        recommendations.append("Examine provider's billing composition and procedure diversity compared to peer specialty baseline.")

    if risk_30d >= 0.30:
        recommendations.append("Institute prospective pre-payment claim review and enhanced monitoring on upcoming submissions.")

    if community_id is not None or network_relationships:
        cid_str = f"Community #{community_id}" if community_id is not None else "shared network"
        recommendations.append(f"Review affiliated providers in {cid_str} to evaluate potential coordinated ring activity.")

    if not recommendations:
        recommendations.append("Review supporting claim documentation and provider billing history.")

    return recommendations[:max_recommendations]


# ------------------------------------------------------------------------------
# Core Case Builder Function
# ------------------------------------------------------------------------------

def build_cases(
    provider_scores: Union[pd.DataFrame, str, Path],
    alerts: Optional[Any] = None,
    evidence: Optional[Any] = None,
    claim_ml: Optional[pd.DataFrame] = None,
    provider_anomaly: Optional[pd.DataFrame] = None,
    future_risk: Optional[pd.DataFrame] = None,
    network_output: Optional[Any] = None,
    config: Optional[Union[Dict[str, Any], Path, str]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Consolidate provider risk intelligence into investigation cases.
    
    Parameters
    ----------
    provider_scores : DataFrame or file path from Unified Risk Engine
    alerts : Optional List[Alert] or DataFrame from R01-R10 rules
    evidence : Optional List[Evidence] records
    claim_ml : Optional claim_ml DataFrame
    provider_anomaly : Optional provider_anomaly DataFrame
    future_risk : Optional future_risk DataFrame
    network_output : Optional network communities or projection data
    config : Optional configuration dictionary or Path
    
    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame]
        (cases_df, case_evidence_df)
    """
    cfg = load_case_config(config)
    eligibility_cfg = cfg.get("eligibility", {})
    priority_map = cfg.get("priority_mapping", {
        "CRITICAL": "CRITICAL",
        "HIGH": "HIGH",
        "MODERATE": "MEDIUM",
        "LOW": "LOW",
    })
    default_status = cfg.get("status", {}).get("default", CaseStatus.NEW.value)
    builder_version = cfg.get("case_builder", {}).get("version", "1.0.0")
    id_prefix = str(cfg.get("case_builder", {}).get("case_id_prefix", "CASE"))

    # Load provider_scores
    if isinstance(provider_scores, (str, Path)):
        p_path = Path(provider_scores)
        if p_path.suffix == ".parquet":
            scores_df = pd.read_parquet(p_path)
        else:
            scores_df = pd.read_csv(p_path)
    elif isinstance(provider_scores, pd.DataFrame):
        scores_df = provider_scores.copy()
    else:
        raise TypeError(f"Unsupported provider_scores type: {type(provider_scores)}")

    if scores_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Deduplicate provider_scores by provider_id
    scores_df = scores_df.drop_duplicates(subset=["provider_id"]).reset_index(drop=True)

    # Pre-index alerts by provider_id: O(alerts)
    alerts_by_prov: Dict[str, List[Dict[str, Any]]] = {}
    if alerts is not None:
        alert_items = []
        if isinstance(alerts, pd.DataFrame):
            alert_items = alerts.to_dict(orient="records")
        elif isinstance(alerts, list):
            for a in alerts:
                if hasattr(a, "to_dict"):
                    alert_items.append(a.to_dict())
                elif isinstance(a, dict):
                    alert_items.append(a)
                elif hasattr(a, "entity_id"):
                    alert_items.append({
                        "alert_id": getattr(a, "alert_id", ""),
                        "rule_id": getattr(a, "rule_id", ""),
                        "entity_type": getattr(a, "entity_type", "provider"),
                        "entity_id": getattr(a, "entity_id", ""),
                        "severity": str(getattr(a, "severity", "MEDIUM")),
                        "est_dollars": getattr(a, "est_dollars", 0.0),
                        "evidence": getattr(a, "evidence", []),
                        "claim_ids": getattr(a, "claim_ids", []),
                    })
        for al in alert_items:
            etype = al.get("entity_type", "provider")
            pid = str(al.get("entity_id") or al.get("provider_id") or "")
            if pid and (not etype or etype == "provider"):
                alerts_by_prov.setdefault(pid, []).append(al)

    # Pre-index network relationships: O(communities)
    net_rel_by_prov: Dict[str, List[Dict[str, Any]]] = {}
    if network_output is not None:
        comms_list = []
        if isinstance(network_output, list):
            comms_list = network_output
        elif isinstance(network_output, tuple) and len(network_output) == 2:
            comms_list = network_output[1] if isinstance(network_output[1], list) else []

        for comm in comms_list:
            if not isinstance(comm, dict):
                continue
            pids = comm.get("provider_ids", [])
            hub_id = comm.get("hub_provider_id", "")
            edge_types = comm.get("edge_types", {})
            primary_rel = max(edge_types.keys(), key=lambda k: edge_types[k]) if edge_types else "connected_community"

            for pid in pids:
                pid_str = str(pid)
                # Attach other providers in same community as relationships
                peers = [p for p in pids if p != pid][:5]
                rels = []
                for peer in peers:
                    rels.append({
                        "provider_id": peer,
                        "relationship": "hub_link" if peer == hub_id else primary_rel,
                        "strength": 0.85 if peer == hub_id else 0.50,
                    })
                net_rel_by_prov[pid_str] = rels

    # Filter eligible providers
    eligible_mask = [is_provider_eligible(row, eligibility_cfg) for _, row in scores_df.iterrows()]
    eligible_df = scores_df[eligible_mask].copy()

    if eligible_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Deterministic sort: (risk_score DESC, evidence_strength DESC, provider_id ASC)
    eligible_df["_sort_risk"] = eligible_df["risk_score"].astype(float)
    eligible_df["_sort_ev"] = eligible_df["evidence_strength"].astype(float)
    eligible_df["_sort_pid"] = eligible_df["provider_id"].astype(str)
    eligible_df = eligible_df.sort_values(
        by=["_sort_risk", "_sort_ev", "_sort_pid"],
        ascending=[False, False, True]
    ).reset_index(drop=True)

    # Build cases and case evidence records
    cases_records: List[Dict[str, Any]] = []
    evidence_records: List[Dict[str, Any]] = []

    timestamp_now = datetime.now(timezone.utc).isoformat()

    for idx, row in eligible_df.iterrows():
        case_id = generate_case_id(idx + 1, id_prefix)
        pid = str(row["provider_id"])

        risk_score = _safe_float(row.get("risk_score", 0.0))
        risk_tier = str(row.get("risk_tier", "LOW")).upper()
        ev_strength = _safe_float(row.get("evidence_strength", 0.0))
        ev_tier = str(row.get("evidence_tier", "LOW")).upper()
        conf_score = _safe_float(row.get("confidence_score", 0.0))
        conf_tier = str(row.get("confidence_tier", "LOW")).upper()

        exposure = _safe_float(row.get("estimated_rule_dollars", 0.0))
        priority = priority_map.get(risk_tier, CasePriority.MEDIUM.value)

        # Retrieve and deduplicate claim IDs
        raw_claims = _parse_list(row.get("high_risk_claim_ids"))
        raw_alert_ids = _parse_list(row.get("rule_alert_ids"))
        raw_evidence_ids = _parse_list(row.get("evidence_ids"))

        prov_alerts = alerts_by_prov.get(pid, [])
        for a in prov_alerts:
            aid = str(a.get("alert_id", ""))
            if aid and aid not in raw_alert_ids:
                raw_alert_ids.append(aid)
            for c in (a.get("claim_ids") or []):
                raw_claims.append(str(c))
            for ev in (a.get("evidence") or []):
                if isinstance(ev, dict) and ev.get("evidence_id"):
                    raw_evidence_ids.append(str(ev["evidence_id"]))
                elif hasattr(ev, "evidence_id"):
                    raw_evidence_ids.append(str(ev.evidence_id))

        claim_ids = sorted(list(set(str(c) for c in raw_claims if c)))
        alert_ids = sorted(list(set(str(a) for a in raw_alert_ids if a)))
        evidence_ids = sorted(list(set(str(e) for e in raw_evidence_ids if e)))

        # Signal families present
        signal_families: List[str] = []
        if _safe_float(row.get("rule_component", 0.0)) > 0 or len(alert_ids) > 0:
            signal_families.append("rules")
        if _safe_float(row.get("ml_component", 0.0)) > 0 or int(_safe_float(row.get("high_risk_claim_count", 0))) > 0:
            signal_families.append("ml")
        if _safe_float(row.get("anomaly_component", 0.0)) > 0 or int(_safe_float(row.get("anomaly_flag", 0))) > 0:
            signal_families.append("anomaly")
        if _safe_float(row.get("network_component", 0.0)) > 0 or row.get("community_id") is not None:
            signal_families.append("network")
        if _safe_float(row.get("future_component", 0.0)) > 0:
            signal_families.append("future_risk")
        if _safe_float(row.get("temporal_component", 0.0)) > 0:
            signal_families.append("temporal")

        # Distinct rules triggered
        distinct_rules: List[str] = []
        for aid in alert_ids:
            # Extract rule ID like R06 from A-R06-xxxx
            parts = aid.split("-")
            if len(parts) >= 2 and parts[1].startswith("R"):
                distinct_rules.append(parts[1])
        distinct_rules = sorted(list(set(distinct_rules)))

        top_reasons = _parse_list(row.get("top_reasons"))
        net_rels = net_rel_by_prov.get(pid, [])
        comm_id = int(row["community_id"]) if pd.notna(row.get("community_id")) else None

        title = generate_case_title(pid, risk_tier, top_reasons, signal_families)
        summary = generate_case_summary(
            pid, risk_score, risk_tier, ev_strength, ev_tier,
            conf_score, conf_tier, exposure, len(alert_ids), len(claim_ids),
            top_reasons, signal_families
        )

        r30 = _safe_float(row.get("risk_30d", 0.0))
        recommendations = generate_investigation_recommendations(
            distinct_rules, len(claim_ids), int(_safe_float(row.get("anomaly_flag", 0))),
            r30, comm_id, net_rels
        )

        case_obj = InvestigationCase(
            case_id=case_id,
            provider_id=pid,
            title=title,
            summary=summary,
            risk_score=risk_score,
            risk_tier=risk_tier,
            evidence_strength=ev_strength,
            evidence_tier=ev_tier,
            confidence_score=conf_score,
            confidence_tier=conf_tier,
            estimated_exposure=exposure,
            status=default_status,
            priority=priority,
            created_at=timestamp_now,
            updated_at=timestamp_now,
            community_id=comm_id,
            claim_count=len(claim_ids),
            high_risk_claim_count=int(_safe_float(row.get("high_risk_claim_count", 0))),
            rule_alert_count=len(alert_ids),
            high_severity_rule_count=int(_safe_float(row.get("high_severity_rule_count", 0))),
            distinct_rule_count=len(distinct_rules),
            anomaly_score=_safe_float(row.get("anomaly_score", 0.0)),
            anomaly_flag=int(_safe_float(row.get("anomaly_flag", 0))),
            risk_30d=r30,
            risk_60d=_safe_float(row.get("risk_60d", 0.0)),
            risk_90d=_safe_float(row.get("risk_90d", 0.0)),
            top_reasons=top_reasons,
            signal_families=signal_families,
            claim_ids=claim_ids,
            alert_ids=alert_ids,
            evidence_ids=evidence_ids,
            network_relationships=net_rels,
            investigation_recommendations=recommendations,
            model_version=str(row.get("model_version", "1.0.0")),
            feature_version=str(row.get("feature_version", "1.0.0")),
            risk_engine_version=str(row.get("risk_engine_version", "1.0.0")),
            case_builder_version=builder_version,
        )

        val_errs = case_obj.validate()
        if val_errs:
            raise ValueError(f"Case validation error for {case_id}: {val_errs}")

        cases_records.append(case_obj.to_dict(serialize_lists=False))

        # Generate Case Evidence Records
        # 1. Rule Alerts Evidence
        for al in prov_alerts:
            ev_rec = CaseEvidenceRecord(
                case_id=case_id,
                evidence_id=str(al.get("alert_id")),
                source_type="RULE",
                source_id=str(al.get("alert_id")),
                provider_id=pid,
                claim_id=",".join(str(c) for c in al.get("claim_ids", [])[:3]),
                rule_id=str(al.get("rule_id", "")),
                description=f"Detection rule {al.get('rule_id')} alert ({al.get('severity')})",
                severity=str(al.get("severity", "MEDIUM")),
                estimated_amount=_safe_float(al.get("est_dollars", 0.0)),
            )
            evidence_records.append(ev_rec.to_dict())

        # 2. Claim ML Evidence (sample top high risk claims)
        for cid in claim_ids[:10]:
            ev_rec = CaseEvidenceRecord(
                case_id=case_id,
                evidence_id=f"E-ML-{cid}",
                source_type="ML",
                source_id=cid,
                provider_id=pid,
                claim_id=cid,
                rule_id=None,
                description=f"Suspicious claim transaction flagged by claim-level ML model",
                severity="HIGH" if risk_tier in ("CRITICAL", "HIGH") else "MEDIUM",
                estimated_amount=0.0,
            )
            evidence_records.append(ev_rec.to_dict())

        # 3. Behavioral Anomaly Evidence
        if case_obj.anomaly_flag == 1 or _safe_float(row.get("anomaly_component", 0.0)) >= 0.70:
            ev_rec = CaseEvidenceRecord(
                case_id=case_id,
                evidence_id=f"E-ANOM-{pid}",
                source_type="ANOMALY",
                source_id="ISOLATION_FOREST",
                provider_id=pid,
                description=f"Behavioral anomaly decision score {case_obj.anomaly_score:.3f}",
                severity="HIGH" if case_obj.anomaly_flag == 1 else "MEDIUM",
                estimated_amount=0.0,
            )
            evidence_records.append(ev_rec.to_dict())

        # 4. Network Evidence
        if comm_id is not None:
            ev_rec = CaseEvidenceRecord(
                case_id=case_id,
                evidence_id=f"E-NET-{pid}-COMM{comm_id}",
                source_type="NETWORK",
                source_id=f"COMM-{comm_id}",
                provider_id=pid,
                description=f"Member of affiliated provider network (Community #{comm_id})",
                severity="HIGH" if net_rels else "MEDIUM",
                estimated_amount=0.0,
            )
            evidence_records.append(ev_rec.to_dict())

    cases_df = pd.DataFrame(cases_records)
    evidence_df = pd.DataFrame(evidence_records)

    return cases_df, evidence_df


# ------------------------------------------------------------------------------
# High-Level Pipeline Runner
# ------------------------------------------------------------------------------

def run_case_builder(
    output_dir: Union[str, Path] = "outputs/cases",
    provider_scores_path: Optional[Union[str, Path]] = None,
    alerts_data: Optional[Any] = None,
    claim_ml_path: Optional[Union[str, Path]] = None,
    anomaly_path: Optional[Union[str, Path]] = None,
    future_risk_path: Optional[Union[str, Path]] = None,
    network_data: Optional[Any] = None,
    config_path: Optional[Union[str, Path]] = None,
    save_parquet: bool = True,
    save_csv: bool = True,
) -> Dict[str, Any]:
    """
    Execute Case Builder pipeline and save cases.parquet, cases.csv, and case_evidence.parquet.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve provider_scores_path
    ps_path = provider_scores_path
    if ps_path is None:
        if Path("outputs/risk/provider_scores.parquet").exists():
            ps_path = "outputs/risk/provider_scores.parquet"
        elif Path("outputs/risk/provider_scores.csv").exists():
            ps_path = "outputs/risk/provider_scores.csv"
        else:
            raise FileNotFoundError("Could not find provider_scores artifact. Run Unified Risk Engine first.")

    print(f"[Case Builder] Loading provider scores from {ps_path}...")
    cases_df, evidence_df = build_cases(
        provider_scores=ps_path,
        alerts=alerts_data,
        network_output=network_data,
        config=config_path,
    )

    print(f"[Case Builder] Constructed {len(cases_df):,} investigation cases ({len(evidence_df):,} evidence items).")

    saved_files: List[Path] = []
    if not cases_df.empty:
        # Save cases.parquet
        if save_parquet:
            cpq_path = out_dir / "cases.parquet"
            pq_df = cases_df.copy()
            for col in [
                "top_reasons", "signal_families", "claim_ids", "alert_ids",
                "evidence_ids", "network_relationships", "investigation_recommendations"
            ]:
                if col in pq_df.columns:
                    pq_df[col] = pq_df[col].apply(lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x)
            pq_df.to_parquet(cpq_path, index=False)
            saved_files.append(cpq_path)
            print(f"[Case Builder] Saved Cases Parquet -> {cpq_path}")

            epq_path = out_dir / "case_evidence.parquet"
            evidence_df.to_parquet(epq_path, index=False)
            saved_files.append(epq_path)
            print(f"[Case Builder] Saved Case Evidence Parquet -> {epq_path}")

        # Save cases.csv
        if save_csv:
            csv_path = out_dir / "cases.csv"
            csv_df = cases_df.copy()
            for col in [
                "top_reasons", "signal_families", "claim_ids", "alert_ids",
                "evidence_ids", "network_relationships", "investigation_recommendations"
            ]:
                if col in csv_df.columns:
                    csv_df[col] = csv_df[col].apply(lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x)
            csv_df.to_csv(csv_path, index=False)
            saved_files.append(csv_path)
            print(f"[Case Builder] Saved Cases CSV -> {csv_path}")

    summary = {
        "n_cases_created": len(cases_df),
        "n_evidence_records": len(evidence_df),
        "priority_distribution": cases_df["priority"].value_counts().to_dict() if not cases_df.empty else {},
        "status_distribution": cases_df["status"].value_counts().to_dict() if not cases_df.empty else {},
        "saved_files": [str(p) for p in saved_files],
    }
    return summary


# ------------------------------------------------------------------------------
# CLI Entry Point
# ------------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Vigil-X Case Builder Subsystem")
    parser.add_argument("--output-dir", default="outputs/cases", help="Output directory for cases")
    parser.add_argument("--scores-path", default="outputs/risk/provider_scores.parquet", help="Path to provider_scores.parquet")
    parser.add_argument("--config", default=None, help="Path to case_config.yaml")
    args = parser.parse_args()

    print("=" * 70)
    print("  VIGIL-X CASE BUILDER SUBSYSTEM")
    print("=" * 70)

    summary = run_case_builder(
        output_dir=args.output_dir,
        provider_scores_path=args.scores_path,
        config_path=args.config,
    )
    print("\n" + "=" * 70)
    print(f"Completed: {summary['n_cases_created']} cases created.")
    print(f"Priority distribution: {summary['priority_distribution']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
