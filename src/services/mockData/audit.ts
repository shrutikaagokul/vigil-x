/**
 * Mock Audit Trail fixtures.
 */
import { AuditEntry } from '@/types/audit';

export const MOCK_AUDIT_ENTRIES: readonly AuditEntry[] = [
  {
    audit_id: 'AUD-2024-0918-001',
    timestamp: '2024-09-18T14:20:00Z',
    actor: 'SIU Investigator #104',
    action: 'case_viewed',
    entity_type: 'case',
    entity_id: 'CASE-2024-0042',
    details: 'Investigator reviewed case dossier, evidence cards, and network graph.',
  },
  {
    audit_id: 'AUD-2024-0918-002',
    timestamp: '2024-09-18T13:45:00Z',
    actor: 'System Engine (Louvain Community Detection)',
    action: 'network_ring_identified',
    entity_type: 'network',
    entity_id: 'NET-RING-001',
    details: 'Identified 6-entity provider community with shared bank account hash 9a8b7c6d5e4f3a21.',
    reason: 'Hard link density threshold >= 0.85 reached.',
  },
  {
    audit_id: 'AUD-2024-0917-003',
    timestamp: '2024-09-17T16:10:00Z',
    actor: 'SIU Supervisor #101',
    action: 'capacity_reallocated',
    entity_type: 'queue',
    entity_id: 'QUEUE-DEFAULT',
    details: 'Increased network specialist weekly allocation from 10h to 20h.',
    reason: 'Backlog of multi-entity ring cases flagged in September cycle.',
  },
  {
    audit_id: 'AUD-2024-0917-004',
    timestamp: '2024-09-17T11:30:00Z',
    actor: 'SIU Investigator #108',
    action: 'decision_recorded',
    entity_type: 'case',
    entity_id: 'CASE-2024-0019',
    details: 'Decision: Escalate to Medical Director review.',
    reason: 'Repeated non-responsive provider audit responses regarding billing modifiers.',
    prev_state: 'under_investigation',
    new_state: 'escalated',
  },
];
