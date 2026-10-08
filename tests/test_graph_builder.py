"""Tests for graph builder and community detection."""
import pytest
import pandas as pd
import networkx as nx
from network.graph_builder import build_graph, get_graph_summary
from network.provider_projection import build_provider_projection
from network.community import detect_communities, enrich_communities_with_claims
from network.subgraph import get_case_subgraph, get_community_subgraph
from network.network_features import compute_network_features, compute_provider_network_features
from entity_resolution.resolver import IdentityLink


def _make_data():
    providers = pd.DataFrame([
        {"provider_id": "P001", "name": "Dr. A", "specialty": "family_medicine",
         "county": "Adams", "owner_name": "Owner A", "bank_hash": "BH001", "address": "100 Main St"},
        {"provider_id": "P002", "name": "Dr. B", "specialty": "cardiology",
         "county": "Baker", "owner_name": "Owner B", "bank_hash": "BH002", "address": "200 Oak Ave"},
        {"provider_id": "P003", "name": "Dr. C", "specialty": "laboratory",
         "county": "Adams", "owner_name": "Owner A", "bank_hash": "BH001", "address": "100 Main St"},
    ])
    claims = pd.DataFrame([
        {"claim_id": "C001", "member_id": "M001", "provider_id": "P001",
         "facility_id": "F001", "paid_amount": 100},
        {"claim_id": "C002", "member_id": "M001", "provider_id": "P002",
         "facility_id": "F001", "paid_amount": 200},
        {"claim_id": "C003", "member_id": "M002", "provider_id": "P001",
         "facility_id": None, "paid_amount": 150},
        {"claim_id": "C004", "member_id": "M002", "provider_id": "P003",
         "facility_id": None, "paid_amount": 300},
    ])
    referrals = pd.DataFrame([
        {"referral_id": "REF001", "referring_provider_id": "P001",
         "target_provider_id": "P002", "member_id": "M001",
         "referral_date": "2024-01-15", "claim_id": "C002"},
    ])
    facilities = pd.DataFrame([
        {"facility_id": "F001", "name": "Clinic A", "facility_type": "clinic"},
    ])
    return providers, claims, referrals, facilities


def test_build_graph():
    providers, claims, referrals, facilities = _make_data()
    G = build_graph(claims, providers, referrals, facilities)
    assert G.number_of_nodes() > 0
    assert G.number_of_edges() > 0
    # Should have provider nodes
    provider_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "provider"]
    assert len(provider_nodes) == 3


def test_graph_summary():
    providers, claims, referrals, facilities = _make_data()
    G = build_graph(claims, providers, referrals, facilities)
    summary = get_graph_summary(G)
    assert "n_nodes" in summary
    assert "edge_types" in summary


def test_identity_links_in_graph():
    providers, claims, referrals, facilities = _make_data()
    link = IdentityLink(
        source_type="provider", source_id="P001",
        target_type="provider", target_id="P003",
        link_basis="bank_hash", confidence=1.0,
        matched_value="HASH_XYZ", weight=1.0,
    )
    G = build_graph(claims, providers, referrals, facilities, identity_links=[link])
    # Check identity edge exists
    edges = [
        (u, v, d) for u, v, d in G.edges(data=True)
        if d.get("edge_type") == "shared_bank_hash"
    ]
    assert len(edges) >= 1


def test_provider_projection():
    providers, claims, referrals, facilities = _make_data()
    G = build_graph(claims, providers, referrals, facilities)
    P = build_provider_projection(G)
    assert isinstance(P, nx.Graph)
    assert P.number_of_nodes() == 3  # only providers


def test_community_detection():
    providers, claims, referrals, facilities = _make_data()
    link = IdentityLink(
        source_type="provider", source_id="P001",
        target_type="provider", target_id="P003",
        link_basis="bank_hash", confidence=1.0,
        matched_value="HASH_XYZ", weight=10.0,
    )
    G = build_graph(claims, providers, referrals, facilities, identity_links=[link])
    P = build_provider_projection(G)
    communities = detect_communities(P, min_size=2)
    assert len(communities) >= 1
    comm = communities[0]
    assert "provider_ids" in comm
    assert "hub_provider_id" in comm
    assert "investigation_category" in comm
    assert comm["investigation_category"] in [
        "high-risk network", "investigation candidate network", "connected provider cluster", "small provider cluster"
    ]


def test_provider_network_features():
    providers, claims, referrals, facilities = _make_data()
    G = build_graph(claims, providers, referrals, facilities)
    P = build_provider_projection(G)
    communities = detect_communities(P, min_size=1)
    df_feat = compute_provider_network_features(P, G, communities, claims)

    assert not df_feat.empty
    assert "provider_id" in df_feat.columns
    assert "community_id" in df_feat.columns
    assert "network_degree" in df_feat.columns
    assert "shared_ownership_count" in df_feat.columns
    assert "referral_connection_count" in df_feat.columns


def test_case_subgraph():
    providers, claims, referrals, facilities = _make_data()
    G = build_graph(claims, providers, referrals, facilities)
    subgraph = get_case_subgraph(G, "P001")
    assert subgraph["focal_entity"] == "P001"
    assert len(subgraph["nodes"]) > 0
    assert "investigation_story" in subgraph
    assert "P001" in subgraph["investigation_story"]


def test_community_subgraph_extraction():
    providers, claims, referrals, facilities = _make_data()
    G = build_graph(claims, providers, referrals, facilities)
    P = build_provider_projection(G)
    communities = detect_communities(P, min_size=1)
    subgraph = get_community_subgraph(G, communities[0]["community_id"], communities)
    assert len(subgraph["nodes"]) > 0
    assert "investigation_story" in subgraph


def test_subgraph_missing_entity():
    providers, claims, referrals, facilities = _make_data()
    G = build_graph(claims, providers, referrals, facilities)
    subgraph = get_case_subgraph(G, "NONEXISTENT")
    assert subgraph["nodes"] == []
    assert subgraph["edges"] == []
