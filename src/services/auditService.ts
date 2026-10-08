/**
 * Service for SIU audit trail and action logs.
 * Canonical Endpoint: GET /api/audit
 */
import { AuditEntry } from '@/types/audit';
import { isMockMode, liveApi } from './apiClient';
import { MOCK_AUDIT_ENTRIES } from './mockData/audit';

interface BackendAuditRecord {
  readonly log_id: string;
  readonly case_id: string;
  readonly action: string;
  readonly decision?: string | null;
  readonly actor: string;
  readonly notes?: string | null;
  readonly payload?: Record<string, unknown> | null;
  readonly timestamp: string;
}

interface BackendAuditResponse {
  readonly total: number;
  readonly limit: number;
  readonly records: readonly (BackendAuditRecord | AuditEntry)[];
}

export async function getAudit(caseId?: string): Promise<readonly AuditEntry[]> {
  if (isMockMode()) {
    if (caseId) {
      return MOCK_AUDIT_ENTRIES.filter((e) => e.entity_id === caseId);
    }
    return MOCK_AUDIT_ENTRIES;
  }

  const raw = await liveApi.get<BackendAuditResponse | readonly AuditEntry[]>('/api/audit', caseId ? { case_id: caseId } : undefined);

  if (Array.isArray(raw)) {
    return raw as readonly AuditEntry[];
  }

  const records = (raw as BackendAuditResponse).records || [];
  return records.map((r) => {
    if ('audit_id' in r) {
      return r as AuditEntry;
    }
    const br = r as BackendAuditRecord;
    return {
      audit_id: br.log_id,
      timestamp: br.timestamp,
      actor: br.actor,
      action: br.action,
      entity_type: 'case',
      entity_id: br.case_id,
      details: br.notes || `Action: ${br.action}`,
      reason: br.notes || null,
      prev_state: null,
      new_state: br.decision || null,
      metadata: br.payload || undefined,
    };
  });
}
