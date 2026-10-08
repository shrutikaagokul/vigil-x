"""
Entity resolution for Vigil-X.

Resolves provider/facility/owner identity links using:
- Exact bank/TIN hash matching
- Normalized address + suite matching
- Fuzzy ownership name matching (rapidfuzz token_set_ratio)
- Shared registered agent

All matching is explainable — every link has a basis and confidence.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from difflib import SequenceMatcher

from config.loader import get_rule_config

# Common address suffix normalization map
_ADDR_SUFFIXES = {
    "street": "st", "st.": "st", "avenue": "ave", "ave.": "ave",
    "boulevard": "blvd", "blvd.": "blvd", "drive": "dr", "dr.": "dr",
    "lane": "ln", "ln.": "ln", "road": "rd", "rd.": "rd",
    "court": "ct", "ct.": "ct", "circle": "cir", "cir.": "cir",
    "place": "pl", "pl.": "pl", "suite": "ste", "ste.": "ste",
    "apartment": "apt", "apt.": "apt", "building": "bldg", "bldg.": "bldg",
    "floor": "fl", "fl.": "fl", "unit": "unit", "#": "unit",
}


@dataclass
class IdentityLink:
    """A single identity link between two entities."""
    source_type: str        # 'provider', 'facility'
    source_id: str
    target_type: str
    target_id: str
    link_basis: str         # 'bank_hash', 'owner_fuzzy', 'address_suite', etc.
    confidence: float
    matched_value: str      # what actually matched
    weight: float = 0.0


@dataclass
class EntityCluster:
    """A cluster of linked entities."""
    cluster_id: str
    members: List[Dict]     # [{entity_type, entity_id}]
    links: List[IdentityLink]
    basis_summary: List[str]
    confidence: float
    documented_group: bool = False

    def to_dict(self):
        return asdict(self)


def normalize_address(address: Optional[str]) -> Optional[str]:
    """
    Normalize an address string for matching.

    - lowercase
    - strip punctuation (except unit markers)
    - normalize common suffixes
    - collapse whitespace
    """
    if not address or not isinstance(address, str) or address.strip() == "":
        return None

    addr = address.lower().strip()
    # Remove periods not part of abbreviations
    addr = re.sub(r'\.(?!\d)', '', addr)
    # Normalize commas
    addr = addr.replace(",", " ")
    # Normalize suffixes
    words = addr.split()
    normalized = []
    for w in words:
        normalized.append(_ADDR_SUFFIXES.get(w, w))
    addr = " ".join(normalized)
    # Collapse whitespace
    addr = re.sub(r'\s+', ' ', addr).strip()
    return addr


def normalize_name(name: Optional[str]) -> Optional[str]:
    """
    Normalize a person/organization name for matching.

    - lowercase
    - remove punctuation
    - collapse whitespace
    """
    if not name or not isinstance(name, str) or name.strip() == "":
        return None

    n = name.lower().strip()
    n = re.sub(r'[^\w\s]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def _find_exact_links(
    providers: pd.DataFrame,
    field: str,
    link_basis: str,
    weight: float,
) -> List[IdentityLink]:
    """Find exact-match links on a given field (e.g., bank_hash)."""
    links = []
    df = providers.dropna(subset=[field])
    if df.empty:
        return links

    # Filter out empty strings
    df = df[df[field].astype(str).str.strip() != ""]

    grouped = df.groupby(field)["provider_id"].apply(list).to_dict()
    for val, pids in grouped.items():
        if len(pids) < 2:
            continue
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                links.append(IdentityLink(
                    source_type="provider",
                    source_id=pids[i],
                    target_type="provider",
                    target_id=pids[j],
                    link_basis=link_basis,
                    confidence=1.0,
                    matched_value=str(val),
                    weight=weight,
                ))
    return links


def _find_address_links(
    providers: pd.DataFrame,
    link_weights: Dict[str, float],
) -> List[IdentityLink]:
    """Find address-based links (with and without suite)."""
    links = []
    df = providers.copy()
    df["_norm_addr"] = df["address"].apply(normalize_address)
    df["_norm_suite"] = df.get("suite", pd.Series(dtype=str)).apply(
        lambda x: normalize_address(x) if pd.notna(x) else None
    )

    # Full address + suite match
    with_suite = df.dropna(subset=["_norm_addr", "_norm_suite"]).copy()
    if not with_suite.empty:
        with_suite["_addr_key"] = with_suite["_norm_addr"] + "|" + with_suite["_norm_suite"]
        grouped = with_suite.groupby("_addr_key")["provider_id"].apply(list).to_dict()
        for val, pids in grouped.items():
            if len(pids) < 2:
                continue
            for i in range(len(pids)):
                for j in range(i + 1, len(pids)):
                    links.append(IdentityLink(
                        source_type="provider", source_id=pids[i],
                        target_type="provider", target_id=pids[j],
                        link_basis="address_suite",
                        confidence=0.9,
                        matched_value=val,
                        weight=link_weights.get("address_suite", 0.6),
                    ))

    # Address-only match (no suite or suite differs)
    addr_only = df.dropna(subset=["_norm_addr"])
    if not addr_only.empty:
        grouped = addr_only.groupby("_norm_addr")["provider_id"].apply(list).to_dict()
        for val, pids in grouped.items():
            if len(pids) < 2:
                continue
            # Check if these are already linked by suite
            suite_linked = set()
            for link in links:
                if link.link_basis == "address_suite":
                    suite_linked.add((link.source_id, link.target_id))
                    suite_linked.add((link.target_id, link.source_id))

            for i in range(len(pids)):
                for j in range(i + 1, len(pids)):
                    if (pids[i], pids[j]) not in suite_linked:
                        links.append(IdentityLink(
                            source_type="provider", source_id=pids[i],
                            target_type="provider", target_id=pids[j],
                            link_basis="address_no_suite",
                            confidence=0.6,
                            matched_value=val,
                            weight=link_weights.get("address_no_suite", 0.4),
                        ))
    return links


def _find_fuzzy_owner_links(
    providers: pd.DataFrame,
    threshold: int = 88,
    weight: float = 0.7,
) -> List[IdentityLink]:
    """Find fuzzy owner-name links using rapidfuzz token_set_ratio."""
    links = []
    df = providers.dropna(subset=["owner_name"]).copy()
    df["_norm_owner"] = df["owner_name"].apply(normalize_name)
    df = df.dropna(subset=["_norm_owner"])
    df = df[df["_norm_owner"] != ""]

    if len(df) < 2:
        return links

    pids = df["provider_id"].values
    owners = df["_norm_owner"].values

    for i in range(len(pids)):
        for j in range(i + 1, len(pids)):
            if owners[i] == owners[j]:
                # Exact match after normalization
                links.append(IdentityLink(
                    source_type="provider", source_id=pids[i],
                    target_type="provider", target_id=pids[j],
                    link_basis="owner_exact",
                    confidence=0.95,
                    matched_value=owners[i],
                    weight=weight + 0.2,
                ))
            else:
                score = SequenceMatcher(None, owners[i], owners[j]).ratio() * 100
                if score >= threshold:
                    links.append(IdentityLink(
                        source_type="provider", source_id=pids[i],
                        target_type="provider", target_id=pids[j],
                        link_basis="owner_fuzzy",
                        confidence=score / 100.0,
                        matched_value=f"{owners[i]} ~ {owners[j]} ({score}%)",
                        weight=weight,
                    ))
    return links


def _find_registered_agent_links(
    providers: pd.DataFrame,
    weight: float = 0.8,
) -> List[IdentityLink]:
    """Find shared registered agent links."""
    links = []
    df = providers.dropna(subset=["registered_agent"]).copy()
    df["_norm_agent"] = df["registered_agent"].apply(normalize_name)
    df = df.dropna(subset=["_norm_agent"])
    df = df[df["_norm_agent"] != ""]

    if len(df) < 2:
        return links

    grouped = df.groupby("_norm_agent")["provider_id"].apply(list).to_dict()
    for val, pids in grouped.items():
        if len(pids) < 2:
            continue
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                links.append(IdentityLink(
                    source_type="provider", source_id=pids[i],
                    target_type="provider", target_id=pids[j],
                    link_basis="registered_agent",
                    confidence=0.85,
                    matched_value=val,
                    weight=weight,
                ))
    return links


def resolve_entities(
    providers: pd.DataFrame,
    config: Optional[Dict] = None,
) -> List[IdentityLink]:
    """
    Run all entity resolution methods and return all identity links found.

    Args:
        providers: DataFrame with provider attributes
        config: R09 config dict (or loads from rules_config.yaml)

    Returns:
        List of IdentityLink objects
    """
    if config is None:
        config = get_rule_config("R09")

    link_weights = config.get("link_weights", {})
    fuzzy_threshold = config.get("fuzzy_threshold", 88)

    all_links: List[IdentityLink] = []

    # 1. Exact bank hash
    if "bank_hash" in providers.columns:
        all_links.extend(_find_exact_links(
            providers, "bank_hash", "bank_hash",
            link_weights.get("bank_hash", 1.0)))

    # 2. Exact TIN hash
    if "tin_hash" in providers.columns:
        all_links.extend(_find_exact_links(
            providers, "tin_hash", "tin_hash",
            link_weights.get("tin_hash", 1.0)))

    # 3. Address matching (suite-level and address-level)
    if "address" in providers.columns:
        all_links.extend(_find_address_links(providers, link_weights))

    # 4. Fuzzy owner matching
    if "owner_name" in providers.columns:
        all_links.extend(_find_fuzzy_owner_links(
            providers, fuzzy_threshold,
            link_weights.get("owner_fuzzy", 0.7)))

    # 5. Registered agent
    if "registered_agent" in providers.columns:
        all_links.extend(_find_registered_agent_links(
            providers, link_weights.get("registered_agent", 0.8)))

    return all_links


def build_entity_clusters(
    links: List[IdentityLink],
    providers: Optional[pd.DataFrame] = None,
) -> List[EntityCluster]:
    """
    Build entity clusters from identity links using union-find.

    Each cluster contains entities connected by at least one identity link.
    """
    if not links:
        return []

    # Union-Find
    parent: Dict[str, str] = {}

    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Build clusters
    for link in links:
        union(link.source_id, link.target_id)

    # Group by root
    clusters_map: Dict[str, List[str]] = {}
    all_ids = set()
    for link in links:
        all_ids.add(link.source_id)
        all_ids.add(link.target_id)

    for eid in all_ids:
        root = find(eid)
        clusters_map.setdefault(root, set()).add(eid)

    # Build EntityCluster objects
    clusters = []
    for root, members_set in clusters_map.items():
        member_list = sorted(members_set)
        cluster_links = [
            l for l in links
            if l.source_id in members_set or l.target_id in members_set
        ]
        basis = sorted(set(l.link_basis for l in cluster_links))
        max_conf = max(l.confidence for l in cluster_links) if cluster_links else 0.0

        # Check if this is a documented group
        documented = False
        if providers is not None and "group_id" in providers.columns:
            group_ids = providers[
                providers["provider_id"].isin(member_list)
            ]["group_id"].dropna().unique()
            if len(group_ids) == 1 and len(member_list) > 1:
                documented = True

        clusters.append(EntityCluster(
            cluster_id=f"EC-{uuid.uuid4().hex[:6]}",
            members=[{"entity_type": "provider", "entity_id": m} for m in member_list],
            links=cluster_links,
            basis_summary=basis,
            confidence=max_conf,
            documented_group=documented,
        ))

    return clusters
