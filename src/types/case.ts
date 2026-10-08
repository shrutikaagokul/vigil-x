/**
 * Case dossier, timeline, brief, interactive copilot, and human decision models.
 */
import { Severity } from './alert';

export type ConfidenceLevel = 'High' | 'Medium' | 'Low';

export type CaseStatus = 'open' | 'under_investigation' | 'decided' | 'escalated' | 'closed';

export type DecisionAction = 'accept' | 'reject' | 'needs_info' | 'escalate';

export interface ConflictingSignal {
  readonly title: string;
  readonly positive_indicator: string; // Mitigating signal
  readonly risk_indicator: string;     // Risk signal
  readonly explanation: string;
}

export interface CaseDecision {
  readonly decision_id: string;
  readonly case_id: string;
  readonly action: DecisionAction;
  readonly reason: string; // Mandatory human justification
  readonly decided_at: string;
  readonly decided_by: string;
  readonly notes?: string | null;
  readonly recommended_recovery_dollars?: number;
}

export interface Case {
  readonly id: string;
  readonly title: string;
  readonly focal_provider_id: string;
  readonly focal_provider_name: string;
  readonly specialty: string;
  readonly status: CaseStatus;
  readonly priority_score: number; // 0-100 deterministic prioritization
  readonly risk_index: number;     // 0-100 risk index
  readonly confidence: ConfidenceLevel;
  readonly severity: Severity;
  readonly est_dollars: number;    // Total financial exposure
  readonly est_overpay: number;    // Direct line-item overpayment
  readonly rules_triggered: readonly string[];
  readonly primary_indicator: string;
  readonly created_at: string;
  readonly updated_at: string;
  readonly sla_due_date: string;
  readonly assigned_investigator?: string | null;
  readonly conflicting_signals?: readonly ConflictingSignal[];
  readonly evidence_count: number;
  readonly claim_count: number;
  readonly network_id?: string | null;
  readonly decision?: CaseDecision | null;
}

export interface TimelineEvent {
  readonly event_id: string;
  readonly case_id: string;
  readonly timestamp: string;
  readonly service_date: string;
  readonly event_type:
    | 'claim_burst'
    | 'travel_anomaly'
    | 'referral_spike'
    | 'identity_linked'
    | 'service_overlap'
    | 'reciprocal_referral'
    | string;
  readonly description: string;
  readonly severity: Severity;
  readonly claim_ids: readonly string[];
  readonly provider_ids: readonly string[];
  readonly evidence_id?: string | null;
  readonly metrics?: Readonly<Record<string, unknown>>;
}

export interface CaseBrief {
  readonly case_id: string;
  readonly title: string;
  readonly summary: string;
  readonly key_findings: readonly string[];
  readonly recommended_actions: readonly string[];
  readonly evidence_citations: readonly string[];
  readonly estimated_financial_impact: number;
  readonly generated_at: string;
}

export interface AskRequest {
  readonly question: string;
}

export interface AskResponse {
  readonly case_id: string;
  readonly question: string;
  readonly answer: string;
  readonly evidence_citations: readonly string[];
  readonly confidence: ConfidenceLevel;
  readonly sources: readonly string[];
}

export interface DecisionRequest {
  readonly action: DecisionAction;
  readonly reason: string; // Mandatory human reason
  readonly notes?: string;
  readonly assigned_investigator?: string;
  readonly recommended_recovery_dollars?: number;
}

export interface DecisionResponse {
  readonly decision_id: string;
  readonly case_id: string;
  readonly action: DecisionAction;
  readonly reason: string;
  readonly decided_at: string;
  readonly decided_by: string;
  readonly notes?: string | null;
  readonly status: CaseStatus;
}
