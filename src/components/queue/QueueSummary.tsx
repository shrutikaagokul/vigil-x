import React from 'react';
import { CapacitySummary } from '@/types/queue';

interface QueueSummaryProps {
  readonly summary?: CapacitySummary;
  readonly totalExposureDollars?: number;
  readonly totalOverpayDollars?: number;
}

export const QueueSummary: React.FC<QueueSummaryProps> = ({
  summary,
  totalExposureDollars = 0,
  totalOverpayDollars = 0,
}) => {
  if (!summary) return null;

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 py-1.5 px-3 bg-surface border border-border text-xs font-sans text-ink">
      <div className="flex items-center gap-1">
        <strong className="font-mono font-bold text-green-950">{summary.total_hours}h</strong>
        <span className="text-ink-muted">available</span>
        <span className="text-[11px] font-mono text-ink-subtle">({summary.general_hours}h gen / {summary.network_hours}h net)</span>
      </div>

      <span className="text-border-strong hidden sm:inline" aria-hidden="true">·</span>

      <div className="flex items-center gap-1">
        <strong className="font-mono font-bold text-green-950">{summary.estimated_cases_addressable}</strong>
        <span className="text-ink-muted">cases addressable</span>
      </div>

      <span className="text-border-strong hidden sm:inline" aria-hidden="true">·</span>

      <div className="flex items-center gap-1">
        <strong className={`font-mono font-bold ${summary.network_backlog_hours > 40 ? 'text-brick' : 'text-green-950'}`}>
          {summary.network_backlog_hours}h
        </strong>
        <span className="text-ink-muted">network backlog</span>
      </div>

      <span className="text-border-strong hidden sm:inline" aria-hidden="true">·</span>

      <div className="flex items-center gap-1">
        <strong className="font-mono font-bold text-green-950">${(totalExposureDollars / 1000).toFixed(0)}k</strong>
        <span className="text-ink-muted">queue exposure</span>
        <span className="text-[11px] font-mono text-ink-subtle">(est. recov: ${(totalOverpayDollars / 1000).toFixed(0)}k)</span>
      </div>
    </div>
  );
};

