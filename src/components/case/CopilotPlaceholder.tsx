import React from 'react';

export const CopilotPlaceholder: React.FC = () => {
  return (
    <div className="bg-surface border border-border p-4 space-y-3">
      <div className="border-b border-border pb-2 flex items-center justify-between">
        <div>
          <span className="text-[10px] font-mono text-ink-subtle uppercase tracking-wider">
            Chapter 06 · Investigative Intelligence
          </span>
          <h2 className="font-sans text-sm sm:text-base font-bold text-green-950 uppercase tracking-wide">
            AI Copilot &amp; Executive Brief
          </h2>
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[11px]">
          <span className="px-2 py-0.5 bg-green-100 text-green-900 border border-green-300 font-semibold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-700" aria-hidden="true" />
            Verified Grounding
          </span>
        </div>
      </div>

      <p className="font-serif text-xs sm:text-sm text-ink leading-relaxed font-normal">
        Automated executive brief synthesis and interactive case Q&amp;A strictly grounded in the case evidence ledger.
      </p>

      <div className="space-y-2 pt-1">
        <div className="p-2.5 bg-paper-subtle border border-border text-xs space-y-1">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] text-green-950 uppercase font-bold">
              Guaranteed Grounding Architecture
            </span>
            <span className="font-mono text-[10px] text-ink-subtle">
              Evidence-Citing Model
            </span>
          </div>
          <p className="font-serif text-xs text-ink-muted leading-relaxed">
            All AI responses require explicit evidence ID citations (<span className="font-mono text-green-950 bg-paper px-1 border border-border font-semibold">E-R06-TIMING-001</span>, <span className="font-mono text-green-950 bg-paper px-1 border border-border font-semibold">E-R07-RECLOOP-003</span>). Unsubstantiated claims and speculative legal conclusions are strictly prohibited.
          </p>
        </div>

        <div className="p-2.5 bg-paper-subtle border border-border text-xs space-y-1">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] text-green-950 uppercase font-bold">
              Executive Brief Generation
            </span>
            <span className="font-mono text-[10px] text-ink-subtle">
              SIU Work Product
            </span>
          </div>
          <p className="font-serif text-xs text-ink-muted leading-relaxed">
            Generates structured summaries detailing financial exposure, key evidentiary findings, and prioritized clinical audit action recommendations.
          </p>
        </div>
      </div>
    </div>
  );
};

