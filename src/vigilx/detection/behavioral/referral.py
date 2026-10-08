from typing import List, Dict, Any
from vigilx.detection.models.outputs import ReferralFeatures
from collections import defaultdict

class ReferralBehaviorExtractor:
    """
    Extracts referral behavior patterns (e.g., in-network vs out-of-network).
    """
    def extract(self, claims: List[Dict[str, Any]]) -> List[ReferralFeatures]:
        features_list = []
        
        referral_counts = defaultdict(lambda: {"total": 0, "unique_targets": set()})
        
        for claim in claims:
            referring = claim.get("referring_provider_id")
            rendering = claim.get("provider_id")
            
            if referring and rendering and referring != rendering:
                referral_counts[referring]["total"] += 1
                referral_counts[referring]["unique_targets"].add(rendering)
                
        for referring_id, stats in referral_counts.items():
            total = stats["total"]
            unique = len(stats["unique_targets"])
            
            features_list.append(ReferralFeatures(
                provider_id=referring_id,
                features={
                    "total_referrals_made": float(total),
                    "unique_referral_targets": float(unique),
                    "referral_concentration_index": float((total - unique) / total if total > 1 else 0.0)
                }
            ))
            
        return features_list
