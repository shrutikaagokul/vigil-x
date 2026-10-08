/**
 * Service for investigation queue triage and capacity-aware prioritization.
 * Canonical Endpoint: GET /api/queue?general_hours=&network_hours=&horizon=&sort=
 */
import { QueueQueryParams, QueueResponse } from '@/types/queue';
import { isMockMode, liveApi } from './apiClient';
import { calculateMockQueue } from './mockData/queue';

export async function getQueue(params: QueueQueryParams = {}): Promise<QueueResponse> {
  if (isMockMode()) {
    return calculateMockQueue(params);
  }

  return liveApi.get<QueueResponse>('/api/queue', {
    general_hours: params.general_hours,
    network_hours: params.network_hours,
    horizon: params.horizon,
    sort: params.sort,
    severity: params.severity,
    rule_id: params.rule_id,
    search: params.search,
  });
}
