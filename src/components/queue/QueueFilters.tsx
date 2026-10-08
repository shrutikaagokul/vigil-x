import React from 'react';

interface QueueFiltersProps {
  readonly selectedSeverity: string;
  readonly selectedRule: string;
  readonly searchQuery: string;
  readonly availableRules: readonly string[];
  readonly onSeverityChange: (sev: string) => void;
  readonly onRuleChange: (rule: string) => void;
  readonly onSearchChange: (q: string) => void;
  readonly onClearFilters: () => void;
  readonly isFiltered: boolean;
}

export const QueueFilters: React.FC<QueueFiltersProps> = ({
  selectedSeverity,
  selectedRule,
  searchQuery,
  availableRules,
  onSeverityChange,
  onRuleChange,
  onSearchChange,
  onClearFilters,
  isFiltered,
}) => {
  const severities: readonly { label: string; value: string }[] = [
    { label: 'All Severities', value: '' },
    { label: 'Critical', value: 'CRITICAL' },
    { label: 'High', value: 'HIGH' },
    { label: 'Medium', value: 'MEDIUM' },
    { label: 'Low', value: 'LOW' },
  ];

  return (
    <div className="bg-surface border border-border px-3 py-2 flex flex-col md:flex-row md:items-center justify-between gap-2.5">
      {/* Left: Filters */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Severity Selector */}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-mono text-ink-subtle uppercase">Severity:</span>
          <select
            value={selectedSeverity}
            onChange={(e) => onSeverityChange(e.target.value)}
            className="h-[26px] px-2 text-xs bg-paper-subtle border border-border text-ink outline-none focus-visible:border-green-800"
            aria-label="Filter queue by severity"
          >
            {severities.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        {/* Rule Filter */}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-mono text-ink-subtle uppercase">Rule:</span>
          <select
            value={selectedRule}
            onChange={(e) => onRuleChange(e.target.value)}
            className="h-[26px] px-2 text-xs bg-paper-subtle border border-border text-ink outline-none focus-visible:border-green-800 font-mono"
            aria-label="Filter queue by triggered rule"
          >
            <option value="">All Rules</option>
            {availableRules.map((rule) => (
              <option key={rule} value={rule}>
                {rule}
              </option>
            ))}
          </select>
        </div>

        {/* Clear Filters Action */}
        {isFiltered && (
          <button
            type="button"
            onClick={onClearFilters}
            className="h-[26px] px-2 text-xs font-mono text-brick hover:bg-brick-soft border border-brick/30 transition-colors"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Right: Search Input */}
      <div className="w-full md:w-72">
        <div className="relative flex items-center">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search Case ID, Provider, NPI..."
            className="w-full h-[26px] pl-2.5 pr-7 text-xs bg-paper-subtle border border-border placeholder:text-ink-subtle focus:bg-surface focus:border-green-800 outline-none font-sans"
            aria-label="Search investigation queue"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              className="absolute right-1.5 text-xs text-ink-subtle hover:text-ink p-0.5"
              aria-label="Clear search query"
            >
              &times;
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

