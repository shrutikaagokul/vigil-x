/**
 * Live Backend End-to-End Flow Verification Script
 * Validates that all frontend service layer adapters correctly communicate
 * with the live FastAPI backend without errors.
 */

const BASE_URL = 'http://127.0.0.1:8000';

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${endpoint}`, options);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} on ${endpoint}: ${await res.text()}`);
  }
  return (await res.json()) as T;
}

async function runLiveSmokeTest() {
  console.log('=== STARTING VIGIL-X LIVE BACKEND E2E SMOKE TEST ===\n');

  // Step 0: Health Check
  console.log('[STEP 0] Checking /api/health...');
  const health = await fetchJson<any>('/api/health');
  console.log(' -> Status:', health.status);
  console.log(' -> Database Reachable:', health.database_reachable);
  console.log(' -> Table Count:', health.table_count);
  console.log(' -> Schema Valid:', health.schema_valid);
  if (!health.database_reachable) throw new Error('Database is not reachable!');

  // Step 1: Dashboard / Summary
  console.log('\n[STEP 1] Testing / (Dashboard) -> /api/summary...');
  const summary = await fetchJson<any>('/api/summary');
  console.log(' -> Claims Analyzed:', summary.claims_analyzed?.toLocaleString());
  console.log(' -> Total Paid:', '$' + summary.paid_total?.toLocaleString());
  console.log(' -> Total Alerts:', summary.alerts_total);
  console.log(' -> Queue Size:', summary.queue_size);
  console.log(' -> Funnel:', JSON.stringify(summary.funnel));

  // Step 2: Queue
  console.log('\n[STEP 2] Testing /queue -> /api/queue...');
  const queue = await fetchJson<any>('/api/queue?capacity_hours=60&horizon_days=30&sort=priority');
  console.log(' -> Total Cases:', queue.total_cases);
  console.log(' -> Queue Items Returned:', queue.items?.length);
  if (!queue.items || queue.items.length === 0) throw new Error('Queue is empty!');

  const firstCase = queue.items[0];
  console.log(' -> Top Priority Case:', firstCase.case_id, '| Entity:', firstCase.entity_name, '| Risk:', firstCase.risk_score, '| Priority:', firstCase.priority);

  const testCaseId = firstCase.case_id;

  // Step 3: Case Dossier
  console.log(`\n[STEP 3] Testing Case Dossier -> /api/cases/${testCaseId}...`);
  const caseDetail = await fetchJson<any>(`/api/cases/${testCaseId}`);
  console.log(' -> Case ID:', caseDetail.case_id);
  console.log(' -> Entity Name:', caseDetail.entity_name);
  console.log(' -> Status:', caseDetail.status);
  console.log(' -> Priority:', caseDetail.priority);
  console.log(' -> Risk Score:', caseDetail.risk_score);
  console.log(' -> Exposure Range: $' + caseDetail.exposure_low?.toLocaleString() + ' - $' + caseDetail.exposure_high?.toLocaleString());
  console.log(' -> Claims Count:', caseDetail.claims_count);
  console.log(' -> Members Affected:', caseDetail.members_affected);

  // Step 4: Case WHY FLAGGED
  console.log('\n[STEP 4] Testing Case WHY FLAGGED...');
  console.log(' -> Why Flagged:', caseDetail.why_flagged);
  console.log(' -> Top Reasons:', caseDetail.top_reasons);
  console.log(' -> Benign Explanations Count:', caseDetail.benign_explanations?.length);
  console.log(' -> Risk Components:', caseDetail.risk_components);

  // Step 5: Case EVIDENCE
  console.log(`\n[STEP 5] Testing Case EVIDENCE -> /api/cases/${testCaseId}/evidence...`);
  const evidenceRes = await fetchJson<any>(`/api/cases/${testCaseId}/evidence`);
  console.log(' -> Total Evidence Items:', evidenceRes.total_evidence_items);
  console.log(' -> Evidence Sample:');
  (evidenceRes.evidence || []).slice(0, 3).forEach((e: any, idx: number) => {
    console.log(`    [${idx + 1}] Rule ${e.rule_id} (${e.rule_name}): ${e.plain_text} | Est Overpay: $${e.est_overpay}`);
  });

  // Step 6: Case CONTEXT / Timeline
  console.log(`\n[STEP 6] Testing Case CONTEXT / Timeline -> /api/cases/${testCaseId}/timeline...`);
  const timelineRes = await fetchJson<any>(`/api/cases/${testCaseId}/timeline`);
  console.log(' -> Timeline Events Count:', timelineRes.events_count);
  (timelineRes.timeline || []).slice(0, 3).forEach((t: any, idx: number) => {
    console.log(`    [${idx + 1}] Date: ${t.date} | Type: ${t.event_type} | ${t.description}`);
  });

  // Step 7: Case NETWORK Subgraph
  console.log(`\n[STEP 7] Testing Case NETWORK Subgraph -> /api/cases/${testCaseId}/network...`);
  const networkRes = await fetchJson<any>(`/api/cases/${testCaseId}/network`);
  const sg = networkRes.subgraph || {};
  console.log(' -> Subgraph Nodes:', sg.nodes?.length);
  console.log(' -> Subgraph Edges:', sg.edges?.length);
  console.log(' -> Focal Node:', sg.nodes?.find((n: any) => n.is_focal)?.id);

  // Step 8: Network Community Page
  const networkId = caseDetail.network_id || 'NET-0000';
  console.log(`\n[STEP 8] Testing Network Community -> /api/networks/${networkId}...`);
  const netDetail = await fetchJson<any>(`/api/networks/${networkId}`);
  console.log(' -> Network ID:', netDetail.network_id);
  console.log(' -> Hub Provider:', netDetail.hub_provider_id);
  console.log(' -> Total Providers:', netDetail.n_providers);
  console.log(' -> Hard Link Score:', netDetail.hard_link_score);
  console.log(' -> Referral Score:', netDetail.referral_score);
  console.log(' -> Total Exposure: $' + netDetail.total_exposure?.toLocaleString());

  // Step 9: Return to Case & Brief
  console.log(`\n[STEP 9] Testing AI Executive Brief -> /api/brief?case_id=${testCaseId}...`);
  const brief = await fetchJson<any>(`/api/brief?case_id=${testCaseId}`);
  console.log(' -> Title:', brief.title);
  console.log(' -> Why Prioritized:', brief.why_prioritized);
  console.log(' -> Verified:', brief.verified);

  // Step 10: Evaluation
  console.log('\n[STEP 10] Testing Evaluation -> /api/evaluation...');
  const evaluation = await fetchJson<any>('/api/evaluation');
  console.log(' -> Total Evaluations:', evaluation.total_evaluations);
  if (evaluation.evaluations?.length > 0) {
    const ev = evaluation.evaluations[0];
    console.log(' -> Baseline (Rules-Only) Precision@10:', ev.baseline_rules_only?.precision_at_10);
    console.log(' -> Nexus Full Engine Precision@10:', ev.nexus_full_engine?.precision_at_10);
    console.log(' -> Recall@10 Lift:', ev.comparison?.recall_at_10_lift);
  }

  // Step 11: Human Decision Recording
  console.log(`\n[STEP 11] Testing Human Decision Recording -> POST /api/decision...`);
  const decisionRes = await fetchJson<any>('/api/decision', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      case_id: testCaseId,
      decision: 'accept',
      notes: 'Confirmed multi-entity referral loop and geographic anomaly across consecutive service dates.\nEscalating to medical records audit.',
      actor: 'investigator',
    }),
  });
  console.log(' -> Decision Status:', decisionRes.status);
  console.log(' -> Audit ID:', decisionRes.audit_id);
  console.log(' -> Message:', decisionRes.message);

  // Step 12: Audit Trail Verification
  console.log(`\n[STEP 12] Testing Audit Trail -> /api/audit?case_id=${testCaseId}...`);
  const auditRes = await fetchJson<any>(`/api/audit?case_id=${testCaseId}`);
  console.log(' -> Audit Entries for Case:', auditRes.total);
  console.log(' -> Latest Action:', auditRes.records?.[0]?.action, '| By:', auditRes.records?.[0]?.actor);

  // Step 13: Case Copilot Question
  console.log(`\n[STEP 13] Testing Case Copilot -> POST /api/ask...`);
  const askRes = await fetchJson<any>('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      case_id: testCaseId,
      question: 'What rules were triggered for this provider?',
    }),
  });
  console.log(' -> Matched Intent:', askRes.matched_intent);
  console.log(' -> Answer:', askRes.answer?.slice(0, 120) + '...');

  console.log('\n=== ALL LIVE BACKEND FLOWS TESTED SUCCESSFULLY WITH ZERO ERRORS ===');
}

runLiveSmokeTest().catch((err) => {
  console.error('\n[SMOKE TEST FAILED]:', err);
  process.exit(1);
});
