/**
 * Service for Claim record lookups.
 * Canonical Endpoint: GET /api/claims/{claim_id}
 */
import { Claim } from '@/types/claim';
import { ApiError, isMockMode, liveApi } from './apiClient';
import { MOCK_CLAIMS } from './mockData/claims';

export async function getClaim(claimId: string): Promise<Claim> {
  if (isMockMode()) {
    const found = MOCK_CLAIMS.find((c) => c.claim_id === claimId);
    if (!found) {
      throw new ApiError(`Claim not found: ${claimId}`, 404, `/api/claims/${claimId}`);
    }
    return found;
  }
  return liveApi.get<Claim>(`/api/claims/${claimId}`);
}
