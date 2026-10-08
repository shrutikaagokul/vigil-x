"""
Network-level risk features for Vigil-X.

Computes structured network signals that feed into the downstream
risk engine. Does NOT compute the final unified Vigil-X risk score.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import networkx as nx
import pandas as pd


def compute_network_features(
    P: nx.Graph,
    communities: List[Dict],
    claims: pd.DataFrame,
    alerts: Optional[List] = None,
) -> pd.DataFrame:
    """
    Compute network-level features per community/network.

    Features:
    - Hard identity link strength
    - Referral concentration/reciprocity
    - Community suspiciousness
    - Financial exposure
    - Centrality metrics

    Returns:
        DataFrame suitable for saving as networks.parquet
    """
    records = []

    for comm in communities:
        comm_id = comm.get("community_id", 0)
        provider_ids = comm.get("provider_ids", [])
        n_providers = len(provider_ids)
        hub = comm.get("hub_provider_id", "")

        if n_providers == 0:
            continue

        prov_set = set(provider_ids)

        # --- Hard link score ---
        hard_link_count = comm.get("hard_link_count", 0)
        hard_link_score = min(hard_link_count / max(n_providers, 1), 1.0)

        # --- Referral score ---
        referral_count = comm.get("referral_link_count", 0)
        referral_score = min(referral_count / max(n_providers * 5, 1), 1.0)

        # --- Concentration score (based on edge type diversity) ---
        edge_types = comm.get("edge_types", {})
        n_edge_types = len(edge_types)
        concentration_score = min(n_edge_types / 5.0, 1.0)

        # --- Ownership overlap ---
        ownership_count = edge_types.get("shared_owner_exact", 0) + edge_types.get("shared_owner_fuzzy", 0)
        ownership_score = min(ownership_count / max(n_providers, 1), 1.0)

        # --- Financial exposure ---
        comm_claims = claims[claims["provider_id"].isin(prov_set)] if not claims.empty else pd.DataFrame()
        total_exposure = float(comm_claims["paid_amount"].sum()) if not comm_claims.empty else 0
        total_claims = len(comm_claims)

        # --- Suspicious claims / rules ---
        suspicious_claims = comm.get("suspicious_claim_count", 0)
        triggered_rules = comm.get("triggered_rules", [])

        # --- Centrality (betweenness of hub in projection) ---
        hub_centrality = 0.0
        if hub in P and P.number_of_nodes() > 1:
            try:
                bc = nx.betweenness_centrality(P, weight="weight")
                hub_centrality = bc.get(hub, 0.0)
            except Exception:
                pass

        # --- Documented group ---
        documented = False
        # (This could be enriched from entity clusters)

        records.append({
            "network_id": f"NET-{comm_id:04d}",
            "community_id": comm_id,
            "n_providers": n_providers,
            "hub_provider_id": hub,
            "hard_link_score": round(hard_link_score, 4),
            "referral_score": round(referral_score, 4),
            "concentration_score": round(concentration_score, 4),
            "ownership_score": round(ownership_score, 4),
            "suspicious_claims": suspicious_claims,
            "total_claims": total_claims,
            "total_exposure": round(total_exposure, 2),
            "triggered_rules": ",".join(triggered_rules),
            "hub_centrality": round(hub_centrality, 4),
            "documented_group": documented,
            "network_feature_version": "1.0.0",
        })

    return pd.DataFrame(records)
