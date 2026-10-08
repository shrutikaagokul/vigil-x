import React from 'react';
import { QueueItem } from '@/types/queue';
import { QueueRow } from './QueueRow';
import { QueueEmptyState } from './QueueEmptyState';

interface QueueTableProps {
  readonly items: readonly QueueItem[];
  readonly isFiltered: boolean;
  readonly addressableCount?: number;
  readonly allocatedHours?: number;
  readonly onClearFilters?: () => void;
}

export const QueueTable: React.FC<QueueTableProps> = ({
  items,
  isFiltered,
  addressableCount = 3,
  allocatedHours = 60,
  onClearFilters,
}) => {
  if (items.length === 0) {
    return <QueueEmptyState isFiltered={isFiltered} onClearFilters={onClearFilters} />;
  }

  // Determine boundary cut-off
  const boundaryIndex = Math.max(1, addressableCount);

  return (
    <div className="bg-surface border border-border overflow-x-auto">
      <table className="w-full border-collapse text-left" role="table" aria-label="Investigation Queue Table">
        <thead>
          <tr className="bg-paper-subtle border-b border-border text-ink-muted text-[11px] font-mono uppercase tracking-wider">
            <th className="py-2 px-3 text-center w-12 font-semibold">Rank</th>
            <th className="py-2 px-3 font-semibold min-w-[200px]">Case</th>
            <th className="py-2 px-3 font-semibold w-24">Risk</th>
            <th className="py-2 px-3 font-semibold">Why Prioritized</th>
            <th className="py-2 px-3 font-semibold w-28">Network</th>
            <th className="py-2 px-3 font-semibold text-right w-32">Exposure</th>
            <th className="py-2 px-3 font-semibold text-right w-20">Action</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => {
            const isDeferred = index >= boundaryIndex;
            const isBoundary = index === boundaryIndex;

            return (
              <React.Fragment key={item.case_id}>
                {isBoundary && (
                  <tr
                    key="capacity-boundary"
                    className="border-t border-b border-dashed border-brass bg-brass-soft/50"
                    data-testid="capacity-boundary-line"
                  >
                    <td colSpan={7} className="py-1.5 px-3 text-center font-mono text-[11px] font-semibold text-ink tracking-wider uppercase select-none">
                      ─── THIS WEEK&apos;S CAPACITY · {allocatedHours} HOURS · {boundaryIndex} CASES ───
                    </td>
                  </tr>
                )}
                <QueueRow
                  item={item}
                  rank={index + 1}
                  isDeferred={isDeferred}
                />
              </React.Fragment>
            );
          })}
          {boundaryIndex >= items.length && items.length > 0 && (
            <tr
              key="capacity-boundary-full"
              className="border-t border-b border-dashed border-brass bg-brass-soft/50"
              data-testid="capacity-boundary-line"
            >
              <td colSpan={7} className="py-1.5 px-3 text-center font-mono text-[11px] font-semibold text-ink tracking-wider uppercase select-none">
                ─── THIS WEEK&apos;S CAPACITY · {allocatedHours} HOURS · ALL {items.length} CASES ADDRESSABLE ───
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

