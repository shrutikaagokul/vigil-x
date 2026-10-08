/**
 * Service for Entity Risk profiling.
 * Canonical Endpoint: GET /api/risk?entity_id=
 */
import { RiskResponse } from '@/types/api';
import { isMockMode, liveApi } from './apiClient';
import { MOCK_RISK_RESPONSES } from './mockData/risk';

interface BackendRiskScoreItem {
  readonly case_id?: string;
  readonly entity_type?: string;
  readonly entity_id: string;
  readonly entity_name?: string;
  readonly risk_score: number;
  readonly priority?: string;
  readonly confidence?: number;
  readonly evidence_strength?: number;
  readonly risk_components?: Record<string, number>;
  readonly future_risk?: Record<string, unknown>;
}

interface BackendRiskListResponse {
  readonly total: number;
  readonly scores: readonly BackendRiskScoreItem[];
  readonly as_of?: string;
  readonly synthetic?: boolean;
}

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

  const raw = await liveApi.get<BackendRiskListResponse | RiskResponse>('/api/risk', { entity_id: entityId });

  if ('risk_index' in raw) {
    return raw as RiskResponse;
  }

  const list = (raw as BackendRiskListResponse).scores || [];
  const found = list.find((s) => s.entity_id === entityId) || list[0];

  if (found) {
    const normalizedRisk = found.risk_score > 1.0 ? Math.round(found.risk_score) : Math.round(found.risk_score * 100);
    const priority = (found.priority || 'Medium').toLowerCase();
    const riskTier = priority.includes('crit') ? 'Critical' : priority.includes('high') ? 'High' : priority.includes('low') ? 'Low' : 'Medium';

    const components = found.risk_components || {};
    const primary_factors = Object.entries(components).map(([name, weight]) => ({
      name: name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      weight: Number(weight),
      score: Math.round(Number(weight) * 100),
      plain_text: `Signal contribution for ${name.replace(/_/g, ' ')}.`,
    }));

    return {
      entity_id: found.entity_id,
      entity_type: found.entity_type || 'provider',
      risk_index: normalizedRisk,
      horizon,
      risk_tier: riskTier,
      primary_factors: primary_factors.length > 0 ? primary_factors : [
        {
          name: 'Multi-Signal Risk Index',
          weight: 1.0,
          score: normalizedRisk,
          plain_text: 'Consolidated anomaly and billing risk signal.',
        },
      ],
      trend: 'stable',
      peer_group_percentile: Math.min(99, Math.max(1, normalizedRisk)),
      calculated_at: (raw as BackendRiskListResponse).as_of || new Date().toISOString(),
    };
  }

  return {
    entity_id: entityId,
    entity_type: 'provider',
    risk_index: 50,
    horizon,
    risk_tier: 'Medium',
    primary_factors: [],
    trend: 'stable',
    peer_group_percentile: 50.0,
    calculated_at: new Date().toISOString(),
  };
}
