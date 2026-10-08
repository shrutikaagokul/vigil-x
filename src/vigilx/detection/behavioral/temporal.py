from typing import List, Dict, Any
from vigilx.detection.models.outputs import TemporalFeatures
from collections import defaultdict
from datetime import datetime

class TemporalBehaviorExtractor:
    """
    Extracts temporal patterns for providers and claims.
    """
    def extract(self, claims: List[Dict[str, Any]]) -> List[TemporalFeatures]:
        features_list = []
        
        # Group by provider
        provider_dates = defaultdict(list)
        for claim in claims:
            provider_id = claim.get("provider_id")
            dos_str = claim.get("date_of_service")
            if provider_id and dos_str:
                try:
                    dos = datetime.strptime(dos_str, "%Y-%m-%d")
                    provider_dates[provider_id].append(dos)
                except ValueError:
                    pass
                    
        for provider_id, dates in provider_dates.items():
            if not dates:
                continue
                
            # Calculate weekend billing ratio
            weekend_claims = sum(1 for d in dates if d.weekday() >= 5)
            weekend_ratio = weekend_claims / len(dates)
            
            # Calculate night billing if times are available (mocked here)
            # Find max consecutive days billed
            dates_sorted = sorted(list(set(dates)))
            max_consecutive = 0
            current_consecutive = 1
            for i in range(1, len(dates_sorted)):
                if (dates_sorted[i] - dates_sorted[i-1]).days == 1:
                    current_consecutive += 1
                else:
                    max_consecutive = max(max_consecutive, current_consecutive)
                    current_consecutive = 1
            max_consecutive = max(max_consecutive, current_consecutive)
            
            features_list.append(TemporalFeatures(
                entity_id=provider_id,
                entity_type="provider",
                features={
                    "weekend_billing_ratio": float(weekend_ratio),
                    "max_consecutive_billing_days": float(max_consecutive),
                    "total_active_days": float(len(dates_sorted))
                }
            ))
            
        return features_list
