import React from 'react';
import { Network } from '@/types/network';

interface NetworkPlaceholderProps {
  readonly network?: Network;
}

export const NetworkPlaceholder: React.FC<NetworkPlaceholderProps> = ({ network }) => {
  return (
    <div className="bg-surface border border-border p-4 space-y-3">
      <div className="border-b border-border pb-2 flex items-center justify-between">
        <div>
          <span className="text-[10px] font-mono text-ink-subtle uppercase tracking-wider">
            Chapter 03 · Entity Topology
          </span>
          <h2 className="font-sans text-sm sm:text-base font-bold text-green-950 uppercase tracking-wide">
            Network Subgraph Summary
          </h2>
        </div>
        <span className="text-xs font-mono bg-paper-subtle border border-border px-2 py-0.5 text-ink-muted">
          Graph Subsystem (Checkpoint 6)
        </span>
      </div>

      <p className="text-xs text-ink leading-relaxed font-normal">
        {network?.description || 'Entity resolution and Louvain community detection link this case to an underlying multi-provider relationship subgraph.'}
      </p>

      {network?.summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs">
          <div className="bg-paper-subtle p-2 border border-border">
            <span className="text-[10px] font-mono text-ink-subtle uppercase block">Entities (Nodes)</span>
            <span className="font-mono text-lg font-bold text-green-950">{network.summary.n_nodes}</span>
          </div>
          <div className="bg-paper-subtle p-2 border border-border">
            <span className="text-[10px] font-mono text-ink-subtle uppercase block">Relationships (Edges)</span>
            <span className="font-mono text-lg font-bold text-green-950">{network.summary.n_edges}</span>
          </div>
          <div className="bg-paper-subtle p-2 border border-border">
            <span className="text-[10px] font-mono text-ink-subtle uppercase block">Patient Cohorts</span>
            <span className="font-mono text-lg font-bold text-green-950">{network.summary.n_cohorts}</span>
          </div>
          <div className="bg-paper-subtle p-2 border border-border">
            <span className="text-[10px] font-mono text-ink-subtle uppercase block">Shared Members</span>
            <span className="font-mono text-lg font-bold text-green-950">{network.summary.total_members}</span>
          </div>
        </div>
      )}

      <div className="p-2.5 bg-paper-subtle border border-border text-xs text-ink-muted space-y-0.5">
        <strong className="text-green-950 font-semibold block text-[11px] uppercase font-mono">
          Cytoscape.js Force-Directed Engine (Checkpoint 6)
        </strong>
        <p className="text-xs">
          Interactive fcose force-directed canvas with node selection, edge inspection, and cohort expansion activates in Checkpoint 6.
        </p>
      </div>
    </div>
  );
};

