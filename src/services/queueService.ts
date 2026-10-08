/**
 * Service for investigation queue triage, capacity-aware prioritization,
 * and backend SIUQueueItem adaptation.
 * Canonical Endpoint: GET /api/queue?capacity_hours=&horizon=&sort=
 */
import {
  BackendSIUQueueItem,
  QueueItem,
  QueueQueryParams,
  QueueReasonItem,
  QueueResponse,
  SIUPriorityTier,
  SIUQueueStatus,
} from '@/types/queue';
import { Severity } from '@/types/alert';
import { ConfidenceLevel } from '@/types/case';
import { isMockMode, liveApi } from './apiClient';
import { calculateMockQueue } from './mockData/queue';

interface BackendQueueItem {
  readonly case_id: string;
  readonly rank: number;
  readonly baseline_rank?: number | null;
  readonly entity_type: string;
  readonly entity_id: string;
  readonly entity_name: string;
  readonly risk: number;
  readonly priority: string;
  readonly exposure_low: number;
  readonly exposure_high: number;
  readonly members_affected: number;
  readonly severity: string;
  readonly evidence_strength: number;
  readonly confidence: number;
  readonly effort_hours: number;
  readonly ev_per_hour: number;
  readonly slot: number;
  readonly top_reasons: readonly string[];
}

interface BackendQueueResponse {
  readonly total_cases: number;
  readonly capacity_hours: number;
  readonly horizon_days: number;
  readonly sort_applied: string;
  readonly items: readonly (BackendQueueItem | QueueItem | BackendSIUQueueItem)[];
  readonly as_of?: string;
  readonly synthetic?: boolean;
}

/**
 * Adapts a backend SIUQueueItem (0.0-1.0 float scores, priority_reasons, capacity fields)
 * into a frontend QueueItem presentation model (0-100 display integer scale).
 */
export function adaptSIUQueueItemToQueueItem(
  siuItem: BackendSIUQueueItem,
  fallbackMeta?: Partial<QueueItem>,
): QueueItem {
  // Normalize 0.0-1.0 float scores into 0-100 integer display scale
  const normalizedPriority =
    siuItem.priority_score <= 1.0
      ? Math.round(siuItem.priority_score * 100)
      : Math.round(siuItem.priority_score);

  const normalizedRisk =
    siuItem.risk_score <= 1.0
      ? Math.round(siuItem.risk_score * 100)
      : Math.round(siuItem.risk_score);

  const severityMap: Record<string, Severity> = {
    CRITICAL: 'CRITICAL',
    HIGH: 'HIGH',
    MEDIUM: 'MEDIUM',
    LOW: 'LOW',
  };

  const severity: Severity =
    severityMap[siuItem.priority_tier?.toUpperCase()] ||
    severityMap[siuItem.risk_tier?.toUpperCase()] ||
    fallbackMeta?.severity ||
    'MEDIUM';

  const confidence: ConfidenceLevel =
    siuItem.confidence_score >= 0.75
      ? 'High'
      : siuItem.confidence_score >= 0.45
      ? 'Medium'
      : 'Low';

  const top_reasons: readonly QueueReasonItem[] =
    siuItem.priority_reasons && siuItem.priority_reasons.length > 0
      ? siuItem.priority_reasons.map((r, idx) => ({
          text: r,
          evidence_chip: `E${idx + 1}`,
        }))
      : fallbackMeta?.top_reasons || [];

  return {
    case_id: siuItem.case_id,
    title: fallbackMeta?.title || `Investigation Case ${siuItem.case_id}`,
    name: fallbackMeta?.name || `Provider ${siuItem.provider_id}`,
    subtitle: fallbackMeta?.subtitle || `${siuItem.provider_id} · ${siuItem.queue_status}`,
    focal_provider_id: siuItem.provider_id,
    focal_provider_name: fallbackMeta?.focal_provider_name || `Provider ${siuItem.provider_id}`,
    specialty: fallbackMeta?.specialty || 'specialist',
    priority_score: normalizedPriority,
    risk_index: normalizedRisk,
    severity,
    confidence,
    est_dollars: siuItem.estimated_exposure || fallbackMeta?.est_dollars || 0,
    est_overpay: fallbackMeta?.est_overpay || Math.round((siuItem.estimated_exposure || 0) * 0.3),
    exposure_low: fallbackMeta?.exposure_low || Math.round((siuItem.estimated_exposure || 0) * 0.8),
    exposure_high: fallbackMeta?.exposure_high || Math.round((siuItem.estimated_exposure || 0) * 1.5),
    effort_hours: fallbackMeta?.effort_hours || 10,
    pool: (siuItem.network_signal && siuItem.network_signal > 0.5) ? 'network' : (fallbackMeta?.pool || 'general'),
    baseline_rank: siuItem.rank || fallbackMeta?.baseline_rank || 1,
    slot: siuItem.capacity_selected ? 'addressable' : (fallbackMeta?.slot || 'deferred'),
    top_reasons,
    cost_of_delay_4w: fallbackMeta?.cost_of_delay_4w || Math.round((siuItem.estimated_exposure || 0) * 0.15),
    members_affected: siuItem.claim_count || fallbackMeta?.members_affected || 42,
    rules_triggered: fallbackMeta?.rules_triggered || ['R06', 'R07'],
    primary_indicator:
      siuItem.priority_reasons?.[0] ||
      fallbackMeta?.primary_indicator ||
      'Multi-signal anomaly prioritized for SIU review',
    network_complexity_score: Math.round((siuItem.network_signal || 0) * 100),
    requires_network_specialist: (siuItem.network_signal || 0) > 0.6,
    sla_status: fallbackMeta?.sla_status || 'on_track',
    sla_due_date: fallbackMeta?.sla_due_date || new Date(Date.now() + 14 * 86400000).toISOString(),
    assigned_to: fallbackMeta?.assigned_to || null,

    // Backend SIU fields
    queue_id: siuItem.queue_id,
    priority_tier: siuItem.priority_tier as SIUPriorityTier,
    risk_tier: siuItem.risk_tier,
    queue_status: siuItem.queue_status as SIUQueueStatus,
    capacity_selected: siuItem.capacity_selected,
    capacity_rank: siuItem.capacity_rank,
    priority_reasons: siuItem.priority_reasons,
    evidence_strength: siuItem.evidence_strength,
    confidence_score: siuItem.confidence_score,
    network_signal: siuItem.network_signal,
    anomaly_signal: siuItem.anomaly_signal,
    future_risk_signal: siuItem.future_risk_signal,
    behavioral_signal: siuItem.behavioral_signal,
    community_id: siuItem.community_id,
  };
}

function adaptBackendQueueItem(item: BackendQueueItem): QueueItem {
  const normalizedRisk = item.risk > 1.0 ? Math.round(item.risk) : Math.round(item.risk * 100);
  const normalizedPriority = normalizedRisk;

  const severityMap: Record<string, Severity> = {
    CRITICAL: 'CRITICAL',
    HIGH: 'HIGH',
    MEDIUM: 'MEDIUM',
    LOW: 'LOW',
  };

  const severity: Severity = severityMap[item.severity?.toUpperCase()] || severityMap[item.priority?.toUpperCase()] || 'MEDIUM';

  const confidence: ConfidenceLevel =
    item.confidence >= 0.75 ? 'High' : item.confidence >= 0.45 ? 'Medium' : 'Low';

  const top_reasons: readonly QueueReasonItem[] = (item.top_reasons || []).map((r, idx) => ({
    text: r,
    evidence_chip: `E${idx + 1}`,
  }));

  return {
    case_id: item.case_id,
    title: item.entity_name ? `${item.entity_name} Case` : `Case ${item.case_id}`,
    name: item.entity_name || `Provider ${item.entity_id}`,
    subtitle: `${item.entity_id} · ${item.entity_type}`,
    focal_provider_id: item.entity_id,
    focal_provider_name: item.entity_name,
    specialty: 'specialist',
    priority_score: normalizedPriority,
    risk_index: normalizedRisk,
    severity,
    confidence,
    est_dollars: item.exposure_high || item.exposure_low || 0,
    est_overpay: Math.round((item.exposure_high || 0) * 0.35),
    exposure_low: item.exposure_low || 0,
    exposure_high: item.exposure_high || 0,
    effort_hours: item.effort_hours || 10,
    pool: 'general',
    baseline_rank: item.baseline_rank ?? item.rank,
    slot: item.slot <= 3 ? 'addressable' : 'deferred',
    top_reasons,
    cost_of_delay_4w: Math.round((item.exposure_high || 0) * 0.12),
    members_affected: item.members_affected || 1,
    rules_triggered: ['R01', 'R02'],
    primary_indicator: item.top_reasons?.[0] || 'Prioritized for SIU investigation',
    network_complexity_score: 50,
    requires_network_specialist: false,
    sla_status: 'on_track',
    sla_due_date: new Date(Date.now() + 14 * 86400000).toISOString(),
    assigned_to: null,
  };
}

export async function getQueue(params: QueueQueryParams = {}): Promise<QueueResponse> {
  if (isMockMode()) {
    return calculateMockQueue(params);
  }

  const totalCapacityHours = (params.general_hours ?? 40) + (params.network_hours ?? 20);
  const horizonDays = params.horizon === '90d' ? 90 : params.horizon === '14d' ? 14 : 30;
  const sortOption = params.sort === 'expected_value' ? 'ev_per_hour' : params.sort === 'risk' ? 'risk' : 'priority';

  const response = await liveApi.get<BackendQueueResponse & Partial<QueueResponse>>('/api/queue', {
    capacity_hours: totalCapacityHours,
    horizon: horizonDays,
    sort: sortOption,
  });

  // Adapt any raw backend items received
  const items: readonly QueueItem[] = (response.items || []).map((item) => {
    if ('priority_score' in item && typeof (item as BackendSIUQueueItem).priority_score === 'number' && (item as BackendSIUQueueItem).priority_score <= 1.0) {
      return adaptSIUQueueItemToQueueItem(item as BackendSIUQueueItem);
    }
    if ('entity_id' in item && 'risk' in item) {
      return adaptBackendQueueItem(item as BackendQueueItem);
    }
    return item as QueueItem;
  });

  const totalCount = response.total_cases ?? response.total_count ?? items.length;

  return {
    items,
    total_count: totalCount,
    capacity_settings: response.capacity_settings ?? {
      general_hours: params.general_hours ?? 40,
      network_hours: params.network_hours ?? 20,
      horizon: params.horizon ?? '30d',
      sort: params.sort ?? 'priority',
    },
    capacity_summary: response.capacity_summary ?? {
      general_hours: params.general_hours ?? 40,
      network_hours: params.network_hours ?? 20,
      total_hours: totalCapacityHours,
      estimated_cases_addressable: items.filter((i) => i.slot === 'addressable').length || Math.min(items.length, 3),
      network_backlog_hours: 40,
    },
  };
}
