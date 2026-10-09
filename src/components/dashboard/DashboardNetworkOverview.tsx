import React from 'react';
import { Link } from 'react-router-dom';

export const DashboardNetworkOverview: React.FC = () => {
  return (
    <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-6 shadow-xs">
      <div className="border-b border-[#E0E8DF] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl font-bold text-[#183B2A] tracking-tight">
            Network Intelligence Overview
          </h2>
          <p className="text-base text-[#68766B] mt-1">
            Bipartite graph projection and Louvain community detection identifying organized collusion rings.
          </p>
        </div>
        <Link
          to="/networks/NET-RING-001"
          className="text-base font-semibold text-[#285239] hover:text-[#183B2A] transition-colors shrink-0"
        >
          Explore Network Intelligence
        </Link>
      </div>

      {/* Spacious 3-Column Text-Based Key Metric Overview (Zero Icons) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 bg-[#F5F8F4] border border-[#E0E8DF] rounded-xl space-y-2">
          <span className="text-xs font-mono uppercase tracking-wider text-[#68766B] font-semibold">
            Detected Communities
          </span>
          <div className="font-serif text-3xl font-bold text-[#183B2A]">
            5 Rings
          </div>
          <p className="text-sm text-[#68766B] leading-relaxed">
            Louvain modularity score 0.72 indicating tightly bound billing subgraphs.
          </p>
        </div>

        <div className="p-6 bg-[#F5F8F4] border border-[#E0E8DF] rounded-xl space-y-2">
          <span className="text-xs font-mono uppercase tracking-wider text-[#68766B] font-semibold">
            Linked Providers
          </span>
          <div className="font-serif text-3xl font-bold text-[#183B2A]">
            16 Providers
          </div>
          <p className="text-sm text-[#68766B] leading-relaxed">
            Resolved entities co-linked via shared banking hashes, tax IDs, and billing addresses.
          </p>
        </div>

        <div className="p-6 bg-[#F5F8F4] border border-[#E0E8DF] rounded-xl space-y-2">
          <span className="text-xs font-mono uppercase tracking-wider text-[#68766B] font-semibold">
            Collusion Exposure
          </span>
          <div className="font-serif text-3xl font-bold text-[#B91C1C]">
            $1.84M
          </div>
          <p className="text-sm text-[#68766B] leading-relaxed">
            Represents 41% of total identified financial exposure across the priority queue.
          </p>
        </div>
      </div>
    </div>
  );
};
