import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getQueue } from '@/services/queueService';
import { formatExposureRange } from '@/utils/currency';
import { useNavigate } from 'react-router-dom';

export const CasesIndexPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('ALL');

  const { data: queueData, isLoading } = useQuery({
    queryKey: ['cases-index-queue'],
    queryFn: () => getQueue(),
  });

  const allItems = queueData?.items || [];

  const filteredItems = allItems.filter((item) => {
    const matchesSearch =
      searchTerm === '' ||
      item.case_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.name && item.name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (item.focal_provider_name && item.focal_provider_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (item.focal_provider_id && item.focal_provider_id.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesPriority =
      priorityFilter === 'ALL' || item.severity?.toUpperCase() === priorityFilter;

    return matchesSearch && matchesPriority;
  });

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-[#285239] font-bold bg-[#E8F2E8] px-3 py-1 rounded border border-[#B8D2B8]">
              Investigation Dossiers
            </span>
            <span className="text-xs text-[#68766B] font-mono">Active Provider Cases</span>
          </div>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-[#183B2A] tracking-tight">
            Case Investigations Directory
          </h1>
          <p className="text-base text-[#68766B] mt-1.5 max-w-4xl leading-relaxed">
            Active investigation files compiled from multi-rule evidence cross-corroboration, network graph clusters, and calibrated unified risk scores.
          </p>
        </div>

        <div className="p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg text-right shrink-0">
          <div className="text-xs text-[#68766B] uppercase font-mono font-semibold">Total Active Cases</div>
          <div className="font-serif text-3xl font-bold text-[#183B2A] tabular-nums mt-0.5">
            {allItems.length} Cases
          </div>
        </div>
      </div>

      {/* Search and Filters (h-11, Zero Icons) */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-6 shadow-xs flex flex-wrap items-center gap-4">
        <div className="flex-1 min-w-[280px]">
          <input
            type="text"
            placeholder="Search by Provider Name, Case ID, or NPI..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full h-11 text-sm bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg px-4 text-[#183B2A] placeholder-[#68766B] focus:outline-none focus:border-[#477A58] focus-visible:ring-2 focus-visible:ring-[#477A58]"
          />
        </div>

        <div className="flex items-center gap-2">
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map((tier) => (
            <button
              key={tier}
              type="button"
              onClick={() => setPriorityFilter(tier)}
              className={`h-11 px-5 rounded-lg text-sm font-semibold transition-colors border shadow-xs ${
                priorityFilter === tier
                  ? 'bg-[#477A58] text-white border-[#477A58]'
                  : 'bg-white text-[#68766B] border-[#E0E8DF] hover:bg-[#F5F8F4] hover:text-[#183B2A]'
              }`}
            >
              {tier}
            </button>
          ))}
        </div>
      </div>

      {/* Cases List Table */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-16 text-center text-[#68766B] flex flex-col items-center justify-center space-y-4">
            <div className="w-10 h-10 border-3 border-[#477A58] border-t-transparent rounded-full animate-spin" />
            <span className="text-sm font-mono">Loading investigation cases...</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-16 text-center text-[#68766B]">
            <p className="text-base">No investigation cases matching search criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-base">
              <thead>
                <tr className="border-b border-[#E0E8DF] bg-[#F5F8F4] text-[#68766B] font-mono text-xs uppercase">
                  <th className="py-4 px-5 font-semibold">Rank</th>
                  <th className="py-4 px-5 font-semibold">Case ID</th>
                  <th className="py-4 px-5 font-semibold">Target Entity</th>
                  <th className="py-4 px-5 font-semibold">Priority</th>
                  <th className="py-4 px-5 font-semibold text-right">Risk Score</th>
                  <th className="py-4 px-5 font-semibold text-right">Evidence</th>
                  <th className="py-4 px-5 font-semibold text-right">Exposure</th>
                  <th className="py-4 px-5 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E0E8DF] text-[#24352A]">
                {filteredItems.map((item, idx) => {
                  const exposure = formatExposureRange(item.exposure_low, item.exposure_high);
                  const isCrit = item.severity === 'CRITICAL';
                  const isHigh = item.severity === 'HIGH';

                  return (
                    <tr
                      key={item.case_id}
                      onClick={() => navigate(`/cases/${item.case_id}`)}
                      className="hover:bg-[#F5F8F4] transition-colors cursor-pointer group"
                    >
                      <td className="py-4 px-5 font-serif font-bold text-lg text-[#285239]">
                        #{idx + 1}
                      </td>
                      <td className="py-4 px-5 font-mono font-bold text-[#285239]">
                        {item.case_id}
                      </td>
                      <td className="py-4 px-5">
                        <div className="font-semibold text-base group-hover:text-[#285239] transition-colors text-[#183B2A]">
                          {item.name || item.focal_provider_name || 'Provider Case'}
                        </div>
                        <div className="text-sm text-[#68766B] mt-0.5">
                          {item.subtitle || `${item.specialty || 'General Practice'} | ${item.pool === 'network' ? 'Network Case' : 'Individual Entity'}`}
                        </div>
                      </td>
                      <td className="py-4 px-5">
                        <span
                          className={`text-xs font-mono px-2.5 py-1 rounded border uppercase font-semibold ${
                            isCrit
                              ? 'bg-[#FEE2E2] border-[#FCA5A5] text-[#B91C1C]'
                              : isHigh
                              ? 'bg-[#FEF3C7] border-[#FCD34D] text-[#B45309]'
                              : 'bg-[#E0F2FE] border-[#BAE6FD] text-[#0369A1]'
                          }`}
                        >
                          {item.severity}
                        </span>
                      </td>
                      <td className="py-4 px-5 text-right font-mono font-bold text-base text-[#183B2A] tabular-nums">
                        {item.risk_index} / 100
                      </td>
                      <td className="py-4 px-5 text-right font-mono text-sm text-[#285239] font-bold">
                        {Math.round((item.evidence_strength || 0.8) * 100)}%
                      </td>
                      <td className="py-4 px-5 text-right font-mono font-semibold text-base tabular-nums text-[#183B2A]">
                        {exposure}
                      </td>
                      <td className="py-4 px-5 text-right">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/cases/${item.case_id}`);
                          }}
                          className="px-4 py-2 bg-[#E8F2E8] hover:bg-[#477A58] text-[#285239] hover:text-white border border-[#B8D2B8] text-sm font-semibold rounded-lg transition-colors shadow-xs"
                        >
                          Open dossier
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
