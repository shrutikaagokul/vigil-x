"""
Script to generate data, run detection rules & network features, and build app.db.

Usage:
    python scripts/build_db.py [--db-path app.db] [--quick]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
from eval.evaluate import evaluate_rules
from eval.ring_recovery import evaluate_ring_recovery
from db.loader import rebuild_database


def build_pipeline_and_db(
    db_path: str = "app.db",
    quick: bool = False,
) -> dict:
    print(f"[*] Starting Vigil-X Pipeline & SQLite DB Build -> {db_path}")

    # 1. Generate synthetic dataset
    if quick:
        print("[1/5] Generating quick synthetic dataset (80 providers, 1500 members, 12 months)...")
        data = generate_synthetic_data(n_providers=80, n_members=1500, n_facilities=15, n_months=12, seed=42)
    else:
        print("[1/5] Generating benchmark synthetic dataset (150 providers, 3000 members, 12 months)...")
        data = generate_synthetic_data(n_providers=150, n_members=3000, n_facilities=25, n_months=12, seed=42)

    # 2. Run detection rules
    print("[2/5] Running detection rules R01–R10...")
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
    print("[3/5] Constructing graph, projecting providers, and detecting communities...")
    G = build_graph(data["claims"], data["providers"], referrals=data["referrals"], facilities=data["facilities"])
    P = build_provider_projection(G)
    communities = detect_communities(P)
    print(f"    - Detected {len(communities)} provider communities")

    networks_df = compute_network_features(P, communities, data["claims"], all_alerts)
    print(f"    - Computed {len(networks_df)} network feature records")

    # 4. Evaluation
    print("[4/5] Evaluating detection against ground truth...")
    eval_metrics = evaluate_rules(
        all_alerts, data["gt_claim_labels"], data["gt_entity_labels"], data["gt_scenarios"]
    )
    ring_metrics = evaluate_ring_recovery(communities, data["gt_scenarios"])
    combined_eval = {
        "rule_evaluation": eval_metrics,
        "ring_recovery": ring_metrics,
    }

    # 5. Build SQLite application database
    print(f"[5/5] Ingesting all pipeline outputs into SQLite ({db_path})...")
    stats = rebuild_database(
        db_path=db_path,
        data_dict=data,
        alerts=all_alerts,
        networks_df=networks_df,
        eval_results=combined_eval,
    )

    print("\n[SUCCESS] Application database built successfully:")
    for k, v in stats.items():
        print(f"    - {k}: {v} records")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Vigil-X SQLite database from pipeline.")
    parser.add_argument("--db-path", default="app.db", help="Target SQLite file path")
    parser.add_argument("--quick", action="store_true", help="Generate smaller dataset for quick build")
    args = parser.parse_args()

    build_pipeline_and_db(db_path=args.db_path, quick=args.quick)
