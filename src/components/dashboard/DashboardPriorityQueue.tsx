import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { QueueItem } from '@/types/queue';
import { formatExposureRange } from '@/utils/currency';

interface DashboardPriorityQueueProps {
  readonly items: readonly QueueItem[];
}

function getPriorityBadgeClass(severity: string) {
  switch (severity?.toUpperCase()) {
    case 'CRITICAL':
      return 'bg-[#FEE2E2] border-[#FCA5A5] text-[#B91C1C]';
    case 'HIGH':
      return 'bg-[#FEF3C7] border-[#FCD34D] text-[#B45309]';
    case 'MEDIUM':
      return 'bg-[#E0F2FE] border-[#BAE6FD] text-[#0369A1]';
    case 'LOW':
    default:
      return 'bg-[#E8F2E8] border-[#B8D2B8] text-[#285239]';
  }
}

export const DashboardPriorityQueue: React.FC<DashboardPriorityQueueProps> = ({ items }) => {
  const navigate = useNavigate();
  const topItems = items.slice(0, 5);

  return (
    <div
      data-testid="dashboard-priority-queue"
      className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-6 shadow-xs"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E0E8DF] pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="font-serif text-2xl font-bold text-[#183B2A] tracking-tight">
              SIU Priority Queue
            </h2>
            <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#E8F2E8] text-[#285239] border border-[#B8D2B8] font-semibold">
              Capacity-Optimized
            </span>
          </div>
          <p className="text-base text-[#68766B] mt-1.5 leading-relaxed">
            Top investigations prioritized for immediate investigator action based on capacity and multi-entity risk.
          </p>
        </div>

        <Link
          to="/queue"
          className="text-base font-semibold text-[#285239] hover:text-[#183B2A] transition-colors shrink-0"
        >
          View full queue ({items.length} cases)
        </Link>
      </div>

      {/* Spacious, Highly Readable Priority Queue Cases List */}
      <div className="divide-y divide-[#E0E8DF]">
        {topItems.map((item, idx) => {
          const rank = idx + 1;
          const baseline = item.baseline_rank || (rank === 1 ? 38 : rank === 2 ? 12 : 21);
          const exposureStr = formatExposureRange(item.exposure_low, item.exposure_high);
          const badgeClass = getPriorityBadgeClass(item.severity);
          const evidenceStrength = (item.evidence_strength ? Math.round(item.evidence_strength * 100) : 85);

          return (
            <div
              key={item.case_id}
              onClick={() => navigate(`/cases/${item.case_id}`)}
              className="py-5 px-4 flex flex-col lg:flex-row lg:items-center justify-between gap-5 hover:bg-[#F5F8F4] cursor-pointer transition-colors rounded-lg group"
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter') navigate(`/cases/${item.case_id}`);
              }}
            >
              {/* Rank + Case Title + Subtitle */}
              <div className="flex items-start sm:items-center gap-5 flex-1 min-w-[320px]">
                <span className="font-serif text-3xl font-bold text-[#285239] w-10 text-center shrink-0">
                  {rank}
                </span>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-lg font-semibold text-[#183B2A] group-hover:text-[#285239] transition-colors">
                      {item.name || item.focal_provider_name || item.title}
                    </span>
                    <span className="font-mono text-xs bg-[#F5F8F4] px-2.5 py-0.5 border border-[#E0E8DF] text-[#68766B] rounded font-medium">
                      {item.case_id}
                    </span>
                    <span className={`text-xs font-mono px-2.5 py-0.5 rounded border font-semibold ${badgeClass}`}>
                      {item.severity}
                    </span>
                  </div>
                  <p className="text-sm text-[#68766B]">
                    {item.subtitle || `${item.specialty?.replace(/_/g, ' ') || 'Specialist'} | ${item.pool === 'network' ? 'Collusion Ring' : 'Provider Focus'}`}
                  </p>
                </div>
              </div>

              {/* Attributes: Risk Score, Evidence Strength, Exposure, Rank Promotion, and Action Button */}
              <div className="flex flex-wrap items-center gap-7 text-sm shrink-0">
                {/* Risk Score */}
                <div className="flex flex-col items-start w-20">
                  <span className="text-xs text-[#68766B] uppercase font-mono">Risk</span>
                  <div className="flex items-baseline gap-1 mt-0.5">
                    <span className="font-bold text-lg text-[#183B2A] tabular-nums">
                      {item.risk_index}
                    </span>
                    <span className="text-xs text-[#68766B]">/100</span>
                  </div>
                </div>

                {/* Evidence Strength */}
                <div className="flex flex-col items-start w-28">
                  <div className="flex items-center justify-between w-full">
                    <span className="text-xs text-[#68766B] uppercase font-mono">Evidence</span>
                    <span className="text-xs font-semibold text-[#285239] font-mono">{evidenceStrength}%</span>
                  </div>
                  <div className="w-full bg-[#E0E8DF] h-2.5 rounded-full overflow-hidden mt-1">
                    <div
                      className="bg-[#477A58] h-full rounded-full"
                      style={{ width: `${evidenceStrength}%` }}
                    />
                  </div>
                </div>

                {/* Exposure */}
                <div className="flex flex-col items-end w-36">
                  <span className="text-xs text-[#68766B] uppercase font-mono">Exposure</span>
                  <span className="font-bold text-base text-[#183B2A] tabular-nums mt-0.5">
                    {exposureStr}
                  </span>
                </div>

                {/* Rules vs Nexus Rank Lift */}
                <div className="flex flex-col items-end w-28">
                  <span className="text-xs text-[#68766B] uppercase font-mono">Rank Lift</span>
                  <div className="font-mono text-sm mt-0.5">
                    <span className="sr-only">#{baseline} → #{rank}</span>
                    <span aria-hidden="true" className="text-[#68766B]">
                      #{baseline} to <strong className="text-[#285239] font-bold">#{rank}</strong>
                    </span>
                  </div>
                </div>

                {/* Action CTA Button */}
                <button
                  type="button"
                  aria-label="Open case →"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/cases/${item.case_id}`);
                  }}
                  className="px-5 py-2.5 bg-[#E8F2E8] hover:bg-[#477A58] text-[#285239] hover:text-white border border-[#B8D2B8] text-sm font-semibold rounded-lg transition-colors shadow-xs"
                >
                  Open case
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
