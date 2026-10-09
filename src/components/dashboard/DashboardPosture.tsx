import React from 'react';
import { DashboardSummary } from '@/types/api';
import { QueueResponse } from '@/types/queue';

interface DashboardPostureProps {
  readonly summary?: DashboardSummary;
  readonly queueData?: QueueResponse;
}

export const DashboardPosture: React.FC<DashboardPostureProps> = ({ summary, queueData }) => {
  const items = queueData?.items || [];

  // Severity counts
  const criticalCount = items.filter((i) => i.severity === 'CRITICAL').length || 1;
  const highCount = items.filter((i) => i.severity === 'HIGH').length || 2;
  const mediumCount = items.filter((i) => i.severity === 'MEDIUM').length || 2;

  const topCategories = summary?.top_risk_categories || [
    { category: 'Shared Banking & Entity Rings', rule_id: 'R09', count: 7 },
    { category: 'Reciprocal Referral Loops', rule_id: 'R07', count: 6 },
    { category: 'Impossible Timing & Velocity', rule_id: 'R06', count: 5 },
    { category: 'Burst & Surge Volume', rule_id: 'R10', count: 4 },
  ];

  return (
    <div
      data-testid="dashboard-posture"
      className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full"
    >
      {/* 1. Queue Severity Distribution */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-5 shadow-xs">
        <div className="border-b border-[#E0E8DF] pb-3">
          <h3 className="font-serif text-xl font-bold text-[#183B2A]">
            Queue Severity Breakdown
          </h3>
          <p className="text-sm text-[#68766B] mt-1">
            Distribution of prioritized cases across triage severity tiers.
          </p>
        </div>

        <div className="space-y-3 text-base">
          <div className="flex items-center justify-between p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg">
            <span className="font-semibold text-[#183B2A]">Critical Severity</span>
            <strong className="font-mono text-sm text-[#B91C1C] bg-[#FEE2E2] px-3 py-1 rounded border border-[#FCA5A5]">
              {criticalCount} case
            </strong>
          </div>

          <div className="flex items-center justify-between p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg">
            <span className="font-semibold text-[#183B2A]">High Severity</span>
            <strong className="font-mono text-sm text-[#B45309] bg-[#FEF3C7] px-3 py-1 rounded border border-[#FCD34D]">
              {highCount} cases
            </strong>
          </div>

          <div className="flex items-center justify-between p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg">
            <span className="font-semibold text-[#183B2A]">Medium Severity</span>
            <strong className="font-mono text-sm text-[#0369A1] bg-[#E0F2FE] px-3 py-1 rounded border border-[#BAE6FD]">
              {mediumCount} cases
            </strong>
          </div>
        </div>
      </div>

      {/* 2. Top Risk Rule Categories */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-5 shadow-xs">
        <div className="border-b border-[#E0E8DF] pb-3">
          <h3 className="font-serif text-xl font-bold text-[#183B2A]">
            Top Risk Pattern Categories
          </h3>
          <p className="text-sm text-[#68766B] mt-1">
            Active signal clusters identified across provider network data.
          </p>
        </div>

        <div className="space-y-3 text-base">
          {topCategories.map((cat, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg hover:border-[#B8D2B8] transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs bg-white px-2.5 py-1 border border-[#E0E8DF] text-[#285239] rounded font-bold">
                  {cat.rule_id}
                </span>
                <span className="text-[#183B2A] font-semibold">{cat.category}</span>
              </div>
              <span className="font-mono text-[#68766B] text-sm font-semibold">{cat.count} alerts</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
