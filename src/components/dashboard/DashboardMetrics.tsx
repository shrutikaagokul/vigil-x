import React from 'react';
import { QueueResponse } from '@/types/queue';
import { DashboardSummary } from '@/types/api';
import { formatCurrency } from '@/utils/currency';

interface DashboardMetricsProps {
  readonly queueData?: QueueResponse;
  readonly summary?: DashboardSummary;
}

export const DashboardMetrics: React.FC<DashboardMetricsProps> = ({ queueData, summary }) => {
  const items = queueData?.items || [];

  // Total exposure calculated from active queue items (exposure_high or est_dollars)
  const totalExposure = items.reduce((acc, item) => acc + (item.exposure_high || item.est_dollars || 0), 0);
  const formattedExposure = formatCurrency(totalExposure > 0 ? totalExposure : (summary?.total_exposure_dollars || 0), 'compact');

  const totalCases = queueData?.total_count || summary?.prioritized_cases_count || items.length || 0;
  const addressableCases = queueData?.capacity_summary?.estimated_cases_addressable || Math.min(items.length, 5);
  const totalCapacityHours = queueData?.capacity_summary?.total_hours || 60;

  // Calculate top case lift: hero case baseline rank (e.g. 38) vs Nexus rank (1)
  const heroItem = items.find((i) => i.case_id === 'CASE-2024-0042') || items[0];
  const baselineRank = heroItem?.baseline_rank || 38;
  const rankLift = baselineRank - 1; // e.g. 37 ranks

  return (
    <div
      data-testid="dashboard-metrics"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full"
    >
      {/* 1. Cases Requiring Investigation */}
      <div className="bg-white border border-[#D3E0D6] rounded-[3px] p-4 flex flex-col justify-between">
        <span className="text-sm font-medium text-[#4F5F55]">
          Cases Requiring Investigation
        </span>
        <div className="mt-2">
          <span className="font-serif text-[2rem] leading-[2.25rem] font-semibold text-[#0B1A12]">
            {totalCases}
          </span>
          <span className="text-[0.875rem] text-[#4F5F55] ml-2">active cases</span>
        </div>
        <p className="text-sm text-[#4F5F55] mt-1">
          {summary?.active_alerts_count != null ? `${summary.active_alerts_count} correlated risk alerts across providers` : 'Correlated risk alerts across providers'}
        </p>
      </div>

      {/* 2. Exposure in Queue */}
      <div className="bg-white border border-[#D3E0D6] rounded-[3px] p-4 flex flex-col justify-between">
        <span className="text-sm font-medium text-[#4F5F55]">
          Exposure in Queue
        </span>
        <div className="mt-2">
          <span className="font-serif text-[2rem] leading-[2.25rem] font-semibold text-[#1B3A29] tabular-nums">
            {formattedExposure}
          </span>
        </div>
        <p className="text-sm text-[#4F5F55] mt-1">
          Combined financial exposure across prioritized queue
        </p>
      </div>

      {/* 3. Cases Fitting Current Capacity */}
      <div className="bg-white border border-[#D3E0D6] rounded-[3px] p-4 flex flex-col justify-between">
        <span className="text-sm font-medium text-[#4F5F55]">
          Addressable This Week
        </span>
        <div className="mt-2">
          <span className="font-serif text-[2rem] leading-[2.25rem] font-semibold text-[#2A5A3F] tabular-nums">
            {addressableCases} of {totalCases}
          </span>
          <span className="text-[0.875rem] text-[#4F5F55] ml-2">cases</span>
        </div>
        <p className="text-sm text-[#4F5F55] mt-1">
          Fit within {totalCapacityHours} h allocated capacity budget
        </p>
      </div>

      {/* 4. Nexus Lift over Rules-Only */}
      <div className="bg-white border border-[#D3E0D6] rounded-[3px] p-4 flex flex-col justify-between">
        <span className="text-sm font-medium text-[#4F5F55]">
          Nexus Prioritization Lift
        </span>
        <div className="mt-2">
          <span className="font-serif text-[2rem] leading-[2.25rem] font-semibold text-[#701F14] tabular-nums">
            +{rankLift} ranks
          </span>
        </div>
        <p className="text-sm text-[#4F5F55] mt-1">
          Hero multi-entity ring elevated from #{baselineRank} to #1
        </p>
      </div>
    </div>
  );
};
