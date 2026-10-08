import React from 'react';

export const CaseLoadingState: React.FC = () => {
  return (
    <div className="bg-surface border border-hairline p-8 shadow-subtle animate-pulse space-y-4">
      <div className="flex items-center justify-between border-b border-hairline pb-4">
        <div className="space-y-2">
          <div className="h-3 w-28 bg-paper-subtle" />
          <div className="h-6 w-64 bg-paper-subtle" />
        </div>
        <div className="h-8 w-32 bg-paper-subtle" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-2">
        <div className="space-y-3">
          <div className="h-24 bg-paper-subtle" />
          <div className="h-32 bg-paper-subtle" />
        </div>
        <div className="lg:col-span-2 space-y-3">
          <div className="h-10 bg-paper-subtle" />
          <div className="h-48 bg-paper-subtle" />
        </div>
      </div>
    </div>
  );
};
