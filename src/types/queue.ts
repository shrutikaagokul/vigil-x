/**
 * Investigation queue models and capacity-aware prioritization parameters.
 */
import { Severity } from './alert';
import { ConfidenceLevel } from './case';

export type QueueSortOption = 'priority' | 'risk' | 'exposure' | 'network_complexity' | 'sla';

export type SlaStatus = 'on_track' | 'warning' | 'breached';

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

export interface QueueItem {
  readonly case_id: string;
  readonly title: string;
  readonly name?: string;
  readonly subtitle?: string;
  readonly focal_provider_id: string;
  readonly focal_provider_name: string;
  readonly specialty: string;
  readonly priority_score: number; // 0-100, dynamic based on capacity & risk
  readonly risk_index: number;     // 0-100
  readonly severity: Severity;
  readonly confidence: ConfidenceLevel;
  readonly est_dollars: number;
  readonly est_overpay: number;
  readonly exposure_low: number;   // Sample INR low
  readonly exposure_high: number;  // Sample INR high
  readonly effort_hours: number;   // e.g. 31, 9, 9, 14
  readonly pool: 'network' | 'general';
  readonly baseline_rank: number;  // e.g. 38 for #38 -> #1
  readonly slot?: 'addressable' | 'deferred';
  readonly top_reasons: readonly QueueReasonItem[];
  readonly cost_of_delay_4w: number; // Sample INR cost of 4w delay
  readonly members_affected: number;
  readonly rules_triggered: readonly string[];
  readonly primary_indicator: string;
  readonly network_complexity_score: number; // 0-100
  readonly requires_network_specialist: boolean;
  readonly sla_status: SlaStatus;
  readonly sla_due_date: string;
  readonly assigned_to?: string | null;
  readonly _sample?: boolean;
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

