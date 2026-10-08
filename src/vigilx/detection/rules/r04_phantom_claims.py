"""
R04 — Phantom / Impossible Claims Detection (Detection Layer).

Detects claims that appear impossible or invalid based on available data:
  - Service after member death
  - Service after eligibility termination
  - Gender-procedure mismatches
  - Inactive/ineligible provider
  - Claims on weekends/holidays for non-emergency care

Only applies checks supported by the actual dataset/schema.
"""

from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime
from vigilx.detection.rules.base import BaseRule, DataContext, RuleResult


# Gender-specific procedure codes
FEMALE_ONLY_CODES = {"58150", "58152", "59400", "59410", "59510", "59610", "59612",
                      "58571", "58573", "57460", "57500"}
MALE_ONLY_CODES = {"55810", "55812", "55815", "55840", "55842", "55845",
                    "54050", "54055", "54056", "54057"}


class R04PhantomClaims(BaseRule):
    """R04: Phantom / Impossible Claims Detection."""

    rule_id = "R04"
    rule_name = "Phantom / Impossible Claims"

    def evaluate(self, context: DataContext) -> List[RuleResult]:
        if not self.enabled:
            return []

        results = []

        # Build member lookup for eligibility checks
        member_lookup = {}
        for m in context.members:
            mid = m.get("member_id") or m.get("patient_id")
            if mid:
                member_lookup[mid] = m

        # Build provider lookup for status checks
        provider_lookup = {}
        for pid, profile in context.provider_profiles.items():
            provider_lookup[pid] = profile

        for claim in context.claims:
            patient_id = claim.get("patient_id") or claim.get("member_id")
            provider_id = claim.get("provider_id") or claim.get("billing_provider_id")
            proc_code = str(claim.get("procedure_code") or claim.get("cpt_code", ""))
            claim_id = claim.get("claim_id")
            dos = claim.get("date_of_service") or claim.get("service_date")
            billed_amount = float(claim.get("billed_amount", 0.0) or 0.0)
            patient_meta = claim.get("patient_metadata", {})

            if not claim_id:
                continue

            # === Check 1: Deceased member billing ===
            is_deceased = patient_meta.get("is_deceased", False)
            dod = patient_meta.get("date_of_death")

            # Also check member lookup
            if patient_id and patient_id in member_lookup:
                member = member_lookup[patient_id]
                if not dod:
                    dod = member.get("death_date") or member.get("date_of_death")
                if not is_deceased and dod:
                    is_deceased = True

            if is_deceased and dos and dod:
                try:
                    dos_dt = datetime.strptime(str(dos)[:10], "%Y-%m-%d") if isinstance(dos, str) else dos
                    dod_dt = datetime.strptime(str(dod)[:10], "%Y-%m-%d") if isinstance(dod, str) else dod
                    if dos_dt > dod_dt:
                        days_after = (dos_dt - dod_dt).days
                        results.append(RuleResult(
                            triggered=True,
                            evidence_data={
                                "description": (
                                    f"Service on {str(dos)[:10]} is {days_after} day(s) after "
                                    f"member {patient_id} date of death ({str(dod)[:10]}). "
                                    f"Procedure: {proc_code}, Provider: {provider_id}."
                                ),
                                "what_happened": f"Claim submitted for service {days_after} days after member death",
                                "why_suspicious": "Services cannot be rendered to a deceased member",
                                "check_type": "deceased_member_billing",
                                "days_after_death": days_after,
                                "false_positive_notes": (
                                    "Verify death date accuracy — retroactive corrections are possible. "
                                    "Lab results or pathology reports may have delayed processing."
                                ),
                                "estimated_overpayment": billed_amount,
                                "claims": [claim_id],
                                "provider_id": provider_id,
                                "member_id": patient_id,
                                "severity": "CRITICAL",
                            }
                        ))
                except (ValueError, TypeError, AttributeError):
                    pass

            # === Check 2: Post-termination billing ===
            if patient_id and patient_id in member_lookup:
                member = member_lookup[patient_id]
                term_date = member.get("enrollment_end") or member.get("termination_date")
                if term_date and dos:
                    try:
                        dos_dt = datetime.strptime(str(dos)[:10], "%Y-%m-%d") if isinstance(dos, str) else dos
                        term_dt = datetime.strptime(str(term_date)[:10], "%Y-%m-%d") if isinstance(term_date, str) else term_date
                        if dos_dt > term_dt:
                            days_after = (dos_dt - term_dt).days
                            results.append(RuleResult(
                                triggered=True,
                                evidence_data={
                                    "description": (
                                        f"Service on {str(dos)[:10]} is {days_after} day(s) after "
                                        f"member {patient_id} eligibility termination ({str(term_date)[:10]})."
                                    ),
                                    "what_happened": f"Claim submitted {days_after} days after coverage ended",
                                    "why_suspicious": "Services billed after eligibility termination are not covered",
                                    "check_type": "post_termination_billing",
                                    "days_after_termination": days_after,
                                    "false_positive_notes": (
                                        "Retroactive eligibility reinstatement may apply. "
                                        "COBRA or continuation coverage may explain post-termination services."
                                    ),
                                    "estimated_overpayment": billed_amount,
                                    "claims": [claim_id],
                                    "provider_id": provider_id,
                                    "member_id": patient_id,
                                    "severity": "HIGH",
                                }
                            ))
                    except (ValueError, TypeError, AttributeError):
                        pass

            # === Check 3: Gender-procedure mismatch ===
            gender = patient_meta.get("gender") or (
                member_lookup.get(patient_id, {}).get("gender") if patient_id else None
            )

            if gender and proc_code:
                if gender.upper() == "M" and proc_code in FEMALE_ONLY_CODES:
                    results.append(RuleResult(
                        triggered=True,
                        evidence_data={
                            "description": (
                                f"Female-only procedure {proc_code} billed for male patient {patient_id}. "
                                f"Provider: {provider_id}."
                            ),
                            "what_happened": f"Gender-specific procedure code mismatch",
                            "why_suspicious": f"Procedure {proc_code} is clinically specific to female patients",
                            "check_type": "gender_procedure_mismatch",
                            "false_positive_notes": (
                                "Could be a data entry error in patient demographics or procedure code. "
                                "Transgender patients may legitimately receive gender-specific procedures."
                            ),
                            "estimated_overpayment": billed_amount,
                            "claims": [claim_id],
                            "provider_id": provider_id,
                            "member_id": patient_id,
                            "severity": "CRITICAL",
                        }
                    ))
                elif gender.upper() == "F" and proc_code in MALE_ONLY_CODES:
                    results.append(RuleResult(
                        triggered=True,
                        evidence_data={
                            "description": (
                                f"Male-only procedure {proc_code} billed for female patient {patient_id}. "
                                f"Provider: {provider_id}."
                            ),
                            "what_happened": f"Gender-specific procedure code mismatch",
                            "why_suspicious": f"Procedure {proc_code} is clinically specific to male patients",
                            "check_type": "gender_procedure_mismatch",
                            "false_positive_notes": (
                                "Could be a data entry error in patient demographics or procedure code."
                            ),
                            "estimated_overpayment": billed_amount,
                            "claims": [claim_id],
                            "provider_id": provider_id,
                            "member_id": patient_id,
                            "severity": "CRITICAL",
                        }
                    ))

            # === Check 4: Inactive/ineligible provider ===
            if provider_id and provider_id in provider_lookup:
                profile = provider_lookup[provider_id]
                provider_status = profile.get("status", "").lower()
                if provider_status in ("inactive", "suspended", "revoked", "terminated"):
                    results.append(RuleResult(
                        triggered=True,
                        evidence_data={
                            "description": (
                                f"Claim billed by provider {provider_id} with status "
                                f"'{provider_status}'. Procedure: {proc_code}."
                            ),
                            "what_happened": f"Claim submitted by {provider_status} provider",
                            "why_suspicious": f"Provider {provider_id} is {provider_status} and should not be billing",
                            "check_type": "inactive_provider",
                            "false_positive_notes": (
                                "Provider status may have been updated retroactively. "
                                "Services may have been rendered before status change."
                            ),
                            "estimated_overpayment": billed_amount,
                            "claims": [claim_id],
                            "provider_id": provider_id,
                            "member_id": patient_id,
                            "severity": "HIGH",
                        }
                    ))

        return results
