import React from 'react';
import { PageContainer } from '@/components/layout/PageContainer';

export const AuditPage: React.FC = () => {
  return (
    <PageContainer>
      <div className="bg-surface border border-hairline p-6 shadow-subtle">
        <div className="border-b border-hairline pb-4 mb-4 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-mono text-ink-subtle uppercase tracking-wider">
              SIU Governance & Compliance
            </span>
            <h1 className="font-serif text-2xl font-bold text-green-950 mt-1">
              Audit Trail
            </h1>
          </div>
          <span className="text-xs font-mono bg-paper-subtle border border-hairline px-2.5 py-1 text-ink-muted">
            Immutable Activity Log
          </span>
        </div>
        <p className="text-xs text-ink-muted">
          Investigation decision history, capacity reallocation events, and system audit ledger will be implemented in subsequent checkpoints.
        </p>
      </div>
    </PageContainer>
  );
};
