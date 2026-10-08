/**
 * Core Alert and Evidence types for ClaimShield Nexus / Vigil-X.
 * Directly maps to Python backend contracts/alert.py dataclasses.
 */

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type EntityType = 'provider' | 'member' | 'facility';

/**
 * A single piece of evidence supporting an alert.
 * Every metric displayed in the UI must be traceable back to an Evidence record.
 */
export interface Evidence {
  readonly evidence_id: string;
  readonly rule_id: string;
  readonly rule_version: string;
  readonly claim_ids: readonly string[];
  readonly fields_matched: readonly string[];
  readonly plain_text: string;
  readonly est_overpay: number;
  readonly severity: Severity;
  readonly fp_notes?: string | null;
}

/**
 * A single FWA alert produced by a detection rule.
 * The system does NOT declare fraud. It identifies suspicious indicators,
 * produces evidence-backed alerts, and prioritizes them for human review.
 */
export interface Alert {
  readonly alert_id: string;
  readonly rule_id: string;
  readonly rule_version: string;
  readonly entity_type: EntityType | string;
  readonly entity_id: string;
  readonly claim_ids: readonly string[];
  readonly severity: Severity;
  readonly est_dollars: number;
  readonly evidence: readonly Evidence[];
  readonly fp_notes?: string | null;
  readonly metadata?: Readonly<Record<string, unknown>>;
}
