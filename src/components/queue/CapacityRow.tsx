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
    <div className="w-full mt-4 px-6 md:px-8">
      <div className="py-4 border-t border-b border-[#E0E8DF] flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        {/* Left Side: Generalist & Network Specialist Sliders */}
        <div className="flex flex-wrap items-center gap-10">
          {/* Generalist Slider */}
          <div className="flex items-center space-x-3.5">
            <span className="text-sm text-[#68766B] font-medium">
              Generalist
            </span>
            <span className="text-sm font-bold text-[#285239] tabular-nums min-w-[42px]">
              {generalHours} h
            </span>
            <Slider.Root
              value={[generalHours]}
              min={0}
              max={120}
              step={5}
              onValueChange={([val]) => onGeneralHoursChange(val)}
              className="relative flex items-center select-none touch-none w-[180px] h-5 cursor-pointer"
              aria-label="Generalist capacity in hours"
            >
              <Slider.Track className="bg-[#E0E8DF] relative grow rounded-full h-[6px]">
                <Slider.Range className="absolute bg-[#477A58] rounded-full h-full" />
              </Slider.Track>
              <Slider.Thumb
                className="block w-5 h-5 bg-[#477A58] border-2 border-white rounded-full shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-[#477A58]"
                aria-label="Generalist hours thumb"
              />
            </Slider.Root>
          </div>

          {/* Network Specialist Slider */}
          <div className="flex items-center space-x-3.5">
            <span className="text-sm text-[#68766B] font-medium">
              Network specialist
            </span>
            <span className="text-sm font-bold text-[#0369A1] tabular-nums min-w-[42px]">
              {networkHours} h
            </span>
            <Slider.Root
              value={[networkHours]}
              min={0}
              max={80}
              step={5}
              onValueChange={([val]) => onNetworkHoursChange(val)}
              className="relative flex items-center select-none touch-none w-[180px] h-5 cursor-pointer"
              aria-label="Network specialist capacity in hours"
            >
              <Slider.Track className="bg-[#E0E8DF] relative grow rounded-full h-[6px]">
                <Slider.Range className="absolute bg-[#0369A1] rounded-full h-full" />
              </Slider.Track>
              <Slider.Thumb
                className="block w-5 h-5 bg-[#0369A1] border-2 border-white rounded-full shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0369A1]"
                aria-label="Network specialist hours thumb"
              />
            </Slider.Root>
          </div>
        </div>

        {/* Right Side: Search Input and Filters Popover */}
        <div className="flex items-center space-x-3.5 shrink-0">
          <div className="relative w-[280px]">
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search cases..."
              className="w-full h-11 px-4 text-sm bg-white border border-[#E0E8DF] rounded-lg text-[#183B2A] placeholder-[#68766B] outline-none focus:border-[#477A58] focus-visible:ring-2 focus-visible:ring-[#477A58] shadow-xs"
              aria-label="Search cases"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => onSearchChange('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-[#68766B] hover:text-[#183B2A] px-1.5 py-0.5 rounded bg-[#F5F8F4]"
                aria-label="Clear search"
              >
                Clear
              </button>
            )}
          </div>

          <Popover.Root>
            <Popover.Trigger asChild>
              <button
                type="button"
                className={`h-11 px-5 text-sm font-semibold rounded-lg border transition-colors outline-none focus-visible:ring-2 focus-visible:ring-[#477A58] shadow-xs ${
                  hasActiveFilters
                    ? 'bg-[#477A58] text-white border-[#477A58]'
                    : 'bg-white border-[#E0E8DF] text-[#68766B] hover:bg-[#F5F8F4] hover:text-[#183B2A]'
                }`}
                aria-label="Filter queue cases"
              >
                Filter {hasActiveFilters ? '(Active)' : ''}
              </button>
            </Popover.Trigger>
            <Popover.Portal>
              <Popover.Content
                className="w-80 bg-white border border-[#E0E8DF] rounded-xl p-5 text-sm shadow-xl z-50 space-y-4"
                sideOffset={6}
                align="end"
              >
                <div className="flex items-center justify-between border-b border-[#E0E8DF] pb-2.5">
                  <span className="font-semibold text-base text-[#183B2A]">Filter Cases</span>
                  {hasActiveFilters && (
                    <button
                      type="button"
                      onClick={onClearFilters}
                      className="text-xs text-[#285239] hover:underline font-semibold"
                    >
                      Reset all
                    </button>
                  )}
                </div>

                {/* Severity Filter */}
                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-[#68766B] uppercase font-semibold">Severity</label>
                  <select
                    value={selectedSeverity}
                    onChange={(e) => onSeverityChange(e.target.value)}
                    className="w-full bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg p-2.5 text-sm text-[#183B2A] focus:outline-none focus:border-[#477A58]"
                  >
                    {severities.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Rule Filter */}
                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-[#68766B] uppercase font-semibold">Triggered Rule</label>
                  <select
                    value={selectedRule}
                    onChange={(e) => onRuleChange(e.target.value)}
                    className="w-full bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg p-2.5 text-sm text-[#183B2A] focus:outline-none focus:border-[#477A58]"
                  >
                    <option value="">All Rules</option>
                    {availableRules.map((r) => (
                      <option key={r} value={r}>
                        {r}
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
