import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAudit } from '@/services/auditService';

export const AuditPage: React.FC = () => {
  const [filterCaseId, setFilterCaseId] = useState('');

  const { data: auditEntries, isLoading } = useQuery({
    queryKey: ['audit-entries', filterCaseId],
    queryFn: () => getAudit(filterCaseId || undefined),
  });

  const entries = auditEntries || [];

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-[#285239] font-bold bg-[#E8F2E8] px-3 py-1 rounded border border-[#B8D2B8]">
              SIU Governance & Compliance
            </span>
            <span className="text-xs text-[#68766B] font-mono">Immutable SQLite Audit Ledger</span>
          </div>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-[#183B2A] tracking-tight">
            Audit Trail & Decision Ledger
          </h1>
          <p className="text-base text-[#68766B] mt-1.5 max-w-4xl leading-relaxed">
            Cryptographically timestamped record of investigator actions, disposition decisions, notes, and evidence verification sign-offs.
          </p>
        </div>

        <div className="p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg text-right shrink-0">
          <div className="text-xs text-[#68766B] uppercase font-mono font-semibold">Logged Actions</div>
          <div className="font-serif text-3xl font-bold text-[#285239] tabular-nums mt-0.5">
            {entries.length} Events
          </div>
        </div>
      </div>

      {/* Filter Bar (Zero Icons, h-11 input) */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-6 shadow-xs flex items-center gap-4">
        <input
          type="text"
          placeholder="Filter audit log by Case ID (e.g. CASE-2024-0042, CASE-PRV-P0030)..."
          value={filterCaseId}
          onChange={(e) => setFilterCaseId(e.target.value)}
          className="flex-1 h-11 text-sm bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg px-4 text-[#183B2A] placeholder-[#68766B] focus:outline-none focus:border-[#477A58] focus-visible:ring-2 focus-visible:ring-[#477A58]"
        />
        {filterCaseId && (
          <button
            type="button"
            onClick={() => setFilterCaseId('')}
            className="h-11 px-5 text-sm text-[#285239] hover:text-[#183B2A] bg-[#E8F2E8] rounded-lg border border-[#B8D2B8] font-semibold transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Audit Log Table */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-16 text-center text-[#68766B] flex flex-col items-center justify-center space-y-4">
            <div className="w-10 h-10 border-3 border-[#477A58] border-t-transparent rounded-full animate-spin" />
            <span className="text-sm font-mono">Loading immutable audit log...</span>
          </div>
        ) : entries.length === 0 ? (
          <div className="p-16 text-center text-[#68766B] space-y-2">
            <h3 className="font-serif text-xl font-bold text-[#183B2A]">No audit entries recorded yet</h3>
            <p className="text-base text-[#68766B]">Actions taken in case dossiers will appear here automatically.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-base">
              <thead>
                <tr className="border-b border-[#E0E8DF] bg-[#F5F8F4] text-[#68766B] font-mono text-xs uppercase">
                  <th className="py-4 px-5 font-semibold">Log ID</th>
                  <th className="py-4 px-5 font-semibold">Timestamp (UTC)</th>
                  <th className="py-4 px-5 font-semibold">Case ID</th>
                  <th className="py-4 px-5 font-semibold">Action</th>
                  <th className="py-4 px-5 font-semibold">Decision / State</th>
                  <th className="py-4 px-5 font-semibold">Actor</th>
                  <th className="py-4 px-5 font-semibold">Notes & Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E0E8DF] text-[#24352A]">
                {entries.map((entry) => (
                  <tr
                    key={entry.audit_id}
                    className="hover:bg-[#F5F8F4] transition-colors"
                  >
                    <td className="py-4 px-5 font-mono text-[#285239] font-bold">
                      {entry.audit_id}
                    </td>
                    <td className="py-4 px-5 font-mono text-[#68766B] text-sm">
                      {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : 'Recent'}
                    </td>
                    <td className="py-4 px-5 font-mono text-[#183B2A] font-semibold">
                      {entry.entity_id}
                    </td>
                    <td className="py-4 px-5 font-mono text-sm">
                      <span className="bg-[#F5F8F4] px-2.5 py-1 rounded border border-[#E0E8DF] text-[#0369A1] font-semibold">
                        {entry.action}
                      </span>
                    </td>
                    <td className="py-4 px-5">
                      {entry.new_state ? (
                        <span className="font-mono text-xs px-2.5 py-1 rounded bg-[#E8F2E8] text-[#285239] border border-[#B8D2B8] uppercase font-semibold">
                          {entry.new_state}
                        </span>
                      ) : (
                        <span className="text-[#68766B] font-mono text-sm">—</span>
                      )}
                    </td>
                    <td className="py-4 px-5 font-mono text-[#68766B] text-sm">
                      {entry.actor}
                    </td>
                    <td className="py-4 px-5 text-[#68766B] text-sm max-w-sm truncate">
                      {entry.details || entry.reason || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
