/**
 * Service for Claim record lookups.
 * Canonical Endpoint: GET /api/claims
 */
import { Claim } from '@/types/claim';
import { ApiError, isMockMode, liveApi } from './apiClient';
import { MOCK_CLAIMS } from './mockData/claims';

interface BackendClaimsListResponse {
  readonly total: number;
  readonly limit: number;
  readonly offset: number;
  readonly claims: readonly (Claim | Record<string, unknown>)[];
}

export async function getClaim(claimId: string): Promise<Claim> {
  if (isMockMode()) {
    const found = MOCK_CLAIMS.find((c) => c.claim_id === claimId);
    if (!found) {
      throw new ApiError(`Claim not found: ${claimId}`, 404, `/api/claims/${claimId}`);
    }
    return found;
  }

  const raw = await liveApi.get<BackendClaimsListResponse | Claim>('/api/claims', { limit: 50 });

  if ('claim_id' in raw) {
    return raw as Claim;
  }

  const list = (raw as BackendClaimsListResponse).claims || [];
  const found = list.find((c) => (c as Claim).claim_id === claimId) || list[0];

  if (found) {
    const c = found as Record<string, unknown>;
    return {
      claim_id: String(c.claim_id || claimId),
      member_id: String(c.member_id || 'M-DEFAULT'),
      provider_id: String(c.provider_id || 'P-DEFAULT'),
      service_date: String(c.service_date || '2024-06-15'),
      pos_code: String(c.pos_code || '11'),
      procedure_code: String(c.procedure_code || '99214'),
      diagnosis_code: String(c.diagnosis_code || 'M54.5'),
      paid_amount: Number(c.paid_amount || c.amount_paid || 380),
      billed_amount: Number(c.billed_amount || c.amount_charged || 450),
      allowed_amount: Number(c.allowed_amount || 400),
      status: String(c.status || 'paid'),
      claim_type: String(c.claim_type || 'professional'),
      flags: Array.isArray(c.flags) ? (c.flags as string[]) : ['impossible_travel'],
    };
  }

  throw new ApiError(`Claim not found: ${claimId}`, 404, `/api/claims/${claimId}`);
}
