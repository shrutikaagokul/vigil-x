/**
 * Network Subgraph and Graph Intelligence models.
 * Directly maps to network/subgraph.py and provider projection clusters.
 */

export type NetworkNodeType = 'provider' | 'member' | 'facility' | 'owner' | 'bank_account' | 'cohort' | string;

export interface NetworkNode {
  readonly id: string;
  readonly node_type: NetworkNodeType;
  readonly label?: string;
  readonly name?: string;
  readonly specialty?: string;
  readonly facility_type?: string;
  readonly risk_index?: number; // 0-100 scale
  readonly is_focal?: boolean;
  readonly community_id?: number | string;
  readonly [key: string]: unknown;
}

export interface NetworkEdge {
  readonly source: string;
  readonly target: string;
  readonly edge_type:
    | 'shared_bank_account'
    | 'shared_owner'
    | 'shared_address'
    | 'shared_registered_agent'
    | 'referral'
    | 'reciprocal_referral'
    | 'same_day_lab'
    | 'billing'
    | string;
  readonly weight: number;
  readonly confidence?: number | null; // 0.0 - 1.0
  readonly matched_value?: string | null;
  readonly evidence_ids: readonly string[];
}

export interface NetworkCohort {
  readonly cohort_type: 'shared_members' | string;
  readonly providers: readonly string[];
  readonly member_count: number;
  readonly sample_member_ids: readonly string[];
}

export interface NetworkSummary {
  readonly n_nodes: number;
  readonly n_edges: number;
  readonly n_cohorts: number;
  readonly total_members: number;
  readonly hub_provider_id?: string;
  readonly hard_link_score?: number;
  readonly referral_loop_count?: number;
}

export interface Network {
  readonly network_id?: string;
  readonly focal_entity: string;
  readonly nodes: readonly NetworkNode[];
  readonly edges: readonly NetworkEdge[];
  readonly cohorts: readonly NetworkCohort[];
  readonly summary: NetworkSummary;
  readonly description?: string;
  readonly metrics?: Readonly<Record<string, unknown>>;
}
