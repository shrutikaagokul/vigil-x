import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { QueueItem } from '@/types/queue';
import { formatExposureRange, formatINR } from '@/utils/currency';

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
    <div className="flex-1 min-w-0" role="region" aria-label="Investigation Worklist">
      {/* 6 Column Header Table */}
      <table className="w-full border-collapse text-left" role="table">
        <thead>
          <tr className="border-b-2 border-[#12291C] text-[0.875rem] font-medium text-[#4F5F55] pb-2">
            <th className="py-2 px-3 w-[56px] font-medium text-left">Rank</th>
            <th className="py-2 px-3 font-medium text-left">Case</th>
            <th className="py-2 px-3 w-[90px] font-medium text-left">Risk</th>
            <th className="py-2 px-3 w-[190px] font-medium text-left">Exposure</th>
            <th className="py-2 px-3 w-[80px] font-medium text-left">Effort</th>
            <th className="py-2 px-3 w-[120px] font-medium text-left">Rules-only</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#D3E0D6]">
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
                      className="h-[46px]"
                    >
                      <td colSpan={6} className="py-2 px-0 select-none">
                        <div className="flex items-center justify-center w-full">
                          <div className="flex-1 border-t-2 border-dashed border-[#B38A2E]" />
                          <span className="px-4 text-[0.875rem] font-semibold text-[#701F14] whitespace-nowrap">
                            Capacity reached · {usedHours} of {allocatedHours} h
                          </span>
                          <div className="flex-1 border-t-2 border-dashed border-[#B38A2E]" />
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
                    className={`cursor-pointer transition-colors outline-none focus-visible:ring-2 focus-visible:ring-[#2A5A3F] focus-visible:ring-offset-2 ${
                      isDeferred ? 'min-h-[64px] h-[68px]' : 'min-h-[72px] h-[76px]'
                    } ${
                      isSelected
                        ? 'bg-[#E3EFE5]'
                        : isDeferred
                        ? 'bg-[#F3F8F4] hover:bg-[#EAEFEA]'
                        : 'bg-[#F3F8F4] hover:bg-[#E8EFE8]'
                    }`}
                  >
                    {/* 1. Rank */}
                    <td className="py-3 px-3 align-middle w-[56px]">
                      <span className="font-serif text-[1.875rem] leading-none font-semibold text-[#1B3A29]">
                        {rank}
                      </span>
                    </td>

                    {/* 2. Case Name & Subtitle */}
                    <td className="py-3 px-3 align-middle min-w-[200px]">
                      <div className="flex flex-col justify-center">
                        <span className="text-[1.1875rem] font-semibold text-[#14201A] leading-snug">
                          {displayName}
                        </span>
                        {isDeferred ? (
                          <span className="text-[0.9375rem] text-[#9E3626] font-normal leading-normal mt-0.5">
                            Waiting 4 weeks puts about {formatINR(item.cost_of_delay_4w, 'compact')} more at risk
                          </span>
                        ) : (
                          <span className="text-[0.9375rem] text-[#4F5F55] font-normal leading-normal mt-0.5">
                            {displaySubtitle}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* 3. Risk */}
                    <td className="py-3 px-3 align-middle w-[90px]">
                      <div className="flex items-center space-x-2">
                        <span
                          className="inline-block w-[10px] h-[10px] rounded-full shrink-0"
                          style={{ backgroundColor: getSeverityDotColor(item.severity) }}
                          aria-hidden="true"
                        />
                        <span className="text-[1.25rem] font-semibold text-[#14201A] tabular-nums">
                          {item.risk_index}
                        </span>
                      </div>
                    </td>

                    {/* 4. Exposure */}
                    <td className="py-3 px-3 align-middle w-[190px]">
                      <span className="text-[1.125rem] font-semibold text-[#14201A] tabular-nums whitespace-nowrap">
                        {formatExposureRange(item.exposure_low, item.exposure_high)}
                      </span>
                    </td>

                    {/* 5. Effort */}
                    <td className="py-3 px-3 align-middle w-[80px]">
                      <span className="text-[1.0625rem] text-[#14201A] font-normal tabular-nums">
                        {item.effort_hours} h
                      </span>
                    </td>

                    {/* 6. Rules-only Rank Delta */}
                    <td className="py-3 px-3 align-middle w-[120px]">
                      <span className="text-[1.0625rem] text-[#4F5F55] tabular-nums">
                        #{item.baseline_rank}{' '}
                        <span className="text-[#8A969C]">→</span>{' '}
                        <strong className="font-bold text-[#1B3A29]">#{rank}</strong>
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
