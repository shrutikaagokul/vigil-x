import React, { useEffect, useRef } from 'react';
import cytoscape, { Core, NodeSingular, EdgeSingular } from 'cytoscape';
import fcose from 'cytoscape-fcose';
import { Network, NetworkNode, NetworkEdge } from '@/types/network';
import { NetworkLegend } from './NetworkLegend';

// Register fcose extension safely
try {
  cytoscape.use(fcose);
} catch {
  // Already registered
}

interface NetworkCanvasProps {
  readonly network: Network;
  readonly selectedNodeId?: string | null;
  readonly selectedEdgeId?: string | null;
  readonly onSelectNode: (node: NetworkNode) => void;
  readonly onSelectEdge: (edge: NetworkEdge) => void;
  readonly onClearSelection: () => void;
}

export const NetworkCanvas: React.FC<NetworkCanvasProps> = ({
  network,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
  onClearSelection,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  // Initialize and update Cytoscape
  useEffect(() => {
    if (!containerRef.current) return;

    // Transform nodes
    const elements: cytoscape.ElementDefinition[] = [];

    (network.nodes || []).forEach((node) => {
      elements.push({
        group: 'nodes',
        data: {
          id: node.id,
          label: node.label || node.name || node.id,
          name: node.name || node.label || node.id,
          node_type: node.node_type || 'provider',
          specialty: node.specialty,
          facility_type: node.facility_type,
          risk_index: node.risk_index,
          is_focal: Boolean(node.is_focal || node.id === network.focal_entity),
          community_id: node.community_id,
          rawNode: node,
        },
      });
    });

    // Transform edges
    (network.edges || []).forEach((edge, idx) => {
      const edgeId = `${edge.source}-${edge.target}-${edge.edge_type || idx}`;
      elements.push({
        group: 'edges',
        data: {
          id: edgeId,
          source: edge.source,
          target: edge.target,
          edge_type: edge.edge_type || 'referral',
          weight: edge.weight ?? 1,
          confidence: edge.confidence,
          matched_value: edge.matched_value,
          evidence_ids: edge.evidence_ids || [],
          rawEdge: edge,
        },
      });
    });

    try {
      const cy = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          // Base Node Style
          {
            selector: 'node',
            style: {
              label: 'data(label)',
              'text-valign': 'bottom',
              'text-margin-y': 6,
              color: '#E3EFE5',
              'font-family': 'Atkinson Hyperlegible Next, sans-serif',
              'font-size': '11px',
              'font-weight': 600,
              'text-background-color': '#0B1A12',
              'text-background-opacity': 0.85,
              'text-background-padding': '3px',
              'text-background-shape': 'roundrectangle',
              width: 38,
              height: 38,
              'transition-property': 'background-color, border-color, border-width',
              'transition-duration': 0.15,
            },
          },
          // Node Entity Type: Provider (Light-green circle)
          {
            selector: 'node[node_type = "provider"]',
            style: {
              shape: 'ellipse',
              'background-color': '#A9CFB0',
              'border-width': 1,
              'border-color': '#1B3A29',
            },
          },
          // Node Entity Type: Facility (Steel square)
          {
            selector: 'node[node_type = "facility"]',
            style: {
              shape: 'rectangle',
              'background-color': '#8FA396',
              'border-width': 1,
              'border-color': '#1B3A29',
              width: 36,
              height: 36,
            },
          },
          // Node Entity Type: Owner (Brass diamond)
          {
            selector: 'node[node_type = "owner"]',
            style: {
              shape: 'diamond',
              'background-color': '#B38A2E',
              'border-width': 1,
              'border-color': '#14201A',
              width: 42,
              height: 42,
            },
          },
          // Node Entity Type: Bank Account (Brass diamond)
          {
            selector: 'node[node_type = "bank_account"]',
            style: {
              shape: 'diamond',
              'background-color': '#B38A2E',
              'border-width': 1,
              'border-color': '#14201A',
              width: 42,
              height: 42,
            },
          },
          // Node Entity Type: Member (Steel circle)
          {
            selector: 'node[node_type = "member"]',
            style: {
              shape: 'ellipse',
              'background-color': '#6B7E72',
              width: 28,
              height: 28,
            },
          },
          // Focal Entity Node (Restrained white border ring)
          {
            selector: 'node[?is_focal]',
            style: {
              'border-width': 3,
              'border-color': '#FFFFFF',
              'border-opacity': 0.95,
              width: 46,
              height: 46,
              'font-size': '12px',
              'font-weight': 700,
            },
          },
          // High-Risk Node (Restrained brick ring)
          {
            selector: 'node[risk_index > 80]',
            style: {
              'border-width': 2.5,
              'border-color': '#9E3626',
            },
          },
          // Selected Node
          {
            selector: 'node:selected',
            style: {
              'border-width': 3.5,
              'border-color': '#F3F8F4',
              'overlay-color': '#A9CFB0',
              'overlay-opacity': 0.2,
              'overlay-padding': 4,
            },
          },
          // Base Edge Style
          {
            selector: 'edge',
            style: {
              'curve-style': 'bezier',
              width: 2,
              'line-color': '#A9CFB0',
              'target-arrow-shape': 'none',
              opacity: 0.85,
            },
          },
          // Hard/Verified Links (Solid, strong line)
          {
            selector: 'edge[edge_type = "shared_bank_account"], edge[edge_type = "shared_owner"], edge[edge_type = "shared_address"], edge[edge_type = "shared_registered_agent"], edge[edge_type = "billing"]',
            style: {
              'line-style': 'solid',
              'line-color': '#A9CFB0',
              width: 3,
              opacity: 0.95,
            },
          },
          // Shared Owner Link
          {
            selector: 'edge[edge_type = "shared_owner"]',
            style: {
              'line-style': 'solid',
              'line-color': '#D3E0D6',
              width: 2.5,
              opacity: 0.9,
            },
          },
          // Referral Links (Dashed line)
          {
            selector: 'edge[edge_type = "referral"], edge[edge_type = "reciprocal_referral"]',
            style: {
              'line-style': 'dashed',
              'line-dash-pattern': [6, 3],
              'line-color': '#B38A2E',
              'target-arrow-shape': 'triangle',
              'target-arrow-color': '#B38A2E',
              width: 2.5,
              'arrow-scale': 1.1,
            },
          },
          // Same-Day Lab Surge (Dotted line)
          {
            selector: 'edge[edge_type = "same_day_lab"]',
            style: {
              'line-style': 'dotted',
              'line-dash-pattern': [2, 2],
              'line-color': '#9E3626',
              'target-arrow-shape': 'triangle',
              'target-arrow-color': '#9E3626',
              width: 2.5,
              'arrow-scale': 1.1,
            },
          },
          // Selected Edge
          {
            selector: 'edge:selected',
            style: {
              width: 4,
              'line-color': '#FFFFFF',
              'target-arrow-color': '#FFFFFF',
              opacity: 1,
            },
          },
        ],
        layout: {
          name: 'fcose',
          quality: 'default',
          randomize: false,
          animate: false,
          nodeDimensionsIncludeLabels: true,
          uniformNodeDimensions: false,
          packComponents: true,
          nodeRepulsion: 7500,
          idealEdgeLength: 130,
          edgeElasticity: 0.45,
          nestingFactor: 0.1,
          gravity: 0.25,
          numIter: 2500,
          tile: true,
          tilingPaddingVertical: 20,
          tilingPaddingHorizontal: 20,
        } as cytoscape.LayoutOptions,
      });

      cy.on('tap', 'node', (evt) => {
        const node = evt.target as NodeSingular;
        const rawNode = node.data('rawNode') as NetworkNode;
        if (rawNode) {
          onSelectNode(rawNode);
        }
      });

      cy.on('tap', 'edge', (evt) => {
        const edge = evt.target as EdgeSingular;
        const rawEdge = edge.data('rawEdge') as NetworkEdge;
        if (rawEdge) {
          onSelectEdge(rawEdge);
        }
      });

      cy.on('tap', (evt) => {
        if (evt.target === cy) {
          onClearSelection();
        }
      });

      cyRef.current = cy;

      // Fit to container
      cy.ready(() => {
        cy.fit(undefined, 36);
      });
    } catch {
      // Graceful fallback for non-DOM / test environments
    }

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [network, onSelectNode, onSelectEdge, onClearSelection]);

  // Handle selected element highlights
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.elements().unselect();
    if (selectedNodeId) {
      const node = cy.getElementById(selectedNodeId);
      if (node && node.length > 0) {
        node.select();
      }
    } else if (selectedEdgeId) {
      const edge = cy.getElementById(selectedEdgeId);
      if (edge && edge.length > 0) {
        edge.select();
      }
    }
  }, [selectedNodeId, selectedEdgeId]);

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.25);
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8);
    }
  };

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 36);
    }
  };

  const handleResetLayout = () => {
    if (cyRef.current) {
      try {
        const layout = cyRef.current.layout({
          name: 'fcose',
          randomize: false,
          animate: false,
          nodeDimensionsIncludeLabels: true,
          nodeRepulsion: 7500,
          idealEdgeLength: 130,
        } as cytoscape.LayoutOptions);
        layout.run();
        cyRef.current.fit(undefined, 36);
      } catch {
        cyRef.current.fit(undefined, 36);
      }
    }
  };

  return (
    <div
      data-testid="network-canvas-container"
      className="relative flex-1 h-[620px] lg:h-[700px] bg-[#0E2317] border border-[#1B3A29] rounded-[3px] overflow-hidden"
    >
      {/* Cytoscape Canvas Container */}
      <div
        ref={containerRef}
        data-testid="cytoscape-canvas"
        className="w-full h-full cursor-grab active:cursor-grabbing"
      />

      {/* Floating Canvas Controls (Top-Right) */}
      <div
        data-testid="network-canvas-controls"
        className="absolute top-3 right-3 flex items-center bg-[#0B1A12]/90 border border-[#2A5A3F] rounded-[3px] p-1 gap-1 text-white shadow-none z-10"
      >
        <button
          type="button"
          onClick={handleZoomIn}
          className="w-7 h-7 flex items-center justify-center text-[0.875rem] font-bold text-[#E3EFE5] hover:bg-[#2A5A3F] rounded-[2px] transition-colors outline-none focus-visible:ring-1 focus-visible:ring-[#A9CFB0]"
          title="Zoom In"
          aria-label="Zoom in"
        >
          +
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          className="w-7 h-7 flex items-center justify-center text-[0.875rem] font-bold text-[#E3EFE5] hover:bg-[#2A5A3F] rounded-[2px] transition-colors outline-none focus-visible:ring-1 focus-visible:ring-[#A9CFB0]"
          title="Zoom Out"
          aria-label="Zoom out"
        >
          −
        </button>
        <div className="w-[1px] h-4 bg-[#2A5A3F] my-auto" />
        <button
          type="button"
          onClick={handleFit}
          className="px-2 h-7 flex items-center justify-center text-[0.75rem] font-medium text-[#E3EFE5] hover:bg-[#2A5A3F] rounded-[2px] transition-colors outline-none focus-visible:ring-1 focus-visible:ring-[#A9CFB0]"
          title="Fit view"
          aria-label="Fit graph"
        >
          Fit
        </button>
        <button
          type="button"
          onClick={handleResetLayout}
          className="px-2 h-7 flex items-center justify-center text-[0.75rem] font-medium text-[#E3EFE5] hover:bg-[#2A5A3F] rounded-[2px] transition-colors outline-none focus-visible:ring-1 focus-visible:ring-[#A9CFB0]"
          title="Reset layout"
          aria-label="Reset layout"
        >
          Reset
        </button>
      </div>

      {/* Floating Legend (Bottom-Left) */}
      <div className="absolute bottom-3 left-3 z-10 max-w-[220px]">
        <NetworkLegend />
      </div>
    </div>
  );
};
