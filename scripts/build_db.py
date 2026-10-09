"""
Script to generate data, run detection rules & network features,
run the unified risk engine, build cases, and populate app.db.

Usage:
    python scripts/build_db.py [--db-path app.db] [--quick]
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from generator.synthetic_data import generate_synthetic_data
from rules.runner import run_network_behavior_rules
from src.vigilx.runner import run_claim_utilization_rules
from network.graph_builder import build_graph
from network.provider_projection import build_provider_projection
from network.community import detect_communities
from network.network_features import compute_network_features
from risk.unified_risk import compute_unified_risk
from eval.evaluate import evaluate_rules
from eval.ring_recovery import evaluate_ring_recovery
from db.loader import rebuild_database


# ── Rule name lookup for human-readable evidence ─────────────────────
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


def _build_cases_from_risk_scores(
    risk_df: pd.DataFrame,
    all_alerts: list,
    claims_df: pd.DataFrame,
    providers_df: pd.DataFrame,
    networks_df: pd.DataFrame,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Build cases, case evidence, and queue items from actual unified risk engine output.

    Each provider with risk_score > 0 gets a case. Priority/rank are determined by
    the integrated risk score, not hard-coded.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Provider name lookup
    provider_names: Dict[str, str] = {}
    if providers_df is not None and not providers_df.empty:
        for _, p in providers_df.iterrows():
            provider_names[str(p["provider_id"])] = str(p.get("name", f"Provider {p['provider_id']}"))

    # Index alerts by provider
    alerts_by_provider: Dict[str, list] = {}
    for a in all_alerts:
        d = a.to_dict() if hasattr(a, "to_dict") else a
        eid = str(d.get("entity_id", ""))
        alerts_by_provider.setdefault(eid, []).append(d)

    # Network lookup by hub provider
    network_by_hub: Dict[str, Dict[str, Any]] = {}
    if networks_df is not None and not networks_df.empty:
        for _, net in networks_df.iterrows():
            hub = str(net.get("hub_provider_id", ""))
            if hub:
                network_by_hub[hub] = net.to_dict()

    cases: List[Dict[str, Any]] = []
    evidence_items: List[Dict[str, Any]] = []
    queue_items: List[Dict[str, Any]] = []

    for _, row in risk_df.iterrows():
        pid = str(row["provider_id"])
        risk_score_01 = float(row.get("risk_score", 0.0))
        # Scale from [0,1] to [0,100] for case display
        risk_score_100 = round(risk_score_01 * 100.0, 1)

        # Only create cases for providers with alerts or meaningful risk
        provider_alerts = alerts_by_provider.get(pid, [])
        if risk_score_100 < 1.0 and not provider_alerts:
            continue

        case_id = f"CASE-PRV-{pid}"
        entity_name = provider_names.get(pid, f"Provider {pid}")

        # Gather claim IDs from alerts
        all_claim_ids = set()
        why_flagged = []
        top_reasons = []
        benign_explanations = []
        total_exposure = 0.0

        for a in provider_alerts:
            rule_id = a.get("rule_id", "UNKNOWN")
            rule_name = RULE_NAMES.get(rule_id, rule_id)
            c_ids = a.get("claim_ids", [])
            all_claim_ids.update(c_ids)
            est = float(a.get("est_dollars", 0.0) or 0.0)
            total_exposure += est

            why = f"Triggered {rule_id} ({rule_name})"
            if why not in why_flagged:
                why_flagged.append(why)

            # Build evidence items from alert evidence
            for ev in a.get("evidence", []):
                ev_d = ev if isinstance(ev, dict) else (ev.to_dict() if hasattr(ev, "to_dict") else {})
                ev_id = ev_d.get("evidence_id") or f"E-{rule_id}-{uuid.uuid4().hex[:6]}"
                plain_text = ev_d.get("plain_text", why)
                fields_matched = ev_d.get("fields_matched", [])
                ev_claims = ev_d.get("claim_ids", c_ids)
                ev_overpay = float(ev_d.get("est_overpay", 0.0) or 0.0)
                fp_note = ev_d.get("fp_notes")
                if fp_note:
                    note_str = str(fp_note) if isinstance(fp_note, str) else "; ".join(fp_note) if isinstance(fp_note, list) else str(fp_note)
                    if note_str and note_str not in benign_explanations:
                        benign_explanations.append(note_str)

                evidence_items.append({
                    "evidence_id": ev_id,
                    "case_id": case_id,
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "claim_id": ev_claims[0] if ev_claims else None,
                    "entity_id": pid,
                    "field_name": ", ".join(fields_matched) if fields_matched else "multiple",
                    "field_value": str(ev_d.get("matched_value", "")),
                    "plain_text": plain_text,
                    "est_overpay": ev_overpay if ev_overpay > 0 else est,
                    "severity": str(ev_d.get("severity", "MEDIUM")),
                    "source_table": "alerts",
                    "source_artifact": f"rule_engine/{rule_id.lower()}",
                    "timestamp": now_iso,
                    "fp_notes": str(fp_note) if fp_note else None,
                })

                if plain_text not in top_reasons and len(top_reasons) < 4:
                    top_reasons.append(plain_text)

        # Use top_reasons from unified risk engine if available
        risk_top_reasons = row.get("top_reasons", [])
        if isinstance(risk_top_reasons, str):
            try:
                risk_top_reasons = json.loads(risk_top_reasons)
            except Exception:
                risk_top_reasons = [risk_top_reasons]
        if risk_top_reasons and isinstance(risk_top_reasons, list):
            top_reasons = risk_top_reasons[:4]

        # Priority tier from risk score
        if risk_score_100 >= 75.0:
            priority = "CRITICAL"
        elif risk_score_100 >= 50.0:
            priority = "HIGH"
        elif risk_score_100 >= 25.0:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        # Members affected
        members_affected = 1
        if claims_df is not None and not claims_df.empty and all_claim_ids:
            matching = claims_df[claims_df["claim_id"].isin(all_claim_ids)]
            if not matching.empty and "member_id" in matching.columns:
                members_affected = int(matching["member_id"].nunique())

        exposure_low = round(total_exposure * 0.8, 2)
        exposure_high = round(max(total_exposure * 1.2, 500.0), 2)

        # Risk components from unified engine
        risk_components = {
            "rule_risk": round(float(row.get("rule_component", 0.0)), 3),
            "ml_risk": round(float(row.get("ml_component", 0.0)), 3),
            "anomaly_risk": round(float(row.get("anomaly_component", 0.0)), 3),
            "network_risk": round(float(row.get("network_component", 0.0)), 3),
            "temporal_risk": round(float(row.get("temporal_component", 0.0)), 3),
            "future_risk": round(float(row.get("future_component", 0.0)), 3),
        }

        confidence = round(float(row.get("confidence_score", 0.85)), 3)
        evidence_strength = round(float(row.get("evidence_strength", 0.80)), 3)

        net_info = network_by_hub.get(pid)
        net_id = net_info.get("network_id") if net_info else None

        future_risk = {
            "risk_30d": round(float(row.get("risk_30d", 0.0)), 2),
            "risk_60d": round(float(row.get("risk_60d", 0.0)), 2),
            "risk_90d": round(float(row.get("risk_90d", 0.0)), 2),
        }

        cases.append({
            "case_id": case_id,
            "entity_type": "provider",
            "entity_id": pid,
            "entity_name": entity_name,
            "status": "NEW",
            "priority": priority,
            "risk_score": risk_score_100,
            "confidence": confidence,
            "evidence_strength": evidence_strength,
            "exposure_low": exposure_low,
            "exposure_high": exposure_high,
            "members_affected": members_affected,
            "claims_count": len(all_claim_ids),
            "why_flagged": why_flagged if why_flagged else ["Elevated unified risk indicator"],
            "top_reasons": top_reasons if top_reasons else ["Elevated risk prioritization indicator"],
            "benign_explanations": benign_explanations,
            "risk_components": risk_components,
            "future_risk": future_risk,
            "network_id": net_id,
            "assigned_to": None,
        })

    # Sort cases by risk score descending for queue ranking
    cases.sort(key=lambda c: c["risk_score"], reverse=True)

    # Build queue items with SIU priority formula
    for rank, c in enumerate(cases, start=1):
        risk_norm = min(c["risk_score"] / 100.0, 1.0)
        dollar_norm = min(c["exposure_high"] / 50000.0, 1.0)
        member_norm = min(c["members_affected"] / 10.0, 1.0)
        sev_map = {"CRITICAL": 1.0, "HIGH": 0.75, "MEDIUM": 0.50, "LOW": 0.25}
        sev_norm = sev_map.get(c["priority"], 0.5)
        ev_norm = c["evidence_strength"]

        # SIU priority formula per spec
        priority_score = 100.0 * (
            0.30 * risk_norm
            + 0.25 * dollar_norm
            + 0.15 * member_norm
            + 0.10 * sev_norm
            + 0.20 * ev_norm
        )

        effort_hours = round(min(2.0 + (c["claims_count"] * 0.1), 8.0), 1)
        ev_per_hour = round(c["exposure_high"] / max(effort_hours, 1.0), 2)

        queue_items.append({
            "case_id": c["case_id"],
            "rank": rank,
            "baseline_rank": rank,
            "entity_type": "provider",
            "entity_id": c["entity_id"],
            "entity_name": c["entity_name"],
            "risk": c["risk_score"],
            "priority": c["priority"],
            "exposure_low": c["exposure_low"],
            "exposure_high": c["exposure_high"],
            "members_affected": c["members_affected"],
            "severity": c["priority"],
            "evidence_strength": c["evidence_strength"],
            "confidence": c["confidence"],
            "effort_hours": effort_hours,
            "ev_per_hour": ev_per_hour,
            "slot": rank,
            "top_reasons": c["top_reasons"],
        })

    # Re-sort queue by priority_score (already sorted by risk_score)
    return cases, evidence_items, queue_items


def _build_risk_scores_for_db(risk_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert unified risk DataFrame to the risk_scores DB contract."""
    records = []
    for _, row in risk_df.iterrows():
        records.append({
            "entity_type": "provider",
            "entity_id": str(row["provider_id"]),
            "risk_score": round(float(row.get("risk_score", 0.0)) * 100.0, 1),
            "anomaly_score": round(float(row.get("anomaly_component", 0.0)), 4),
            "rule_score": round(float(row.get("rule_component", 0.0)), 4),
            "network_score": round(float(row.get("network_component", 0.0)), 4),
            "future_risk_score": round(float(row.get("future_component", 0.0)), 4),
            "confidence": round(float(row.get("confidence_score", 0.85)), 4),
            "evidence_strength": round(float(row.get("evidence_strength", 0.80)), 4),
        })
    return records


def build_pipeline_and_db(
    db_path: str = "app.db",
    quick: bool = False,
    export_artifacts_dir: Optional[str] = None,
) -> dict:
    print(f"[*] Starting Vigil-X Full Integrated Pipeline & SQLite DB Build -> {db_path}")

    # 1. Generate synthetic dataset
    if quick:
        print("[1/7] Generating quick synthetic dataset (80 providers, 1500 members, 12 months)...")
        data = generate_synthetic_data(n_providers=80, n_members=1500, n_facilities=15, n_months=12, seed=42)
    else:
        print("[1/7] Generating benchmark synthetic dataset (150 providers, 3000 members, 12 months)...")
        data = generate_synthetic_data(n_providers=150, n_members=3000, n_facilities=25, n_months=12, seed=42)

    # 2. Run detection rules R01-R10
    print("[2/7] Running detection rules R01–R10...")
    all_alerts = []

    # R01-R05
    try:
        data_r01 = dict(data)
        claims_adapter = data["claims"].copy()
        if "service_date" in claims_adapter.columns and "service_from" not in claims_adapter.columns:
            claims_adapter["service_from"] = pd.to_datetime(claims_adapter["service_date"])
        if "procedure_code" in claims_adapter.columns and "cpt_code" not in claims_adapter.columns:
            claims_adapter["cpt_code"] = claims_adapter["procedure_code"]
        if "provider_id" in claims_adapter.columns and "billing_provider_id" not in claims_adapter.columns:
            claims_adapter["billing_provider_id"] = claims_adapter["provider_id"]
        if "status" in claims_adapter.columns and "claim_status" not in claims_adapter.columns:
            claims_adapter["claim_status"] = claims_adapter["status"]
        if "modifier" not in claims_adapter.columns:
            claims_adapter["modifier"] = None
        data_r01["claims"] = claims_adapter

        r01_r05 = run_claim_utilization_rules(data_r01)
        all_alerts.extend(r01_r05)
        print(f"    - R01–R05 produced {len(r01_r05)} alerts")
    except Exception as e:
        print(f"    - [WARN] R01–R05 error: {e}")

    # R06-R10
    try:
        r06_r10 = run_network_behavior_rules(data)
        all_alerts.extend(r06_r10)
        print(f"    - R06–R10 produced {len(r06_r10)} alerts")
    except Exception as e:
        print(f"    - [WARN] R06–R10 error: {e}")

    print(f"    Total alerts: {len(all_alerts)}")

    # 3. Graph construction and network features
    print("[3/7] Constructing graph, projecting providers, and detecting communities...")
    G = build_graph(data["claims"], data["providers"], referrals=data["referrals"], facilities=data["facilities"])
    P = build_provider_projection(G)
    communities = detect_communities(P)
    print(f"    - Detected {len(communities)} provider communities")

    networks_df = compute_network_features(P, communities, data["claims"], all_alerts)
    print(f"    - Computed {len(networks_df)} network feature records")

    # 4. Unified Risk Engine
    print("[4/7] Running unified risk engine...")
    risk_df = compute_unified_risk(
        rules_output=all_alerts,
        network_output=communities,
        config=None,  # Uses default risk_config.yaml
    )
    print(f"    - Scored {len(risk_df)} providers")
    if not risk_df.empty:
        tier_dist = risk_df["risk_tier"].value_counts().to_dict()
        print(f"    - Tier distribution: {tier_dist}")

    # 5. Build cases and queue from actual risk engine output
    print("[5/7] Building cases and SIU queue from unified risk output...")
    cases, case_evidence, queue_items = _build_cases_from_risk_scores(
        risk_df, all_alerts, data["claims"], data["providers"], networks_df
    )
    print(f"    - Built {len(cases)} cases, {len(case_evidence)} evidence items, {len(queue_items)} queue items")

    # 6. Evaluation
    print("[6/7] Evaluating detection against ground truth...")
    eval_metrics = evaluate_rules(
        all_alerts, data["gt_claim_labels"], data["gt_entity_labels"], data["gt_scenarios"]
    )
    ring_metrics = evaluate_ring_recovery(communities, data["gt_scenarios"])
    combined_eval = {
        "rule_evaluation": eval_metrics,
        "ring_recovery": ring_metrics,
    }

    # 7. Build SQLite application database
    print(f"[7/7] Ingesting all pipeline outputs into SQLite ({db_path})...")
    risk_scores_for_db = _build_risk_scores_for_db(risk_df) if not risk_df.empty else None

    stats = rebuild_database(
        db_path=db_path,
        data_dict=data,
        alerts=all_alerts,
        networks_df=networks_df,
        cases_data=cases if cases else None,
        case_evidence_data=case_evidence if case_evidence else None,
        queue_data=queue_items if queue_items else None,
        risk_scores_data=risk_scores_for_db,
        eval_results=combined_eval,
        data_mode="fixture",
    )

    # 8. Export compatible artifacts if requested/quick mode
    export_dir = export_artifacts_dir or ("outputs/quick" if quick else None)
    if export_dir:
        out_p = Path(export_dir)
        out_p.mkdir(parents=True, exist_ok=True)
        if cases:
            cpq_df = pd.DataFrame(cases).copy()
            for col in ["why_flagged", "top_reasons", "benign_explanations", "risk_components", "future_risk"]:
                if col in cpq_df.columns:
                    cpq_df[col] = cpq_df[col].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)
            cpq_df.to_parquet(out_p / "cases.parquet", index=False)
        if case_evidence:
            pd.DataFrame(case_evidence).to_parquet(out_p / "case_evidence.parquet", index=False)
        if queue_items:
            q_df = pd.DataFrame(queue_items).copy()
            if "top_reasons" in q_df.columns:
                q_df["top_reasons"] = q_df["top_reasons"].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)
            q_df.to_parquet(out_p / "siu_queue.parquet", index=False)
        if risk_df is not None and not risk_df.empty:
            risk_df.to_parquet(out_p / "provider_scores.parquet", index=False)
        with open(out_p / "evaluation_report.json", "w") as fp:
            json.dump(combined_eval, fp, indent=2, default=str)
        print(f"    - Exported compatible quick dataset artifacts to {out_p}")

    print("\n[SUCCESS] Application database built successfully:")
    for k, v in stats.items():
        print(f"    - {k}: {v} records")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Vigil-X SQLite database from full integrated pipeline.")
    parser.add_argument("--db-path", default="app.db", help="Target SQLite file path")
    parser.add_argument("--quick", action="store_true", help="Generate smaller dataset for quick build")
    parser.add_argument("--export-artifacts", default=None, help="Directory to export matching parquet artifacts")
    args = parser.parse_args()

    build_pipeline_and_db(db_path=args.db_path, quick=args.quick, export_artifacts_dir=args.export_artifacts)

