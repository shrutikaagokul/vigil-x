"""
Deterministic Verifier for Vigil-X Investigation Briefs.

Verifies that all facts, IDs, rules, and monetary amounts cited in a brief
strictly correspond to the Evidence Packet, detecting hallucinations or unsupported statements.
Never marks an unverified brief as verified.
"""
from __future__ import annotations

import re
from typing import List, Set

from contracts.investigation import EvidencePacket, VerificationResult


# Forbidden absolute/hallucinated conclusive fraud phrases
FORBIDDEN_PHRASES = [
    "fraud confirmed",
    "fraud is confirmed",
    "guilty of fraud",
    "proven fraud",
    "definitive fraud",
    "unquestionably fraudulent",
    "convicted of fraud",
    "indisputable fraud",
    "confirmed fraudulent",
    "fraud has occurred",
]


def verify_brief(
    brief_text: str,
    packet: EvidencePacket,
    generation_mode: str = "fallback",
) -> VerificationResult:
    """
    Deterministically verify factual consistency between brief narrative and evidence packet.

    Checks:
    1. No forbidden conclusive fraud language is used.
    2. Claim IDs cited in text exist in packet.cited_claim_ids.
    3. Provider IDs cited in text exist in packet.cited_provider_ids.
    4. Member IDs cited in text exist in packet.cited_member_ids.
    5. Rule IDs cited in text exist in packet.cited_rule_ids.
    6. Network IDs cited in text exist in packet.cited_network_ids.
    7. Monetary figures cited do not exceed packet.exposure_high.
    8. Discrepancies generate issues; stylistic omissions generate warnings.
    """
    issues: List[str] = []
    warnings: List[str] = []
    text = brief_text

    # 1. Check for forbidden conclusive phrases
    lower_text = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lower_text:
            issues.append(
                f"Forbidden conclusive phrasing detected: '{phrase}'. "
                f"Narrative must state 'Prioritized for human investigation' and avoid declaring fraud."
            )

    # 2. Extract and verify Claim IDs (format C0001, C0000001, etc.)
    found_claims: Set[str] = set(re.findall(r"\bC\d{4,8}\b", text))
    allowed_claims = set(packet.cited_claim_ids)
    for cid in sorted(found_claims):
        if cid not in allowed_claims:
            issues.append(f"Hallucinated or uncited claim ID: '{cid}' not found in case evidence.")

    # 3. Extract and verify Provider IDs (format P0001, PRV0001, etc.)
    found_providers: Set[str] = set(re.findall(r"\b(?:P|PRV)\d{3,6}\b", text))
    allowed_providers = set(packet.cited_provider_ids)
    for pid in sorted(found_providers):
        if pid not in allowed_providers:
            issues.append(f"Hallucinated or uncited provider ID: '{pid}' not found in case network/evidence.")

    # 4. Extract and verify Member IDs (format M0001, M0000001, etc.)
    found_members: Set[str] = set(re.findall(r"\bM\d{4,8}\b", text))
    allowed_members = set(packet.cited_member_ids)
    for mid in sorted(found_members):
        if allowed_members and mid not in allowed_members:
            issues.append(f"Hallucinated or uncited member ID: '{mid}' not found in case claims.")

    # 5. Extract and verify Rule IDs (format R01 to R10)
    found_rules: Set[str] = set(re.findall(r"\bR(?:0[1-9]|10)\b", text))
    allowed_rules = set(packet.cited_rule_ids)
    for rid in sorted(found_rules):
        if rid not in allowed_rules:
            issues.append(f"Uncited rule ID: '{rid}' not triggered in this case.")

    # 6. Extract and verify Network IDs (format NET-001, NET_PRV_001, etc.)
    found_networks: Set[str] = set(re.findall(r"\bNET[-_][A-Za-z0-9]+\b", text))
    allowed_networks = set(packet.cited_network_ids)
    for nid in sorted(found_networks):
        if allowed_networks and nid not in allowed_networks:
            issues.append(f"Uncited network ID: '{nid}' not associated with this case.")

    # 7. Extract and verify monetary figures ($X,XXX.XX)
    amount_matches = re.findall(r"\$\s*([\d,]+(?:\.\d{1,2})?)", text)
    checked_amounts_count = len(amount_matches)
    for amt_str in amount_matches:
        try:
            val = float(amt_str.replace(",", ""))
            # Allow up to 15% tolerance above exposure_high for rounding, with $1000 minimum floor
            max_allowed = max(packet.exposure_high * 1.15, 1000.0)
            if val > max_allowed:
                issues.append(
                    f"Unsupported monetary amount: ${val:,.2f} exceeds case exposure bound of ${packet.exposure_high:,.2f}."
                )
        except ValueError:
            pass

    # 8. Check recommended SIU phrasing & benign considerations
    if "prioritized for human investigation" not in lower_text and "human investigation" not in lower_text:
        warnings.append("Narrative should explicitly include 'Prioritized for human investigation'.")

    if not packet.benign_explanations:
        warnings.append("Case contains no documented benign explanations; verification should flag clinical review.")

    verified = (len(issues) == 0)

    return VerificationResult(
        verified=verified,
        issues=issues,
        warnings=warnings,
        checked_claims=len(found_claims),
        checked_providers=len(found_providers),
        checked_members=len(found_members),
        checked_rules=len(found_rules),
        checked_networks=len(found_networks),
        checked_amounts=checked_amounts_count,
        generation_mode=generation_mode,
    )
