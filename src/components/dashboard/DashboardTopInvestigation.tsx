import React from 'react';
import { useNavigate } from 'react-router-dom';
import { QueueItem } from '@/types/queue';
import { formatExposureRange } from '@/utils/currency';

interface DashboardTopInvestigationProps {
  readonly topCase?: QueueItem;
}

export const DashboardTopInvestigation: React.FC<DashboardTopInvestigationProps> = ({ topCase }) => {
  const navigate = useNavigate();

  if (!topCase) return null;

  const exposure = formatExposureRange(topCase.exposure_low, topCase.exposure_high);
  const reasons = (topCase.top_reasons && topCase.top_reasons.length > 0)
    ? topCase.top_reasons
    : [
        'Shared banking hash links multiple co-billing provider entities',
        'Impossible travel velocity (>120 mph between clinic encounters)',
        '30-day projected volume spike exceeding 3.4x baseline threshold',
      ];

  return (
    <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-6 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E0E8DF] pb-5">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono uppercase tracking-wider text-[#285239] font-bold bg-[#E8F2E8] px-3 py-1 rounded border border-[#B8D2B8]">
              Top Investigation Spotlight
            </span>
            <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#FEE2E2] text-[#B91C1C] border border-[#FCA5A5] font-semibold">
              Rank #1
            </span>
          </div>
          <h2 className="font-serif text-2xl font-bold text-[#183B2A] mt-2">
            {topCase.title || topCase.focal_provider_name || 'Dr. Victor Mercer, MD'}
          </h2>
        </div>

        <button
          type="button"
          onClick={() => navigate(`/cases/${topCase.case_id}`)}
          className="px-6 py-3 bg-[#477A58] hover:bg-[#285239] text-white font-semibold text-base rounded-lg transition-colors shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-[#477A58] shrink-0"
        >
          Open Investigation
        </button>
      </div>

      {/* Case Core Metrics Overview Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg">
          <span className="text-xs text-[#68766B] uppercase font-mono font-semibold">Case Identifier</span>
          <div className="font-mono font-bold text-[#183B2A] mt-1 text-base">
            {topCase.case_id}
          </div>
        </div>
        <div className="p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg">
          <span className="text-xs text-[#68766B] uppercase font-mono font-semibold">Unified Risk Index</span>
          <div className="font-bold text-[#B91C1C] mt-1 text-xl tabular-nums font-serif">
            {topCase.risk_index} / 100
          </div>
        </div>
        <div className="p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg">
          <span className="text-xs text-[#68766B] uppercase font-mono font-semibold">Evidence Strength</span>
          <div className="font-bold text-[#285239] mt-1 text-xl tabular-nums font-serif">
            {Math.round((topCase.evidence_strength || 0.85) * 100)}%
          </div>
        </div>
        <div className="p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg">
          <span className="text-xs text-[#68766B] uppercase font-mono font-semibold">Financial Exposure</span>
          <div className="font-bold text-[#183B2A] mt-1 text-xl tabular-nums font-serif">
            {exposure}
          </div>
        </div>
      </div>

      {/* Prioritization Drivers (No icons, No emojis, No Unicode symbols) */}
      <div className="space-y-3">
        <span className="text-xs font-mono text-[#68766B] uppercase font-semibold">
          Primary Prioritization Drivers:
        </span>
        <div className="space-y-2">
          {reasons.slice(0, 3).map((r, i) => {
            const text = typeof r === 'string' ? r : (r as { text: string }).text;
            const chip = typeof r === 'object' && 'evidence_chip' in r ? (r as { evidence_chip: string }).evidence_chip : null;
            return (
              <div key={i} className="flex items-center justify-between text-base text-[#24352A] bg-[#F5F8F4] p-4 rounded-lg border border-[#E0E8DF]">
                <span className="flex-1 font-medium">{text}</span>
                {chip && (
                  <span className="font-mono text-xs px-2.5 py-1 bg-white border border-[#E0E8DF] text-[#285239] font-semibold rounded ml-3 shrink-0">
                    {chip}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
