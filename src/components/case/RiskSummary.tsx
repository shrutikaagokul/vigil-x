import React from 'react';
import { Case } from '@/types/case';
import { ConflictingSignals } from './ConflictingSignals';

interface RiskSummaryProps {
  readonly caseItem: Case;
}

export const RiskSummary: React.FC<RiskSummaryProps> = ({ caseItem }) => {
  return (
    <div className="space-y-3">
      {/* Risk Index & Financial Exposure Assessment Panel */}
      <div className="bg-surface border border-border p-4 space-y-3">
        <div className="border-b border-border pb-2 flex items-center justify-between">
          <span className="text-[10px] font-mono font-semibold text-green-950 uppercase tracking-wider">
            Risk & Exposure Assessment
          </span>
          <span className="text-[10px] font-mono text-ink-subtle uppercase">
            Confidence: <strong className="text-green-900 font-semibold">{caseItem.confidence}</strong>
          </span>
        </div>

        {/* Major Risk Metric */}
        <div className="space-y-1">
          <div className="flex items-baseline justify-between">
            <span className="text-xs font-semibold text-green-950 uppercase tracking-wider text-[11px]">
              Risk Index
            </span>
            <div className="flex items-baseline gap-1">
              <span
                data-testid="risk-index-value"
                className="font-sans text-2xl sm:text-3xl font-bold text-green-950 leading-none"
              >
                {caseItem.risk_index}
              </span>
              <span className="text-xs font-mono text-ink-subtle">/ 100</span>
            </div>
          </div>

          <div className="w-full bg-paper-subtle h-1.5 border border-border overflow-hidden">
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
          <div className="flex justify-between text-[10px] font-mono text-ink-subtle">
            <span>0 (Low)</span>
            <span>50 (Moderate)</span>
            <span>100 (Critical)</span>
          </div>
        </div>

        {/* Operational Fact Ledger Table */}
        <div className="pt-2 border-t border-border">
          <table className="w-full text-xs font-sans">
            <tbody>
              <tr className="border-b border-border/70">
                <td className="py-1.5 px-0 text-ink-muted">Financial exposure</td>
                <td className="py-1.5 px-0 text-right font-mono font-bold text-green-950">
                  ${caseItem.est_dollars.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </td>
              </tr>
              <tr className="border-b border-border/70">
                <td className="py-1.5 px-0 text-ink-muted">Identifiable overpay</td>
                <td className="py-1.5 px-0 text-right font-mono font-bold text-brick">
                  ${caseItem.est_overpay.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </td>
              </tr>
              <tr className="border-b border-border/70">
                <td className="py-1.5 px-0 text-ink-muted">Claims analyzed</td>
                <td className="py-1.5 px-0 text-right font-mono font-bold text-ink">
                  {caseItem.claim_count}
                </td>
              </tr>
              <tr className="border-b border-border/70">
                <td className="py-1.5 px-0 text-ink-muted">Triggered rule models</td>
                <td className="py-1.5 px-0 text-right font-mono font-bold text-ink">
                  {caseItem.rules_triggered.length}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Triggered Rule Chips */}
        <div className="pt-1.5 space-y-1">
          <span className="text-[10px] font-mono text-ink-subtle uppercase block">
            Rule Models ({caseItem.rules_triggered.length}):
          </span>
          <div className="flex flex-wrap gap-1 font-mono text-xs">
            {caseItem.rules_triggered.map((rule) => (
              <span
                key={rule}
                className="px-1.5 py-0.2 bg-paper border border-border text-green-950 font-semibold"
              >
                {rule}
              </span>
            ))}
          </div>
        </div>

        {/* Primary Indicator */}
        <div className="pt-2 border-t border-border space-y-1">
          <span className="text-[10px] font-mono text-ink-subtle uppercase block">
            Primary Behavioral Anomaly:
          </span>
          <p className="text-xs text-ink leading-relaxed font-normal p-2 bg-paper-subtle border border-border">
            {caseItem.primary_indicator}
          </p>
        </div>
      </div>

      {/* Conflicting Signals Sub-panel */}
      <ConflictingSignals signals={caseItem.conflicting_signals} />
    </div>
  );
};

