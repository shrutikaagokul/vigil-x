import React, { useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getNetwork } from '@/services/networkService';
import { NetworkNode, NetworkEdge } from '@/types/network';
import { NetworkHeader, NetworkCanvas, NetworkInsightPanel } from '@/components/network';

export const NetworkPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const linkedCaseId = searchParams.get('caseId');

  const activeNetworkId = id || 'NET-RING-001';

  // Selection state
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<NetworkEdge | null>(null);

  // Fetch Network Data
  const {
    data: network,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['network', activeNetworkId],
    queryFn: () => getNetwork(activeNetworkId),
    retry: false,
  });

  const handleSelectNode = (node: NetworkNode) => {
    setSelectedEdge(null);
    setSelectedNode(node);
  };

  const handleSelectEdge = (edge: NetworkEdge) => {
    setSelectedNode(null);
    setSelectedEdge(edge);
  };

  const handleClearSelection = () => {
    setSelectedNode(null);
    setSelectedEdge(null);
  };

  const handleSelectNodeById = (nodeId: string) => {
    if (!network?.nodes) return;
    const found = network.nodes.find((n) => n.id === nodeId);
    if (found) {
      handleSelectNode(found);
    }
  };

  if (isLoading) {
    return (
      <main className="w-full min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center p-8 bg-[#F5F8F4]">
        <div className="p-8 bg-white border border-[#E0E8DF] rounded text-center max-w-md space-y-3 shadow-xs">
          <div className="w-8 h-8 border-2 border-[#477A58] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="font-serif text-lg font-semibold text-[#183B2A]">
            Loading Network Investigation Graph...
          </p>
          <span className="font-mono text-xs text-[#68766B] block">
            ID: {activeNetworkId}
          </span>
        </div>
      </main>
    );
  }

  if (isError || !network) {
    return (
      <main className="w-full min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center p-8 bg-[#F5F8F4]">
        <div className="p-8 bg-white border border-[#FCA5A5] rounded text-center max-w-md space-y-3 shadow-xs">
          <h2 className="font-serif text-lg font-bold text-[#B91C1C]">
            Unable to Load Network
          </h2>
          <p className="text-xs text-[#68766B]">
            {error instanceof Error ? error.message : `Network ID '${activeNetworkId}' not found.`}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 bg-[#477A58] text-white text-xs font-semibold rounded hover:bg-[#285239] transition-colors"
          >
            Retry
          </button>
        </div>
      </main>
    );
  }

  const selectedEdgeId = selectedEdge
    ? `${selectedEdge.source}-${selectedEdge.target}-${selectedEdge.edge_type}`
    : null;

  return (
    <main className="w-full min-h-[calc(100vh-8rem)] flex flex-col bg-[#F5F8F4]" role="main">
      {/* 1. Header & Compact Fact Strip */}
      <NetworkHeader network={network} linkedCaseId={linkedCaseId} />

      {/* 2. Main Workspace: Canvas (Left/Center) + Investigation Panel (Right) */}
      <div className="w-full px-6 md:px-12 py-6 flex-1 flex flex-col lg:flex-row gap-6 items-stretch">
        <NetworkCanvas
          network={network}
          selectedNodeId={selectedNode?.id}
          selectedEdgeId={selectedEdgeId}
          onSelectNode={handleSelectNode}
          onSelectEdge={handleSelectEdge}
          onClearSelection={handleClearSelection}
        />

        <NetworkInsightPanel
          network={network}
          selectedNode={selectedNode}
          selectedEdge={selectedEdge}
          onSelectNodeById={handleSelectNodeById}
          onClearSelection={handleClearSelection}
        />
      </div>
    </main>
  );
};
