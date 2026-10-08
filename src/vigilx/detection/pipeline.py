from typing import List, Dict, Any
from vigilx.detection.models.outputs import DetectionOutput, Alert, Evidence
from vigilx.detection.rules.base import DataContext, BaseRule
from vigilx.detection.behavioral.temporal import TemporalBehaviorExtractor
from vigilx.detection.behavioral.utilization import UtilizationBehaviorExtractor
from vigilx.detection.behavioral.referral import ReferralBehaviorExtractor
from vigilx.detection.behavioral.geographic import GeographicBehaviorExtractor

class DetectionPipeline:
    """
    Main orchestrator for the Detection & Behavioral Intelligence module.
    """
    def __init__(self, rules: List[BaseRule]):
        self.rules = rules
        self.temporal_extractor = TemporalBehaviorExtractor()
        self.utilization_extractor = UtilizationBehaviorExtractor()
        self.referral_extractor = ReferralBehaviorExtractor()
        self.geographic_extractor = GeographicBehaviorExtractor()

    def run(self, raw_claims: List[Dict[str, Any]], provider_profiles: Dict[str, Any]) -> DetectionOutput:
        """
        Executes the detection pipeline.
        
        1. Ingest Data
        2. Update Behavioral Intelligence Baselines
        3. Evaluate Rules (R01-R10)
        4. Generate Evidence & Alerts
        5. Extract Features
        """
        context = DataContext(claims=raw_claims, provider_profiles=provider_profiles)
        
        output = DetectionOutput()
        
        # Evaluate rules
        for rule in self.rules:
            results = rule.evaluate(context)
            for result in results:
                if result.triggered:
                    # In a real implementation, EvidenceGenerator would format this
                    # For now, we mock the evidence generation
                    evidence = Evidence(
                        evidence_id=f"ev_{rule.rule_id}_{len(output.evidence)}",
                        rule_id=rule.rule_id,
                        description=result.evidence_data.get("description", "Suspicious behavior detected"),
                        false_positive_notes=result.evidence_data.get("false_positive_notes"),
                        estimated_overpayment=result.evidence_data.get("estimated_overpayment", 0.0),
                        claim_level_traceability=result.evidence_data.get("claims", [])
                    )
                    output.evidence.append(evidence)
                    
                    # Generate Alert
                    alert = Alert(
                        alert_id=f"al_{rule.rule_id}_{len(output.alerts)}",
                        provider_id=result.evidence_data.get("provider_id", "UNKNOWN"),
                        rule_id=rule.rule_id,
                        severity=result.evidence_data.get("severity", "MEDIUM"),
                        evidence_ids=[evidence.evidence_id]
                    )
                    output.alerts.append(alert)
        
        # Run behavioral feature extractors to populate output
        output.temporal_features = self.temporal_extractor.extract(raw_claims)
        output.provider_behavior_features = self.utilization_extractor.extract(raw_claims, provider_profiles)
        output.referral_features = self.referral_extractor.extract(raw_claims)
        output.geographic_features = self.geographic_extractor.extract(raw_claims)
        
        return output
