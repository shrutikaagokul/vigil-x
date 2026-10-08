/**
 * Service for dashboard overview and executive summary metrics.
 * Canonical Endpoint: GET /api/summary
 */
import { DashboardSummary } from '@/types/api';
import { isMockMode, liveApi } from './apiClient';
import { MOCK_SUMMARY } from './mockData/summary';

export async function getSummary(): Promise<DashboardSummary> {
  if (isMockMode()) {
    return MOCK_SUMMARY;
  }
  return liveApi.get<DashboardSummary>('/api/summary');
}
