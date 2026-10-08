import React from 'react';
import { Case } from '@/types/case';
import { Evidence } from '@/types/alert';

interface WhyFlaggedProps {
  readonly caseItem: Case;
  readonly evidenceList: readonly Evidence[];
}

export const WhyFlagged: React.FC<WhyFlaggedProps> = ({ caseItem, evidenceList }) => {
  const criticalCount = evidenceList.filter((e) => e.severity === 'CRITICAL').length;
  const highCount = evidenceList.filter((e) => e.severity === 'HIGH').length;

  return (
    <div className="bg-surface border border-border p-4 space-y-3">
      {/* Section Header */}
      <div className="flex items-center justify-between border-b border-border pb-2">
        <div>
          <span className="text-[10px] font-mono text-ink-subtle uppercase tracking-wider">
            Chapter 01 · Prioritization Rationale
          </span>
          <h2 className="font-sans text-sm sm:text-base font-bold text-green-950 uppercase tracking-wide">
            Why this case was prioritized
          </h2>
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[11px]">
          <span className="px-1.5 py-0.2 bg-paper-subtle border border-border text-ink">
            {evidenceList.length} Records
          </span>
          {criticalCount > 0 && (
            <span className="px-1.5 py-0.2 bg-critical-soft border border-critical/30 text-critical font-semibold">
              {criticalCount} Critical
            </span>
          )}
          {highCount > 0 && (
            <span className="px-1.5 py-0.2 bg-brick-soft border border-brick/30 text-brick font-semibold">
              {highCount} High
            </span>
          )}
        </div>
      </div>

      {/* Narrative Summary */}
      <p className="text-xs text-ink leading-relaxed font-normal">
        {caseItem.primary_indicator}. Multi-dimensional analytics engines identified concurrent behavioral anomalies across the focal provider and affiliated network entities, indicating non-standard billing velocity, reciprocal referral clustering, and shared corporate identities.
      </p>

      {/* Rules Triggered Line */}
      <div className="pt-2 border-t border-border flex flex-wrap items-center gap-2 text-xs">
        <span className="text-[10px] font-mono text-ink-subtle uppercase">Triggered Rules:</span>
        <div className="font-mono text-xs font-semibold text-green-950">
          {caseItem.rules_triggered.join(' · ')}
        </div>
      </div>

      {/* Aligned Facts Line */}
      <div className="pt-2 border-t border-border flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-sans text-ink">
        <div className="flex items-center gap-1">
          <strong className="font-mono font-bold text-green-950">{caseItem.claim_count}</strong>
          <span className="text-ink-muted">claims</span>
        </div>
        <span className="text-border-strong" aria-hidden="true">·</span>
        <div className="flex items-center gap-1">
          <strong className="font-mono font-bold text-green-950">${caseItem.est_dollars.toLocaleString()}</strong>
          <span className="text-ink-muted">exposure</span>
        </div>
        <span className="text-border-strong" aria-hidden="true">·</span>
        <div className="flex items-center gap-1">
          <strong className="font-mono font-bold text-brick">${caseItem.est_overpay.toLocaleString()}</strong>
          <span className="text-ink-muted">identifiable overpayment</span>
        </div>
        <span className="text-border-strong" aria-hidden="true">·</span>
        <div className="flex items-center gap-1">
          <span className="text-ink-subtle text-[10px] font-mono uppercase">Confidence:</span>
          <strong className="text-green-900 font-semibold">{caseItem.confidence}</strong>
        </div>
      </div>
    </div>
  );
};

