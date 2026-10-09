import React from 'react';
import { Link } from 'react-router-dom';
import { Network } from '@/types/network';

interface NetworkHeaderProps {
  readonly network: Network;
  readonly linkedCaseId?: string | null;
}

export const NetworkHeader: React.FC<NetworkHeaderProps> = ({ network, linkedCaseId }) => {
  const summary = network.summary || {
    n_nodes: network.nodes?.length || 0,
    n_edges: network.edges?.length || 0,
    n_cohorts: network.cohorts?.length || 0,
    total_members: 0,
  };

  const caseId = linkedCaseId || (network.network_id === 'NET-RING-001' ? 'CASE-2024-0042' : null);

  return (
    <div className="w-full pt-6 pb-4 px-6 md:px-12 border-b border-[#D3E0D6] bg-[#F3F8F4]">
      {/* Case Context Link / Breadcrumb */}
      {caseId && (
        <div className="flex items-center gap-2 mb-2">
          <Link
            to={`/cases/${caseId}`}
            className="text-base font-medium text-[#2A5A3F] hover:underline flex items-center gap-1.5"
          >
            <span className="sr-only">← Back to Case </span>
            <span aria-hidden="true">Back to Case </span>
            <strong className="font-mono text-[#0B1A12]">{caseId}</strong>
          </Link>
          <span className="text-[#8A969C]">·</span>
          <span className="text-[0.8125rem] text-[#4F5F55] font-normal">
            Network investigation view
          </span>
        </div>
      )}

      {/* Main Header Row */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-serif text-[1.75rem] leading-[2rem] font-semibold text-[#0B1A12] tracking-tight">
              Network Investigation
            </h1>
            <span
              data-testid="network-id-badge"
              className="px-2.5 py-0.5 text-[0.8125rem] font-mono font-medium bg-[#E3EFE5] text-[#1B3A29] border border-[#D3E0D6] rounded-[3px]"
            >
              {network.network_id || 'NET-RING-001'}
            </span>
            {network.focal_entity && (
              <span className="text-[0.8125rem] text-[#4F5F55]">
                Focal: <strong className="font-mono text-[#14201A]">{network.focal_entity}</strong>
              </span>
            )}
          </div>
          {network.description && (
            <p className="text-[0.9375rem] text-[#4F5F55] mt-1 font-normal max-w-3xl">
              {network.description}
            </p>
          )}
        </div>

        {/* Compact Fact Strip */}
        <div
          data-testid="network-fact-strip"
          className="flex flex-wrap items-center gap-2 text-[0.8125rem] bg-white border border-[#D3E0D6] rounded-[3px] p-1.5 px-3 shrink-0"
        >
          <div className="flex items-center gap-1.5">
            <span className="text-[#4F5F55]">Nodes:</span>
            <strong className="font-mono text-[#0B1A12]">{summary.n_nodes}</strong>
          </div>
          <span className="text-[#D3E0D6]">|</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[#4F5F55]">Relationships:</span>
            <strong className="font-mono text-[#0B1A12]">{summary.n_edges}</strong>
          </div>
          <span className="text-[#D3E0D6]">|</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[#4F5F55]">Cohorts:</span>
            <strong className="font-mono text-[#0B1A12]">{summary.n_cohorts}</strong>
          </div>
          <span className="text-[#D3E0D6]">|</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[#4F5F55]">Members Affected:</span>
            <strong className="font-mono text-[#0B1A12]">{summary.total_members}</strong>
          </div>
        </div>
      </div>
    </div>
  );
};
