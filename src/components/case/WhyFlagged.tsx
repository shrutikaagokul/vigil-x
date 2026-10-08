import React from 'react';
import { Case } from '@/types/case';
import { Evidence } from '@/types/alert';
import { formatCurrency } from '@/utils/currency';

interface WhyFlaggedProps {
  readonly caseItem: Case;
  readonly evidenceList: readonly Evidence[];
  readonly onSelectEvidence?: (evidenceId: string) => void;
  readonly onSelectClaim?: (claimId: string) => void;
}

export const WhyFlagged: React.FC<WhyFlaggedProps> = ({
  caseItem,
  evidenceList,
  onSelectEvidence,
}) => {
  // Select up to 4 distinct strongest evidence reasons
  const ruleMap = new Map<string, Evidence>();
  evidenceList.forEach((ev) => {
    if (!ruleMap.has(ev.rule_id)) {
      ruleMap.set(ev.rule_id, ev);
    }
  });

  let topReasons = Array.from(ruleMap.values()).slice(0, 4);
  if (topReasons.length === 0 && evidenceList.length > 0) {
    topReasons = evidenceList.slice(0, 4);
  }

  return (
    <section className="bg-surface border border-border p-5 sm:p-6 space-y-5">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="font-serif text-lg sm:text-xl font-bold text-green-950">
            Why this case was prioritized
          </h2>
          <p className="text-sm text-ink-muted mt-0.5">
            Key behavioral signals and correlated evidence driving the investigation priority.
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs shrink-0">
          <span className="px-2 py-0.5 bg-paper-subtle border border-border text-ink">
            {caseItem.confidence} Confidence
          </span>
          <span className="px-2 py-0.5 bg-critical-soft border border-critical/30 text-critical font-semibold">
            {caseItem.severity}
          </span>
        </div>
      </div>

      {/* Primary Prioritization Summary */}
      <div className="p-4 bg-paper-subtle border border-border space-y-2">
        <p className="text-sm sm:text-base text-ink leading-relaxed font-sans font-normal">
          {caseItem.primary_indicator}. Multi-dimensional analytics engines identified concurrent behavioral anomalies across the focal provider and affiliated network entities, indicating non-standard billing velocity, reciprocal referral clustering, and shared corporate identities.
        </p>

        <div className="pt-2 border-t border-border flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted font-sans">
          <span>
            Triggered Rules: <strong className="font-mono text-green-950">{caseItem.rules_triggered.join(' · ')}</strong>
          </span>
          <span className="text-border-strong">·</span>
          <span>
            Analyzed Claims: <strong className="font-mono text-ink">{caseItem.claim_count}</strong>
          </span>
          {caseItem.est_overpay > 0 && (
            <>
              <span className="text-border-strong">·</span>
              <span>
                Identifiable Overpayment: <strong className="font-mono text-brick">{formatCurrency(caseItem.est_overpay, 'full')}</strong>
              </span>
            </>
          )}
        </div>
      </div>

      {/* 4 Concise Prioritized Reasons */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
          <h3 className="text-sm font-semibold text-green-950">
            Key Prioritized Reasons ({topReasons.length} Primary Signals)
          </h3>
          <span className="text-xs text-ink-subtle font-sans">
            Click an evidence chip to inspect full audit ledger in Evidence
          </span>
        </div>

        <div className="border border-border divide-y divide-border bg-surface">
          {topReasons.length === 0 ? (
            <div className="p-4 text-center text-sm text-ink-muted bg-paper-subtle">
              No distinct evidence signals flagged for this case.
            </div>
          ) : (
            topReasons.map((ev) => {
              const severityClass = {
              CRITICAL: 'bg-critical-soft text-critical border-critical/30',
              HIGH: 'bg-brick-soft text-brick border-brick/30',
              MEDIUM: 'bg-brass-soft text-ink border-brass/40',
              LOW: 'bg-paper-subtle text-ink-subtle border-border',
            }[ev.severity] || 'bg-paper-subtle text-ink';

            return (
              <div
                key={ev.evidence_id}
                className="p-3.5 sm:p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-paper-subtle/40 transition-colors"
              >
                {/* Left: Metadata chips & One-line explanation */}
                <div className="flex flex-col sm:flex-row sm:items-center gap-3 flex-1 min-w-0">
                  <div className="flex items-center gap-2 shrink-0">
                    {/* Clickable Evidence ID Chip */}
                    <button
                      type="button"
                      data-testid="evidence-id-chip"
                      onClick={() => onSelectEvidence?.(ev.evidence_id)}
                      title="Click to view in Evidence chapter"
                      className="font-mono text-xs font-bold text-green-950 bg-paper border border-border px-2 py-0.5 hover:bg-green-100 hover:border-green-300 transition-colors cursor-pointer"
                    >
                      {ev.evidence_id}
                    </button>

                    {/* Rule ID & Version */}
                    <span className="font-mono text-xs text-ink-muted px-2 py-0.5 bg-paper border border-border">
                      {ev.rule_id} · v{ev.rule_version}
                    </span>

                    {/* Severity Badge */}
                    <span className={`px-2 py-0.5 text-[11px] font-mono font-bold uppercase border ${severityClass}`}>
                      {ev.severity}
                    </span>
                  </div>

                  {/* One-Line Explanation */}
                  <p className="text-sm text-ink leading-snug font-normal line-clamp-2 md:line-clamp-1">
                    {ev.plain_text}
                  </p>
                </div>

                {/* Right: Financial Figure (only if available) */}
                {ev.est_overpay > 0 && (
                  <div className="shrink-0 flex items-baseline gap-1.5 font-mono text-xs self-start md:self-center">
                    <span className="text-[11px] text-ink-subtle uppercase">Overpayment:</span>
                    <strong
                      data-testid="evidence-overpay"
                      className="font-bold text-brick text-sm tabular-nums"
                    >
                      {formatCurrency(ev.est_overpay, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </strong>
                  </div>
                )}
              </div>
            );
          }))}
        </div>
      </div>
    </section>
  );
};

