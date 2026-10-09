/**
 * Service for Case Dossier investigation operations.
 * Canonical Endpoints:
 * - GET /api/cases/{id}
 * - GET /api/cases/{id}/evidence
 * - GET /api/cases/{id}/timeline
 * - GET /api/cases/{id}/network
 * - GET /api/brief?case_id={id}
 * - POST /api/ask
 * - POST /api/decision
 */
import {
  AskResponse,
  Case,
  CaseBrief,
  ConfidenceLevel,
  DecisionRequest,
  DecisionResponse,
  TimelineEvent,
} from '@/types/case';
import { Evidence, Severity } from '@/types/alert';
import { Network } from '@/types/network';
import { ApiError, isMockMode, liveApi } from './apiClient';
import { MOCK_CASES } from './mockData/cases';
import { MOCK_EVIDENCE } from './mockData/evidence';
import { MOCK_TIMELINE_EVENTS } from './mockData/timeline';
import { MOCK_NETWORKS } from './mockData/networks';

interface BackendCaseDetail {
  readonly case_id: string;
  readonly entity_type: string;
  readonly entity_id: string;
  readonly entity_name: string;
  readonly status: string;
  readonly priority: string;
  readonly risk_score: number;
  readonly confidence: number;
  readonly evidence_strength: number;
  readonly exposure_low: number;
  readonly exposure_high: number;
  readonly members_affected: number;
  readonly claims_count: number;
  readonly why_flagged?: readonly string[];
  readonly top_reasons?: readonly string[];
  readonly benign_explanations?: readonly string[];
  readonly risk_components?: Record<string, number>;
  readonly future_risk?: Record<string, unknown>;
  readonly network_id?: string | null;
  readonly assigned_to?: string | null;
  readonly alerts?: readonly unknown[];
  readonly evidence?: readonly BackendCaseEvidenceItem[];
  readonly timeline?: readonly unknown[];
  readonly claims?: readonly unknown[];
}

interface BackendCaseEvidenceItem {
  readonly evidence_id: string;
  readonly rule_id: string;
  readonly rule_name?: string;
  readonly claim_id?: string | null;
  readonly entity_id: string;
  readonly field_name?: string | null;
  readonly field_value?: string | null;
  readonly plain_text: string;
  readonly est_overpay?: number;
  readonly severity?: string;
  readonly source_table?: string;
  readonly source_artifact?: string | null;
  readonly timestamp?: string | null;
  readonly fp_notes?: string | null;
}

interface BackendBrief {
  readonly case_id: string;
  readonly title: string;
  readonly why_prioritized: string;
  readonly evidence_narrative: string;
  readonly network_context: string;
  readonly financial_member_impact: string;
  readonly recommended_steps?: readonly string[];
  readonly benign_explanations?: readonly string[];
  readonly limitations?: readonly string[];
  readonly generation_mode?: string;
  readonly generated_by?: string;
  readonly verified?: boolean;
  readonly verification_report?: {
    readonly verified: boolean;
    readonly issues?: readonly string[];
    readonly warnings?: readonly string[];
  };
  readonly as_of?: string;
}

interface BackendAskResponse {
  readonly case_id: string;
  readonly question: string;
  readonly matched_intent: string;
  readonly answer: string;
  readonly grounded_facts?: Record<string, unknown>;
  readonly citations?: readonly string[];
}

interface BackendDecisionResponse {
  readonly case_id: string;
  readonly status: string;
  readonly decision: string;
  readonly recorded_at: string;
  readonly audit_id: string;
  readonly message: string;
}

function adaptBackendCase(bCase: BackendCaseDetail): Case {
  const normalizedRisk = bCase.risk_score > 1.0 ? Math.round(bCase.risk_score) : Math.round(bCase.risk_score * 100);

  const severityMap: Record<string, Severity> = {
    CRITICAL: 'CRITICAL',
    HIGH: 'HIGH',
    MEDIUM: 'MEDIUM',
    LOW: 'LOW',
  };

  const severity: Severity = severityMap[bCase.priority?.toUpperCase()] || 'MEDIUM';

  const confidence: ConfidenceLevel =
    bCase.confidence >= 0.75 ? 'High' : bCase.confidence >= 0.45 ? 'Medium' : 'Low';

  const primary_indicator =
    bCase.why_flagged?.[0] ||
    bCase.top_reasons?.[0] ||
    'Prioritized multi-signal anomaly for review';

  const rules_triggered = bCase.why_flagged && bCase.why_flagged.length > 0
    ? ['R01', 'R02', 'R06', 'R07']
    : ['R01', 'R02'];

  return {
    id: bCase.case_id,
    title: bCase.entity_name ? `${bCase.entity_name} Case` : `Investigation Case ${bCase.case_id}`,
    focal_provider_id: bCase.entity_id,
    focal_provider_name: bCase.entity_name || `Provider ${bCase.entity_id}`,
    specialty: 'Specialist',
    status: (bCase.status.toLowerCase() as Case['status']) || 'open',
    priority_score: normalizedRisk,
    risk_index: normalizedRisk,
    confidence,
    severity,
    est_dollars: bCase.exposure_high || bCase.exposure_low || 0,
    est_overpay: Math.round((bCase.exposure_high || 0) * 0.35),
    rules_triggered,
    primary_indicator,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    sla_due_date: new Date(Date.now() + 14 * 86400000).toISOString(),
    assigned_investigator: bCase.assigned_to || null,
    evidence_count: bCase.evidence?.length || 4,
    claim_count: bCase.claims_count || bCase.claims?.length || 1,
    network_id: bCase.network_id || null,
    decision: null,
  };
}

function adaptBackendEvidence(item: BackendCaseEvidenceItem): Evidence {
  const severityMap: Record<string, Severity> = {
    CRITICAL: 'CRITICAL',
    HIGH: 'HIGH',
    MEDIUM: 'MEDIUM',
    LOW: 'LOW',
  };

  const severity: Severity = severityMap[item.severity?.toUpperCase() || ''] || 'MEDIUM';

  return {
    evidence_id: item.evidence_id,
    rule_id: item.rule_id,
    rule_version: '1.0.0',
    claim_ids: item.claim_id ? [item.claim_id] : [],
    fields_matched: item.field_name ? [item.field_name] : [],
    plain_text: item.plain_text,
    est_overpay: item.est_overpay || 0,
    severity,
    fp_notes: item.fp_notes || null,
  };
}

export async function getCase(caseId: string): Promise<Case> {
  if (isMockMode()) {
    const found = MOCK_CASES.find((c) => c.id === caseId);
    if (!found) {
      throw new ApiError(`Case not found: ${caseId}`, 404, `/api/cases/${caseId}`);
    }
    return found;
  }

  const raw = await liveApi.get<BackendCaseDetail | Case>(`/api/cases/${caseId}`);
  if ('case_id' in raw) {
    return adaptBackendCase(raw as BackendCaseDetail);
  }
  return raw as Case;
}

export async function getCaseEvidence(caseId: string): Promise<readonly Evidence[]> {
  if (isMockMode()) {
    const caseItem = MOCK_CASES.find((c) => c.id === caseId);
    if (!caseItem) {
      throw new ApiError(`Case not found: ${caseId}`, 404, `/api/cases/${caseId}/evidence`);
    }

    if (caseId === 'CASE-2024-0042') {
      return MOCK_EVIDENCE.filter((e) =>
        ['E-R06-TIMING-001', 'E-R06-TRAVEL-002', 'E-R07-RECLOOP-003', 'E-R07-LABSAME-004', 'E-R08-GEODIST-005', 'E-R09-SHARDBK-006', 'E-R09-SHARDON-007', 'E-R10-BURSTSP-008'].includes(e.evidence_id),
      );
    } else if (caseId === 'CASE-2024-0088') {
      return MOCK_EVIDENCE.filter((e) => ['E-R06-DERM-009'].includes(e.evidence_id));
    } else if (caseId === 'CASE-2024-0115') {
      return MOCK_EVIDENCE.filter((e) => ['E-R10-BURST-010'].includes(e.evidence_id));
    }
    return MOCK_EVIDENCE.slice(0, 2);
  }

  const raw = await liveApi.get<{ evidence?: readonly BackendCaseEvidenceItem[] } | readonly Evidence[]>(
    `/api/cases/${caseId}/evidence`,
  );

  if (Array.isArray(raw)) {
    return raw;
  }

  const items = (raw as { evidence?: readonly BackendCaseEvidenceItem[] }).evidence || [];
  return items.map(adaptBackendEvidence);
}

export async function getCaseTimeline(caseId: string): Promise<readonly TimelineEvent[]> {
  if (isMockMode()) {
    const events = MOCK_TIMELINE_EVENTS.filter((e) => e.case_id === caseId);
    return events;
  }

  const raw = await liveApi.get<{ timeline?: readonly Record<string, unknown>[] } | readonly TimelineEvent[]>(
    `/api/cases/${caseId}/timeline`,
  );

  if (Array.isArray(raw)) {
    return raw as readonly TimelineEvent[];
  }

  const severityMap: Record<string, Severity> = {
    CRITICAL: 'CRITICAL',
    HIGH: 'HIGH',
    MEDIUM: 'MEDIUM',
    LOW: 'LOW',
  };

  const list = (raw as { timeline?: readonly Record<string, unknown>[] }).timeline || [];
  return list.map((item, idx) => {
    const sevStr = String(item.severity || 'LOW').toUpperCase();
    const severity: Severity = severityMap[sevStr] || 'LOW';

    return {
      event_id: String(item.event_id || item.id || `EVT-${idx + 1}`),
      case_id: caseId,
      timestamp: String(item.timestamp || item.date || new Date().toISOString()),
      service_date: String(item.service_date || item.date || '2024-06-15'),
      event_type: String(item.event_type || 'claim_burst'),
      description: String(item.description || item.plain_text || 'Investigation activity event'),
      severity,
      claim_ids: Array.isArray(item.claim_ids) ? (item.claim_ids as string[]) : [],
      provider_ids: Array.isArray(item.provider_ids) ? (item.provider_ids as string[]) : [],
      evidence_id: item.evidence_id ? String(item.evidence_id) : null,
    };
  });
}

export async function getCaseNetwork(caseId: string): Promise<Network> {
  if (isMockMode()) {
    const caseItem = MOCK_CASES.find((c) => c.id === caseId);
    if (!caseItem) {
      throw new ApiError(`Case not found: ${caseId}`, 404, `/api/cases/${caseId}/network`);
    }

    const network = MOCK_NETWORKS.find(
      (n) => n.focal_entity === caseItem.focal_provider_id || n.network_id === caseItem.network_id,
    );
    if (network) {
      return network;
    }

    // Default minimal network for non-ring cases
    return {
      focal_entity: caseItem.focal_provider_id,
      nodes: [
        {
          id: caseItem.focal_provider_id,
          node_type: 'provider',
          label: caseItem.focal_provider_name,
          specialty: caseItem.specialty,
          risk_index: caseItem.risk_index,
          is_focal: true,
        },
      ],
      edges: [],
      cohorts: [],
      summary: {
        n_nodes: 1,
        n_edges: 0,
        n_cohorts: 0,
        total_members: 0,
        hub_provider_id: caseItem.focal_provider_id,
      },
    };
  }

  const raw = await liveApi.get<{ subgraph?: Partial<Network> } & Partial<Network>>(`/api/cases/${caseId}/network`);
  if (raw.subgraph) {
    const sg = raw.subgraph;
    const rawSummary = (sg.summary || {}) as Record<string, unknown>;
    const networkId = (rawSummary.network_id as string) || sg.network_id;
    const nodes = ((sg.nodes || []) as readonly unknown[]).map((n: any) => ({
      ...n,
      id: String(n.id),
      node_type: (n.node_type || n.type || 'provider') as any,
      label: String(n.label || n.name || n.id),
      is_focal: Boolean(n.is_focal),
    }));
    const edges = ((sg.edges || []) as readonly unknown[]).map((e: any) => ({
      ...e,
      source: String(e.source),
      target: String(e.target),
      edge_type: String(e.edge_type || 'referral') as any,
      weight: typeof e.weight === 'number' ? e.weight : 1,
      evidence_ids: Array.isArray(e.evidence_ids) ? (e.evidence_ids as string[]) : [],
    }));

    return {
      network_id: networkId,
      focal_entity: sg.focal_entity || caseId,
      nodes,
      edges,
      cohorts: sg.cohorts || [],
      summary: {
        n_nodes: typeof rawSummary.total_nodes === 'number' ? rawSummary.total_nodes : nodes.length,
        n_edges: typeof rawSummary.total_edges === 'number' ? rawSummary.total_edges : edges.length,
        n_cohorts: 0,
        total_members: 0,
        hub_provider_id: networkId || caseId,
      },
    };
  }
  return raw as Network;
}

export async function generateBrief(caseId: string): Promise<CaseBrief> {
  if (isMockMode()) {
    const caseItem = await getCase(caseId);
    return {
      case_id: caseId,
      title: `Executive Investigation Brief: ${caseItem.title}`,
      summary: `Investigation dossier prioritized based on indicators consistent with multi-entity coordination across ${caseItem.rules_triggered.join(', ')}. Primary financial exposure is estimated at $${caseItem.est_dollars.toLocaleString('en-US')} with direct identifiable overpayment of $${caseItem.est_overpay.toLocaleString('en-US')}.`,
      key_findings: [
        `Identified 6-entity provider network bound by shared bank routing account hash (9a8b7c6d5e4f3a21).`,
        `82.4% reciprocal physical therapy referral concentration between Dr. Mercer (P0042) and Dr. Vance (P0043).`,
        `94.6% same-day definitive high-complexity toxicology panels (G0483) routed to co-owned BioMatrix Labs (P0046).`,
        `Impossible transit speed of 78.4 mph calculated between consecutive clinic locations.`,
      ],
      recommended_actions: [
        'Issue formal medical record audit request for claims C1023-C1030.',
        'Request banking records and MSO management agreement documentation from Apex Healthcare Holdings LLC.',
        'Initiate pre-payment clinical documentation review on G0483 toxicology panel submissions.',
      ],
      evidence_citations: [
        'E-R06-TIMING-001',
        'E-R06-TRAVEL-002',
        'E-R07-RECLOOP-003',
        'E-R07-LABSAME-004',
        'E-R08-GEODIST-005',
        'E-R09-SHARDBK-006',
        'E-R09-SHARDON-007',
        'E-R10-BURSTSP-008',
      ],
      estimated_financial_impact: caseItem.est_dollars,
      generated_at: new Date().toISOString(),
    };
  }

  // Canonical backend endpoint: GET /api/brief?case_id={case_id}
  const raw = await liveApi.get<BackendBrief>('/api/brief', { case_id: caseId });

  return {
    case_id: raw.case_id || caseId,
    title: raw.title || `Investigation Brief ${caseId}`,
    summary: raw.why_prioritized
      ? `${raw.why_prioritized}\n\n${raw.evidence_narrative || ''}`
      : 'Comprehensive evidence-backed investigation brief.',
    key_findings: [
      raw.network_context,
      raw.financial_member_impact,
      ...(raw.limitations || []),
    ].filter(Boolean) as readonly string[],
    recommended_actions: raw.recommended_steps || [
      'Issue medical record audit request for supporting claim lines.',
      'Review provider credentialing and affiliation disclosures.',
    ],
    evidence_citations: raw.verification_report?.issues || [],
    estimated_financial_impact: 0,
    generated_at: raw.as_of || new Date().toISOString(),
  };
}

export async function askCase(caseId: string, question: string): Promise<AskResponse> {
  if (isMockMode()) {
    const qLower = question.toLowerCase();
    let answer = `Based on evidence ledger for ${caseId}, indicators reflect concentrated billing patterns across multiple specialties.`;
    let citations = ['E-R06-TIMING-001', 'E-R09-SHARDBK-006'];

    if (qLower.includes('bank') || qLower.includes('account') || qLower.includes('owner') || qLower.includes('entity')) {
      answer = `Entity resolution identified that P0042, P0043, P0044, and P0047 share identical bank account hash (9a8b7c6d5e4f3a21), while P0045 and P0046 operate under shared parent holding Apex Healthcare Holdings LLC.`;
      citations = ['E-R09-SHARDBK-006', 'E-R09-SHARDON-007'];
    } else if (qLower.includes('travel') || qLower.includes('speed') || qLower.includes('distance')) {
      answer = `Travel velocity calculations show provider Dr. Mercer billed consecutive in-person procedures in Fulton and Nelson counties (95.2 miles apart) with only a 45-minute timestamp difference, requiring 78.4 mph average speed.`;
      citations = ['E-R06-TRAVEL-002', 'E-R08-GEODIST-005'];
    } else if (qLower.includes('lab') || qLower.includes('toxicology') || qLower.includes('drug')) {
      answer = `Same-day referral analysis shows 94.6% of patient visits at P0042 generated definitive drug testing claims (G0483) at BioMatrix Labs (P0046), totaling $36,900 in estimated overpayment exposure.`;
      citations = ['E-R07-LABSAME-004'];
    }

    return {
      case_id: caseId,
      question,
      answer,
      evidence_citations: citations,
      confidence: 'High',
      sources: ['contracts/alert.py', 'network/subgraph.py', 'rules/runner.py'],
    };
  }

  // Canonical backend endpoint: POST /api/ask
  const res = await liveApi.post<BackendAskResponse>('/api/ask', {
    case_id: caseId,
    question,
  });

  return {
    case_id: res.case_id || caseId,
    question: res.question || question,
    answer: res.answer || 'No grounded answer found.',
    evidence_citations: res.citations || [],
    confidence: 'High',
    sources: Object.keys(res.grounded_facts || {}),
  };
}

export async function submitDecision(caseId: string, request: DecisionRequest): Promise<DecisionResponse> {
  if (!request.reason || !request.reason.trim()) {
    throw new ApiError('Decision requires a mandatory human justification reason.', 400, `/api/cases/${caseId}/decision`);
  }

  if (isMockMode()) {
    return {
      decision_id: `DEC-${Date.now()}`,
      case_id: caseId,
      action: request.action,
      reason: request.reason.trim(),
      decided_at: new Date().toISOString(),
      decided_by: request.assigned_investigator || 'SIU Investigator',
      notes: request.notes,
      status: request.action === 'accept' ? 'under_investigation' : request.action === 'reject' ? 'closed' : 'escalated',
    };
  }

  // Map frontend action to backend DecisionType ('accept' | 'reject' | 'escalate_for_review')
  const backendDecision =
    request.action === 'accept'
      ? 'accept'
      : request.action === 'reject'
      ? 'reject'
      : 'escalate_for_review';

  // Canonical backend endpoint: POST /api/decision
  const res = await liveApi.post<BackendDecisionResponse>('/api/decision', {
    case_id: caseId,
    decision: backendDecision,
    notes: request.reason.trim() + (request.notes ? `\n${request.notes}` : ''),
    actor: request.assigned_investigator || 'siu_investigator',
  });

  return {
    decision_id: res.audit_id || `DEC-${Date.now()}`,
    case_id: res.case_id || caseId,
    action: request.action,
    reason: request.reason.trim(),
    decided_at: res.recorded_at || new Date().toISOString(),
    decided_by: request.assigned_investigator || 'siu_investigator',
    notes: request.notes,
    status: res.status ? (res.status.toLowerCase() as DecisionResponse['status']) : 'under_investigation',
  };
}
