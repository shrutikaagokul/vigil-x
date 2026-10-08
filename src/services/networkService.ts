/**
 * Service for Network graph retrieval and community inspection.
 * Canonical Endpoint: GET /api/networks/{id}
 */
import { Network } from '@/types/network';
import { ApiError, isMockMode, liveApi } from './apiClient';
import { MOCK_NETWORKS } from './mockData/networks';

export async function getNetwork(networkId: string): Promise<Network> {
  if (isMockMode()) {
    const found = MOCK_NETWORKS.find((n) => n.network_id === networkId || n.focal_entity === networkId);
    if (!found) {
      throw new ApiError(`Network not found: ${networkId}`, 404, `/api/networks/${networkId}`);
    }
    return found;
  }
  return liveApi.get<Network>(`/api/networks/${networkId}`);
}
