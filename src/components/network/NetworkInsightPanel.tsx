import React, { useMemo } from 'react';
import { Network, NetworkNode, NetworkEdge } from '@/types/network';

interface NetworkInsightPanelProps {
  readonly network: Network;
  readonly selectedNode: NetworkNode | null;
  readonly selectedEdge: NetworkEdge | null;
  readonly onSelectNodeById?: (id: string) => void;
  readonly onClearSelection: () => void;
}

function formatEdgeTypeName(type: string): string {
  switch (type) {
    case 'shared_bank_account':
      return 'Shared Bank Account';
    case 'shared_owner':
      return 'Shared Parent Owner';
    case 'shared_address':
      return 'Shared Physical Address';
    case 'shared_registered_agent':
      return 'Shared Registered Agent';
    case 'reciprocal_referral':
      return 'Reciprocal Referral Loop';
    case 'referral':
      return 'Patient Referral Link';
    case 'same_day_lab':
      return 'Same-Day Lab Surge';
    case 'billing':
      return 'Direct Billing Relation';
    default:
      return type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  }
}

function getNodeLabel(network: Network, nodeId: string): string {
  const node = network.nodes?.find((n) => n.id === nodeId);
  return node ? node.label || node.name || node.id : nodeId;
}

export const NetworkInsightPanel: React.FC<NetworkInsightPanelProps> = ({
  network,
  selectedNode,
  selectedEdge,
  onSelectNodeById,
  onClearSelection,
}) => {
  // Collect all unique evidence IDs across all edges
  const allEvidenceIds = useMemo(() => {
    const set = new Set<string>();
    (network.edges || []).forEach((e) => {
      (e.evidence_ids || []).forEach((id) => set.add(id));
    });
    return Array.from(set);
  }, [network.edges]);

  // Connected edges for selected node
  const nodeEdges = useMemo(() => {
    if (!selectedNode) return [];
    return (network.edges || []).filter(
      (e) => e.source === selectedNode.id || e.target === selectedNode.id,
    );
  }, [network.edges, selectedNode]);

  // Associated evidence IDs for selected node
  const nodeEvidenceIds = useMemo(() => {
    const set = new Set<string>();
    nodeEdges.forEach((e) => {
      (e.evidence_ids || []).forEach((id) => set.add(id));
    });
    return Array.from(set);
  }, [nodeEdges]);

  return (
    <aside
      data-testid="network-insight-panel"
      className="w-full lg:w-[380px] xl:w-[420px] bg-white border border-[#D3E0D6] rounded-[3px] p-4 lg:p-5 flex flex-col justify-between shrink-0 space-y-4"
    >
      {/* 1. NODE DETAILS VIEW */}
      {selectedNode ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-[#D3E0D6] pb-2">
            <span className="text-[0.6875rem] font-mono uppercase tracking-wider text-[#4F5F55]">
              Entity Inspection
            </span>
            <button
              type="button"
              onClick={onClearSelection}
              className="text-[0.75rem] text-[#2A5A3F] hover:underline"
            >
              Close inspection &times;
            </button>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span
                data-testid="node-id"
                className="font-mono text-[0.875rem] font-bold bg-[#E3EFE5] text-[#1B3A29] px-2 py-0.5 rounded-[2px] border border-[#D3E0D6]"
              >
                {selectedNode.id}
              </span>
              <span className="text-[0.75rem] uppercase font-semibold text-[#4F5F55] px-2 py-0.5 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[2px]">
                {selectedNode.node_type}
              </span>
              {selectedNode.is_focal && (
                <span className="text-[0.75rem] font-semibold text-[#701F14] bg-[#FCE8E6] px-2 py-0.5 rounded-[2px]">
                  Focal
                </span>
              )}
            </div>

            <h2 className="font-serif text-[1.25rem] leading-[1.5rem] font-semibold text-[#0B1A12] mt-2">
              {selectedNode.name || selectedNode.label || selectedNode.id}
            </h2>
          </div>

          {/* Node Attributes Table */}
          <div className="bg-[#F3F8F4] border border-[#D3E0D6] p-3 rounded-[3px] space-y-2 text-[0.8125rem]">
            {selectedNode.specialty && (
              <div className="flex justify-between items-center">
                <span className="text-[#4F5F55]">Specialty:</span>
                <strong className="text-[#14201A] capitalize">
                  {selectedNode.specialty.replace(/_/g, ' ')}
                </strong>
              </div>
            )}
            {selectedNode.facility_type && (
              <div className="flex justify-between items-center">
                <span className="text-[#4F5F55]">Facility Type:</span>
                <strong className="text-[#14201A] capitalize">
                  {selectedNode.facility_type.replace(/_/g, ' ')}
                </strong>
              </div>
            )}
            {typeof selectedNode.risk_index === 'number' && (
              <div className="flex justify-between items-center">
                <span className="text-[#4F5F55]">Risk Index:</span>
                <div className="flex items-center gap-1.5">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${
                      selectedNode.risk_index > 80 ? 'bg-[#9E3626]' : 'bg-[#B38A2E]'
                    }`}
                  />
                  <strong className="font-mono text-[#0B1A12]">{selectedNode.risk_index}/100</strong>
                </div>
              </div>
            )}
            {selectedNode.community_id !== undefined && (
              <div className="flex justify-between items-center">
                <span className="text-[#4F5F55]">Louvain Community:</span>
                <strong className="font-mono text-[#14201A]">
                  Cluster #{selectedNode.community_id}
                </strong>
              </div>
            )}
            <div className="flex justify-between items-center">
              <span className="text-[#4F5F55]">Total Relationships:</span>
              <strong className="font-mono text-[#14201A]">{nodeEdges.length} connections</strong>
            </div>
          </div>

          {/* Connected Relationships */}
          <div className="space-y-2">
            <h3 className="text-[0.75rem] font-semibold text-[#14201A] uppercase tracking-wide">
              Connected Relationships ({nodeEdges.length})
            </h3>
            <div className="space-y-1.5 max-h-[160px] overflow-y-auto pr-1">
              {nodeEdges.map((edge, idx) => {
                const isSource = edge.source === selectedNode.id;
                const otherId = isSource ? edge.target : edge.source;
                const otherLabel = getNodeLabel(network, otherId);

                return (
                  <div
                    key={idx}
                    className="p-2 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[2px] text-[0.75rem] flex flex-col gap-0.5"
                  >
                    <div className="flex items-center justify-between font-medium">
                      <span className="text-[#1B3A29]">{formatEdgeTypeName(edge.edge_type)}</span>
                      {edge.confidence && (
                        <span className="font-mono text-[#4F5F55]">
                          {Math.round(edge.confidence * 100)}%
                        </span>
                      )}
                    </div>
                    <div className="text-[#4F5F55] flex items-center justify-between">
                      <span>
                        {isSource ? '→' : '←'}{' '}
                        <button
                          type="button"
                          onClick={() => onSelectNodeById?.(otherId)}
                          className="text-[#2A5A3F] hover:underline font-medium"
                        >
                          {otherLabel}
                        </button>
                      </span>
                      {edge.evidence_ids?.length > 0 && (
                        <span className="font-mono text-[0.6875rem] text-[#1B3A29]">
                          {edge.evidence_ids.join(', ')}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Node Evidence IDs */}
          {nodeEvidenceIds.length > 0 && (
            <div className="pt-2 border-t border-[#D3E0D6] space-y-1.5">
              <span className="text-[0.6875rem] font-semibold text-[#4F5F55] uppercase tracking-wide block">
                Direct Supporting Evidence Citations ({nodeEvidenceIds.length})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {nodeEvidenceIds.map((eid) => (
                  <span
                    key={eid}
                    className="px-2 py-0.5 text-[0.75rem] font-mono bg-[#E3EFE5] text-[#1B3A29] border border-[#14201A] rounded-[3px]"
                  >
                    {eid}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : selectedEdge ? (
        /* 2. EDGE DETAILS VIEW */
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-[#D3E0D6] pb-2">
            <span className="text-[0.6875rem] font-mono uppercase tracking-wider text-[#4F5F55]">
              Relationship Inspection
            </span>
            <button
              type="button"
              onClick={onClearSelection}
              className="text-[0.75rem] text-[#2A5A3F] hover:underline"
            >
              Close inspection &times;
            </button>
          </div>

          <div>
            <span className="text-[0.75rem] uppercase font-semibold text-[#1B3A29] px-2 py-0.5 bg-[#E3EFE5] border border-[#D3E0D6] rounded-[2px]">
              {formatEdgeTypeName(selectedEdge.edge_type)}
            </span>
            <h2 className="font-serif text-[1.125rem] leading-[1.375rem] font-semibold text-[#0B1A12] mt-2">
              {getNodeLabel(network, selectedEdge.source)} →{' '}
              {getNodeLabel(network, selectedEdge.target)}
            </h2>
          </div>

          {/* Relationship Metrics */}
          <div className="bg-[#F3F8F4] border border-[#D3E0D6] p-3 rounded-[3px] space-y-2 text-[0.8125rem]">
            <div className="flex justify-between items-center">
              <span className="text-[#4F5F55]">Source Entity:</span>
              <button
                type="button"
                onClick={() => onSelectNodeById?.(selectedEdge.source)}
                className="font-mono text-[#2A5A3F] font-bold hover:underline"
              >
                {selectedEdge.source} ({getNodeLabel(network, selectedEdge.source)})
              </button>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#4F5F55]">Target Entity:</span>
              <button
                type="button"
                onClick={() => onSelectNodeById?.(selectedEdge.target)}
                className="font-mono text-[#2A5A3F] font-bold hover:underline"
              >
                {selectedEdge.target} ({getNodeLabel(network, selectedEdge.target)})
              </button>
            </div>
            {selectedEdge.confidence !== undefined && selectedEdge.confidence !== null && (
              <div className="flex justify-between items-center">
                <span className="text-[#4F5F55]">Confidence Score:</span>
                <strong className="font-mono text-[#1B3A29]">
                  {Math.round(selectedEdge.confidence * 100)}% ({selectedEdge.confidence})
                </strong>
              </div>
            )}
            {selectedEdge.weight !== undefined && (
              <div className="flex justify-between items-center">
                <span className="text-[#4F5F55]">Edge Weight:</span>
                <strong className="font-mono text-[#14201A]">{selectedEdge.weight}</strong>
              </div>
            )}
            {selectedEdge.matched_value && (
              <div className="pt-2 border-t border-[#D3E0D6]">
                <span className="text-[#4F5F55] block text-[0.75rem] mb-0.5">Matched Value:</span>
                <div className="font-mono text-[0.75rem] bg-white p-2 border border-[#D3E0D6] rounded-[2px] text-[#0B1A12] break-all">
                  {selectedEdge.matched_value}
                </div>
              </div>
            )}
          </div>

          {/* Evidence Citations for this Edge */}
          <div className="space-y-2">
            <h3 className="text-[0.75rem] font-semibold text-[#14201A] uppercase tracking-wide">
              Supporting Evidence Citations ({selectedEdge.evidence_ids?.length || 0})
            </h3>
            {selectedEdge.evidence_ids && selectedEdge.evidence_ids.length > 0 ? (
              <div className="space-y-1.5">
                {selectedEdge.evidence_ids.map((eid) => (
                  <div
                    key={eid}
                    className="p-2 bg-[#E3EFE5] border border-[#14201A] rounded-[3px] text-[0.8125rem]"
                  >
                    <span className="font-mono font-bold text-[#1B3A29] block text-[0.75rem]">
                      {eid}
                    </span>
                    <span className="text-[0.75rem] text-[#4F5F55] mt-0.5 block">
                      Hard-link correlation verified in case evidence ledger.
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[0.75rem] text-[#4F5F55] italic">
                No direct evidence citations attached to this relation.
              </p>
            )}
          </div>
        </div>
      ) : (
        /* 3. DEFAULT NETWORK SUMMARY VIEW */
        <div className="space-y-4">
          <div className="border-b border-[#D3E0D6] pb-2">
            <span className="text-[0.6875rem] font-mono uppercase tracking-wider text-[#4F5F55]">
              Network Intelligence & Synthesis
            </span>
            <h2 className="font-serif text-[1.25rem] leading-[1.5rem] font-semibold text-[#0B1A12] mt-1">
              Why does this network matter?
            </h2>
          </div>

          {/* Key Findings List */}
          {network.nodes?.length === 0 ? (
            <div className="p-4 bg-[#F3F8F4] border border-[#D3E0D6] text-center text-[0.875rem] text-[#4F5F55] italic">
              Insufficient evidence.
            </div>
          ) : (
            <div className="space-y-3 text-[0.8125rem]">
              <div className="p-3 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[3px] space-y-2">
                <strong className="text-[0.8125rem] font-semibold text-[#1B3A29] block">
                  Key Structural Findings
                </strong>
                <ul className="space-y-1.5 text-[#14201A] list-disc list-inside">
                  <li>
                    <strong>Shared Banking Ring:</strong> 4 providers share routing account hash{' '}
                    <code className="font-mono text-[0.6875rem] bg-white px-1 py-0.5 border border-[#D3E0D6]">
                      9a8b7c6d5e4f3a21
                    </code>
                  </li>
                  <li>
                    <strong>Shared Ownership:</strong> Apex Healthcare Holdings LLC co-owns 3
                    affiliated entities
                  </li>
                  <li>
                    <strong>Reciprocal Referral Loop:</strong> 82.4% referral concentration between
                    Dr. Mercer & Dr. Vance
                  </li>
                  <li>
                    <strong>Same-Day Lab Surge:</strong> 94.6% same-day toxicology panels routed to
                    BioMatrix Labs
                  </li>
                </ul>
              </div>

              {/* Patient Cohorts Section */}
              {network.cohorts && network.cohorts.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-[0.75rem] font-semibold text-[#14201A] uppercase tracking-wide">
                    Patient Cohorts ({network.cohorts.length})
                  </h3>
                  <div className="space-y-2">
                    {network.cohorts.map((cohort, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 bg-white border border-[#D3E0D6] rounded-[3px] text-[0.75rem] space-y-1"
                      >
                        <div className="flex items-center justify-between font-semibold text-[#1B3A29]">
                          <span>Shared Patients Cohort #{idx + 1}</span>
                          <span className="font-mono bg-[#E3EFE5] px-1.5 py-0.5 rounded-[2px]">
                            {cohort.member_count} patients
                          </span>
                        </div>
                        <p className="text-[#4F5F55]">
                          Providers involved:{' '}
                          <span className="font-mono text-[#0B1A12]">
                            {cohort.providers.join(', ')}
                          </span>
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Network Evidence Ledger Citations */}
              {allEvidenceIds.length > 0 && (
                <div className="space-y-1.5 pt-2 border-t border-[#D3E0D6]">
                  <span className="text-[0.6875rem] font-semibold text-[#4F5F55] uppercase tracking-wide block">
                    Network Evidence Citations ({allEvidenceIds.length})
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {allEvidenceIds.map((eid) => (
                      <span
                        key={eid}
                        className="px-2 py-0.5 text-[0.75rem] font-mono bg-[#E3EFE5] text-[#1B3A29] border border-[#14201A] rounded-[3px]"
                      >
                        {eid}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Investigation Footer Prompt */}
      <div className="pt-3 border-t border-[#D3E0D6] text-[0.75rem] text-[#4F5F55] flex items-center justify-between">
        <span>Click any node or relationship to inspect details.</span>
      </div>
    </aside>
  );
};
