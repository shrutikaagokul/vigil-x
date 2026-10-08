"""
Provider projection for Vigil-X.

Creates a provider-level graph suitable for community detection
and network analytics. Edge weights are explainable:

Hard identity links (bank, TIN, owner) > Referral > Shared facility > Shared members
"""
from __future__ import annotations

from typing import Dict, Optional, Set, Tuple

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
    "shared_facility": 1.5,
    "shared_ownership": 6.0,
    "shared_address": 1.5,
}


def build_provider_projection(
    G: nx.MultiDiGraph,
    weight_overrides: Optional[Dict[str, float]] = None,
) -> nx.Graph:
    """
    Create an undirected provider-level projection from the full graph.

    Collapses direct multi-edges and 2-hop shared entity links (facility, owner,
    bank, address) into single weighted provider-provider edges.
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

    edge_data: Dict[Tuple[str, str], Dict] = {}

    def _add_proj_edge(u: str, v: str, edge_type: str, raw_weight: float, ev_ids: list):
        if u == v:
            return
        pair = tuple(sorted([u, v]))
        type_mult = weights.get(edge_type, 1.0)

        if pair not in edge_data:
            edge_data[pair] = {
                "total_weight": 0.0,
                "edge_types": {},
                "evidence_ids": [],
            }

        edge_data[pair]["total_weight"] += raw_weight * type_mult
        edge_data[pair]["edge_types"][edge_type] = (
            edge_data[pair]["edge_types"].get(edge_type, 0) + raw_weight
        )
        edge_data[pair]["evidence_ids"].extend(ev_ids)

    # 1. Direct edges between provider nodes
    for u, v, data in G.edges(data=True):
        if u in provider_set and v in provider_set:
            edge_type = data.get("edge_type", "unknown")
            raw_weight = data.get("weight", 1.0)
            ev_ids = data.get("evidence_ids", [])
            _add_proj_edge(u, v, edge_type, raw_weight, ev_ids)

    # 2. 2-hop paths through intermediate non-provider nodes (facility, owner, bank_identity, address)
    non_provider_nodes = [
        n for n, d in G.nodes(data=True) if d.get("node_type") != "provider"
    ]
    for np_node in non_provider_nodes:
        ndata = G.nodes[np_node]
        ntype = ndata.get("node_type", "")

        # Find connected providers (predecessors and successors)
        connected_providers = set()
        for p in G.predecessors(np_node):
            if p in provider_set:
                connected_providers.add(p)
        for s in G.successors(np_node):
            if s in provider_set:
                connected_providers.add(s)

        prov_list = sorted(connected_providers)
        if len(prov_list) < 2:
            continue

        # Map non-provider node type to projected edge type
        proj_edge_type = "shared_facility"
        if ntype == "owner":
            proj_edge_type = "shared_ownership"
        elif ntype == "bank_identity":
            proj_edge_type = "shared_bank_hash"
        elif ntype == "address":
            proj_edge_type = "shared_address"
        elif ntype == "facility":
            proj_edge_type = "shared_facility"

        for i in range(len(prov_list)):
            for j in range(i + 1, len(prov_list)):
                _add_proj_edge(prov_list[i], prov_list[j], proj_edge_type, 1.0, [])

    # Add edges to projection graph
    for (u, v), d in edge_data.items():
        P.add_edge(
            u, v,
            weight=d["total_weight"],
            edge_types=d["edge_types"],
            evidence_ids=list(set(d["evidence_ids"])),
        )

    return P
