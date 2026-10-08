/**
 * Service for System Diagnostics and Health Checks.
 * Canonical Endpoint: GET /api/health
 */
import { HealthResponse } from '@/types/api';
import { isMockMode, liveApi } from './apiClient';
import { MOCK_HEALTH } from './mockData/health';

export async function getHealth(): Promise<HealthResponse> {
  if (isMockMode()) {
    return MOCK_HEALTH;
  }
  return liveApi.get<HealthResponse>('/api/health');
}
