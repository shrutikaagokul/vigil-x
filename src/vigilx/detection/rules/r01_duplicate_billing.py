"""
R01 — Duplicate Billing Detection (Detection Layer).

Detects suspicious duplicate claims using multiple field combinations:
  A. Exact: same member/patient, provider, procedure, service date, amount
  B. Near:  same member/patient, provider, procedure, date ±1 day, same amount

Generates: duplicate count, affected claim IDs, duplicate amount,
           duplicate pattern, confidence/evidence strength.
"""

from typing import List, Dict, Any
from collections import defaultdict
from vigilx.detection.rules.base import BaseRule, DataContext, RuleResult


class R01DuplicateBilling(BaseRule):
    """R01: Duplicate Billing Detection."""

    rule_id = "R01"
    rule_name = "Duplicate Billing"

    def evaluate(self, context: DataContext) -> List[RuleResult]:
        if not self.enabled:
            return []

        results = []
        day_window = self.cfg.get("near_dup_day_window", 1)
        legit_mods = set(self.cfg.get("legitimate_modifiers", ["LT", "RT", "50", "76", "77"]))
        void_statuses = set(
            s.lower() for s in self.cfg.get("void_statuses", ["voided", "void", "reversed"])
        )
        corrected_statuses = set(
            s.lower() for s in self.cfg.get("corrected_statuses", ["corrected", "adjusted", "replacement"])
        )

        # Track claims by composite key for exact + near-duplicate detection
        seen_claims: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)

        for claim in context.claims:
            patient_id = claim.get("patient_id") or claim.get("member_id")
            dos = claim.get("date_of_service") or claim.get("service_date")
            procedure_code = claim.get("procedure_code") or claim.get("cpt_code")
            provider_id = claim.get("provider_id") or claim.get("billing_provider_id")
            claim_id = claim.get("claim_id")
            billed_amount = float(claim.get("billed_amount", 0.0) or 0.0)
            modifier = claim.get("modifier", "")
            status = str(claim.get("status", claim.get("claim_status", ""))).lower()

            if not all([patient_id, dos, procedure_code, provider_id, claim_id]):
                continue

            # Skip voided/corrected claims
            if status in void_statuses or status in corrected_statuses:
                continue

            # Skip legitimate modifiers (bilateral, repeat procedures)
            if modifier and set(str(modifier).split(",")) & legit_mods:
                continue

            key = (patient_id, procedure_code, provider_id)
            seen_claims[key].append({
                "claim_id": claim_id,
                "billed_amount": billed_amount,
                "date_of_service": dos,
                "provider_id": provider_id,
                "patient_id": patient_id,
                "procedure_code": procedure_code,
            })

        # Analyze groups for duplicates
        for key, claims_group in seen_claims.items():
            if len(claims_group) < 2:
                continue

            patient_id, procedure_code, provider_id = key

            # Sort by date for temporal analysis
            sorted_claims = sorted(claims_group, key=lambda c: str(c["date_of_service"]))

            # Exact duplicate detection (same date + same amount)
            date_amount_groups: Dict[tuple, List[dict]] = defaultdict(list)
            for c in sorted_claims:
                date_amount_groups[(str(c["date_of_service"]), c["billed_amount"])].append(c)

            for (dos, amount), group in date_amount_groups.items():
                if len(group) >= 2:
                    claim_ids = [c["claim_id"] for c in group]
                    dup_count = len(group)
                    dup_amount = amount * (dup_count - 1)  # excess amount

                    results.append(RuleResult(
                        triggered=True,
                        evidence_data={
                            "description": (
                                f"Exact duplicate billing detected: {dup_count} identical claims "
                                f"for procedure {procedure_code} on {dos} "
                                f"(member={patient_id}, provider={provider_id}). "
                                f"Each billed at ${amount:,.2f}."
                            ),
                            "what_happened": f"{dup_count} claims with identical fields submitted",
                            "why_suspicious": "Multiple identical claims for the same service suggest duplicate submission",
                            "baseline_used": "Exact field match: member + provider + procedure + date + amount",
                            "deviation": f"{dup_count - 1} excess claim(s)",
                            "false_positive_notes": (
                                "May be legitimate if modifiers indicate separate encounters "
                                "(e.g., bilateral procedures). Verify claim submission timestamps."
                            ),
                            "estimated_overpayment": float(dup_amount),
                            "claimed_amount": float(amount * dup_count),
                            "expected_amount": float(amount),
                            "estimated_excess": float(dup_amount),
                            "calculation_basis": "Single legitimate service amount",
                            "claims": claim_ids,
                            "provider_id": provider_id,
                            "member_id": patient_id,
                            "duplicate_count": dup_count,
                            "duplicate_pattern": "exact",
                            "confidence": "HIGH",
                            "severity": "HIGH",
                        }
                    ))

            # Near-duplicate detection (date ±day_window, same amount)
            for i in range(len(sorted_claims)):
                for j in range(i + 1, len(sorted_claims)):
                    c1, c2 = sorted_claims[i], sorted_claims[j]

                    # Skip if same date (already caught as exact)
                    if str(c1["date_of_service"]) == str(c2["date_of_service"]):
                        continue

                    # Check date proximity
                    try:
                        from datetime import datetime
                        d1 = datetime.strptime(str(c1["date_of_service"])[:10], "%Y-%m-%d")
                        d2 = datetime.strptime(str(c2["date_of_service"])[:10], "%Y-%m-%d")
                        date_diff = abs((d2 - d1).days)
                    except (ValueError, TypeError):
                        continue

                    if date_diff > day_window:
                        continue

                    # Amount must match for near-duplicate
                    if c1["billed_amount"] != c2["billed_amount"]:
                        continue

                    amount = c1["billed_amount"]
                    results.append(RuleResult(
                        triggered=True,
                        evidence_data={
                            "description": (
                                f"Near-duplicate billing: claims {c1['claim_id']} and {c2['claim_id']} "
                                f"for procedure {procedure_code} are {date_diff} day(s) apart "
                                f"with identical amounts (${amount:,.2f}). "
                                f"Member={patient_id}, Provider={provider_id}."
                            ),
                            "what_happened": f"Two claims {date_diff} day(s) apart with same procedure and amount",
                            "why_suspicious": "Near-identical claims within a short window may indicate accidental or intentional re-submission",
                            "baseline_used": f"Date window: ±{day_window} day(s) with amount match",
                            "deviation": f"{date_diff} day(s) apart",
                            "false_positive_notes": (
                                "Date difference may indicate a legitimate follow-up visit. "
                                "Verify clinical documentation for separate encounters."
                            ),
                            "estimated_overpayment": float(amount),
                            "claimed_amount": float(amount * 2),
                            "expected_amount": float(amount),
                            "estimated_excess": float(amount),
                            "calculation_basis": "One of two near-identical claims is potentially excess",
                            "claims": [c1["claim_id"], c2["claim_id"]],
                            "provider_id": provider_id,
                            "member_id": patient_id,
                            "duplicate_count": 2,
                            "duplicate_pattern": "near",
                            "date_difference_days": date_diff,
                            "confidence": "MEDIUM",
                            "severity": "MEDIUM",
                        }
                    ))

        return results
