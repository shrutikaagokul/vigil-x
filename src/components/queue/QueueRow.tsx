import React from 'react';
import { useNavigate } from 'react-router-dom';
import { QueueItem } from '@/types/queue';

interface QueueRowProps {
  readonly item: QueueItem;
  readonly rank: number;
  readonly isDeferred?: boolean;
}

export const QueueRow: React.FC<QueueRowProps> = ({
  item,
  rank,
  isDeferred = false,
}) => {
  const navigate = useNavigate();

  const handleRowClick = () => {
    navigate(`/cases/${item.case_id}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTableRowElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      navigate(`/cases/${item.case_id}`);
    }
  };

  return (
    <tr
      onClick={handleRowClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="row"
      aria-label={`Case ${item.case_id} for ${item.focal_provider_name}`}
      className={`group cursor-pointer transition-colors border-b border-border outline-none focus-visible:bg-green-50/70 hover:bg-paper-subtle ${
        isDeferred ? 'bg-surface opacity-80' : 'bg-surface'
      }`}
    >
      {/* 1. Rank */}
      <td className="py-2.5 px-3 align-top text-center w-12">
        <span className="font-mono text-xs font-bold text-green-950">
          {String(rank).padStart(2, '0')}
        </span>
      </td>

      {/* 2. Case & Focal Provider */}
      <td className="py-2.5 px-3 align-top min-w-[200px]">
        <div className="flex flex-col">
          <span className="font-mono text-xs font-bold text-green-950 group-hover:text-green-700 transition-colors">
            {item.case_id}
          </span>
          <span className="text-xs font-medium text-ink mt-0.5 leading-snug">
            {item.focal_provider_name}
          </span>
          <span className="text-[11px] font-mono text-ink-subtle uppercase mt-0.5">
            {item.focal_provider_id} · {item.specialty.replace('_', ' ')}
          </span>
        </div>
      </td>

      {/* 3. Risk Index */}
      <td className="py-2.5 px-3 align-top w-24">
        <div className="flex flex-col">
          <div className="flex items-baseline gap-1">
            <span className="font-sans text-sm font-bold text-green-950 leading-none">
              {item.risk_index}
            </span>
            <span className="text-[10px] font-mono text-ink-subtle">/ 100</span>
          </div>
          <div className="w-full bg-paper-subtle h-1 mt-1 border border-border">
            <div
              className={`h-full ${
                item.risk_index >= 90
                  ? 'bg-critical'
                  : item.risk_index >= 75
                  ? 'bg-brick'
                  : 'bg-brass'
              }`}
              style={{ width: `${item.risk_index}%` }}
            />
          </div>
          <span className="text-[10px] font-mono text-ink-subtle mt-0.5 uppercase">
            {item.severity}
          </span>
        </div>
      </td>

      {/* 4. Why Prioritized */}
      <td className="py-2.5 px-3 align-top">
        <div className="flex flex-col space-y-1">
          <p className="text-xs text-ink leading-snug font-normal">
            {item.primary_indicator}
          </p>
          <div className="font-mono text-[11px] text-ink-muted">
            {item.rules_triggered.join(' · ')}
          </div>
        </div>
      </td>

      {/* 5. Network Complexity */}
      <td className="py-2.5 px-3 align-top w-28">
        <div className="flex flex-col">
          {item.requires_network_specialist ? (
            <div>
              <span className="text-xs font-semibold text-green-950">
                Multi-entity
              </span>
              <span className="block text-[11px] text-ink-muted mt-0.5 font-sans">
                6 providers
              </span>
            </div>
          ) : (
            <span className="text-[11px] text-ink-subtle font-sans">
              Single provider
            </span>
          )}
        </div>
      </td>

      {/* 6. Exposure */}
      <td className="py-2.5 px-3 align-top text-right w-32">
        <div className="flex flex-col items-end">
          <span className="font-sans text-xs font-bold text-green-950">
            ${item.est_dollars.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </span>
          <span className="text-[10px] font-mono text-ink-subtle mt-0.5">
            ${(item.est_overpay / 1000).toFixed(1)}K overpay
          </span>
        </div>
      </td>

      {/* 7. Action */}
      <td className="py-3 px-4 align-top text-right w-24">
        <div className="flex flex-col items-end space-y-1">
          <span className="text-sm font-semibold text-green-800 group-hover:text-green-950">
            Open
          </span>
          <span className="text-xs font-mono text-ink-subtle uppercase">
            {new Date(item.sla_due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          </span>
        </div>
      </td>
    </tr>
  );
};

