import React from 'react';
import { formatCurrency } from '@/utils/currency';

interface QueueHeaderProps {
  readonly fitCount: number;
  readonly totalAtRisk: number;
  readonly horizon: string;
  readonly onHorizonChange: (horizon: string) => void;
}

export const QueueHeader: React.FC<QueueHeaderProps> = ({
  fitCount,
  totalAtRisk,
  horizon,
  onHorizonChange,
}) => {
  const formattedAmount = formatCurrency(totalAtRisk, 'compact');

  const horizons = [
    { label: '30', value: '30d' },
    { label: '60', value: '60d' },
    { label: '90', value: '90d' },
  ];

  return (
    <div className="w-full pt-6 pb-3 px-6 md:px-8 flex flex-col md:flex-row md:items-end justify-between gap-5">
      {/* Left: Heading and dynamic summary sentence */}
      <div>
        <h1 className="font-serif text-3xl md:text-4xl font-bold text-[#183B2A] tracking-tight">
          Queue
        </h1>
        <p className="text-base text-[#68766B] mt-1.5 font-normal">
          {fitCount} cases fit this week.{' '}
          <strong className="font-semibold text-[#285239]">{formattedAmount}</strong> at risk in the queue.
        </p>
      </div>

      {/* Right: Horizon segmented control */}
      <div className="flex items-center shrink-0">
        <div
          className="inline-flex border border-[#E0E8DF] rounded-lg bg-white p-1 shadow-xs"
          role="group"
          aria-label="Lookback Horizon"
        >
          {horizons.map((h) => {
            const isActive = horizon === h.value;
            return (
              <button
                key={h.value}
                type="button"
                onClick={() => onHorizonChange(h.value)}
                aria-pressed={isActive}
                className={`px-4 py-2 text-sm font-semibold transition-colors rounded-md outline-none focus-visible:ring-2 focus-visible:ring-[#477A58] ${
                  isActive
                    ? 'bg-[#477A58] text-white shadow-xs'
                    : 'bg-transparent text-[#68766B] hover:text-[#183B2A] hover:bg-[#F5F8F4]'
                }`}
              >
                {h.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
