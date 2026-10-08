/**
 * Service for Live Batch Ingest and Engine Reset.
 * Canonical Endpoints:
 * - POST /api/ingest/batch
 * - GET /api/ingest/{run_id}
 * - POST /api/ingest/reset
 */
import { BatchIngestRequest, IngestResetResponse, IngestRun } from '@/types/ingest';
import { isMockMode, liveApi } from './apiClient';
import { MOCK_INGEST_RUNS } from './mockData/ingest';

export async function startIngest(request: BatchIngestRequest = {}): Promise<IngestRun> {
  if (isMockMode()) {
    const runId = `RUN-${Date.now()}`;
    return {
      run_id: runId,
      status: 'completed',
      started_at: new Date().toISOString(),
      completed_at: new Date(Date.now() + 1500).toISOString(),
      claims_processed: request.claims_count || 5000,
      providers_evaluated: 150,
      alerts_generated: 18,
      cases_updated: 2,
      execution_time_ms: 1450,
    };
  }
  return liveApi.post<IngestRun>('/api/ingest/batch', request);
}

export async function getIngestRun(runId: string): Promise<IngestRun> {
  if (isMockMode()) {
    const found = MOCK_INGEST_RUNS[runId];
    if (found) {
      return found;
    }
    return {
      run_id: runId,
      status: 'completed',
      started_at: '2024-09-18T14:00:00Z',
      completed_at: '2024-09-18T14:00:30Z',
      claims_processed: 5000,
      providers_evaluated: 120,
      alerts_generated: 12,
      cases_updated: 2,
      execution_time_ms: 30000,
    };
  }
  return liveApi.get<IngestRun>(`/api/ingest/${runId}`);
}

export async function resetIngest(): Promise<IngestResetResponse> {
  if (isMockMode()) {
    return {
      success: true,
      message: 'Engine state and mock database tables reset to baseline synthetic state.',
      timestamp: new Date().toISOString(),
    };
  }
  return liveApi.post<IngestResetResponse>('/api/ingest/reset');
}
