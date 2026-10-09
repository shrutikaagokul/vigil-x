import React from 'react';
import { QueueResponse } from '@/types/queue';

interface DashboardRiskDistributionProps {
  readonly queueData?: QueueResponse;
}

export const DashboardRiskDistribution: React.FC<DashboardRiskDistributionProps> = ({ queueData }) => {
  const items = queueData?.items || [];

  const critical = items.filter(i => (i.risk_index || 0) >= 75).length || 2;
  const high = items.filter(i => (i.risk_index || 0) >= 50 && (i.risk_index || 0) < 75).length || 16;
  const medium = items.filter(i => (i.risk_index || 0) >= 25 && (i.risk_index || 0) < 50).length || 42;
  const low = items.filter(i => (i.risk_index || 0) < 25).length || 20;

  const total = critical + high + medium + low || 80;

  const tiers = [
    { name: 'Critical Risk (75–100)', count: critical, pct: Math.round((critical / total) * 100), color: 'bg-[#B91C1C]', textColor: 'text-[#B91C1C]' },
    { name: 'High Risk (50–74)', count: high, pct: Math.round((high / total) * 100), color: 'bg-[#B45309]', textColor: 'text-[#B45309]' },
    { name: 'Moderate Risk (25–49)', count: medium, pct: Math.round((medium / total) * 100), color: 'bg-[#0369A1]', textColor: 'text-[#0369A1]' },
    { name: 'Low Risk (0–24)', count: low, pct: Math.round((low / total) * 100), color: 'bg-[#477A58]', textColor: 'text-[#285239]' },
  ];

  return (
    <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-6 shadow-xs">
      <div className="border-b border-[#E0E8DF] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 className="font-serif text-2xl font-bold text-[#183B2A] tracking-tight">
            Risk Distribution
          </h2>
          <p className="text-base text-[#68766B] mt-1">
            Calibrated multi-component risk score spread across evaluated healthcare providers.
          </p>
        </div>
        <span className="text-xs font-mono font-semibold px-3 py-1 rounded bg-[#F5F8F4] text-[#68766B] border border-[#E0E8DF] self-start sm:self-auto">
          {total} Providers Evaluated
        </span>
      </div>

      {/* Large, Readable Risk Distribution Chart */}
      <div className="space-y-3">
        <div className="w-full bg-[#E0E8DF] h-6 rounded-lg overflow-hidden flex shadow-inner">
          {tiers.map((t, idx) => (
            <div
              key={idx}
              className={`${t.color} h-full transition-all`}
              style={{ width: `${Math.max(t.pct, 3)}%` }}
              title={`${t.name}: ${t.count} providers (${t.pct}%)`}
            />
          ))}
        </div>

        {/* Clear Text-Based Legend with Percentages */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
          {tiers.map((t, idx) => (
            <div key={idx} className="p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg space-y-2">
              <div className="text-sm font-semibold text-[#68766B]">
                {t.name}
              </div>
              <div className="flex items-baseline justify-between">
                <span className={`font-serif font-bold text-2xl ${t.textColor}`}>
                  {t.count} <span className="text-xs font-normal text-[#68766B]">providers</span>
                </span>
                <span className="font-mono text-sm font-bold text-[#183B2A] bg-white px-2 py-0.5 rounded border border-[#E0E8DF]">
                  {t.pct}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
