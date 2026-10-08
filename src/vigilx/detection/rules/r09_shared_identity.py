"""
R09 — Shared Identity Detection (Detection Layer).

Behaviorally intelligent shared identity detection:
  - Detects identity farming, synthetic identities, or identity theft.
  - Identifies massive concurrency of unassociated providers for a single patient identity.
  - Outputs behavior features for the risk engine.
"""
from typing import List, Dict, Any
from collections import defaultdict
from vigilx.detection.rules.base import BaseRule, DataContext, RuleResult

class R09SharedIdentityDetection(BaseRule):
    rule_id = "R09"
    rule_name = "Shared Identity Detection"

    def evaluate(self, context: DataContext) -> List[RuleResult]:
        results = []
        
        # Group providers by patient
        patient_providers = defaultdict(set)
        patient_claims = defaultdict(list)
        
        for claim in context.claims:
            patient_id = claim.get("patient_id")
            provider_id = claim.get("provider_id")
            if patient_id and provider_id:
                patient_providers[patient_id].add(provider_id)
                patient_claims[patient_id].append(claim)
                
        THRESHOLD_PROVIDERS = 15
        
        for patient_id, providers in patient_providers.items():
            provider_count = len(providers)
            if provider_count > THRESHOLD_PROVIDERS:
                total_billed = sum(c.get("billed_amount", 0.0) for c in patient_claims[patient_id])
                
                provider_behavior_features = {
                    "shared_identity_risk_flag": 1.0,
                    "patient_identity_fanout": provider_count,
                    "synthetic_identity_risk": provider_count / THRESHOLD_PROVIDERS
                }
                
                # We flag the providers utilizing this highly shared identity
                for provider_id in providers:
                    results.append(RuleResult(
                        triggered=True,
                        evidence_data={
                            "description": f"Shared Identity Risk: Patient {patient_id} seen by {provider_count} distinct providers. Provider {provider_id} is part of this cluster.",
                            "false_positive_notes": "Patient might have severe complex chronic conditions or recent major trauma requiring many specialists.",
                            "estimated_overpayment": 0.0,
                            "claims": [c.get("claim_id") for c in patient_claims[patient_id] if c.get("provider_id") == provider_id],
                            "provider_id": provider_id,
                            "severity": "HIGH",
                            "provider_behavior_features": provider_behavior_features
                        }
                    ))
                
        return results
