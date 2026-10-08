import React from 'react';

export const NetworkLegend: React.FC = () => {
  return (
    <div
      data-testid="network-legend"
      className="bg-[#0B1A12]/90 backdrop-blur-none border border-[#2A5A3F] rounded-[3px] p-3 text-white text-[0.75rem] space-y-2 select-none"
    >
      <div className="font-semibold text-[#A9CFB0] tracking-wide uppercase text-[0.6875rem] border-b border-[#2A5A3F] pb-1">
        Legend
      </div>

      {/* Entity Nodes */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-[#A9CFB0] border border-[#0B1A12] shrink-0" />
          <span className="text-[#E3EFE5]">Provider</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-[1px] bg-[#8FA396] border border-[#0B1A12] shrink-0" />
          <span className="text-[#E3EFE5]">Facility</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rotate-45 bg-[#B38A2E] border border-[#0B1A12] shrink-0" />
          <span className="text-[#E3EFE5]">Owner / Bank Account</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-[#6B7E72] border border-[#0B1A12] shrink-0" />
          <span className="text-[#E3EFE5]">Member</span>
        </div>
      </div>

      <div className="border-t border-[#2A5A3F] pt-1.5 space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="w-4 h-[2px] bg-[#A9CFB0] shrink-0" />
          <span className="text-[#E3EFE5]">Solid (Verified Link)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-4 h-[2px] border-b-2 border-dashed border-[#B38A2E] shrink-0" />
          <span className="text-[#E3EFE5]">Dashed (Referral Ring)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-4 h-[2px] border-b-2 border-dotted border-[#9E3626] shrink-0" />
          <span className="text-[#E3EFE5]">Dotted (Same-Day Lab)</span>
        </div>
      </div>
    </div>
  );
};
