import React from 'react';
import * as Slider from '@radix-ui/react-slider';
import * as Popover from '@radix-ui/react-popover';

interface CapacityRowProps {
  readonly generalHours: number;
  readonly networkHours: number;
  readonly searchQuery: string;
  readonly selectedSeverity: string;
  readonly selectedRule: string;
  readonly availableRules: readonly string[];
  readonly searchInputRef: React.RefObject<HTMLInputElement>;
  readonly onGeneralHoursChange: (hours: number) => void;
  readonly onNetworkHoursChange: (hours: number) => void;
  readonly onSearchChange: (q: string) => void;
  readonly onSeverityChange: (sev: string) => void;
  readonly onRuleChange: (rule: string) => void;
  readonly onClearFilters: () => void;
}

export const CapacityRow: React.FC<CapacityRowProps> = ({
  generalHours,
  networkHours,
  searchQuery,
  selectedSeverity,
  selectedRule,
  availableRules,
  searchInputRef,
  onGeneralHoursChange,
  onNetworkHoursChange,
  onSearchChange,
  onSeverityChange,
  onRuleChange,
  onClearFilters,
}) => {
  const severities = [
    { label: 'All Severities', value: '' },
    { label: 'Critical', value: 'CRITICAL' },
    { label: 'High', value: 'HIGH' },
    { label: 'Medium', value: 'MEDIUM' },
    { label: 'Low', value: 'LOW' },
  ];

  const hasActiveFilters = Boolean(selectedSeverity || selectedRule);

  return (
    <div className="w-full mt-[1.25rem] px-[3rem]">
      <div className="py-[0.875rem] border-t border-b border-[#D3E0D6] flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left Side: Generalist & Network Specialist Sliders */}
        <div className="flex flex-wrap items-center gap-8">
          {/* Generalist Slider */}
          <div className="flex items-center space-x-3">
            <span className="text-[0.9375rem] text-[#4F5F55] font-normal">
              Generalist
            </span>
            <span className="text-[0.9375rem] font-bold text-[#1B3A29] tabular-nums min-w-[36px]">
              {generalHours} h
            </span>
            <Slider.Root
              value={[generalHours]}
              min={0}
              max={120}
              step={5}
              onValueChange={([val]) => onGeneralHoursChange(val)}
              className="relative flex items-center select-none touch-none w-[170px] h-4 cursor-pointer"
              aria-label="Generalist capacity in hours"
            >
              <Slider.Track className="bg-[#D3E0D6] relative grow rounded-full h-[4px]">
                <Slider.Range className="absolute bg-[#2A5A3F] rounded-full h-full" />
              </Slider.Track>
              <Slider.Thumb
                className="block w-4 h-4 bg-[#2A5A3F] rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2A5A3F] focus-visible:ring-offset-2"
                aria-label="Generalist hours thumb"
              />
            </Slider.Root>
          </div>

          {/* Network Specialist Slider */}
          <div className="flex items-center space-x-3">
            <span className="text-[0.9375rem] text-[#4F5F55] font-normal">
              Network specialist
            </span>
            <span className="text-[0.9375rem] font-bold text-[#1B3A29] tabular-nums min-w-[36px]">
              {networkHours} h
            </span>
            <Slider.Root
              value={[networkHours]}
              min={0}
              max={80}
              step={5}
              onValueChange={([val]) => onNetworkHoursChange(val)}
              className="relative flex items-center select-none touch-none w-[170px] h-4 cursor-pointer"
              aria-label="Network specialist capacity in hours"
            >
              <Slider.Track className="bg-[#D3E0D6] relative grow rounded-full h-[4px]">
                <Slider.Range className="absolute bg-[#2A5A3F] rounded-full h-full" />
              </Slider.Track>
              <Slider.Thumb
                className="block w-4 h-4 bg-[#2A5A3F] rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2A5A3F] focus-visible:ring-offset-2"
                aria-label="Network specialist hours thumb"
              />
            </Slider.Root>
          </div>
        </div>

        {/* Right Side: Search Input and Filters Popover */}
        <div className="flex items-center space-x-3 shrink-0">
          <div className="relative w-[240px]">
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search cases"
              className="w-full h-[36px] px-3 text-[0.9375rem] bg-white border border-[#D3E0D6] rounded-[3px] text-[#14201A] placeholder-[#8A969C] outline-none focus:border-[#2A5A3F] focus-visible:ring-2 focus-visible:ring-[#2A5A3F]"
              aria-label="Search cases"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => onSearchChange('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[0.875rem] text-[#8A969C] hover:text-[#14201A]"
                aria-label="Clear search"
              >
                ×
              </button>
            )}
          </div>

          <Popover.Root>
            <Popover.Trigger asChild>
              <button
                type="button"
                className={`h-[36px] px-4 text-[0.9375rem] font-semibold rounded-[3px] border border-[#2A5A3F] transition-colors outline-none focus-visible:ring-2 focus-visible:ring-[#2A5A3F] focus-visible:ring-offset-2 ${
                  hasActiveFilters
                    ? 'bg-[#2A5A3F] text-white'
                    : 'bg-transparent text-[#2A5A3F] hover:bg-[#E3EFE5]'
                }`}
                aria-label="Filter queue cases"
              >
                Filters {hasActiveFilters && '●'}
              </button>
            </Popover.Trigger>
            <Popover.Portal>
              <Popover.Content
                className="w-72 bg-white border border-[#D3E0D6] p-4 rounded-[3px] shadow-none z-50 space-y-3 focus:outline-none"
                sideOffset={5}
                align="end"
              >
                <div className="flex items-center justify-between border-b border-[#D3E0D6] pb-2">
                  <span className="text-[0.875rem] font-semibold text-[#0B1A12]">Filter Cases</span>
                  {hasActiveFilters && (
                    <button
                      type="button"
                      onClick={onClearFilters}
                      className="text-[0.75rem] text-[#9E3626] hover:underline"
                    >
                      Reset
                    </button>
                  )}
                </div>

                <div className="space-y-1">
                  <label htmlFor="filter-severity" className="text-[0.8125rem] font-medium text-[#4F5F55] block">
                    Severity
                  </label>
                  <select
                    id="filter-severity"
                    value={selectedSeverity}
                    onChange={(e) => onSeverityChange(e.target.value)}
                    className="w-full h-8 px-2 text-[0.875rem] bg-white border border-[#D3E0D6] rounded-[3px] text-[#14201A] outline-none focus:border-[#2A5A3F]"
                  >
                    {severities.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1">
                  <label htmlFor="filter-rule" className="text-[0.8125rem] font-medium text-[#4F5F55] block">
                    Triggered Rule
                  </label>
                  <select
                    id="filter-rule"
                    value={selectedRule}
                    onChange={(e) => onRuleChange(e.target.value)}
                    className="w-full h-8 px-2 text-[0.875rem] bg-white border border-[#D3E0D6] rounded-[3px] text-[#14201A] outline-none focus:border-[#2A5A3F]"
                  >
                    <option value="">All Rules</option>
                    {availableRules.map((rule) => (
                      <option key={rule} value={rule}>
                        {rule}
                      </option>
                    ))}
                  </select>
                </div>
              </Popover.Content>
            </Popover.Portal>
          </Popover.Root>
        </div>
      </div>
    </div>
  );
};
