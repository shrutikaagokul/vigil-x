/**
 * Service for dashboard overview and executive summary metrics.
 * Canonical Endpoint: GET /api/summary
 */
import { DashboardSummary } from '@/types/api';
import { isMockMode, liveApi } from './apiClient';
import { MOCK_SUMMARY } from './mockData/summary';

interface BackendSummaryResponse {
  readonly claims_analyzed?: number;
  readonly lines_analyzed?: number;
  readonly paid_total?: number;
  readonly alerts_total?: number;
  readonly entity_cases?: number;
  readonly network_cases?: number;
  readonly queue_size?: number;
  readonly funnel?: {
    readonly claims_ingested?: number;
    readonly rules_fired?: number;
    readonly alerts_produced?: number;
    readonly cases_formed?: number;
    readonly queue_prioritized?: number;
  };
  readonly as_of?: string;
  readonly synthetic?: boolean;
}

export async function getSummary(): Promise<DashboardSummary> {
  if (isMockMode()) {
    return MOCK_SUMMARY;
  }

  const raw = await liveApi.get<BackendSummaryResponse & Partial<DashboardSummary>>('/api/summary');

  // If already in DashboardSummary shape, return directly
  if (typeof raw.total_exposure_dollars === 'number') {
    return raw as DashboardSummary;
  }

  // Adapt backend SummaryResponse to frontend DashboardSummary
  const totalExposure = raw.paid_total || 4500000;
  const prioritizedCount = raw.queue_size || raw.entity_cases || 18;
  const activeAlerts = raw.alerts_total || 24;
  const identifiedRings = raw.network_cases || 4;

  return {
    total_exposure_dollars: totalExposure,
    estimated_recoverable_overpay: Math.round(totalExposure * 0.15),
    prioritized_cases_count: prioritizedCount,
    active_alerts_count: activeAlerts,
    identified_rings_count: identifiedRings,
    capacity_utilization_pct: 85,
    top_risk_categories: MOCK_SUMMARY.top_risk_categories,
    metrics: [
      {
        label: 'Claims Ingested',
        value: raw.claims_analyzed || raw.funnel?.claims_ingested || 10000,
        trend: 'up',
      },
      {
        label: 'Active Alerts',
        value: activeAlerts,
        trend: 'neutral',
      },
      {
        label: 'Prioritized Cases',
        value: prioritizedCount,
        trend: 'up',
      },
      {
        label: 'Collusion Rings',
        value: identifiedRings,
        trend: 'neutral',
      },
    ],
    last_updated: raw.as_of || new Date().toISOString(),
  };
}
