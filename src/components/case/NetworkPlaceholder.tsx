import React from 'react';
import { Link } from 'react-router-dom';
import { Network } from '@/types/network';

interface NetworkPlaceholderProps {
  readonly network?: Network;
  readonly caseId?: string;
}

export const NetworkPlaceholder: React.FC<NetworkPlaceholderProps> = ({ network, caseId }) => {
  const networkId = network?.network_id || 'NET-RING-001';

  return (
    <section className="bg-surface border border-border p-5 sm:p-6 space-y-5">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="font-serif text-lg sm:text-xl font-bold text-green-950">
            Network Subgraph Summary
          </h2>
          <p className="text-sm text-ink-muted mt-0.5 font-sans">
            Multi-provider topology, referral concentration, and shared corporate infrastructure.
          </p>
        </div>
        <span className="text-xs font-mono bg-paper-subtle border border-border px-2.5 py-1 text-green-950 font-semibold shrink-0">
          ID: {networkId}
        </span>
      </div>

      {/* Narrative Explanation of Why Network Matters */}
      <div className="p-4 bg-paper-subtle border border-border space-y-2">
        <span className="text-[11px] font-mono font-bold text-green-950 uppercase tracking-wider block">
          Network Prioritization Rationale
        </span>
        <p className="text-sm sm:text-base text-ink leading-relaxed font-sans font-normal">
          {network?.description ||
            'Entity resolution and Louvain community detection link this case to an underlying multi-provider relationship subgraph. Cross-provider referral cycles and shared financial infrastructure indicate coordinated billing velocity.'}
        </p>
      </div>

      {/* Network Quantitative Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="bg-paper-subtle p-3.5 border border-border">
          <span className="text-[11px] font-mono text-ink-subtle uppercase block">
            Entities (Nodes)
          </span>
          <span className="font-serif text-2xl font-bold text-green-950 block mt-1">
            {network?.summary?.n_nodes ?? 6}
          </span>
          <span className="text-[11px] text-ink-muted mt-0.5 block font-sans">
            Affiliated Providers &amp; Entities
          </span>
        </div>

        <div className="bg-paper-subtle p-3.5 border border-border">
          <span className="text-[11px] font-mono text-ink-subtle uppercase block">
            Relationships (Edges)
          </span>
          <span className="font-serif text-2xl font-bold text-green-950 block mt-1">
            {network?.summary?.n_edges ?? 14}
          </span>
          <span className="text-[11px] text-ink-muted mt-0.5 block font-sans">
            Referral &amp; Corporate Links
          </span>
        </div>

        <div className="bg-paper-subtle p-3.5 border border-border">
          <span className="text-[11px] font-mono text-ink-subtle uppercase block">
            Patient Cohorts
          </span>
          <span className="font-serif text-2xl font-bold text-green-950 block mt-1">
            {network?.summary?.n_cohorts ?? 3}
          </span>
          <span className="text-[11px] text-ink-muted mt-0.5 block font-sans">
            Co-Billed Member Clusters
          </span>
        </div>

        <div className="bg-paper-subtle p-3.5 border border-border">
          <span className="text-[11px] font-mono text-ink-subtle uppercase block">
            Shared Members
          </span>
          <span className="font-serif text-2xl font-bold text-green-950 block mt-1">
            {network?.summary?.total_members ?? 48}
          </span>
          <span className="text-[11px] text-ink-muted mt-0.5 block font-sans">
            Cross-Provider Patients
          </span>
        </div>
      </div>

      {/* CTA Box linking to full Network Page */}
      <div className="p-4 bg-paper-subtle border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <strong className="text-green-950 font-bold block text-sm font-sans">
            Interactive Network Investigation Canvas
          </strong>
          <p className="text-xs text-ink-muted leading-relaxed font-sans">
            Explore 6-provider ring topology, shared bank account hashes, and referral flows on the dedicated Network Investigation workstation.
          </p>
        </div>

        <Link
          to={`/networks/${networkId}${caseId ? `?caseId=${caseId}` : ''}`}
          className="inline-flex items-center justify-center px-5 py-2.5 bg-green-800 text-white hover:bg-green-900 text-sm font-semibold border border-green-700 transition-colors shrink-0 rounded-md"
        >
          Open Full Network Investigation
        </Link>
      </div>
    </section>
  );
};
