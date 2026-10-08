import React from 'react';
import { Case } from '@/types/case';
import { ConflictingSignals } from './ConflictingSignals';

interface RiskSummaryProps {
  readonly caseItem: Case;
}

export const RiskSummary: React.FC<RiskSummaryProps> = ({ caseItem }) => {
  return (
    <section className="bg-surface border border-border p-5 sm:p-6 space-y-6">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="font-serif text-lg sm:text-xl font-bold text-green-950">
            Risk Score Decomposition
          </h2>
          <p className="text-sm text-ink-muted mt-0.5 font-sans">
            Multi-signal scoring components, financial exposure breakdown, and model confidence.
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs shrink-0">
          <span className="text-ink-subtle uppercase text-[11px]">Confidence Level:</span>
          <strong className="text-green-900 font-bold bg-paper-subtle border border-border px-2 py-0.5">
            {caseItem.confidence}
          </strong>
        </div>
      </div>

      {/* Primary 3-Metric Score Hierarchy */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Overall Risk Score */}
        <div className="p-4 bg-paper-subtle border border-border space-y-2">
          <span className="text-[11px] font-mono text-ink-subtle uppercase block tracking-wider">
            Overall Risk Score
          </span>
          <div className="flex items-baseline gap-1.5">
            <span
              data-testid="risk-index-value"
              className="font-serif text-3xl sm:text-4xl font-bold text-green-950 leading-none"
            >
              {caseItem.risk_index}
            </span>
            <span className="font-mono text-sm text-ink-subtle">/ 100</span>
          </div>
          <div className="w-full bg-paper h-2 border border-border overflow-hidden mt-1">
            <div
              className={`h-full ${
                caseItem.risk_index >= 90
                  ? 'bg-critical'
                  : caseItem.risk_index >= 75
                  ? 'bg-brick'
                  : 'bg-brass'
              }`}
              style={{ width: `${caseItem.risk_index}%` }}
            />
          </div>
          <span className="text-[11px] font-mono text-ink-muted block pt-0.5">
            Severity Tier: <strong className="text-critical">{caseItem.severity}</strong>
          </span>
        </div>

        {/* Financial Exposure */}
        <div className="p-4 bg-paper-subtle border border-border space-y-2">
          <span className="text-[11px] font-mono text-ink-subtle uppercase block tracking-wider">
            Financial Exposure
          </span>
          <span className="font-mono text-2xl sm:text-3xl font-bold text-green-950 block leading-none">
            ₹{caseItem.est_dollars.toLocaleString('en-IN')}
          </span>
          <span className="text-xs text-brick font-mono font-semibold block pt-1">
            ₹{caseItem.est_overpay.toLocaleString('en-IN')} direct overpayment
          </span>
          <span className="text-[11px] text-ink-muted block font-sans">
            Calculated across {caseItem.claim_count} analyzed claims
          </span>
        </div>

        {/* Behavioral Signals */}
        <div className="p-4 bg-paper-subtle border border-border space-y-2">
          <span className="text-[11px] font-mono text-ink-subtle uppercase block tracking-wider">
            Active Signal Models
          </span>
          <span className="font-mono text-2xl sm:text-3xl font-bold text-green-950 block leading-none">
            {caseItem.rules_triggered.length}
          </span>
          <div className="flex flex-wrap gap-1 font-mono text-[11px] pt-1">
            {caseItem.rules_triggered.map((rule) => (
              <span
                key={rule}
                className="px-1.5 py-0.5 bg-paper border border-border text-green-950 font-semibold"
              >
                {rule}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Exposure & Overpayment Ledger Breakdown */}
      <div className="p-4 bg-surface border border-border space-y-3">
        <h3 className="text-xs font-mono font-bold uppercase text-green-950 tracking-wider">
          Quantitative Risk Attributes
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm font-sans">
            <tbody className="divide-y divide-border">
              <tr>
                <td className="py-2 text-ink-muted">Estimated Total Financial Exposure</td>
                <td className="py-2 text-right font-mono font-bold text-green-950">
                  ₹{caseItem.est_dollars.toLocaleString('en-IN')}
                </td>
              </tr>
              <tr>
                <td className="py-2 text-ink-muted">Identifiable Line-Item Overpayment</td>
                <td className="py-2 text-right font-mono font-bold text-brick">
                  ₹{caseItem.est_overpay.toLocaleString('en-IN')}
                </td>
              </tr>
              <tr>
                <td className="py-2 text-ink-muted">Claims Evaluated Under Triggered Rules</td>
                <td className="py-2 text-right font-mono font-semibold text-ink">
                  {caseItem.claim_count}
                </td>
              </tr>
              <tr>
                <td className="py-2 text-ink-muted">Deterministic Priority Score</td>
                <td className="py-2 text-right font-mono font-semibold text-green-950">
                  {caseItem.priority_score} / 100
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Conflicting & Mitigating Signals Sub-section */}
      <ConflictingSignals signals={caseItem.conflicting_signals} />
    </section>
  );
};

