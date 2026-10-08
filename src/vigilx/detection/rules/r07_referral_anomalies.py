"""
R07 — Referral Anomalies Detection (Detection Layer).

Behaviorally intelligent referral anomaly detection:
  - Detects highly circular, mutually exclusive, or abnormally concentrated referral loops.
  - Generates structural referral features for the downstream risk engine.
"""
from typing import List, Dict, Any
from collections import defaultdict
from vigilx.detection.rules.base import BaseRule, DataContext, RuleResult

class R07ReferralAnomalies(BaseRule):
    rule_id = "R07"
    rule_name = "Referral Anomalies"

    def evaluate(self, context: DataContext) -> List[RuleResult]:
        results = []
        
        # Count referrals from referring_provider -> rendering_provider
        referral_counts = defaultdict(lambda: defaultdict(int))
        total_referrals = defaultdict(int)
        rendering_totals = defaultdict(int)
        
        for claim in context.claims:
            referring = claim.get("referring_provider_id")
            rendering = claim.get("provider_id")
            
            if referring and rendering and referring != rendering:
                referral_counts[referring][rendering] += 1
                total_referrals[referring] += 1
                rendering_totals[rendering] += 1
                
        # Analyze concentration
        for referring, targets in referral_counts.items():
            if total_referrals[referring] > 20: # Require a minimum volume
                for target, count in targets.items():
                    outbound_ratio = count / total_referrals[referring]
                    
                    if outbound_ratio > 0.80:
                        target_total_outbound = total_referrals.get(target, 0)
                        target_back_count = referral_counts.get(target, {}).get(referring, 0)
                        
                        is_loop = False
                        loop_ratio = 0.0
                        if target_total_outbound > 10:
                            loop_ratio = target_back_count / target_total_outbound
                            if loop_ratio > 0.50:
                                is_loop = True
                                
                        desc = f"High referral concentration: Provider {referring} sends {outbound_ratio:.1%} of referrals to {target}."
                        if is_loop:
                            desc += f" Mutual referral loop detected ({loop_ratio:.1%} return rate) - Kickback risk."
                            
                        # Generate referral behavior features
                        referral_features = {
                            "max_outbound_referral_ratio": outbound_ratio,
                            "mutual_loop_flag": 1.0 if is_loop else 0.0,
                            "loop_return_ratio": loop_ratio,
                            "total_referrals_made": total_referrals[referring],
                            "concentration_risk_score": outbound_ratio * (1.5 if is_loop else 1.0)
                        }
                        
                        provider_behavior_features = {
                            "has_referral_anomaly": 1.0,
                            "kickback_risk_indicator": 1.0 if is_loop else 0.5
                        }
                            
                        results.append(RuleResult(
                            triggered=True,
                            evidence_data={
                                "description": desc,
                                "false_positive_notes": "Providers might belong to the same exclusive health system/ACO or rural area with limited specialists.",
                                "estimated_overpayment": 0.0,
                                "claims": [], 
                                "provider_id": referring,
                                "severity": "HIGH" if is_loop else "MEDIUM",
                                "referral_features": referral_features,
                                "provider_behavior_features": provider_behavior_features
                            }
                        ))
                        
        return results
