/**
 * Data Contracts and Service Layer Validation Tests.
 */
import { describe, it, expect } from 'vitest';
import {
  getSummary,
  getQueue,
  getCase,
  getCaseEvidence,
  getCaseTimeline,
  getCaseNetwork,
  getClaim,
  getProvider,
  getRisk,
  getAudit,
  getEvaluation,
  getHealth,
  submitDecision,
  isMockMode,
} from '@/services';
import { MOCK_CASES, MOCK_EVIDENCE, MOCK_CLAIMS, MOCK_PROVIDERS, MOCK_NETWORKS } from '@/services/mockData';

describe('Checkpoint 2 — Data Contracts & Service Layer', () => {
  // 1. Mock summary returns valid typed data
  it('1. mock summary returns valid typed data', async () => {
    const summary = await getSummary();
    expect(summary).toBeDefined();
    expect(summary.total_exposure_dollars).toBeGreaterThan(0);
    expect(summary.prioritized_cases_count).toBeGreaterThan(0);
    expect(summary.active_alerts_count).toBeGreaterThan(0);
    expect(summary.top_risk_categories.length).toBeGreaterThan(0);
  });

  // 2. Mock queue returns deterministic results
  it('2. mock queue returns deterministic results', async () => {
    const q1 = await getQueue({ general_hours: 40, network_hours: 20, horizon: '30d' });
    const q2 = await getQueue({ general_hours: 40, network_hours: 20, horizon: '30d' });
    expect(q1.items.length).toBe(q2.items.length);
    expect(q1.items.map((i) => i.case_id)).toEqual(q2.items.map((i) => i.case_id));
    expect(q1.items[0].priority_score).toEqual(q2.items[0].priority_score);
  });

  // 3. Changing capacity parameters changes queue prioritization
  it('3. changing capacity parameters changes queue prioritization', async () => {
    // Low network specialist hours vs high network specialist hours
    const lowNet = await getQueue({ general_hours: 80, network_hours: 5, horizon: '30d', sort: 'priority' });
    const highNet = await getQueue({ general_hours: 20, network_hours: 60, horizon: '30d', sort: 'priority' });

    // In highNet, the network case (CASE-2024-0042) should have a higher priority boost than in lowNet
    const heroLow = lowNet.items.find((i) => i.case_id === 'CASE-2024-0042');
    const heroHigh = highNet.items.find((i) => i.case_id === 'CASE-2024-0042');

    expect(heroLow).toBeDefined();
    expect(heroHigh).toBeDefined();
    expect(heroHigh!.priority_score).toBeGreaterThan(heroLow!.priority_score);
  });

  // 4. Hero queue item resolves to an existing case
  it('4. hero queue item resolves to an existing case', async () => {
    const queue = await getQueue();
    const heroItem = queue.items.find((i) => i.case_id === 'CASE-2024-0042');
    expect(heroItem).toBeDefined();

    const caseDetail = await getCase(heroItem!.case_id);
    expect(caseDetail).toBeDefined();
    expect(caseDetail.id).toBe('CASE-2024-0042');
    expect(caseDetail.focal_provider_id).toBe('P0042');
  });

  // 5. Case evidence references existing evidence
  it('5. case evidence references existing evidence', async () => {
    const evidenceList = await getCaseEvidence('CASE-2024-0042');
    expect(evidenceList.length).toBeGreaterThan(0);
    evidenceList.forEach((ev) => {
      expect(ev.evidence_id).toMatch(/^E-R\d{2}-/);
      expect(ev.plain_text).toBeDefined();
      expect(ev.severity).toBeDefined();
      expect(ev.claim_ids.length).toBeGreaterThan(0);
    });

    const timeline = await getCaseTimeline('CASE-2024-0042');
    expect(timeline.length).toBeGreaterThan(0);
  });

  // 6. Evidence claim IDs resolve to claim fixtures
  it('6. evidence claim IDs resolve to claim fixtures', async () => {
    const evidenceList = await getCaseEvidence('CASE-2024-0042');
    for (const ev of evidenceList) {
      for (const claimId of ev.claim_ids) {
        const claim = await getClaim(claimId);
        expect(claim).toBeDefined();
        expect(claim.claim_id).toBe(claimId);
      }
    }
  });

  // 7. Case network references valid nodes/edges
  it('7. case network references valid nodes/edges', async () => {
    const network = await getCaseNetwork('CASE-2024-0042');
    expect(network.nodes.length).toBeGreaterThan(0);
    expect(network.edges.length).toBeGreaterThan(0);

    const nodeIds = new Set(network.nodes.map((n) => n.id));
    network.edges.forEach((edge) => {
      expect(nodeIds.has(edge.source)).toBe(true);
      expect(nodeIds.has(edge.target)).toBe(true);
      expect(edge.evidence_ids.length).toBeGreaterThan(0);
    });
  });

  // 8. Network edge evidence IDs resolve to evidence fixtures where provided
  it('8. network edge evidence IDs resolve to evidence fixtures where provided', async () => {
    const network = await getCaseNetwork('CASE-2024-0042');
    const allEvidenceIds = new Set(MOCK_EVIDENCE.map((e) => e.evidence_id));

    network.edges.forEach((edge) => {
      edge.evidence_ids.forEach((evId) => {
        expect(allEvidenceIds.has(evId)).toBe(true);
      });
    });
  });

  // 9. Decision requires a reason
  it('9. decision requires a mandatory reason', async () => {
    await expect(
      submitDecision('CASE-2024-0042', {
        action: 'accept',
        reason: '', // Empty reason
      }),
    ).rejects.toThrow(/Decision requires a mandatory human justification reason/i);

    // Valid decision succeeds
    const res = await submitDecision('CASE-2024-0042', {
      action: 'accept',
      reason: 'Valid multi-entity bank linkage verified against state registry.',
    });
    expect(res.decision_id).toBeDefined();
    expect(res.action).toBe('accept');
    expect(res.reason).toBe('Valid multi-entity bank linkage verified against state registry.');
  });

  // 10. Mock/live service selection respects VITE_API_MODE
  it('10. mock/live service selection respects VITE_API_MODE', () => {
    expect(isMockMode()).toBe(true);
  });

  // 11. IDs remain unchanged through service calls (opaque strings)
  it('11. IDs remain unchanged through service calls', async () => {
    const caseId = 'CASE-2024-0042';
    const c = await getCase(caseId);
    expect(c.id).toBe(caseId);

    const providerId = 'P0042';
    const p = await getProvider(providerId);
    expect(p.provider_id).toBe(providerId);

    const claimId = 'C1023';
    const cl = await getClaim(claimId);
    expect(cl.claim_id).toBe(claimId);
  });

  // 12. No forbidden terminology appears in mock data
  it('12. no forbidden terminology appears in mock data', () => {
    const serializedMockData = JSON.stringify({
      cases: MOCK_CASES,
      evidence: MOCK_EVIDENCE,
      claims: MOCK_CLAIMS,
      providers: MOCK_PROVIDERS,
      networks: MOCK_NETWORKS,
    }).toLowerCase();

    // Must NOT contain forbidden phrases
    expect(serializedMockData).not.toContain('fraud detected');
    expect(serializedMockData).not.toContain('ai says fraud');
    expect(serializedMockData).not.toContain('confirmed fraud');
    expect(serializedMockData).not.toContain('confirmed criminal');
  });

  // 13. Audit, Evaluation, Risk, and Health diagnostics return valid contracts
  it('13. audit, evaluation, risk, and health diagnostics return valid contracts', async () => {
    const risk = await getRisk('P0042');
    expect(risk.risk_index).toBe(94);
    expect(risk.primary_factors.length).toBeGreaterThan(0);

    const audit = await getAudit();
    expect(audit.length).toBeGreaterThan(0);

    const evalSummary = await getEvaluation();
    expect(evalSummary.scenario_recall).toBe(1.0);
    expect(evalSummary.ring_recovery_mean_jaccard).toBeGreaterThan(0.9);

    const health = await getHealth();
    expect(health.status).toBe('healthy');
  });
});
