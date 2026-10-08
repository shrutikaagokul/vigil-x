/**
 * Service for Provider profile lookups.
 * Canonical Endpoint: GET /api/providers/{id}
 */
import { Provider } from '@/types/provider';
import { ApiError, isMockMode, liveApi } from './apiClient';
import { MOCK_PROVIDERS } from './mockData/providers';

export async function getProvider(providerId: string): Promise<Provider> {
  if (isMockMode()) {
    const found = MOCK_PROVIDERS.find((p) => p.provider_id === providerId || p.npi === providerId);
    if (!found) {
      throw new ApiError(`Provider not found: ${providerId}`, 404, `/api/providers/${providerId}`);
    }
    return found;
  }
  return liveApi.get<Provider>(`/api/providers/${providerId}`);
}
