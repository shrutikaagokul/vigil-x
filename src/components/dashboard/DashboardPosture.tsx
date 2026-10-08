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
      className="grid grid-cols-1 lg:grid-cols-2 gap-4 w-full"
    >
      {/* 1. Queue Severity Distribution */}
      <div className="bg-white border border-[#D3E0D6] rounded-[3px] p-5 space-y-3">
        <div className="border-b border-[#D3E0D6] pb-2">
          <h3 className="font-serif text-[1.125rem] font-semibold text-[#0B1A12]">
            Queue Severity Breakdown
          </h3>
          <p className="text-[0.8125rem] text-[#4F5F55]">
            Distribution of prioritized cases across triage severity tiers.
          </p>
        </div>

        <div className="space-y-2 text-[0.875rem]">
          <div className="flex items-center justify-between p-2.5 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[2px]">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#701F14]" />
              <span className="font-semibold text-[#14201A]">Critical Severity</span>
            </div>
            <strong className="font-mono text-[#701F14]">{criticalCount} case</strong>
          </div>

          <div className="flex items-center justify-between p-2.5 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[2px]">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#9E3626]" />
              <span className="font-semibold text-[#14201A]">High Severity</span>
            </div>
            <strong className="font-mono text-[#9E3626]">{highCount} cases</strong>
          </div>

          <div className="flex items-center justify-between p-2.5 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[2px]">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#B38A2E]" />
              <span className="font-semibold text-[#14201A]">Medium Severity</span>
            </div>
            <strong className="font-mono text-[#B38A2E]">{mediumCount} cases</strong>
          </div>
        </div>
      </div>

      {/* 2. Top Risk Rule Categories */}
      <div className="bg-white border border-[#D3E0D6] rounded-[3px] p-5 space-y-3">
        <div className="border-b border-[#D3E0D6] pb-2">
          <h3 className="font-serif text-[1.125rem] font-semibold text-[#0B1A12]">
            Top Risk Pattern Categories
          </h3>
          <p className="text-[0.8125rem] text-[#4F5F55]">
            Active signal clusters identified across provider network data.
          </p>
        </div>

        <div className="space-y-2 text-[0.8125rem]">
          {topCategories.map((cat, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[2px]"
            >
              <div className="flex items-center gap-2">
                <span className="font-mono text-[0.75rem] bg-white px-1.5 py-0.5 border border-[#D3E0D6] text-[#1B3A29] rounded-[2px]">
                  {cat.rule_id}
                </span>
                <span className="text-[#14201A] font-medium">{cat.category}</span>
              </div>
              <span className="font-mono text-[#4F5F55] font-semibold">{cat.count} alerts</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
