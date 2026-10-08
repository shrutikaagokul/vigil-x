"""
Ring recovery evaluation for Vigil-X.

Measures whether the graph/community detection subsystem
recovers the planted provider networks from synthetic data.

Ground truth is used ONLY here — never in detection.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

import pandas as pd


def evaluate_ring_recovery(
    communities: List[Dict],
    gt_scenarios: pd.DataFrame,
    output_path: Optional[str] = None,
) -> Dict:
    """
    Evaluate ring recovery: do detected communities match planted rings?

    For each planted ring:
    - ring ID
    - expected providers
    - best-matching detected community
    - recovered providers
    - recovery rate
    - whether it forms one community
    - false member count
    """
    if gt_scenarios.empty:
        return {"rings": [], "summary": {}}

    results = []

    for _, scenario in gt_scenarios.iterrows():
        ring_id = scenario.get("ring_id", scenario.get("scenario_id"))
        expected_providers = set(
            str(scenario["provider_ids"]).split(",")
        )

        if not expected_providers:
            continue

        # Find best matching community
        best_match = None
        best_overlap = 0
        best_community = None

        for comm in communities:
            comm_providers = set(comm.get("provider_ids", []))
            overlap = expected_providers & comm_providers
            if len(overlap) > best_overlap:
                best_overlap = len(overlap)
                best_match = comm
                best_community = comm.get("community_id")

        recovered = set()
        false_members = 0
        forms_one = False

        if best_match:
            comm_providers = set(best_match.get("provider_ids", []))
            recovered = expected_providers & comm_providers
            false_members = len(comm_providers - expected_providers)
            forms_one = recovered == expected_providers

        recovery_rate = len(recovered) / len(expected_providers) if expected_providers else 0

        results.append({
            "ring_id": ring_id,
            "scenario_id": scenario["scenario_id"],
            "scenario_type": scenario.get("scenario_type", ""),
            "expected_providers": sorted(expected_providers),
            "detected_community": best_community,
            "recovered_providers": sorted(recovered),
            "recovery_rate": round(recovery_rate, 4),
            "forms_one_community": forms_one,
            "false_member_count": false_members,
            "expected_count": len(expected_providers),
            "recovered_count": len(recovered),
        })

    # Summary
    total_rings = len(results)
    fully_recovered = sum(1 for r in results if r["recovery_rate"] == 1.0)
    partially_recovered = sum(1 for r in results if 0 < r["recovery_rate"] < 1.0)
    not_recovered = sum(1 for r in results if r["recovery_rate"] == 0.0)
    avg_recovery = (
        sum(r["recovery_rate"] for r in results) / total_rings
        if total_rings > 0 else 0
    )

    output = {
        "rings": results,
        "summary": {
            "total_rings": total_rings,
            "fully_recovered": fully_recovered,
            "partially_recovered": partially_recovered,
            "not_recovered": not_recovered,
            "avg_recovery_rate": round(avg_recovery, 4),
        },
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

    return output
