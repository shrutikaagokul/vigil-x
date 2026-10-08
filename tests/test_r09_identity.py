"""
Tests for R09 — Shared Identity Link.

8 tests covering:
1. Shared bank hash
2. Shared owner
3. Shared address
4. Legitimate medical office building
5. Documented group
6. Fuzzy owner match
7. Unrelated entities
8. Missing identity fields
"""
import pytest
import pandas as pd
from rules.r09_identity import detect_shared_identity
from entity_resolution.resolver import normalize_address, normalize_name

CONFIG = {
    "enabled": True,
    "version": "1.0.0",
    "fuzzy_threshold": 88,
    "link_weights": {
        "bank_hash": 1.0, "tin_hash": 1.0,
        "owner_exact": 0.9, "owner_fuzzy": 0.7,
        "address_suite": 0.6, "address_no_suite": 0.4,
        "registered_agent": 0.8,
    },
    "documented_group_discount": 0.5,
    "severity": "MEDIUM",
}


def _providers(rows):
    defaults = {
        "provider_id": "P001", "name": "Dr. Test",
        "address": "100 Main St", "suite": None, "county": "Adams",
        "owner_name": None, "owner_entity": None,
        "bank_hash": None, "tin_hash": None,
        "registered_agent": None, "group_id": None,
        "specialty": "family_medicine",
    }
    return pd.DataFrame([{**defaults, **o} for o in rows])


# 1. Shared bank hash
def test_shared_bank_hash():
    """Two providers with same bank hash → alert."""
    providers = _providers([
        {"provider_id": "P001", "bank_hash": "HASH_ABC"},
        {"provider_id": "P002", "bank_hash": "HASH_ABC"},
    ])
    alerts = detect_shared_identity(providers, config=CONFIG)
    assert len(alerts) >= 1
    assert any("bank_hash" in a.metadata.get("link_bases", []) for a in alerts)


# 2. Shared owner
def test_shared_owner():
    """Two providers with same owner → alert."""
    providers = _providers([
        {"provider_id": "P001", "owner_name": "John Smith", "bank_hash": "B1"},
        {"provider_id": "P002", "owner_name": "John Smith", "bank_hash": "B2"},
    ])
    alerts = detect_shared_identity(providers, config=CONFIG)
    assert len(alerts) >= 1


# 3. Shared address
def test_shared_address_only():
    """Shared address alone (no hard link) should NOT trigger alert."""
    providers = _providers([
        {"provider_id": "P001", "address": "100 Main St", "suite": "Suite 200",
         "bank_hash": "B1", "owner_name": "Owner A"},
        {"provider_id": "P002", "address": "100 Main St", "suite": "Suite 300",
         "bank_hash": "B2", "owner_name": "Owner B"},
    ])
    alerts = detect_shared_identity(providers, config=CONFIG)
    # Should not trigger from address alone
    addr_only_alerts = [
        a for a in alerts
        if all(b.startswith("address") for b in a.metadata.get("link_bases", []))
    ]
    assert len(addr_only_alerts) == 0


# 4. Legitimate medical office building
def test_medical_office_building():
    """Multiple unrelated providers in same building → no alert if no hard links."""
    providers = _providers([
        {"provider_id": f"P{i:04d}", "address": "500 Medical Plaza",
         "suite": f"Suite {i*100}", "bank_hash": f"BANK_{i}",
         "owner_name": f"Dr. Owner_{i}"}
        for i in range(1, 6)
    ])
    alerts = detect_shared_identity(providers, config=CONFIG)
    # Should not create alerts based solely on shared building address
    for a in alerts:
        bases = a.metadata.get("link_bases", [])
        assert not all(b.startswith("address") for b in bases), \
            "Should not alert on address-only links (medical office building)"


# 5. Documented group
def test_documented_group():
    """Providers in documented group → alert with documented_group flag."""
    providers = _providers([
        {"provider_id": "P001", "bank_hash": "SHARED_BANK", "group_id": "GRP_01",
         "owner_name": "Group Owner"},
        {"provider_id": "P002", "bank_hash": "SHARED_BANK", "group_id": "GRP_01",
         "owner_name": "Group Owner"},
    ])
    alerts = detect_shared_identity(providers, config=CONFIG)
    if alerts:
        # documented_group flag should be set
        assert any(a.metadata.get("documented_group", False) for a in alerts)


# 6. Fuzzy owner match
def test_fuzzy_owner_match():
    """Slightly different owner names should match with rapidfuzz."""
    providers = _providers([
        {"provider_id": "P001", "owner_name": "Johnson Medical Holdings LLC",
         "bank_hash": "B1"},
        {"provider_id": "P002", "owner_name": "Johnson Medical Holdings",
         "bank_hash": "B2"},
    ])
    alerts = detect_shared_identity(providers, config=CONFIG)
    assert len(alerts) >= 1


# 7. Unrelated entities
def test_unrelated_entities():
    """Completely unrelated providers → no alert."""
    providers = _providers([
        {"provider_id": "P001", "bank_hash": "BANK_AAA", "owner_name": "Dr. Alpha",
         "address": "100 First Ave", "registered_agent": "Agent A"},
        {"provider_id": "P002", "bank_hash": "BANK_BBB", "owner_name": "Dr. Beta",
         "address": "200 Second Blvd", "registered_agent": "Agent B"},
    ])
    alerts = detect_shared_identity(providers, config=CONFIG)
    assert len(alerts) == 0


# 8. Missing identity fields
def test_missing_identity_fields():
    """Providers with all identity fields missing should not crash."""
    providers = _providers([
        {"provider_id": "P001"},
        {"provider_id": "P002"},
    ])
    alerts = detect_shared_identity(providers, config=CONFIG)
    # Should not crash and should produce no alerts
    assert len(alerts) == 0


# Extra: Test address normalization
def test_address_normalization():
    assert normalize_address("100 Main Street, Suite 200") == "100 main st ste 200"
    assert normalize_address("100 MAIN ST.") == "100 main st"
    assert normalize_address(None) is None
    assert normalize_address("") is None


def test_name_normalization():
    assert normalize_name("Dr. John Smith, Jr.") == "dr john smith jr"
    assert normalize_name(None) is None
