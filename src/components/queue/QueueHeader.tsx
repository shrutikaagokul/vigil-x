import React from 'react';

interface QueueHeaderProps {
  readonly fitCount: number;
  readonly totalAtRisk: number; // in INR
  readonly horizon: string;
  readonly onHorizonChange: (horizon: string) => void;
}

export const QueueHeader: React.FC<QueueHeaderProps> = ({
  fitCount,
  totalAtRisk,
  horizon,
  onHorizonChange,
}) => {
  // Format totalAtRisk compactly e.g. "₹1.8 Cr" or "₹38 L"
  const formattedAmount = (() => {
    const abs = Math.abs(totalAtRisk);
    if (abs >= 1e7) {
      const cr = (abs / 1e7).toFixed(1).replace(/\.0$/, '');
      return `₹${cr} Cr`;
    }
    if (abs >= 1e5) {
      const l = (abs / 1e5).toFixed(1).replace(/\.0$/, '');
      return `₹${l} L`;
    }
    return `₹${Math.round(abs).toLocaleString('en-IN')}`;
  })();

  const horizons = [
    { label: '30 days', value: '30d' },
    { label: '60', value: '60d' },
    { label: '90', value: '90d' },
  ];

  return (
    <div className="w-full pt-[1.75rem] px-[3rem] flex flex-col md:flex-row md:items-end justify-between gap-4">
      {/* Left: Heading and dynamic summary sentence */}
      <div>
        <h1 className="font-serif text-[2.5rem] leading-[2.75rem] font-semibold text-[#0B1A12] tracking-tight">
          Queue
        </h1>
        <p className="text-[1.125rem] text-[#4F5F55] mt-1 font-normal">
          {fitCount} cases fit this week.{' '}
          <strong className="font-semibold text-[#14201A]">{formattedAmount}</strong> at risk in the queue.
        </p>
      </div>

      {/* Right: Horizon segmented control */}
      <div className="flex items-center shrink-0">
        <div
          className="inline-flex border border-[#2A5A3F] rounded-[3px] bg-white p-[1px]"
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
                className={`px-3 py-1.5 text-[0.9375rem] font-semibold transition-colors rounded-[2px] outline-none focus-visible:ring-2 focus-visible:ring-[#2A5A3F] ${
                  isActive
                    ? 'bg-[#2A5A3F] text-white'
                    : 'bg-transparent text-[#4F5F55] hover:text-[#14201A] hover:bg-[#F3F8F4]'
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
