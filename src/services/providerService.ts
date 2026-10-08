/**
 * Service for Provider profile lookups.
 * Canonical Endpoint: GET /api/providers/{id}
 */
import { Provider } from '@/types/provider';
import { ApiError, isMockMode, liveApi } from './apiClient';
import { MOCK_PROVIDERS } from './mockData/providers';

interface BackendProviderRecord {
  readonly provider_id: string;
  readonly npi?: string;
  readonly first_name?: string;
  readonly last_name?: string;
  readonly specialty?: string;
  readonly practice_name?: string;
  readonly street_address?: string;
  readonly city?: string;
  readonly state?: string;
  readonly zip_code?: string;
  readonly county?: string;
  readonly phone?: string;
  readonly is_excluded?: boolean;
}

export async function getProvider(providerId: string): Promise<Provider> {
  if (isMockMode()) {
    const found = MOCK_PROVIDERS.find((p) => p.provider_id === providerId || p.npi === providerId);
    if (!found) {
      throw new ApiError(`Provider not found: ${providerId}`, 404, `/api/providers/${providerId}`);
    }
    return found;
  }

  const raw = await liveApi.get<BackendProviderRecord | Provider>(`/api/providers/${providerId}`);

  if ('name' in raw && 'latitude' in raw) {
    return raw as Provider;
  }

  const bp = raw as BackendProviderRecord;
  const name =
    bp.practice_name ||
    (bp.first_name && bp.last_name ? `Dr. ${bp.first_name} ${bp.last_name}` : `Provider ${bp.provider_id}`);

  return {
    provider_id: bp.provider_id,
    npi: bp.npi || '1928374650',
    name,
    specialty: bp.specialty || 'Specialist',
    latitude: 33.749,
    longitude: -84.388,
    address: bp.street_address || '100 Medical Center Dr',
    city: bp.city || 'Atlanta',
    state: bp.state || 'GA',
    zip: bp.zip_code || '30303',
    county: bp.county || 'Fulton',
    facility_type: 'clinic',
    enrolled_date: '2020-01-15',
    risk_index: 75,
  };
}
