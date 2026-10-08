from typing import List, Dict, Any
from vigilx.detection.models.outputs import GeographicFeatures
from collections import defaultdict

class GeographicBehaviorExtractor:
    """
    Extracts geographic behavior and travel anomalies for claims and providers.
    """
    def extract(self, claims: List[Dict[str, Any]]) -> List[GeographicFeatures]:
        features_list = []
        
        provider_states = defaultdict(set)
        
        for claim in claims:
            provider_id = claim.get("provider_id")
            state = claim.get("service_location_state")
            if provider_id and state:
                provider_states[provider_id].add(state)
                
        for provider_id, states in provider_states.items():
            features_list.append(GeographicFeatures(
                entity_id=provider_id,
                entity_type="provider",
                features={
                    "unique_states_billed": float(len(states)),
                    "multi_state_biller_flag": 1.0 if len(states) > 1 else 0.0
                }
            ))
            
        return features_list
