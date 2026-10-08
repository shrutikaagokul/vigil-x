/**
 * Service for Case Dossier investigation operations.
 * Canonical Endpoints:
 * - GET /api/cases/{id}
 * - GET /api/cases/{id}/evidence
 * - GET /api/cases/{id}/timeline
 * - GET /api/cases/{id}/network
 * - POST /api/cases/{id}/brief
 * - POST /api/cases/{id}/ask
 * - POST /api/cases/{id}/decision
 */
import {
  AskResponse,
  Case,
  CaseBrief,
  DecisionRequest,
  DecisionResponse,
  TimelineEvent,
} from '@/types/case';
import { Evidence } from '@/types/alert';
import { Network } from '@/types/network';
import { ApiError, isMockMode, liveApi } from './apiClient';
import { MOCK_CASES } from './mockData/cases';
import { MOCK_EVIDENCE } from './mockData/evidence';
import { MOCK_TIMELINE_EVENTS } from './mockData/timeline';
import { MOCK_NETWORKS } from './mockData/networks';

export async function getCase(caseId: string): Promise<Case> {
  if (isMockMode()) {
    const found = MOCK_CASES.find((c) => c.id === caseId);
    if (!found) {
      throw new ApiError(`Case not found: ${caseId}`, 404, `/api/cases/${caseId}`);
    }
    return found;
  }
  return liveApi.get<Case>(`/api/cases/${caseId}`);
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
  return liveApi.get<readonly Evidence[]>(`/api/cases/${caseId}/evidence`);
}

export async function getCaseTimeline(caseId: string): Promise<readonly TimelineEvent[]> {
  if (isMockMode()) {
    const events = MOCK_TIMELINE_EVENTS.filter((e) => e.case_id === caseId);
    return events;
  }
  return liveApi.get<readonly TimelineEvent[]>(`/api/cases/${caseId}/timeline`);
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
  return liveApi.get<Network>(`/api/cases/${caseId}/network`);
}

export async function generateBrief(caseId: string): Promise<CaseBrief> {
  if (isMockMode()) {
    const caseItem = await getCase(caseId);
    return {
      case_id: caseId,
      title: `Executive Investigation Brief: ${caseItem.title}`,
      summary: `Investigation dossier prioritized based on indicators consistent with multi-entity coordination across ${caseItem.rules_triggered.join(', ')}. Primary financial exposure is estimated at $${caseItem.est_dollars.toLocaleString()} with direct identifiable overpayment of $${caseItem.est_overpay.toLocaleString()}.`,
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
  return liveApi.post<CaseBrief>(`/api/cases/${caseId}/brief`);
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
  return liveApi.post<AskResponse>(`/api/cases/${caseId}/ask`, { question });
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
  return liveApi.post<DecisionResponse>(`/api/cases/${caseId}/decision`, request);
}
