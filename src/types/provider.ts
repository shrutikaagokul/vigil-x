/**
 * Provider models for ClaimShield Nexus.
 * Corresponds to schema.sql providers table and provider risk profiling.
 */

export interface Provider {
  readonly provider_id: string;
  readonly npi: string;
  readonly name: string;
  readonly specialty: string;
  readonly latitude: number;
  readonly longitude: number;
  readonly address: string;
  readonly suite?: string | null;
  readonly city: string;
  readonly state: string;
  readonly zip: string;
  readonly county: string;
  readonly facility_type: 'clinic' | 'hospital' | 'residential' | 'virtual_office' | string;
  readonly owner_name?: string | null;
  readonly owner_entity?: string | null;
  readonly registered_agent?: string | null;
  readonly bank_hash?: string | null;
  readonly tin_hash?: string | null;
  readonly group_id?: string | null;
  readonly enrolled_date: string;
  // Dynamic risk profiling metrics
  readonly risk_index?: number; // 0-100 scale
  readonly total_paid_30d?: number;
  readonly total_paid_90d?: number;
  readonly active_alert_count?: number;
  readonly peer_percentile?: number;
}
