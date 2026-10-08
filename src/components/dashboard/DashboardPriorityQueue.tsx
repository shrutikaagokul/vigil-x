import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { QueueItem } from '@/types/queue';
import { formatExposureRange } from '@/utils/currency';

interface DashboardPriorityQueueProps {
  readonly items: readonly QueueItem[];
}

function getSeverityColor(severity: string): string {
  switch (severity?.toUpperCase()) {
    case 'CRITICAL':
      return 'bg-[#701F14]';
    case 'HIGH':
      return 'bg-[#9E3626]';
    case 'MEDIUM':
      return 'bg-[#B38A2E]';
    case 'LOW':
    default:
      return 'bg-[#4C8C5E]';
  }
}

export const DashboardPriorityQueue: React.FC<DashboardPriorityQueueProps> = ({ items }) => {
  const navigate = useNavigate();
  const topItems = items.slice(0, 3);

  return (
    <div
      data-testid="dashboard-priority-queue"
      className="bg-white border border-[#D3E0D6] rounded-[3px] p-5 space-y-4"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#D3E0D6] pb-3">
        <div>
          <h2 className="font-serif text-[1.375rem] font-semibold text-[#0B1A12]">
            Priority Queue
          </h2>
          <p className="text-[0.875rem] text-[#4F5F55] mt-0.5">
            Top investigations prioritized for immediate investigator action based on capacity and multi-entity risk.
          </p>
        </div>

        <Link
          to="/queue"
          className="inline-flex items-center text-[0.875rem] font-semibold text-[#2A5A3F] hover:underline shrink-0"
        >
          View full queue ({items.length} cases) →
        </Link>
      </div>

      {/* Cases List */}
      <div className="divide-y divide-[#D3E0D6] -my-2">
        {topItems.map((item, idx) => {
          const rank = idx + 1;
          const baseline = item.baseline_rank || (rank === 1 ? 38 : rank === 2 ? 12 : 21);
          const exposureStr = formatExposureRange(item.exposure_low, item.exposure_high);

          return (
            <div
              key={item.case_id}
              onClick={() => navigate(`/cases/${item.case_id}`)}
              className="py-3.5 px-2 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-[#E3EFE5]/40 cursor-pointer transition-colors rounded-[2px]"
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter') navigate(`/cases/${item.case_id}`);
              }}
            >
              {/* Rank + Case Title */}
              <div className="flex items-center gap-4 min-w-[280px] flex-1">
                <span className="font-serif text-[1.75rem] font-semibold text-[#1B3A29] w-8 text-center shrink-0">
                  {rank}
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[1.0625rem] font-semibold text-[#0B1A12]">
                      {item.name || item.focal_provider_name || item.title}
                    </span>
                    <span className="font-mono text-[0.75rem] bg-[#F3F8F4] px-1.5 py-0.5 border border-[#D3E0D6] text-[#4F5F55] rounded-[2px]">
                      {item.case_id}
                    </span>
                  </div>
                  <p className="text-[0.875rem] text-[#4F5F55] mt-0.5">
                    {item.subtitle || `${item.specialty?.replace(/_/g, ' ')} · ${item.pool === 'network' ? 'Network case' : 'Single provider'}`}
                  </p>
                </div>
              </div>

              {/* Attributes: Risk, Exposure, Effort, Rank Promotion */}
              <div className="flex flex-wrap items-center gap-6 text-[0.875rem] shrink-0">
                {/* Risk */}
                <div className="flex items-center gap-1.5 w-20">
                  <span className={`w-3 h-3 rounded-full shrink-0 ${getSeverityColor(item.severity)}`} />
                  <span className="font-semibold text-[1.125rem] text-[#0B1A12] tabular-nums">
                    {item.risk_index}
                  </span>
                </div>

                {/* Exposure */}
                <div className="w-36 text-right font-semibold text-[#0B1A12] tabular-nums">
                  {exposureStr}
                </div>

                {/* Effort */}
                <div className="w-16 text-right text-[#4F5F55] font-medium">
                  {item.effort_hours || 10} h
                </div>

                {/* Rules vs Nexus Rank */}
                <div className="w-24 text-right">
                  <span className="text-[#4F5F55]">#{baseline} → </span>
                  <strong className="text-[#1B3A29] font-bold">#{rank}</strong>
                </div>

                {/* CTA */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/cases/${item.case_id}`);
                  }}
                  className="px-3 py-1 bg-[#2A5A3F] text-white hover:bg-[#1B3A29] text-[0.8125rem] font-semibold rounded-[3px] transition-colors"
                >
                  Open case →
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
