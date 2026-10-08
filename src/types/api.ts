/**
 * Summary, Risk, Health, and generic API types.
 */

export interface DashboardMetric {
  readonly label: string;
  readonly value: number | string;
  readonly delta?: string;
  readonly trend?: 'up' | 'down' | 'neutral';
  readonly subtitle?: string;
}

export interface RiskCategoryBreakdown {
  readonly category: string; // e.g. 'Impossible Timing', 'Referral Loop', 'Identity Ring'
  readonly rule_id: string;
  readonly count: number;
  readonly exposure_dollars: number;
}

export interface DashboardSummary {
  readonly total_exposure_dollars: number;
  readonly estimated_recoverable_overpay: number;
  readonly prioritized_cases_count: number;
  readonly active_alerts_count: number;
  readonly identified_rings_count: number;
  readonly capacity_utilization_pct: number;
  readonly top_risk_categories: readonly RiskCategoryBreakdown[];
  readonly metrics: readonly DashboardMetric[];
  readonly last_updated: string;
}

export interface RiskFactor {
  readonly name: string;
  readonly rule_id?: string;
  readonly weight: number; // 0.0 - 1.0
  readonly score: number;  // 0 - 100
  readonly plain_text: string;
}

export interface RiskResponse {
  readonly entity_id: string;
  readonly entity_type: string;
  readonly risk_index: number; // 0-100
  readonly horizon: string;
  readonly risk_tier: 'Low' | 'Medium' | 'High' | 'Critical';
  readonly primary_factors: readonly RiskFactor[];
  readonly trend: 'increasing' | 'stable' | 'decreasing';
  readonly peer_group_percentile: number;
  readonly calculated_at: string;
}

export interface HealthResponse {
  readonly status: 'healthy' | 'degraded' | 'unhealthy';
  readonly version: string;
  readonly database: string;
  readonly engine: string;
  readonly memory_usage_mb?: number;
  readonly uptime_seconds: number;
  readonly timestamp: string;
}

export interface ApiErrorResponse {
  readonly error: string;
  readonly message: string;
  readonly status_code: number;
  readonly details?: unknown;
}
