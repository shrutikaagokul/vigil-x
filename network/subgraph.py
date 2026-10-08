"""
Case subgraph extraction for Vigil-X.

Provides investigation-friendly subgraphs centered on a focal entity or community.
Supports cohort aggregation to avoid graph hairballs and generates explainable
investigation story narratives for Member 3's UI and human SIU investigators.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

import networkx as nx


def generate_investigation_story(
    focal_entity: str,
    nodes: List[Dict],
    edges: List[Dict],
    community_info: Optional[Dict] = None,
) -> str:
    """
    Generate an investigation narrative explaining why the focal entity is connected.

    Example:
    Provider P102 is connected to 5 entities via 2 shared ownership relationships,
    1 referral relationship, 1 shared facility, and 1 shared address.
    """
    other_nodes = [n for n in nodes if n.get("id") != focal_entity]
    connected_provs = [n for n in other_nodes if n.get("node_type") == "provider"]
    facilities = [n for n in other_nodes if n.get("node_type") == "facility"]
    owners = [n for n in other_nodes if n.get("node_type") == "owner"]

    edge_type_counts: Dict[str, int] = {}
    for e in edges:
        et = e.get("edge_type", "unknown")
        edge_type_counts[et] = edge_type_counts.get(et, 0) + 1

    connection_phrases = []
    if edge_type_counts.get("shared_bank_hash", 0) > 0:
        connection_phrases.append(f"{edge_type_counts['shared_bank_hash']} shared bank account link(s)")
    if edge_type_counts.get("shared_tin_hash", 0) > 0:
        connection_phrases.append(f"{edge_type_counts['shared_tin_hash']} shared TIN hash link(s)")
    if (edge_type_counts.get("shared_owner_exact", 0) + edge_type_counts.get("shared_owner_fuzzy", 0) + edge_type_counts.get("shared_ownership", 0)) > 0:
        cnt = edge_type_counts.get("shared_owner_exact", 0) + edge_type_counts.get("shared_owner_fuzzy", 0) + edge_type_counts.get("shared_ownership", 0)
        connection_phrases.append(f"{cnt} shared ownership relationship(s)")
    if edge_type_counts.get("refers_to", 0) > 0:
        connection_phrases.append(f"{edge_type_counts['refers_to']} referral relationship(s)")
    if (edge_type_counts.get("works_at", 0) + edge_type_counts.get("shared_facility", 0)) > 0:
        cnt = edge_type_counts.get("works_at", 0) + edge_type_counts.get("shared_facility", 0)
        connection_phrases.append(f"{cnt} facility connection(s)")
    if (edge_type_counts.get("shared_address_suite", 0) + edge_type_counts.get("shared_address_no_suite", 0) + edge_type_counts.get("shared_address", 0)) > 0:
        cnt = edge_type_counts.get("shared_address_suite", 0) + edge_type_counts.get("shared_address_no_suite", 0) + edge_type_counts.get("shared_address", 0)
        connection_phrases.append(f"{cnt} shared address link(s)")

    desc = f"Provider {focal_entity} is connected to {len(connected_provs)} provider(s)"
    if facilities:
        desc += f" and {len(facilities)} facility(ies)"
    if connection_phrases:
        desc += " via " + ", ".join(connection_phrases) + "."
    else:
        desc += "."

    if community_info:
        cid = community_info.get("community_id")
        n_p = community_info.get("n_providers", len(connected_provs) + 1)
        cat = community_info.get("investigation_category", "investigation candidate network")
        desc += f" Provider belongs to Community C{cid:02d} ({n_p} providers), classified as a {cat}."

    return desc


def get_case_subgraph(
    G: nx.MultiDiGraph,
    entity_id: str,
    max_depth: int = 2,
    max_member_nodes: int = 5,
    edge_type_filter: Optional[Set[str]] = None,
    min_weight: float = 0.0,
    community_info: Optional[Dict] = None,
) -> Dict:
    """
    Extract a compact investigation subgraph around a focal entity.

    Supports:
    - Focal provider + directly connected providers
    - Relevant facilities, owners, bank nodes, address nodes
    - Cohort aggregation for shared members (avoids hairballs)
    - Filtering by edge type and weight
    - Explainable investigation story

    Args:
        G: Full Vigil-X graph
        entity_id: Focal entity ID (typically a provider)
        max_depth: Max BFS depth
        max_member_nodes: Max individual member nodes before aggregation
        edge_type_filter: Only include these edge types (None = all)
        min_weight: Minimum edge weight to include
        community_info: Optional community metadata dict

    Returns:
        Dict with nodes, edges, cohorts, summary, and investigation_story
    """
    if entity_id not in G:
        return {"focal_entity": entity_id, "nodes": [], "edges": [], "cohorts": [], "summary": {}, "investigation_story": "Entity not found in network."}

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

    # Narrative investigation story
    story = generate_investigation_story(entity_id, subgraph_nodes, subgraph_edges, community_info)

    return {
        "focal_entity": entity_id,
        "nodes": subgraph_nodes,
        "edges": subgraph_edges,
        "cohorts": cohorts,
        "investigation_story": story,
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
        return {"nodes": [], "edges": [], "cohorts": [], "summary": {}, "investigation_story": "Empty community."}

    hub = community.get("hub_provider_id", provider_ids[0])
    return get_case_subgraph(G, hub, max_depth=1, community_info=community)


def get_community_subgraph(
    G: nx.MultiDiGraph,
    community_id: int,
    communities: List[Dict],
) -> Dict:
    """
    Find community by ID and return its full subgraph.

    Args:
        G: Full multi-relational graph
        community_id: Target community ID
        communities: List of detected community dicts
    """
    match = [c for c in communities if c.get("community_id") == community_id]
    if not match:
        return {"nodes": [], "edges": [], "cohorts": [], "summary": {}, "investigation_story": f"Community {community_id} not found."}
    return get_subgraph_by_community(G, match[0])
