"""
Graph builder for Vigil-X.

Constructs a multi-relational graph from claims, referrals,
provider identity links, and facility relationships.

Every edge retains metadata explaining WHY it exists.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

import networkx as nx
import pandas as pd

from entity_resolution.resolver import IdentityLink


def build_graph(
    claims: pd.DataFrame,
    providers: pd.DataFrame,
    referrals: Optional[pd.DataFrame] = None,
    facilities: Optional[pd.DataFrame] = None,
    identity_links: Optional[List[IdentityLink]] = None,
    alerts: Optional[List] = None,
) -> nx.MultiDiGraph:
    """
    Build the Vigil-X investigation graph.

    Nodes: providers, members (aggregated), facilities, owners
    Edges: submits, has_claim, works_at, refers_to, shared_identity, etc.

    Returns a NetworkX MultiDiGraph with metadata on every edge.
    """
    G = nx.MultiDiGraph()

    # --- Provider nodes ---
    for _, p in providers.iterrows():
        pid = p["provider_id"]
        G.add_node(pid, node_type="provider",
                   specialty=p.get("specialty", ""),
                   name=p.get("name", ""),
                   county=p.get("county", ""))

    # --- Facility nodes and provider->facility edges ---
    if facilities is not None and not facilities.empty:
        for _, f in facilities.iterrows():
            fid = f["facility_id"]
            G.add_node(fid, node_type="facility",
                       name=f.get("name", ""),
                       facility_type=f.get("facility_type", ""))

        # Provider -> works_at -> Facility
        if "facility_id" in claims.columns:
            prov_fac = (
                claims.dropna(subset=["facility_id"])
                .groupby(["provider_id", "facility_id"])
                .agg(claim_count=("claim_id", "count"))
                .reset_index()
            )
            for _, row in prov_fac.iterrows():
                G.add_edge(row["provider_id"], row["facility_id"],
                           edge_type="works_at",
                           weight=row["claim_count"],
                           evidence_ids=[])

    # --- Owner nodes ---
    if "owner_name" in providers.columns:
        owners = providers.dropna(subset=["owner_name"])
        for _, p in owners.iterrows():
            owner_key = f"OWNER:{p['owner_name']}"
            if not G.has_node(owner_key):
                G.add_node(owner_key, node_type="owner", name=p["owner_name"])
            G.add_edge(p["provider_id"], owner_key,
                       edge_type="owned_by",
                       weight=1,
                       evidence_ids=[])

    # --- Referral edges ---
    if referrals is not None and not referrals.empty:
        ref_counts = (
            referrals.groupby(["referring_provider_id", "target_provider_id"])
            .agg(
                count=("referral_id", "count"),
                claim_ids=("claim_id", lambda x: list(x.dropna())),
            )
            .reset_index()
        )
        for _, row in ref_counts.iterrows():
            G.add_edge(
                row["referring_provider_id"], row["target_provider_id"],
                edge_type="refers_to",
                weight=row["count"],
                claim_ids=row["claim_ids"][:20],
                evidence_ids=[],
            )

    # --- Provider-member shared-member edges (aggregated) ---
    if not claims.empty:
        prov_mem = (
            claims.groupby(["provider_id", "member_id"])
            .agg(claim_count=("claim_id", "count"),
                 total_paid=("paid_amount", "sum"))
            .reset_index()
        )
        # Create provider-provider shared-member edges
        merged = prov_mem.merge(prov_mem, on="member_id", suffixes=("_a", "_b"))
        merged = merged[merged["provider_id_a"] < merged["provider_id_b"]]
        shared_members = (
            merged.groupby(["provider_id_a", "provider_id_b"])
            .agg(shared_member_count=("member_id", "nunique"))
            .reset_index()
        )
        for _, row in shared_members.iterrows():
            if row["shared_member_count"] >= 2:  # Threshold to avoid noise
                G.add_edge(
                    row["provider_id_a"], row["provider_id_b"],
                    edge_type="shared_members",
                    weight=row["shared_member_count"],
                    evidence_ids=[],
                )

    # --- Identity link edges ---
    if identity_links:
        for link in identity_links:
            G.add_edge(
                link.source_id, link.target_id,
                edge_type=f"shared_{link.link_basis}",
                weight=link.weight,
                confidence=link.confidence,
                matched_value=link.matched_value,
                evidence_ids=[],
            )

    return G


def get_graph_summary(G: nx.MultiDiGraph) -> Dict:
    """Get summary statistics for the graph."""
    edge_types = {}
    for u, v, data in G.edges(data=True):
        et = data.get("edge_type", "unknown")
        edge_types[et] = edge_types.get(et, 0) + 1

    node_types = {}
    for n, data in G.nodes(data=True):
        nt = data.get("node_type", "unknown")
        node_types[nt] = node_types.get(nt, 0) + 1

    return {
        "n_nodes": G.number_of_nodes(),
        "n_edges": G.number_of_edges(),
        "node_types": node_types,
        "edge_types": edge_types,
    }
