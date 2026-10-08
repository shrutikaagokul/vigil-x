/**
 * Mock Ingest fixtures.
 */
import { IngestRun } from '@/types/ingest';

export const MOCK_INGEST_RUNS: Record<string, IngestRun> = {
  'RUN-2024-0918-01': {
    run_id: 'RUN-2024-0918-01',
    status: 'completed',
    started_at: '2024-09-18T14:15:00Z',
    completed_at: '2024-09-18T14:15:42Z',
    claims_processed: 12500,
    providers_evaluated: 320,
    alerts_generated: 42,
    cases_updated: 5,
    execution_time_ms: 42350,
  },
};
