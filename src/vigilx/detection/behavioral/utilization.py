from typing import List, Dict, Any
from vigilx.detection.models.outputs import ProviderBehaviorFeatures
from collections import defaultdict

class UtilizationBehaviorExtractor:
    """
    Extracts provider utilization trends and historical baselines.
    """
    def extract(self, claims: List[Dict[str, Any]], provider_profiles: Dict[str, Any]) -> List[ProviderBehaviorFeatures]:
        features_list = []
        
        provider_stats = defaultdict(lambda: {"total_claims": 0, "total_amount": 0.0, "unique_patients": set()})
        
        for claim in claims:
            provider_id = claim.get("provider_id")
            if not provider_id:
                continue
                
            provider_stats[provider_id]["total_claims"] += 1
            provider_stats[provider_id]["total_amount"] += claim.get("billed_amount", 0.0)
            
            patient_id = claim.get("patient_id")
            if patient_id:
                provider_stats[provider_id]["unique_patients"].add(patient_id)
                
        for provider_id, stats in provider_stats.items():
            profile = provider_profiles.get(provider_id, {})
            hist_avg_claims = profile.get("historical_monthly_avg_claims", 100)
            
            current_claims = stats["total_claims"]
            spike_ratio = current_claims / hist_avg_claims if hist_avg_claims > 0 else 1.0
            
            avg_amount_per_claim = stats["total_amount"] / current_claims if current_claims > 0 else 0.0
            
            features_list.append(ProviderBehaviorFeatures(
                provider_id=provider_id,
                features={
                    "claim_volume_spike_ratio": float(spike_ratio),
                    "avg_amount_per_claim": float(avg_amount_per_claim),
                    "unique_patient_count": float(len(stats["unique_patients"])),
                    "claims_per_patient_ratio": float(current_claims / len(stats["unique_patients"]) if stats["unique_patients"] else 0.0)
                }
            ))
            
        return features_list
