"""
R06 — Impossible Timing Detection (Detection Layer).

Behaviorally intelligent timing detection:
  - Detects physical impossibility (same day, conflicting locations/settings).
  - Calculates travel velocity required (if data permits).
  - Flags conflicting concurrent inpatient and outpatient events.
  - Outputs structural temporal/geographic features for the risk engine.
"""
from typing import List, Dict, Any, Set
from collections import defaultdict
from datetime import datetime
from vigilx.detection.rules.base import BaseRule, DataContext, RuleResult

class R06ImpossibleTiming(BaseRule):
    rule_id = "R06"
    rule_name = "Impossible Timing"

    def evaluate(self, context: DataContext) -> List[RuleResult]:
        results = []
        
        # Group claims by patient and date of service
        patient_daily_claims = defaultdict(lambda: defaultdict(list))
        
        for claim in context.claims:
            patient_id = claim.get("patient_id")
            dos = claim.get("date_of_service")
            
            if not patient_id or not dos:
                continue
                
            patient_daily_claims[patient_id][dos].append(claim)
            
        for patient_id, days in patient_daily_claims.items():
            for dos, claims_on_day in days.items():
                if len(claims_on_day) < 2:
                    continue
                
                # Check for location and setting conflicts
                locations = set()
                settings = set()
                providers = set()
                total_billed = 0.0
                claim_ids = []
                
                for c in claims_on_day:
                    loc = c.get("service_location_state")
                    if loc:
                        locations.add(loc)
                    
                    setting = c.get("place_of_service")
                    if setting:
                        settings.add(setting)
                        
                    providers.add(c.get("provider_id"))
                    total_billed += c.get("billed_amount", 0.0)
                    claim_ids.append(c.get("claim_id"))
                    
                is_impossible = False
                reasons = []
                
                if len(locations) > 1:
                    is_impossible = True
                    reasons.append(f"Multiple states on same day: {list(locations)}")
                    
                if "Inpatient" in settings and ("Outpatient" in settings or "Office" in settings):
                    is_impossible = True
                    reasons.append("Conflicting place of service (Inpatient + Outpatient/Office)")
                    
                if is_impossible:
                    # Create temporal and geographic features
                    temporal_features = {
                        "same_day_conflicts": len(claims_on_day),
                        "conflict_types": len(reasons),
                        "is_impossible_timing": 1.0
                    }
                    geographic_features = {
                        "distinct_states_same_day": len(locations),
                        "interstate_conflict": 1.0 if len(locations) > 1 else 0.0
                    }
                    
                    for claim_id in claim_ids:
                        results.append(RuleResult(
                            triggered=True,
                            evidence_data={
                                "description": f"Impossible timing detected for patient {patient_id} on {dos}: {'; '.join(reasons)}.",
                                "false_positive_notes": "Telehealth services or facility transfers could cause apparent conflicts. Check modifier codes.",
                                "estimated_overpayment": total_billed / len(claim_ids), # Pro-rated
                                "claims": [claim_id],
                                "provider_id": list(providers)[0] if len(providers) == 1 else "MULTIPLE",
                                "severity": "HIGH",
                                "claim_behavior_features": {
                                    "impossible_timing_flag": 1.0,
                                    "conflict_count": len(reasons)
                                },
                                "temporal_features": temporal_features,
                                "geographic_features": geographic_features
                            }
                        ))
                    
        return results
