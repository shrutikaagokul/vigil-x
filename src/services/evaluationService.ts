/**
 * Service for Ground Truth Evaluation & Benchmarking metrics.
 * Canonical Endpoint: GET /api/evaluation
 */
import { EvaluationSummary } from '@/types/eval';
import { isMockMode, liveApi } from './apiClient';
import { MOCK_EVALUATION_SUMMARY } from './mockData/evaluation';

export async function getEvaluation(): Promise<EvaluationSummary> {
  if (isMockMode()) {
    return MOCK_EVALUATION_SUMMARY;
  }
  return liveApi.get<EvaluationSummary>('/api/evaluation');
}
