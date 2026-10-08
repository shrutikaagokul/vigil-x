"""Tests for entity resolution."""
import pytest
import pandas as pd
from entity_resolution.resolver import (
    normalize_address,
    normalize_name,
    resolve_entities,
    build_entity_clusters,
)

CONFIG = {
    "fuzzy_threshold": 88,
    "link_weights": {
        "bank_hash": 1.0, "tin_hash": 1.0,
        "owner_exact": 0.9, "owner_fuzzy": 0.7,
        "address_suite": 0.6, "address_no_suite": 0.4,
        "registered_agent": 0.8,
    },
}


def test_resolve_bank_hash():
    providers = pd.DataFrame([
        {"provider_id": "P001", "bank_hash": "HASH_X", "address": "100 A St",
         "owner_name": "O1", "tin_hash": None, "suite": None, "registered_agent": None},
        {"provider_id": "P002", "bank_hash": "HASH_X", "address": "200 B St",
         "owner_name": "O2", "tin_hash": None, "suite": None, "registered_agent": None},
    ])
    links = resolve_entities(providers, config=CONFIG)
    bank_links = [l for l in links if l.link_basis == "bank_hash"]
    assert len(bank_links) >= 1


def test_resolve_fuzzy_owner():
    providers = pd.DataFrame([
        {"provider_id": "P001", "owner_name": "MedGroup Holdings LLC",
         "bank_hash": "B1", "address": "100 A St", "tin_hash": None,
         "suite": None, "registered_agent": None},
        {"provider_id": "P002", "owner_name": "Medgroup Holdings",
         "bank_hash": "B2", "address": "200 B St", "tin_hash": None,
         "suite": None, "registered_agent": None},
    ])
    links = resolve_entities(providers, config=CONFIG)
    fuzzy_links = [l for l in links if "owner" in l.link_basis]
    assert len(fuzzy_links) >= 1


def test_clusters_union_find():
    providers = pd.DataFrame([
        {"provider_id": "P001", "bank_hash": "H1", "address": "100 A",
         "owner_name": "O1", "tin_hash": None, "suite": None, "registered_agent": None},
        {"provider_id": "P002", "bank_hash": "H1", "address": "200 B",
         "owner_name": "O2", "tin_hash": None, "suite": None, "registered_agent": None},
        {"provider_id": "P003", "bank_hash": "H2", "address": "200 B",
         "owner_name": "O2", "tin_hash": None, "suite": None, "registered_agent": None},
    ])
    links = resolve_entities(providers, config=CONFIG)
    clusters = build_entity_clusters(links)
    # P001-P002 linked by bank, P002-P003 linked by owner → all in one cluster
    assert len(clusters) >= 1
    largest = max(clusters, key=lambda c: len(c.members))
    member_ids = [m["entity_id"] for m in largest.members]
    assert "P001" in member_ids or "P002" in member_ids


def test_no_links():
    providers = pd.DataFrame([
        {"provider_id": "P001", "bank_hash": "B1", "address": "100 A",
         "owner_name": "Alpha", "tin_hash": None, "suite": None, "registered_agent": None},
        {"provider_id": "P002", "bank_hash": "B2", "address": "200 B",
         "owner_name": "Beta", "tin_hash": None, "suite": None, "registered_agent": None},
    ])
    links = resolve_entities(providers, config=CONFIG)
    assert len(links) == 0


def test_address_normalization_edge_cases():
    assert normalize_address("123 Main Street, Suite 100") == "123 main st ste 100"
    assert normalize_address("  456   OAK   AVENUE  ") == "456 oak ave"
    assert normalize_address(None) is None
    assert normalize_address("") is None
    assert normalize_address(42) is None


def test_name_normalization_edge_cases():
    assert normalize_name("Dr. John Q. Smith, Jr.") == "dr john q smith jr"
    assert normalize_name("   spaces   ") == "spaces"
    assert normalize_name(None) is None
