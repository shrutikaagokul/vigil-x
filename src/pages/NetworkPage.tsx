import React from 'react';
import { useParams } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';

export const NetworkPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const activeNetworkId = id || 'NET-RING-001';

  return (
    <PageContainer>
      <div className="bg-surface border border-hairline p-6 shadow-subtle">
        <div className="border-b border-hairline pb-4 mb-4 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-mono text-ink-subtle uppercase tracking-wider">
              Graph Intelligence & Entity Clustering
            </span>
            <h1 className="font-serif text-2xl font-bold text-green-950 mt-1">
              Network Explorer
            </h1>
          </div>
          <span className="text-xs font-mono bg-paper-subtle border border-hairline px-2.5 py-1 text-ink">
            Network ID: <strong data-testid="network-id-display">{activeNetworkId}</strong>
          </span>
        </div>
        <p className="text-xs text-ink-muted">
          Interactive Cytoscape.js network canvas, entity node details, and member cohort inspector will be implemented in subsequent checkpoints.
        </p>
      </div>
    </PageContainer>
  );
};
