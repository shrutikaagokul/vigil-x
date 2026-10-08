/**
 * Service for SIU audit trail and action logs.
 * Canonical Endpoint: GET /api/audit
 */
import { AuditEntry } from '@/types/audit';
import { isMockMode, liveApi } from './apiClient';
import { MOCK_AUDIT_ENTRIES } from './mockData/audit';

export async function getAudit(): Promise<readonly AuditEntry[]> {
  if (isMockMode()) {
    return MOCK_AUDIT_ENTRIES;
  }
  return liveApi.get<readonly AuditEntry[]>('/api/audit');
}
