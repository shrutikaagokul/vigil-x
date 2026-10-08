import React from 'react';
import { PageContainer } from '@/components/layout/PageContainer';

export const EvaluationPage: React.FC = () => {
  return (
    <PageContainer>
      <div className="bg-surface border border-hairline p-6 shadow-subtle">
        <div className="border-b border-hairline pb-4 mb-4 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-mono text-ink-subtle uppercase tracking-wider">
              Benchmark Verification
            </span>
            <h1 className="font-serif text-2xl font-bold text-green-950 mt-1">
              Ground Truth Evaluation
            </h1>
          </div>
          <span className="text-xs font-mono bg-paper-subtle border border-hairline px-2.5 py-1 text-ink-muted">
            Isolated Ground Truth Labels
          </span>
        </div>
        <p className="text-xs text-ink-muted">
          Precision/recall metrics, planted ring recovery scores, and rule performance breakdowns will be implemented in subsequent checkpoints.
        </p>
      </div>
    </PageContainer>
  );
};
