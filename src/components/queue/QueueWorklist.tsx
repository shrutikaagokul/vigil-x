import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { QueueItem } from '@/types/queue';
import { formatExposureRange, formatCurrency } from '@/utils/currency';

interface QueueWorklistProps {
  readonly items: readonly QueueItem[];
  readonly selectedCaseId: string | null;
  readonly addressableCount: number;
  readonly allocatedHours: number;
  readonly usedHours: number;
  readonly onSelectCase: (caseId: string) => void;
}

export const QueueWorklist: React.FC<QueueWorklistProps> = ({
  items,
  selectedCaseId,
  addressableCount,
  allocatedHours,
  usedHours,
  onSelectCase,
}) => {
  const boundaryIndex = Math.max(1, Math.min(items.length, addressableCount));

  const getSeverityDotColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return '#701F14';
      case 'HIGH':
        return '#9E3626';
      case 'MEDIUM':
        return '#B38A2E';
      case 'LOW':
      default:
        return '#4C8C5E';
    }
  };

  return (
    <div className="flex-1 min-w-0 bg-white border border-[#E0E8DF] rounded-xl overflow-hidden shadow-xs" role="region" aria-label="Investigation Worklist">
      {/* 6 Column Header Table */}
      <table className="w-full border-collapse text-left" role="table">
        <thead>
          <tr className="border-b border-[#E0E8DF] bg-[#F5F8F4] text-[0.875rem] font-medium text-[#68766B]">
            <th className="py-3 px-4 w-[64px] font-medium text-left">Rank</th>
            <th className="py-3 px-4 font-medium text-left">Case</th>
            <th className="py-3 px-4 w-[96px] font-medium text-left">Risk</th>
            <th className="py-3 px-4 w-[200px] font-medium text-left">Exposure</th>
            <th className="py-3 px-4 w-[84px] font-medium text-left">Effort</th>
            <th className="py-3 px-4 w-[130px] font-medium text-left">Rules-only</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#E0E8DF]">
          <AnimatePresence initial={false}>
            {items.map((item, index) => {
              const rank = index + 1;
              const isDeferred = index >= boundaryIndex;
              const isBoundary = index === boundaryIndex;
              const isSelected = selectedCaseId === item.case_id;

              const displayName = item.name || item.focal_provider_name || item.title;
              const displaySubtitle = item.subtitle || `${item.specialty.replace('_', ' ')} · single provider`;

              return (
                <React.Fragment key={item.case_id}>
                  {/* Capacity Boundary Line */}
                  {isBoundary && (
                    <tr
                      key="capacity-boundary-line"
                      data-testid="capacity-boundary-line"
                      className="h-[46px] bg-[#FEF3C7]/40"
                    >
                      <td colSpan={6} className="py-2 px-0 select-none">
                        <div className="flex items-center justify-center w-full">
                          <div className="flex-1 border-t-2 border-dashed border-[#B45309]/50" />
                          <span className="px-4 text-[0.8125rem] font-semibold text-[#B45309] uppercase tracking-wider whitespace-nowrap">
                            Capacity reached · {usedHours} of {allocatedHours} h
                          </span>
                          <div className="flex-1 border-t-2 border-dashed border-[#B45309]/50" />
                        </div>
                      </td>
                    </tr>
                  )}

                  {/* Worklist Row */}
                  <motion.tr
                    layout
                    transition={{ duration: 0.18, ease: 'easeInOut' }}
                    onClick={() => onSelectCase(item.case_id)}
                    tabIndex={0}
                    role="row"
                    aria-selected={isSelected}
                    aria-label={`Case ${displayName}, Rank ${rank}`}
                    onKeyDown={(e) => {
                      if (e.key === ' ' || e.key === 'Spacebar') {
                        e.preventDefault();
                        onSelectCase(item.case_id);
                      }
                    }}
                    className={`cursor-pointer transition-colors outline-none focus-visible:ring-2 focus-visible:ring-[#477A58] focus-visible:ring-offset-2 focus-visible:ring-offset-white ${
                      isDeferred ? 'min-h-[64px] h-[68px]' : 'min-h-[72px] h-[76px]'
                    } ${
                      isSelected
                        ? 'bg-[#E8F2E8] border-l-4 border-l-[#477A58]'
                        : isDeferred
                        ? 'bg-white/80 hover:bg-[#F5F8F4]'
                        : 'bg-white hover:bg-[#F5F8F4]'
                    }`}
                  >
                    {/* 1. Rank */}
                    <td className="py-3 px-4 align-middle w-[64px]">
                      <span className={`font-mono text-[1.5rem] leading-none font-bold ${isSelected ? 'text-[#183B2A]' : 'text-[#285239]'}`}>
                        {rank}
                      </span>
                    </td>

                    {/* 2. Case Name & Subtitle */}
                    <td className="py-3 px-4 align-middle min-w-[200px]">
                      <div className="flex flex-col justify-center">
                        <span className="text-[1.0625rem] font-semibold text-[#183B2A] leading-snug">
                          {displayName}
                        </span>
                        {isDeferred ? (
                          <span className="text-[0.875rem] text-[#B91C1C] font-normal leading-normal mt-0.5">
                            Waiting 4 weeks puts about {formatCurrency(item.cost_of_delay_4w, 'compact')} more at risk
                          </span>
                        ) : (
                          <span className="text-[0.875rem] text-[#68766B] font-normal leading-normal mt-0.5">
                            {displaySubtitle}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* 3. Risk */}
                    <td className="py-3 px-4 align-middle w-[96px]">
                      <div className="flex items-center space-x-2">
                        <span
                          className="inline-block w-[10px] h-[10px] rounded-full shrink-0"
                          style={{ backgroundColor: getSeverityDotColor(item.severity) }}
                          aria-hidden="true"
                        />
                        <span className="text-[1.125rem] font-semibold text-[#183B2A] tabular-nums">
                          {item.risk_index}
                        </span>
                      </div>
                    </td>

                    {/* 4. Exposure */}
                    <td className="py-3 px-4 align-middle w-[200px]">
                      <span className="text-[1.0625rem] font-semibold text-[#183B2A] tabular-nums whitespace-nowrap">
                        {formatExposureRange(item.exposure_low, item.exposure_high)}
                      </span>
                    </td>

                    {/* 5. Effort */}
                    <td className="py-3 px-4 align-middle w-[84px]">
                      <span className="text-[0.9375rem] text-[#24352A] font-normal tabular-nums">
                        {item.effort_hours} h
                      </span>
                    </td>

                    {/* 6. Rules-only Rank Delta */}
                    <td className="py-4 px-5 align-middle w-[140px]">
                      <span className="text-base text-[#68766B] tabular-nums">
                        #{item.baseline_rank}{' '}
                        <span className="text-[#68766B]">to</span>{' '}
                        <strong className="font-bold text-[#285239]">#{rank}</strong>
                      </span>
                    </td>
                  </motion.tr>
                </React.Fragment>
              );
            })}
          </AnimatePresence>
        </tbody>
      </table>
    </div>
  );
};
