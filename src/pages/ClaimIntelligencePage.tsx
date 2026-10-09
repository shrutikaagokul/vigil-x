import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getClaimsList } from '@/services/claimService';
import { formatCurrency } from '@/utils/currency';
import { useNavigate } from 'react-router-dom';

export const ClaimIntelligencePage: React.FC = () => {
  const navigate = useNavigate();
  const [providerFilter, setProviderFilter] = useState('');
  const [memberFilter, setMemberFilter] = useState('');
  const [procedureFilter, setProcedureFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['claims-list', providerFilter, memberFilter, procedureFilter],
    queryFn: () => getClaimsList({
      provider_id: providerFilter || undefined,
      member_id: memberFilter || undefined,
      procedure_code: procedureFilter || undefined,
      limit: 100,
    }),
  });

  const claims = data?.claims || [];
  const total = data?.total || 0;

  const totalPaid = claims.reduce((acc, c) => acc + (c.paid_amount || 0), 0);
  const avgPaid = claims.length > 0 ? Math.round(totalPaid / claims.length) : 0;

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-[#285239] font-bold bg-[#E8F2E8] px-3 py-1 rounded border border-[#B8D2B8]">
              Claim-Level Diagnostics
            </span>
            <span className="text-xs text-[#68766B] font-mono">Live SQLite Claims Repository</span>
          </div>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-[#183B2A] tracking-tight">
            Claim Intelligence Explorer
          </h1>
          <p className="text-base text-[#68766B] mt-1.5 max-w-4xl leading-relaxed">
            Inspect individual claim line items, diagnostic codes, paid amounts, and procedural anomaly flags associated with monitored providers.
          </p>
        </div>

        {/* Quick Stats Bar */}
        <div className="flex flex-wrap items-center gap-4 shrink-0">
          <div className="p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg text-right">
            <div className="text-xs text-[#68766B] uppercase font-mono font-semibold">Claims Loaded</div>
            <div className="font-serif text-2xl font-bold text-[#183B2A] tabular-nums mt-0.5">
              {claims.length} of {total}
            </div>
          </div>
          <div className="p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg text-right">
            <div className="text-xs text-[#68766B] uppercase font-mono font-semibold">Sample Paid Total</div>
            <div className="font-serif text-2xl font-bold text-[#285239] tabular-nums mt-0.5">
              {formatCurrency(totalPaid, 'compact')}
            </div>
          </div>
          <div className="p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg text-right">
            <div className="text-xs text-[#68766B] uppercase font-mono font-semibold">Avg Paid / Claim</div>
            <div className="font-serif text-2xl font-bold text-[#183B2A] tabular-nums mt-0.5">
              {formatCurrency(avgPaid, 'compact')}
            </div>
          </div>
        </div>
      </div>

      {/* Filter Controls (h-11, clear text, zero icons) */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-6 shadow-xs flex flex-wrap items-center gap-4">
        <div className="flex-1 min-w-[240px]">
          <input
            type="text"
            placeholder="Filter by Provider ID (e.g. P0001, P0030)..."
            value={providerFilter}
            onChange={(e) => setProviderFilter(e.target.value)}
            className="w-full h-11 text-sm bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg px-4 text-[#183B2A] placeholder-[#68766B] focus:outline-none focus:border-[#477A58] focus-visible:ring-2 focus-visible:ring-[#477A58]"
          />
        </div>

        <div className="w-56">
          <input
            type="text"
            placeholder="Member ID..."
            value={memberFilter}
            onChange={(e) => setMemberFilter(e.target.value)}
            className="w-full h-11 text-sm bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg px-4 text-[#183B2A] placeholder-[#68766B] focus:outline-none focus:border-[#477A58] focus-visible:ring-2 focus-visible:ring-[#477A58]"
          />
        </div>

        <div className="w-48">
          <input
            type="text"
            placeholder="CPT Code (e.g. 99214)..."
            value={procedureFilter}
            onChange={(e) => setProcedureFilter(e.target.value)}
            className="w-full h-11 text-sm bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg px-4 text-[#183B2A] placeholder-[#68766B] focus:outline-none focus:border-[#477A58] focus-visible:ring-2 focus-visible:ring-[#477A58]"
          />
        </div>

        {(providerFilter || memberFilter || procedureFilter) && (
          <button
            type="button"
            onClick={() => {
              setProviderFilter('');
              setMemberFilter('');
              setProcedureFilter('');
            }}
            className="h-11 px-5 text-sm text-[#285239] hover:text-[#183B2A] bg-[#E8F2E8] rounded-lg border border-[#B8D2B8] font-semibold transition-colors"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Claims Table */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-16 text-center text-[#68766B] flex flex-col items-center justify-center space-y-4">
            <div className="w-10 h-10 border-3 border-[#477A58] border-t-transparent rounded-full animate-spin" />
            <span className="text-sm font-mono">Retrieving live claim records...</span>
          </div>
        ) : claims.length === 0 ? (
          <div className="p-16 text-center text-[#68766B] space-y-2">
            <h3 className="font-serif text-xl font-bold text-[#183B2A]">No claims matching filters</h3>
            <p className="text-base text-[#68766B]">Try adjusting the provider ID or CPT code search terms.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-base">
              <thead>
                <tr className="border-b border-[#E0E8DF] bg-[#F5F8F4] text-[#68766B] font-mono text-xs uppercase">
                  <th className="py-4 px-5 font-semibold">Claim ID</th>
                  <th className="py-4 px-5 font-semibold">Provider</th>
                  <th className="py-4 px-5 font-semibold">Member</th>
                  <th className="py-4 px-5 font-semibold">Service Date</th>
                  <th className="py-4 px-5 font-semibold">Procedure</th>
                  <th className="py-4 px-5 font-semibold text-right">Billed</th>
                  <th className="py-4 px-5 font-semibold text-right">Paid</th>
                  <th className="py-4 px-5 font-semibold">Status</th>
                  <th className="py-4 px-5 font-semibold">Flags</th>
                  <th className="py-4 px-5 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E0E8DF] text-[#24352A]">
                {claims.map((c) => (
                  <tr
                    key={c.claim_id}
                    className="hover:bg-[#F5F8F4] transition-colors group"
                  >
                    <td className="py-4 px-5 font-mono font-semibold text-[#285239]">
                      {c.claim_id}
                    </td>
                    <td className="py-4 px-5 font-mono text-[#183B2A]">
                      {c.provider_id}
                    </td>
                    <td className="py-4 px-5 font-mono text-[#68766B]">
                      {c.member_id}
                    </td>
                    <td className="py-4 px-5 text-[#68766B] font-mono text-sm">
                      {c.service_date}
                    </td>
                    <td className="py-4 px-5">
                      <span className="font-mono bg-[#F5F8F4] px-2 py-0.5 rounded border border-[#E0E8DF] text-[#0369A1] text-sm">
                        CPT {c.procedure_code}
                      </span>
                    </td>
                    <td className="py-4 px-5 text-right font-mono text-[#68766B]">
                      ${(c.billed_amount || 0).toFixed(2)}
                    </td>
                    <td className="py-4 px-5 text-right font-mono font-semibold text-[#183B2A]">
                      ${(c.paid_amount || 0).toFixed(2)}
                    </td>
                    <td className="py-4 px-5">
                      <span className="px-2 py-0.5 rounded bg-[#E8F2E8] text-[#285239] border border-[#B8D2B8] text-xs font-mono uppercase font-semibold">
                        {c.status || 'PAID'}
                      </span>
                    </td>
                    <td className="py-4 px-5">
                      {c.flags && c.flags.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {c.flags.map((f, i) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 rounded bg-[#FEE2E2] text-[#B91C1C] border border-[#FCA5A5] text-xs font-mono font-semibold"
                            >
                              {f}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-[#68766B] font-mono text-sm">—</span>
                      )}
                    </td>
                    <td className="py-4 px-5 text-right">
                      <button
                        type="button"
                        onClick={() => navigate(`/cases/CASE-PRV-${c.provider_id}`)}
                        className="px-4 py-1.5 bg-[#E8F2E8] hover:bg-[#477A58] text-[#285239] hover:text-white border border-[#B8D2B8] rounded-md text-sm font-semibold transition-colors"
                      >
                        Inspect
                      </button>
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
