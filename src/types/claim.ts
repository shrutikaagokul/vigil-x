/**
 * Claim and Claim Line models for ClaimShield Nexus.
 * Corresponds to schema.sql claims and claim_lines tables.
 */

export interface ClaimLine {
  readonly line_id: string;
  readonly claim_id: string;
  readonly line_number: number;
  readonly procedure_code: string;
  readonly modifier?: string | null;
  readonly units: number;
  readonly paid_amount: number;
  readonly billed_amount: number;
  readonly ndc_code?: string | null;
}

export interface Claim {
  readonly claim_id: string;
  readonly member_id: string;
  readonly provider_id: string;
  readonly facility_id?: string | null;
  readonly referring_provider_id?: string | null;
  readonly service_date: string; // YYYY-MM-DD
  readonly service_start_ts?: string | null; // YYYY-MM-DD HH:MM:SS
  readonly service_end_ts?: string | null;
  readonly service_minutes?: number | null;
  readonly pos_code: string; // Place of Service code
  readonly procedure_code: string;
  readonly diagnosis_code: string;
  readonly paid_amount: number;
  readonly billed_amount: number;
  readonly allowed_amount: number;
  readonly status: 'paid' | 'denied' | 'pending' | string;
  readonly claim_type: 'professional' | 'institutional' | 'pharmacy' | string;
  readonly lines?: readonly ClaimLine[];
  readonly flags?: readonly string[]; // Indicator tags (e.g., 'impossible_travel', 'burst_surge')
}
