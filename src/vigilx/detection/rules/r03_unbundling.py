"""
R03 — Unbundling Detection (Detection Layer).

Detects combinations of individually billed services that normally represent
a bundled service billed to the same provider, member, and encounter.

Generates: bundle pattern, affected claims, expected bundled service,
           individual billed services, estimated excess amount.
"""

from typing import List, Dict, Any
from collections import defaultdict
from vigilx.detection.rules.base import BaseRule, DataContext, RuleResult


# Known comprehensive → component bundling pairs
# In production, this would come from CCI/NCCI edits database
DEFAULT_BUNDLE_RULES = {
    # Comprehensive Metabolic Panel includes individual components
    "80053": {
        "name": "Comprehensive Metabolic Panel",
        "components": ["82310", "82374", "82435", "82565", "82947", "84132", "84295",
                        "84520", "84550", "82040", "84075", "84460"],
    },
    # Basic Metabolic Panel
    "80048": {
        "name": "Basic Metabolic Panel",
        "components": ["82310", "82374", "82435", "82565", "82947", "84132", "84295", "84520"],
    },
    # Lipid Panel
    "80061": {
        "name": "Lipid Panel",
        "components": ["82465", "83718", "84478"],
    },
    # CBC with differential
    "85025": {
        "name": "CBC with Differential",
        "components": ["85004", "85007", "85008", "85009"],
    },
}


class R03Unbundling(BaseRule):
    """R03: Unbundling Detection."""

    rule_id = "R03"
    rule_name = "Unbundling"

    def evaluate(self, context: DataContext) -> List[RuleResult]:
        if not self.enabled:
            return []

        results = []
        override_mods = set(self.cfg.get("allowed_override_modifiers", ["59", "25", "XE"]))

        # Group claims by encounter: (patient, date, provider)
        encounters: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)

        for claim in context.claims:
            patient_id = claim.get("patient_id") or claim.get("member_id")
            dos = claim.get("date_of_service") or claim.get("service_date")
            provider_id = claim.get("provider_id") or claim.get("billing_provider_id")

            if not all([patient_id, dos, provider_id]):
                continue

            encounters[(patient_id, dos, provider_id)].append(claim)

        # Track provider unbundling rates for escalation
        provider_unbundle_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"total_encounters": 0, "unbundled_encounters": 0}
        )

        for (patient_id, dos, provider_id), encounter_claims in encounters.items():
            provider_unbundle_counts[provider_id]["total_encounters"] += 1

            billed_codes = {}
            for c in encounter_claims:
                proc = c.get("procedure_code") or c.get("cpt_code")
                if proc:
                    billed_codes[proc] = c

            # Check for override modifiers
            has_override = False
            for c in encounter_claims:
                modifier = c.get("modifier", "")
                if modifier and set(str(modifier).split(",")) & override_mods:
                    has_override = True
                    break

            if has_override:
                continue

            # Check each bundle rule
            for comp_code, bundle_info in DEFAULT_BUNDLE_RULES.items():
                components_found = [c for c in bundle_info["components"] if c in billed_codes]

                if not components_found:
                    continue

                # Case 1: Comprehensive code billed WITH component codes
                if comp_code in billed_codes and components_found:
                    related_claims = [billed_codes[comp_code].get("claim_id")]
                    component_amounts = []
                    for comp in components_found:
                        related_claims.append(billed_codes[comp].get("claim_id"))
                        component_amounts.append(
                            float(billed_codes[comp].get("billed_amount", 0.0) or 0.0)
                        )

                    overpayment = sum(component_amounts)
                    comp_amount = float(billed_codes[comp_code].get("billed_amount", 0.0) or 0.0)

                    provider_unbundle_counts[provider_id]["unbundled_encounters"] += 1

                    results.append(RuleResult(
                        triggered=True,
                        evidence_data={
                            "description": (
                                f"Unbundling detected: {bundle_info['name']} ({comp_code}) "
                                f"billed alongside {len(components_found)} component code(s) "
                                f"{components_found} for member {patient_id} by provider "
                                f"{provider_id} on {dos}. "
                                f"Components should be included in the comprehensive code."
                            ),
                            "what_happened": (
                                f"Comprehensive code {comp_code} and {len(components_found)} "
                                f"component codes billed on same encounter"
                            ),
                            "why_suspicious": (
                                f"Component codes {components_found} are included in "
                                f"{bundle_info['name']} ({comp_code}) and should not be billed separately"
                            ),
                            "bundle_pattern": {
                                "comprehensive_code": comp_code,
                                "comprehensive_name": bundle_info["name"],
                                "component_codes": components_found,
                                "comprehensive_amount": comp_amount,
                                "component_amounts": component_amounts,
                            },
                            "baseline_used": "CCI/NCCI bundling edits",
                            "false_positive_notes": (
                                "Modifier -59 (Distinct Procedural Service) may justify "
                                "separate billing if clinically documented. "
                                "Distinct anatomical sites may also justify separate billing."
                            ),
                            "estimated_overpayment": float(overpayment),
                            "claimed_amount": float(comp_amount + overpayment),
                            "expected_amount": float(comp_amount),
                            "estimated_excess": float(overpayment),
                            "calculation_basis": "Component code amounts are excess when comprehensive code covers them",
                            "claims": [c for c in related_claims if c],
                            "provider_id": provider_id,
                            "member_id": patient_id,
                            "severity": "MEDIUM",
                        }
                    ))

                # Case 2: Multiple component codes without comprehensive (potential unbundling)
                elif len(components_found) >= 3 and comp_code not in billed_codes:
                    related_claims = [billed_codes[c].get("claim_id") for c in components_found]
                    component_amounts = [
                        float(billed_codes[c].get("billed_amount", 0.0) or 0.0)
                        for c in components_found
                    ]
                    total_components = sum(component_amounts)

                    provider_unbundle_counts[provider_id]["unbundled_encounters"] += 1

                    results.append(RuleResult(
                        triggered=True,
                        evidence_data={
                            "description": (
                                f"Potential unbundling: {len(components_found)} component codes "
                                f"of {bundle_info['name']} ({comp_code}) billed individually "
                                f"for member {patient_id} by provider {provider_id} on {dos}. "
                                f"Expected bundled service: {comp_code}."
                            ),
                            "what_happened": (
                                f"{len(components_found)} individual components of "
                                f"{bundle_info['name']} billed separately"
                            ),
                            "why_suspicious": (
                                "Multiple components of a panel billed individually "
                                "typically costs more than the bundled panel code"
                            ),
                            "bundle_pattern": {
                                "expected_bundled_code": comp_code,
                                "expected_bundled_name": bundle_info["name"],
                                "individual_codes": components_found,
                                "individual_amounts": component_amounts,
                            },
                            "false_positive_notes": (
                                "Provider may have ordered only specific tests within the panel. "
                                "Clinical necessity should be reviewed."
                            ),
                            "estimated_overpayment": 0.0,
                            "claims": [c for c in related_claims if c],
                            "provider_id": provider_id,
                            "member_id": patient_id,
                            "severity": "LOW",
                        }
                    ))

        # Escalate providers with high unbundling rates
        for result in results:
            pid = result.evidence_data.get("provider_id")
            if pid and pid in provider_unbundle_counts:
                stats = provider_unbundle_counts[pid]
                if stats["total_encounters"] > 0:
                    rate = stats["unbundled_encounters"] / stats["total_encounters"]
                    result.evidence_data["provider_unbundling_rate"] = round(rate, 4)
                    if rate > 0.20:  # >20% unbundling rate → escalate
                        result.evidence_data["severity"] = "HIGH"
                        result.evidence_data["escalation_reason"] = (
                            f"Provider unbundling rate {rate:.1%} exceeds 20% threshold"
                        )

        return results
