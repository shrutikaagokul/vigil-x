import React from 'react';
import { Case } from '@/types/case';
import { Evidence } from '@/types/alert';

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
  onSelectClaim,
}) => {
  // Select the strongest evidence per distinct detection rule to provide 3-4 comprehensive reasons
  const ruleMap = new Map<string, Evidence>();
  evidenceList.forEach((ev) => {
    if (!ruleMap.has(ev.rule_id)) {
      ruleMap.set(ev.rule_id, ev);
    }
  });
  const topReasons = Array.from(ruleMap.values()).slice(0, 4);

  return (
    <section className="bg-surface border border-border p-5 sm:p-6 space-y-5">
      {/* Chapter 01 Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <span className="text-[11px] font-mono text-ink-subtle uppercase tracking-wider block">
            Primary Investigation View · Chapter 01
          </span>
          <h2 className="font-serif text-lg sm:text-xl font-bold text-green-950">
            Why this case was prioritized
          </h2>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="px-2 py-0.5 bg-paper-subtle border border-border text-ink">
            {caseItem.confidence} Confidence
          </span>
          <span className="px-2 py-0.5 bg-critical-soft border border-critical/30 text-critical font-semibold">
            {caseItem.severity}
          </span>
        </div>
      </div>

      {/* Primary Indicator Context Banner */}
      <div className="p-4 bg-paper-subtle border border-border space-y-2">
        <span className="text-[11px] font-mono font-bold text-green-950 uppercase tracking-wider block">
          Primary Prioritization Rationale
        </span>
        <p className="text-sm sm:text-base text-ink leading-relaxed font-sans font-normal">
          {caseItem.primary_indicator}. Multi-dimensional analytics engines identified concurrent behavioral anomalies across the focal provider and affiliated network entities, indicating non-standard billing velocity, reciprocal referral clustering, and shared corporate identities.
        </p>

        <div className="pt-2 border-t border-border flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted">
          <span>
            Triggered Rules: <strong className="font-mono text-green-950">{caseItem.rules_triggered.join(' · ')}</strong>
          </span>
          <span className="text-border-strong">·</span>
          <span>
            Analyzed Claims: <strong className="font-mono text-ink">{caseItem.claim_count}</strong>
          </span>
          <span className="text-border-strong">·</span>
          <span>
            Identifiable Overpayment: <strong className="font-mono text-brick">${caseItem.est_overpay.toLocaleString()}</strong>
          </span>
        </div>
      </div>

      {/* 3-4 Strongest Evidentiary Reasons */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono uppercase font-bold text-green-950 tracking-wider">
            Key Supporting Evidence ({topReasons.length} Primary Signals)
          </h3>
          <span className="text-xs text-ink-subtle font-sans">
            Click any evidence chip to focus in Evidence Ledger
          </span>
        </div>

        <div className="space-y-3">
          {topReasons.map((ev) => {
            const severityClass = {
              CRITICAL: 'bg-critical-soft text-critical border-critical/30',
              HIGH: 'bg-brick-soft text-brick border-brick/30',
              MEDIUM: 'bg-brass-soft text-ink border-brass/40',
              LOW: 'bg-paper-subtle text-ink-subtle border-border',
            }[ev.severity] || 'bg-paper-subtle text-ink';

            return (
              <article
                key={ev.evidence_id}
                className="p-4 bg-surface border border-border space-y-2.5 hover:bg-paper-subtle/40 transition-colors"
              >
                {/* Evidence Item Header */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Clickable Evidence ID Chip */}
                    <button
                      type="button"
                      data-testid="evidence-id-chip"
                      onClick={() => onSelectEvidence?.(ev.evidence_id)}
                      title="Click to view in Evidence Ledger"
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

                  {/* Overpayment Value */}
                  <div className="flex items-baseline gap-1.5 font-mono text-xs">
                    <span className="text-[11px] text-ink-subtle uppercase">Est. Overpayment:</span>
                    <strong
                      data-testid="evidence-overpay"
                      className="font-bold text-brick text-sm"
                    >
                      ${ev.est_overpay.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </strong>
                  </div>
                </div>

                {/* Plain-Text Finding Explanation */}
                <p className="text-sm text-ink leading-relaxed font-normal">
                  {ev.plain_text}
                </p>

                {/* Matched Fields & Associated Claims */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-border text-xs">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[11px] font-mono text-ink-subtle uppercase">Matched:</span>
                    {ev.fields_matched.map((f) => (
                      <span
                        key={f}
                        className="px-1.5 py-0.5 text-[11px] font-mono bg-paper border border-border text-ink-muted"
                      >
                        {f}
                      </span>
                    ))}
                  </div>

                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[11px] font-mono text-ink-subtle uppercase">Claims:</span>
                    {ev.claim_ids.map((cid) => (
                      <button
                        key={cid}
                        type="button"
                        onClick={() => onSelectClaim?.(cid)}
                        title={`Inspect claim ${cid}`}
                        className="px-2 py-0.5 text-[11px] font-mono bg-green-50 hover:bg-green-100 text-green-900 border border-green-300 font-semibold"
                      >
                        {cid} →
                      </button>
                    ))}
                  </div>
                </div>

                {/* False Positive Context Notes if present */}
                {ev.fp_notes && (
                  <div
                    data-testid="fp-notes-box"
                    className="p-2.5 bg-paper border border-border text-xs text-ink-muted space-y-1"
                  >
                    <strong className="font-mono text-[11px] text-green-950 uppercase block">
                      False-Positive Context:
                    </strong>
                    <p className="leading-relaxed">{ev.fp_notes}</p>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
};

