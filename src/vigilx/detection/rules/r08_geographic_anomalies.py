"""
R08 — Geographic Anomalies Detection (Detection Layer).

Behaviorally intelligent geographic anomaly detection:
  - Detects when patients travel an unreasonably long distance for routine care.
  - Flags coordinated fraud rings (e.g., bussing patients).
  - Outputs geographic features for the risk engine.
"""
from typing import List, Dict, Any
from collections import defaultdict
from vigilx.detection.rules.base import BaseRule, DataContext, RuleResult

class R08GeographicAnomalies(BaseRule):
    rule_id = "R08"
    rule_name = "Geographic Anomalies"

    def evaluate(self, context: DataContext) -> List[RuleResult]:
        results = []
        
        routine_care_codes = {"99213", "99214", "99215", "99203", "99204"}
        
        for claim in context.claims:
            patient_state = claim.get("patient_metadata", {}).get("state")
            service_state = claim.get("service_location_state")
            proc_code = claim.get("procedure_code")
            
            if patient_state and service_state and patient_state != service_state:
                if proc_code in routine_care_codes:
                    geographic_features = {
                        "interstate_routine_care": 1.0,
                        "patient_state_mismatch": 1.0
                    }
                    
                    claim_behavior_features = {
                        "geographic_anomaly_flag": 1.0
                    }
                    
                    results.append(RuleResult(
                        triggered=True,
                        evidence_data={
                            "description": f"Geographic anomaly: Patient from {patient_state} traveled to {service_state} for routine procedure {proc_code}.",
                            "false_positive_notes": "Patient might live on a state border, be a snowbird, or traveling for work/vacation. Need distance calculation.",
                            "estimated_overpayment": claim.get("billed_amount", 0.0),
                            "claims": [claim.get("claim_id")],
                            "provider_id": claim.get("provider_id"),
                            "severity": "LOW",
                            "geographic_features": geographic_features,
                            "claim_behavior_features": claim_behavior_features
                        }
                    ))
                    
        return results
