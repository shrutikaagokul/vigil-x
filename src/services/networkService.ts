/**
 * Service for Network graph retrieval and community inspection.
 * Canonical Endpoint: GET /api/networks/{id}
 */
import { Network } from '@/types/network';
import { ApiError, isMockMode, liveApi } from './apiClient';
import { MOCK_NETWORKS } from './mockData/networks';

interface BackendNetworkRecord {
  readonly network_id: string;
  readonly community_id?: number;
  readonly n_providers?: number;
  readonly hub_provider_id?: string;
  readonly hard_link_score?: number;
  readonly referral_score?: number;
  readonly concentration_score?: number;
  readonly ownership_score?: number;
  readonly suspicious_claims?: number;
  readonly total_claims?: number;
  readonly total_exposure?: number;
  readonly name?: string;
  readonly entity_type?: string;
  readonly risk_score?: number;
  readonly members_count?: number;
  readonly providers_count?: number;
  readonly exposure_est?: number;
  readonly nodes_json?: string;
  readonly edges_json?: string;
  readonly density?: number;
  readonly modularity?: number;
}

export async function getNetwork(networkId: string): Promise<Network> {
  if (isMockMode()) {
    const found = MOCK_NETWORKS.find((n) => n.network_id === networkId || n.focal_entity === networkId);
    if (!found) {
      throw new ApiError(`Network not found: ${networkId}`, 404, `/api/networks/${networkId}`);
    }
    return found;
  }

  const raw = await liveApi.get<BackendNetworkRecord & Partial<Network>>(`/api/networks/${networkId}`);

  // If already structured as Network
  if (Array.isArray(raw.nodes) && Array.isArray(raw.edges) && raw.nodes.length > 0) {
    return raw as Network;
  }

  // Parse nodes_json and edges_json if returned as raw database record
  let nodes: Network['nodes'] = [];
  let edges: Network['edges'] = [];

  try {
    if (typeof raw.nodes_json === 'string') {
      nodes = JSON.parse(raw.nodes_json);
    }
    if (typeof raw.edges_json === 'string') {
      edges = JSON.parse(raw.edges_json);
    }
  } catch {
    // Fallback if parsing fails
  }

  // If nodes are still empty, try to fetch case subgraph for the hub provider
  if (nodes.length === 0 && raw.hub_provider_id) {
    try {
      const hubCaseNetwork = await liveApi.get<{ subgraph?: Partial<Network> }>(
        `/api/cases/CASE-PRV-${raw.hub_provider_id}/network`,
      );
      if (hubCaseNetwork?.subgraph) {
        const sg = hubCaseNetwork.subgraph;
        nodes = ((sg.nodes || []) as readonly unknown[]).map((n: any) => ({
          ...n,
          id: String(n.id),
          node_type: (n.node_type || n.type || 'provider') as any,
          label: String(n.label || n.name || n.id),
          is_focal: Boolean(n.is_focal || n.id === raw.hub_provider_id),
        }));
        edges = ((sg.edges || []) as readonly unknown[]).map((e: any) => ({
          ...e,
          source: String(e.source),
          target: String(e.target),
          edge_type: String(e.edge_type || 'referral') as any,
          weight: typeof e.weight === 'number' ? e.weight : 1,
          evidence_ids: Array.isArray(e.evidence_ids) ? (e.evidence_ids as string[]) : [],
        }));
      }
    } catch {
      // Keep minimal fallback if case network fetch fails
    }
  }

  if (nodes.length === 0) {
    nodes = [
      {
        id: raw.hub_provider_id || networkId,
        node_type: 'provider',
        label: raw.hub_provider_id || networkId,
        name: raw.name || raw.hub_provider_id || networkId,
        is_focal: true,
      },
    ];
  }

  return {
    network_id: raw.network_id,
    focal_entity: raw.hub_provider_id || networkId,
    nodes,
    edges,
    cohorts: [],
    summary: {
      n_nodes: nodes.length || raw.n_providers || raw.providers_count || 1,
      n_edges: edges.length || 0,
      n_cohorts: 1,
      total_members: raw.total_claims || raw.members_count || 0,
      hub_provider_id: raw.hub_provider_id || networkId,
      hard_link_score: raw.hard_link_score,
      referral_loop_count: raw.suspicious_claims,
    },
    metrics: {
      hard_link_score: raw.hard_link_score,
      referral_score: raw.referral_score,
      concentration_score: raw.concentration_score,
      ownership_score: raw.ownership_score,
      total_exposure: raw.total_exposure,
      total_claims: raw.total_claims,
    },
  };
}
