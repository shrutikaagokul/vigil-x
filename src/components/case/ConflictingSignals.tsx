import React from 'react';
import { ConflictingSignal } from '@/types/case';

interface ConflictingSignalsProps {
  readonly signals?: readonly ConflictingSignal[];
}

export const ConflictingSignals: React.FC<ConflictingSignalsProps> = ({ signals = [] }) => {
  return (
    <div className="bg-surface border border-border p-4 space-y-3">
      <div className="flex items-center justify-between border-b border-border pb-2">
        <h3 className="text-xs font-bold text-green-950 uppercase tracking-wide">
          Conflicting &amp; Mitigating Signals
        </h3>
        <span className="text-[10px] font-mono text-ink-subtle uppercase">
          Uncertainty Review
        </span>
      </div>

      {signals.length === 0 ? (
        <p className="text-xs text-ink-muted italic">
          No conflicting operational signals identified. All available indicators point consistently to current prioritization assessment.
        </p>
      ) : (
        <div className="space-y-2">
          {signals.map((sig, idx) => (
            <div
              key={idx}
              className="p-2.5 bg-paper-subtle border border-border space-y-2 text-xs"
            >
              <span className="font-semibold text-ink block border-b border-border pb-1">
                {sig.title}
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                {/* Mitigating / Positive Signal */}
                <div className="bg-surface p-2 border border-border">
                  <span className="text-[10px] font-mono font-bold text-green-900 uppercase block mb-0.5">
                    Mitigating Signal
                  </span>
                  <p className="text-ink-muted leading-relaxed">{sig.positive_indicator}</p>
                </div>
                {/* Risk Signal */}
                <div className="bg-surface p-2 border border-border">
                  <span className="text-[10px] font-mono font-bold text-brick uppercase block mb-0.5">
                    Risk Signal
                  </span>
                  <p className="text-ink-muted leading-relaxed">{sig.risk_indicator}</p>
                </div>
              </div>
              <p className="text-[11px] text-ink-subtle italic pt-0.5">
                <strong>Investigator Note:</strong> {sig.explanation}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

