import React from 'react';

export const DashboardWhyNexus: React.FC = () => {
  return (
    <div
      data-testid="dashboard-why-nexus"
      className="bg-white border border-[#D3E0D6] rounded-[3px] p-5 space-y-4"
    >
      <div className="border-b border-[#D3E0D6] pb-2">
        <h2 className="font-serif text-[1.25rem] font-semibold text-[#0B1A12]">
          Why Nexus Changes the Order
        </h2>
        <p className="text-[0.875rem] text-[#4F5F55] mt-0.5">
          How capacity matching and network entity resolution optimize investigation sequencing over static rule thresholds.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[0.875rem]">
        {/* 1. Capacity-Aware Prioritization */}
        <div className="p-3.5 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[3px] space-y-1.5">
          <strong className="text-[#1B3A29] font-semibold block text-[0.9375rem]">
            1. Capacity-Aware Prioritization
          </strong>
          <p className="text-[#4F5F55] text-[0.8125rem] leading-relaxed">
            High-complexity multi-provider networks (e.g. 31h effort) are dynamically prioritized when specialist hours are budgeted, preventing unworked alerts from expiring.
          </p>
        </div>

        {/* 2. Network Context */}
        <div className="p-3.5 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[3px] space-y-1.5">
          <strong className="text-[#1B3A29] font-semibold block text-[0.9375rem]">
            2. Network Context & Entity Resolution
          </strong>
          <p className="text-[#4F5F55] text-[0.8125rem] leading-relaxed">
            Shared banking hash (<code>9a8b7c6d5e4f3a21</code>) and parent ownership link 6 providers together, promoting ring coordinators over isolated single-provider rule flags.
          </p>
        </div>

        {/* 3. Evidence Strength */}
        <div className="p-3.5 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[3px] space-y-1.5">
          <strong className="text-[#1B3A29] font-semibold block text-[0.9375rem]">
            3. Multi-Rule Evidence Cross-Corroboration
          </strong>
          <p className="text-[#4F5F55] text-[0.8125rem] leading-relaxed">
            Corroborates 5 concurrent indicators (timing velocity, referral loops, same-day lab surges, banking rings, and burst billing) into a single unified dossier.
          </p>
        </div>

        {/* 4. Investigator Effort Allocation */}
        <div className="p-3.5 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[3px] space-y-1.5">
          <strong className="text-[#1B3A29] font-semibold block text-[0.9375rem]">
            4. Exposure Yield per Investigation Hour
          </strong>
          <p className="text-[#4F5F55] text-[0.8125rem] leading-relaxed">
            Sequences investigations to maximize identifiable overpayment exposure per investigator hour within available generalist and specialist capacity.
          </p>
        </div>
      </div>
    </div>
  );
};
