import React from 'react';
import { QueueSortOption } from '@/types/queue';

interface CapacityControlsProps {
  readonly generalHours: number;
  readonly networkHours: number;
  readonly horizon: string;
  readonly sort: QueueSortOption;
  readonly onGeneralHoursChange: (hours: number) => void;
  readonly onNetworkHoursChange: (hours: number) => void;
  readonly onHorizonChange: (horizon: string) => void;
  readonly onSortChange: (sort: QueueSortOption) => void;
}

export const CapacityControls: React.FC<CapacityControlsProps> = ({
  generalHours,
  networkHours,
  horizon,
  sort,
  onGeneralHoursChange,
  onNetworkHoursChange,
  onHorizonChange,
  onSortChange,
}) => {
  return (
    <div className="bg-paper-subtle border border-border px-3 py-2 sm:py-2.5">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 sm:gap-4">
        {/* Sliders in single compact row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 flex-1">
          {/* Generalist Hours */}
          <div className="flex flex-col space-y-0.5">
            <div className="flex items-center justify-between text-xs">
              <label htmlFor="general-hours-slider" className="font-sans font-semibold text-green-950 uppercase tracking-wider text-[11px]">
                Generalist <span className="text-ink-subtle font-normal lowercase">(h/wk)</span>
              </label>
              <span className="font-mono font-bold text-xs text-green-950">
                {generalHours} <span className="text-ink-subtle font-normal text-[10px]">h</span>
              </span>
            </div>
            <input
              id="general-hours-slider"
              type="range"
              min="0"
              max="120"
              step="5"
              value={generalHours}
              onChange={(e) => onGeneralHoursChange(Number(e.target.value))}
              className="w-full h-1 bg-border-strong rounded-none appearance-none cursor-pointer accent-green-800"
              aria-label="Generalist capacity in hours per week"
            />
          </div>

          {/* Network Specialist Hours */}
          <div className="flex flex-col space-y-0.5">
            <div className="flex items-center justify-between text-xs">
              <label htmlFor="network-hours-slider" className="font-sans font-semibold text-green-950 uppercase tracking-wider text-[11px]">
                Network Specialist <span className="text-ink-subtle font-normal lowercase">(h/wk)</span>
              </label>
              <span className="font-mono font-bold text-xs text-green-950">
                {networkHours} <span className="text-ink-subtle font-normal text-[10px]">h</span>
              </span>
            </div>
            <input
              id="network-hours-slider"
              type="range"
              min="0"
              max="80"
              step="5"
              value={networkHours}
              onChange={(e) => onNetworkHoursChange(Number(e.target.value))}
              className="w-full h-1 bg-border-strong rounded-none appearance-none cursor-pointer accent-green-800"
              aria-label="Network specialist capacity in hours per week"
            />
          </div>
        </div>

        {/* Vertical Divider */}
        <div className="hidden lg:block w-[1px] h-6 bg-border-strong self-center" />

        {/* Horizon & Sort Controls */}
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-3 shrink-0">
          {/* Horizon Selector */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-mono text-ink-subtle uppercase tracking-wider">
              Horizon:
            </span>
            <div className="inline-flex border border-border bg-surface" role="group" aria-label="Investigation Horizon">
              {(['30d', '60d', '90d'] as const).map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => onHorizonChange(h)}
                  aria-pressed={horizon === h}
                  className={`px-2 py-0.5 text-xs font-mono transition-colors outline-none focus-visible:bg-green-100 ${
                    horizon === h
                      ? 'bg-green-900 text-ink-inverse font-semibold'
                      : 'text-ink-muted hover:text-ink hover:bg-paper-subtle'
                  }`}
                >
                  {h.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Sort Selector */}
          <div className="flex items-center gap-1.5">
            <label htmlFor="queue-sort-select" className="text-[10px] font-mono text-ink-subtle uppercase tracking-wider">
              Sort:
            </label>
            <select
              id="queue-sort-select"
              value={sort}
              onChange={(e) => onSortChange(e.target.value as QueueSortOption)}
              className="h-[26px] px-2 text-xs bg-surface border border-border text-ink outline-none focus-visible:border-green-800 font-sans"
            >
              <option value="priority">Priority Score</option>
              <option value="risk">Risk Index</option>
              <option value="exposure">Financial Exposure</option>
              <option value="network_complexity">Network Complexity</option>
              <option value="sla">SLA Due Date</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};

