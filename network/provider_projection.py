"""
Provider projection for Vigil-X.

Creates a provider-level graph suitable for community detection
and network analytics. Edge weights are explainable:

Hard identity links (bank, TIN, owner) > Referral > Shared members
"""
from __future__ import annotations

from typing import Dict, Optional

import networkx as nx
import pandas as pd


# Weight multipliers for different relationship types
_DEFAULT_WEIGHTS = {
    "shared_bank_hash": 10.0,
    "shared_tin_hash": 10.0,
    "shared_owner_exact": 8.0,
    "shared_owner_fuzzy": 5.0,
    "shared_registered_agent": 7.0,
    "shared_address_suite": 3.0,
    "shared_address_no_suite": 2.0,
    "refers_to": 1.0,
    "shared_members": 0.5,
    "works_at": 0.3,
}


def build_provider_projection(
    G: nx.MultiDiGraph,
    weight_overrides: Optional[Dict[str, float]] = None,
) -> nx.Graph:
    """
    Create an undirected provider-level projection from the full graph.

    Collapses multi-edges into single weighted edges.
    Only includes provider nodes.

    Args:
        G: Full Vigil-X graph
        weight_overrides: Optional overrides for edge type weights

    Returns:
        Undirected weighted Graph of providers
    """
    weights = {**_DEFAULT_WEIGHTS, **(weight_overrides or {})}

    # Get provider nodes
    provider_nodes = [
        n for n, d in G.nodes(data=True) if d.get("node_type") == "provider"
    ]
    provider_set = set(provider_nodes)

    P = nx.Graph()
    P.add_nodes_from(provider_nodes)

    # Copy node attributes
    for n in provider_nodes:
        P.nodes[n].update(G.nodes[n])

    # Aggregate edges between providers
    edge_data: Dict = {}
    for u, v, data in G.edges(data=True):
        if u not in provider_set or v not in provider_set:
            continue

        pair = tuple(sorted([u, v]))
        edge_type = data.get("edge_type", "unknown")
        raw_weight = data.get("weight", 1)
        type_mult = weights.get(edge_type, 1.0)

        if pair not in edge_data:
            edge_data[pair] = {
                "total_weight": 0,
                "edge_types": {},
                "evidence_ids": [],
            }

        edge_data[pair]["total_weight"] += raw_weight * type_mult

        if edge_type not in edge_data[pair]["edge_types"]:
            edge_data[pair]["edge_types"][edge_type] = 0
        edge_data[pair]["edge_types"][edge_type] += raw_weight

        ev_ids = data.get("evidence_ids", [])
        edge_data[pair]["evidence_ids"].extend(ev_ids)

    # Add edges to projection
    for (u, v), d in edge_data.items():
        P.add_edge(u, v,
                   weight=d["total_weight"],
                   edge_types=d["edge_types"],
                   evidence_ids=list(set(d["evidence_ids"])))

    return P
