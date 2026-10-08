/**
 * Investigation queue models, capacity-aware prioritization parameters,
 * and backend SIUQueueItem contract alignment.
 */
import { Severity } from './alert';
import { ConfidenceLevel } from './case';

export type QueueSortOption = 'priority' | 'risk' | 'exposure' | 'network_complexity' | 'sla';

export type SlaStatus = 'on_track' | 'warning' | 'breached';

export type SIUPriorityTier = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type SIUQueueStatus = 'QUEUED' | 'ASSIGNED' | 'IN_PROGRESS' | 'DEFERRED' | 'COMPLETED';

export interface QueueReasonItem {
  readonly text: string;
  readonly evidence_chip: string;
}

export interface QueueQueryParams {
  readonly general_hours?: number;
  readonly network_hours?: number;
  readonly horizon?: '30d' | '60d' | '90d' | string;
  readonly sort?: QueueSortOption | string;
  readonly severity?: Severity | string;
  readonly rule_id?: string;
  readonly search?: string;
}

/**
 * Direct TypeScript contract mapping to Python backend SIUQueueItem dataclass (siu/contracts.py).
 */
export interface BackendSIUQueueItem {
  readonly queue_id: string;
  readonly case_id: string;
  readonly provider_id: string;
  readonly rank: number;
  readonly priority_score: number;       // 0.0 - 1.0 normalized float
  readonly priority_tier: SIUPriorityTier | string;
  readonly risk_score: number;           // 0.0 - 1.0 normalized float
  readonly risk_tier: string;
  readonly evidence_strength: number;     // 0.0 - 1.0 normalized float
  readonly confidence_score: number;      // 0.0 - 1.0 normalized float
  readonly estimated_exposure: number;
  readonly network_signal: number;       // 0.0 - 1.0 normalized float
  readonly anomaly_signal: number;       // 0.0 - 1.0 normalized float
  readonly future_risk_signal: number;   // 0.0 - 1.0 normalized float
  readonly behavioral_signal: number;    // 0.0 - 1.0 normalized float
  readonly case_status: string;
  readonly queue_status: SIUQueueStatus | string;
  readonly capacity_selected: boolean;
  readonly capacity_rank: number;
  readonly priority_reasons: readonly string[];
  readonly claim_count?: number;
  readonly alert_count?: number;
  readonly evidence_count?: number;
  readonly community_id?: number | null;
  readonly created_at?: string;
  readonly queued_at?: string;
  readonly case_builder_version?: string;
  readonly siu_version?: string;
}

/**
 * Frontend presentation queue item with SIU multi-signal enrichment.
 */
export interface QueueItem {
  readonly case_id: string;
  readonly title: string;
  readonly name?: string;
  readonly subtitle?: string;
  readonly focal_provider_id: string;
  readonly focal_provider_name: string;
  readonly specialty: string;
  readonly priority_score: number; // 0-100 display scale, dynamic based on capacity & risk
  readonly risk_index: number;     // 0-100 display scale
  readonly severity: Severity;
  readonly confidence: ConfidenceLevel;
  readonly est_dollars: number;
  readonly est_overpay: number;
  readonly exposure_low: number;   // Sample USD low
  readonly exposure_high: number;  // Sample USD high
  readonly effort_hours: number;   // e.g. 31, 9, 9, 14
  readonly pool: 'network' | 'general';
  readonly baseline_rank: number;  // e.g. 38 for #38 -> #1
  readonly slot?: 'addressable' | 'deferred';
  readonly top_reasons: readonly QueueReasonItem[];
  readonly cost_of_delay_4w: number; // Sample USD cost of 4w delay
  readonly members_affected: number;
  readonly rules_triggered: readonly string[];
  readonly primary_indicator: string;
  readonly network_complexity_score: number; // 0-100
  readonly requires_network_specialist: boolean;
  readonly sla_status: SlaStatus;
  readonly sla_due_date: string;
  readonly assigned_to?: string | null;
  readonly _sample?: boolean;

  // Backend SIU fields
  readonly queue_id?: string;
  readonly priority_tier?: SIUPriorityTier | string;
  readonly risk_tier?: string;
  readonly queue_status?: SIUQueueStatus | string;
  readonly capacity_selected?: boolean;
  readonly capacity_rank?: number;
  readonly priority_reasons?: readonly string[];
  readonly evidence_strength?: number;
  readonly confidence_score?: number;
  readonly network_signal?: number;
  readonly anomaly_signal?: number;
  readonly future_risk_signal?: number;
  readonly behavioral_signal?: number;
  readonly community_id?: number | null;
}

export interface CapacitySummary {
  readonly general_hours: number;
  readonly network_hours: number;
  readonly total_hours: number;
  readonly estimated_cases_addressable: number;
  readonly network_backlog_hours: number;
}

export interface QueueResponse {
  readonly items: readonly QueueItem[];
  readonly total_count: number;
  readonly capacity_settings: {
    readonly general_hours: number;
    readonly network_hours: number;
    readonly horizon: string;
    readonly sort: string;
  };
  readonly capacity_summary: CapacitySummary;
}

