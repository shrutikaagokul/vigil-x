"""
Community detection for Vigil-X.

Uses Louvain community detection on the provider projection graph.
For each community, computes descriptive statistics and identifies hub providers,
classifying clusters into investigation candidates without making declarative fraud labels.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import networkx as nx
import pandas as pd

try:
    import community as community_louvain
    HAS_LOUVAIN = True
except ImportError:
    HAS_LOUVAIN = False


def detect_communities(
    P: nx.Graph,
    resolution: float = 1.0,
    min_size: int = 2,
) -> List[Dict]:
    """
    Detect provider communities using Louvain.

    Args:
        P: Provider projection graph (undirected, weighted)
        resolution: Louvain resolution parameter
        min_size: Minimum community size to report

    Returns:
        List of community dicts with metadata
    """
    if not HAS_LOUVAIN:
        raise ImportError("python-louvain is required. Install: pip install python-louvain")

    if P.number_of_nodes() == 0:
        return []

    # Run Louvain
    partition = community_louvain.best_partition(P, weight="weight", resolution=resolution)

    # Group providers by community
    communities_map: Dict[int, List[str]] = {}
    for node, comm_id in partition.items():
        communities_map.setdefault(comm_id, []).append(node)

    # Build community metadata
    communities = []
    for comm_id, members in communities_map.items():
        if len(members) < min_size:
            continue

        # Identify hub (highest weighted degree)
        subgraph = P.subgraph(members)
        degrees = dict(subgraph.degree(weight="weight"))
        hub = max(degrees, key=degrees.get) if degrees else members[0]

        # Edge type breakdown
        edge_types: Dict[str, int] = {}
        for u, v, data in subgraph.edges(data=True):
            for et, count in data.get("edge_types", {}).items():
                edge_types[et] = edge_types.get(et, 0) + count

        # Count hard identity links
        hard_bases = {"shared_bank_hash", "shared_tin_hash", "shared_owner_exact", "shared_registered_agent"}
        hard_link_count = sum(
            count for et, count in edge_types.items() if et in hard_bases
        )

        # Referral link count
        referral_count = edge_types.get("refers_to", 0)

        # Objective investigation category assessment (non-declarative)
        if hard_link_count >= 2 or (hard_link_count >= 1 and referral_count >= 2):
            category = "high-risk network"
        elif hard_link_count >= 1 or referral_count >= 3:
            category = "investigation candidate network"
        elif len(members) >= 3:
            category = "connected provider cluster"
        else:
            category = "small provider cluster"

        communities.append({
            "community_id": comm_id,
            "provider_ids": sorted(members),
            "n_providers": len(members),
            "hub_provider_id": hub,
            "edge_types": edge_types,
            "hard_link_count": hard_link_count,
            "referral_link_count": referral_count,
            "investigation_category": category,
            "total_internal_weight": sum(
                data.get("weight", 0)
                for _, _, data in subgraph.edges(data=True)
            ),
        })

    return sorted(communities, key=lambda c: -c["n_providers"])


def enrich_communities_with_claims(
    communities: List[Dict],
    claims: pd.DataFrame,
    alerts: Optional[List] = None,
) -> List[Dict]:
    """
    Enrich community metadata with claim-level statistics.

    For each community:
    - total claims
    - total dollars
    - triggered rules (if alerts provided)
    """
    for comm in communities:
        prov_set = set(comm["provider_ids"])

        comm_claims = claims[claims["provider_id"].isin(prov_set)]
        comm["total_claims"] = len(comm_claims)
        comm["total_dollars"] = float(comm_claims["paid_amount"].sum()) if not comm_claims.empty else 0.0

        if alerts:
            triggered = set()
            suspicious_claims = set()
            for a in alerts:
                if getattr(a, "entity_id", None) in prov_set:
                    triggered.add(getattr(a, "rule_id", ""))
                    suspicious_claims.update(getattr(a, "claim_ids", []))
            comm["triggered_rules"] = sorted(triggered)
            comm["suspicious_claim_count"] = len(suspicious_claims)
        else:
            comm["triggered_rules"] = []
            comm["suspicious_claim_count"] = 0

    return communities
