import React from 'react';

interface QueueEmptyStateProps {
  readonly isFiltered: boolean;
  readonly onClearFilters?: () => void;
}

export const QueueEmptyState: React.FC<QueueEmptyStateProps> = ({
  isFiltered,
  onClearFilters,
}) => {
  return (
    <div className="bg-surface border border-hairline p-10 text-center shadow-subtle my-2">
      <span className="text-[11px] font-mono text-ink-subtle uppercase tracking-wider block mb-1">
        Queue Status
      </span>
      <h3 className="font-serif text-lg font-bold text-green-950 mb-2">
        {isFiltered ? 'No Investigations Match Current Filters' : 'Investigation Queue Empty'}
      </h3>
      <p className="text-xs text-ink-muted max-w-md mx-auto mb-4">
        {isFiltered
          ? 'No active cases in the current capacity window meet the selected severity, rule, or search criteria.'
          : 'All alerts for the selected horizon have been processed or are below current prioritization thresholds.'}
      </p>
      {isFiltered && onClearFilters && (
        <button
          type="button"
          onClick={onClearFilters}
          className="px-3.5 py-1.5 bg-green-900 text-ink-inverse text-xs font-medium hover:bg-green-800 transition-colors"
        >
          Reset Filter Parameters
        </button>
      )}
    </div>
  );
};
