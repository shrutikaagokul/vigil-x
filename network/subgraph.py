"""
Case subgraph extraction for Vigil-X.

Provides investigation-friendly subgraphs centered on a focal entity.
Supports cohort aggregation to avoid graph hairballs.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

import networkx as nx


def get_case_subgraph(
    G: nx.MultiDiGraph,
    entity_id: str,
    max_depth: int = 2,
    max_member_nodes: int = 5,
    edge_type_filter: Optional[Set[str]] = None,
    min_weight: float = 0.0,
) -> Dict:
    """
    Extract a compact investigation subgraph around a focal entity.

    Supports:
    - Focal provider + directly connected providers
    - Relevant facilities and owners
    - Cohort aggregation for shared members (avoids hairballs)
    - Filtering by edge type and weight

    Args:
        G: Full Vigil-X graph
        entity_id: Focal entity ID (typically a provider)
        max_depth: Max BFS depth
        max_member_nodes: Max individual member nodes before aggregation
        edge_type_filter: Only include these edge types (None = all)
        min_weight: Minimum edge weight to include

    Returns:
        Dict with nodes, edges, cohorts, and summary
    """
    if entity_id not in G:
        return {"nodes": [], "edges": [], "cohorts": [], "summary": {}}

    # BFS to collect neighborhood
    visited = {entity_id}
    frontier = {entity_id}

    for _ in range(max_depth):
        next_frontier = set()
        for node in frontier:
            for neighbor in set(G.successors(node)) | set(G.predecessors(node)):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier

    # Filter edges
    subgraph_edges = []
    for u, v, key, data in G.edges(keys=True, data=True):
        if u not in visited or v not in visited:
            continue
        if edge_type_filter and data.get("edge_type") not in edge_type_filter:
            continue
        if data.get("weight", 0) < min_weight:
            continue
        subgraph_edges.append({
            "source": u,
            "target": v,
            "edge_type": data.get("edge_type", "unknown"),
            "weight": data.get("weight", 1),
            "confidence": data.get("confidence"),
            "matched_value": data.get("matched_value"),
            "evidence_ids": data.get("evidence_ids", []),
        })

    # Collect nodes with attributes
    subgraph_nodes = []
    member_nodes = []
    for n in visited:
        node_data = G.nodes.get(n, {})
        node_type = node_data.get("node_type", "unknown")

        if node_type == "member":
            member_nodes.append(n)
        else:
            subgraph_nodes.append({
                "id": n,
                "node_type": node_type,
                **{k: v for k, v in node_data.items() if k != "node_type"},
            })

    # Cohort aggregation for members
    cohorts = []
    if len(member_nodes) > max_member_nodes:
        # Group members by which providers they connect
        member_provider_map: Dict[str, Set[str]] = {}
        for m in member_nodes:
            connected_providers = set()
            for neighbor in set(G.successors(m)) | set(G.predecessors(m)):
                nd = G.nodes.get(neighbor, {})
                if nd.get("node_type") == "provider":
                    connected_providers.add(neighbor)
            key = frozenset(connected_providers)
            member_provider_map.setdefault(str(key), {
                "providers": sorted(connected_providers),
                "count": 0,
                "member_ids": [],
            })
            member_provider_map[str(key)]["count"] += 1
            member_provider_map[str(key)]["member_ids"].append(m)

        for cohort_data in member_provider_map.values():
            cohorts.append({
                "cohort_type": "shared_members",
                "providers": cohort_data["providers"],
                "member_count": cohort_data["count"],
                "sample_member_ids": cohort_data["member_ids"][:3],
            })
    else:
        # Include individual member nodes
        for m in member_nodes:
            subgraph_nodes.append({
                "id": m,
                "node_type": "member",
            })

    return {
        "focal_entity": entity_id,
        "nodes": subgraph_nodes,
        "edges": subgraph_edges,
        "cohorts": cohorts,
        "summary": {
            "n_nodes": len(subgraph_nodes),
            "n_edges": len(subgraph_edges),
            "n_cohorts": len(cohorts),
            "total_members": len(member_nodes),
        },
    }


def get_subgraph_by_community(
    G: nx.MultiDiGraph,
    community: Dict,
) -> Dict:
    """
    Extract a subgraph for an entire community.

    Args:
        G: Full graph
        community: Community dict from detect_communities()

    Returns:
        Subgraph dict
    """
    provider_ids = community.get("provider_ids", [])
    if not provider_ids:
        return {"nodes": [], "edges": [], "cohorts": [], "summary": {}}

    hub = community.get("hub_provider_id", provider_ids[0])
    return get_case_subgraph(G, hub, max_depth=1)
