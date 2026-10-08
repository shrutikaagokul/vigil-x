/**
 * Service for Entity Risk profiling.
 * Canonical Endpoint: GET /api/risk/{entity_id}?horizon=
 */
import { RiskResponse } from '@/types/api';
import { isMockMode, liveApi } from './apiClient';
import { MOCK_RISK_RESPONSES } from './mockData/risk';

export async function getRisk(entityId: string, horizon: string = '30d'): Promise<RiskResponse> {
  if (isMockMode()) {
    const found = MOCK_RISK_RESPONSES[entityId];
    if (found) {
      return { ...found, horizon };
    }

    // Default risk response for entities without explicit detailed risk breakdown
    return {
      entity_id: entityId,
      entity_type: 'provider',
      risk_index: 50,
      horizon,
      risk_tier: 'Medium',
      primary_factors: [
        {
          name: 'Baseline Operational Volume',
          weight: 1.0,
          score: 50,
          plain_text: 'Provider shows volume within normal parameters; insufficient evidence of anomalous behavior.',
        },
      ],
      trend: 'stable',
      peer_group_percentile: 50.0,
      calculated_at: new Date().toISOString(),
    };
  }

  return liveApi.get<RiskResponse>(`/api/risk/${entityId}`, { horizon });
}
