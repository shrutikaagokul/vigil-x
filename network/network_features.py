"""
Network-level risk features for Vigil-X.

Computes structured network signals that feed into Member 1's downstream
risk engine. Does NOT compute the final unified Vigil-X risk score.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

import networkx as nx
import pandas as pd


def compute_provider_network_features(
    P: nx.Graph,
    G: Optional[nx.MultiDiGraph] = None,
    communities: Optional[List[Dict]] = None,
    claims: Optional[pd.DataFrame] = None,
    alerts: Optional[List] = None,
) -> pd.DataFrame:
    """
    Compute provider-level network features for Member 1's risk engine.

    Returns a DataFrame with one row per provider in P.
    """
    if P.number_of_nodes() == 0:
        return pd.DataFrame()

    # Map provider -> community info
    comm_map: Dict[str, Dict] = {}
    if communities:
        for c in communities:
            cid = c.get("community_id", -1)
            csize = c.get("n_providers", len(c.get("provider_ids", [])))
            for pid in c.get("provider_ids", []):
                comm_map[pid] = {
                    "community_id": cid,
                    "community_size": csize,
                    "hard_link_count": c.get("hard_link_count", 0),
                    "referral_link_count": c.get("referral_link_count", 0),
                }

    # Map of suspicious providers based on alerts
    suspicious_pids: Set[str] = set()
    if alerts:
        for a in alerts:
            eid = getattr(a, "entity_id", None)
            if eid:
                suspicious_pids.add(eid)

    # Provider financial exposure lookup
    prov_exposure: Dict[str, float] = {}
    prov_claims_count: Dict[str, int] = {}
    if claims is not None and not claims.empty and "provider_id" in claims.columns:
        grp = claims.groupby("provider_id").agg(
            total_paid=("paid_amount", "sum"),
            claim_count=("claim_id", "count"),
        )
        prov_exposure = grp["total_paid"].to_dict()
        prov_claims_count = grp["claim_count"].to_dict()

    # Compute graph centralities
    betweenness = {}
    if P.number_of_nodes() > 1:
        try:
            betweenness = nx.betweenness_centrality(P, weight="weight")
        except Exception:
            betweenness = {}

    records = []
    for pid in P.nodes():
        node_data = P.nodes[pid]
        if node_data.get("node_type") and node_data.get("node_type") != "provider":
            continue

        cinfo = comm_map.get(pid, {"community_id": -1, "community_size": 1, "hard_link_count": 0, "referral_link_count": 0})
        comm_id = cinfo["community_id"]
        comm_size = cinfo["community_size"]

        # Degrees in projection P
        deg = P.degree(pid)
        w_deg = P.degree(pid, weight="weight")

        # Neighbors Analysis
        neighbors = list(P.neighbors(pid))
        susp_neighbors = [n for n in neighbors if n in suspicious_pids]
        susp_neighbor_count = len(susp_neighbors)
        susp_neighbor_ratio = round(susp_neighbor_count / max(len(neighbors), 1), 4)

        # Relationship counts breakdown from edge metadata in P
        shared_identity_count = 0
        shared_ownership_count = 0
        shared_address_count = 0
        referral_connection_count = 0
        facility_connection_count = 0

        for nbr in neighbors:
            edata = P.get_edge_data(pid, nbr) or {}
            etypes = edata.get("edge_types", {})

            shared_identity_count += int(
                etypes.get("shared_bank_hash", 0) + etypes.get("shared_tin_hash", 0) + etypes.get("shared_registered_agent", 0)
            )
            shared_ownership_count += int(
                etypes.get("shared_owner_exact", 0) + etypes.get("shared_owner_fuzzy", 0) + etypes.get("shared_ownership", 0)
            )
            shared_address_count += int(
                etypes.get("shared_address_suite", 0) + etypes.get("shared_address_no_suite", 0) + etypes.get("shared_address", 0)
            )
            referral_connection_count += int(etypes.get("refers_to", 0))
            facility_connection_count += int(etypes.get("works_at", 0) + etypes.get("shared_facility", 0))

        # Total relationships in MultiDiGraph G
        network_relationship_count = 0
        if G is not None and pid in G:
            network_relationship_count = G.degree(pid)

        # Density of provider's community subgraph
        density = 0.0
        if comm_size > 1 and communities:
            comm_members = [c["provider_ids"] for c in communities if c.get("community_id") == comm_id]
            if comm_members:
                sub = P.subgraph(comm_members[0])
                density = round(nx.density(sub), 4)

        # Financial exposure
        exposure = float(prov_exposure.get(pid, 0.0))

        records.append({
            "provider_id": pid,
            "community_id": comm_id,
            "community_size": comm_size,
            "network_degree": deg,
            "weighted_degree": round(w_deg, 2),
            "network_density": density,
            "suspicious_neighbor_count": susp_neighbor_count,
            "suspicious_neighbor_ratio": susp_neighbor_ratio,
            "shared_identity_count": shared_identity_count,
            "shared_ownership_count": shared_ownership_count,
            "shared_address_count": shared_address_count,
            "referral_connection_count": referral_connection_count,
            "facility_connection_count": facility_connection_count,
            "network_exposure": round(exposure, 2),
            "network_relationship_count": network_relationship_count,
            "referral_centrality": round(betweenness.get(pid, 0.0), 4),
            "ownership_centrality": round(min(shared_ownership_count / max(deg, 1), 1.0), 4),
            "community_risk_score": round(min((shared_identity_count * 0.4 + susp_neighbor_count * 0.3 + referral_connection_count * 0.3) / 5.0, 1.0), 4),
        })

    return pd.DataFrame(records)


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
        ownership_count = edge_types.get("shared_owner_exact", 0) + edge_types.get("shared_owner_fuzzy", 0) + edge_types.get("shared_ownership", 0)
        ownership_score = min(ownership_count / max(n_providers, 1), 1.0)

        # --- Financial exposure ---
        comm_claims = claims[claims["provider_id"].isin(prov_set)] if not claims.empty and "provider_id" in claims.columns else pd.DataFrame()
        total_exposure = float(comm_claims["paid_amount"].sum()) if not comm_claims.empty else 0.0
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
        documented = comm.get("documented_group", False)

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
            "investigation_category": comm.get("investigation_category", "connected provider cluster"),
            "network_feature_version": "1.0.0",
        })

    return pd.DataFrame(records)
