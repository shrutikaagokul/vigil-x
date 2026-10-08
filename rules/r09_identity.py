"""
R09 — Shared Identity Link

Detects unrelated providers sharing suspicious identity attributes:
- bank hash / TIN hash
- address + suite
- owner / ownership entity (fuzzy matching)
- registered agent

Uses entity resolution to build explainable clusters.
A shared address alone is NOT automatically suspicious.
Documented groups are noted for downstream discounting.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from contracts.alert import Alert, Evidence, Severity
from config.loader import get_rule_config
from entity_resolution.resolver import (
    resolve_entities,
    build_entity_clusters,
    EntityCluster,
    IdentityLink,
)

RULE_ID = "R09"

# Link bases considered "hard" identity signals
_HARD_LINK_BASES = {"bank_hash", "tin_hash", "owner_exact", "registered_agent"}


def detect_shared_identity(
    providers: pd.DataFrame,
    config: Optional[Dict] = None,
) -> List[Alert]:
    """
    Run R09: detect shared identity links and produce alerts.

    Args:
        providers: Providers DataFrame with identity columns
        config: R09 config dict

    Returns:
        List[Alert] — one alert per suspicious cluster
    """
    if config is None:
        config = get_rule_config("R09")

    if not config.get("enabled", True):
        return []

    version = config.get("version", "1.0.0")
    severity = config.get("severity", Severity.MEDIUM.value)
    group_discount = config.get("documented_group_discount", 0.5)

    # Step 1: Resolve entity links
    links = resolve_entities(providers, config)
    if not links:
        return []

    # Step 2: Build clusters
    clusters = build_entity_clusters(links, providers)

    # Step 3: Generate alerts per cluster
    alerts = []

    for cluster in clusters:
        if len(cluster.members) < 2:
            continue

        member_ids = [m["entity_id"] for m in cluster.members]
        link_bases = cluster.basis_summary
        has_hard_link = any(b in _HARD_LINK_BASES for b in link_bases)

        # Address-only links without hard identity are low suspicion
        if not has_hard_link and all(b.startswith("address") for b in link_bases):
            continue  # A shared address alone is not automatically suspicious

        # Build evidence from links
        evidence_list = []
        for link in cluster.links:
            ev = Evidence(
                evidence_id=Evidence.generate_id(RULE_ID),
                rule_id=RULE_ID,
                rule_version=version,
                claim_ids=[],
                fields_matched=[link.link_basis, "source_id", "target_id", "matched_value"],
                plain_text=(
                    f"Providers {link.source_id} and {link.target_id} share "
                    f"{link.link_basis}: '{link.matched_value}' "
                    f"(confidence: {link.confidence:.2f})."
                ),
                est_overpay=0,
                severity=severity,
                fp_notes=(
                    "Shared identity may be legitimate (billing company, medical office building, "
                    "documented group practice). Review organizational relationships."
                ),
            )
            evidence_list.append(ev)

        # Documented group note
        fp_note = None
        if cluster.documented_group:
            fp_note = (
                "These providers appear to belong to a documented group practice. "
                "Identity sharing may be expected."
            )

        # Compose alert
        alerts.append(Alert(
            alert_id=Alert.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            entity_type="provider",
            entity_id=member_ids[0],  # hub/first provider
            claim_ids=[],
            severity=severity,
            est_dollars=0,
            evidence=evidence_list,
            fp_notes=fp_note,
            metadata={
                "cluster_id": cluster.cluster_id,
                "cluster_members": member_ids,
                "link_bases": link_bases,
                "cluster_confidence": round(cluster.confidence, 3),
                "documented_group": cluster.documented_group,
                "n_providers": len(member_ids),
            },
        ))

    return alerts


def get_entity_clusters(
    providers: pd.DataFrame,
    config: Optional[Dict] = None,
) -> List[EntityCluster]:
    """
    Public interface: return entity clusters without generating alerts.
    Useful for graph construction and downstream network analysis.
    """
    if config is None:
        config = get_rule_config("R09")

    links = resolve_entities(providers, config)
    return build_entity_clusters(links, providers)
