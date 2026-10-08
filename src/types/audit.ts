/**
 * Audit trail models for human investigator governance and system logging.
 */

export interface AuditEntry {
  readonly audit_id: string;
  readonly timestamp: string;
  readonly actor: string; // e.g., 'SIU Investigator #104', 'System Engine'
  readonly action: string; // e.g., 'case_prioritized', 'decision_recorded', 'brief_generated'
  readonly entity_type: 'case' | 'provider' | 'claim' | 'ingest' | string;
  readonly entity_id: string;
  readonly details: string;
  readonly reason?: string | null;
  readonly prev_state?: string | null;
  readonly new_state?: string | null;
  readonly metadata?: Readonly<Record<string, unknown>>;
}
