"""
R10 — Billing Bursts Detection (Detection Layer).

Behaviorally intelligent billing burst ("bust-out" fraud) detection:
  - Detects sudden, extreme spikes in billing volume relative to historical baselines.
  - Outputs temporal and provider behavioral features for the risk engine.
"""
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime
from vigilx.detection.rules.base import BaseRule, DataContext, RuleResult

class R10BillingBursts(BaseRule):
    rule_id = "R10"
    rule_name = "Billing Bursts"

    def evaluate(self, context: DataContext) -> List[RuleResult]:
        results = []
        
        provider_weekly_amounts = defaultdict(lambda: defaultdict(float))
        provider_weekly_claims = defaultdict(lambda: defaultdict(list))
        
        for claim in context.claims:
            provider_id = claim.get("provider_id")
            dos_str = claim.get("date_of_service")
            amt = claim.get("billed_amount", 0.0)
            
            if not provider_id or not dos_str:
                continue
                
            try:
                # Assuming YYYY-MM-DD
                dos_date = datetime.strptime(dos_str[:10], "%Y-%m-%d")
                year, week, _ = dos_date.isocalendar()
                week_key = f"{year}-W{week}"
                
                provider_weekly_amounts[provider_id][week_key] += amt
                provider_weekly_claims[provider_id][week_key].append(claim.get("claim_id"))
            except (ValueError, TypeError):
                pass
                
        for provider_id, weeks in provider_weekly_amounts.items():
            profile = context.provider_profiles.get(provider_id, {})
            historical_weekly_avg = profile.get("historical_weekly_avg_billing", 5000.0)
            if historical_weekly_avg <= 0:
                historical_weekly_avg = 5000.0
                
            for week, amt in weeks.items():
                spike_ratio = amt / historical_weekly_avg
                
                if spike_ratio > 10.0 and amt > 50000:
                    claim_ids = provider_weekly_claims[provider_id][week]
                    
                    temporal_features = {
                        "weekly_billing_spike_ratio": spike_ratio,
                        "is_billing_burst": 1.0,
                        "burst_magnitude": amt
                    }
                    
                    provider_behavior_features = {
                        "bust_out_risk_flag": 1.0,
                        "historical_deviation_max": spike_ratio
                    }
                    
                    results.append(RuleResult(
                        triggered=True,
                        evidence_data={
                            "description": f"Billing Burst (Bust-Out Risk): Provider billed ${amt:,.2f} in week {week}. This is a {spike_ratio:.1f}x spike over the ${historical_weekly_avg:,.2f} baseline.",
                            "false_positive_notes": "Could be a backlog of claims submitted simultaneously due to a new EMR/billing system rollout.",
                            "estimated_overpayment": amt - historical_weekly_avg,
                            "claims": claim_ids, 
                            "provider_id": provider_id,
                            "severity": "CRITICAL",
                            "temporal_features": temporal_features,
                            "provider_behavior_features": provider_behavior_features
                        }
                    ))
                    
        return results
