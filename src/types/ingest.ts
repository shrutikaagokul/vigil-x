/**
 * Live ingest and simulation batch models.
 */

export type IngestStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface BatchIngestRequest {
  readonly batch_id?: string;
  readonly claims_count?: number;
  readonly scenario_inject?: string;
  readonly dry_run?: boolean;
}

export interface IngestRun {
  readonly run_id: string;
  readonly status: IngestStatus;
  readonly started_at: string;
  readonly completed_at?: string | null;
  readonly claims_processed: number;
  readonly providers_evaluated: number;
  readonly alerts_generated: number;
  readonly cases_updated: number;
  readonly execution_time_ms: number;
  readonly errors?: readonly string[];
}

export interface IngestResetResponse {
  readonly success: boolean;
  readonly message: string;
  readonly timestamp: string;
}
