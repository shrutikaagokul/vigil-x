import React from 'react';

export const DashboardWhyNexus: React.FC = () => {
  return (
    <div
      data-testid="dashboard-why-nexus"
      className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-6 shadow-xs"
    >
      <div className="border-b border-[#E0E8DF] pb-4">
        <h2 className="font-serif text-2xl font-bold text-[#183B2A] tracking-tight">
          Why Nexus Changes the Order
        </h2>
        <p className="text-base text-[#68766B] mt-1">
          How capacity matching and network entity resolution optimize investigation sequencing over static rule thresholds.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-base">
        {/* 1. Capacity-Aware Prioritization */}
        <div className="p-6 bg-[#F5F8F4] border border-[#E0E8DF] rounded-xl space-y-2 hover:border-[#B8D2B8] transition-colors">
          <strong className="text-[#285239] font-bold text-lg block">
            1. Capacity-Aware Prioritization
          </strong>
          <p className="text-[#68766B] leading-relaxed">
            High-complexity multi-provider networks (e.g. 31h effort) are dynamically prioritized when specialist hours are budgeted, preventing unworked alerts from expiring.
          </p>
        </div>

        {/* 2. Network Context */}
        <div className="p-6 bg-[#F5F8F4] border border-[#E0E8DF] rounded-xl space-y-2 hover:border-[#B8D2B8] transition-colors">
          <strong className="text-[#0369A1] font-bold text-lg block">
            2. Network Context & Entity Resolution
          </strong>
          <p className="text-[#68766B] leading-relaxed">
            Shared banking hash (<code className="text-[#183B2A] font-mono bg-white px-1.5 py-0.5 rounded border border-[#E0E8DF]">9a8b7c6d5e4f3a21</code>) and parent ownership link 6 providers together, promoting ring coordinators over isolated single-provider rule flags.
          </p>
        </div>

        {/* 3. Evidence Strength */}
        <div className="p-6 bg-[#F5F8F4] border border-[#E0E8DF] rounded-xl space-y-2 hover:border-[#B8D2B8] transition-colors">
          <strong className="text-[#B45309] font-bold text-lg block">
            3. Multi-Rule Evidence Cross-Corroboration
          </strong>
          <p className="text-[#68766B] leading-relaxed">
            Corroborates 5 concurrent indicators (timing velocity, referral loops, same-day lab surges, banking rings, and burst billing) into a single unified dossier.
          </p>
        </div>

        {/* 4. Investigator Effort Allocation */}
        <div className="p-6 bg-[#F5F8F4] border border-[#E0E8DF] rounded-xl space-y-2 hover:border-[#B8D2B8] transition-colors">
          <strong className="text-[#285239] font-bold text-lg block">
            4. Exposure Yield per Investigation Hour
          </strong>
          <p className="text-[#68766B] leading-relaxed">
            Sequences investigations to maximize identifiable overpayment exposure per investigator hour within available generalist and specialist capacity.
          </p>
        </div>
      </div>
    </div>
  );
};
