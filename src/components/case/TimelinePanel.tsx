import React from 'react';
import { TimelineEvent } from '@/types/case';

interface TimelinePanelProps {
  readonly events: readonly TimelineEvent[];
  readonly onSelectClaim?: (claimId: string) => void;
}

export const TimelinePanel: React.FC<TimelinePanelProps> = ({ events, onSelectClaim }) => {
  if (events.length === 0) {
    return (
      <section className="bg-surface border border-border p-8 text-center text-sm text-ink-muted font-sans">
        No chronological timeline events recorded for this case dossier.
      </section>
    );
  }

  return (
    <section className="bg-surface border border-border p-5 sm:p-6 space-y-5">
      {/* Chapter Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <span className="text-[11px] font-mono text-ink-subtle uppercase tracking-wider block">
            Chronological Audit Sequence · Chapter 05
          </span>
          <h2 className="font-serif text-lg sm:text-xl font-bold text-green-950">
            Investigation Timeline &amp; Context
          </h2>
        </div>
        <span className="text-xs font-mono text-ink-muted bg-paper-subtle border border-border px-2.5 py-1">
          {events.length} Sequenced Events
        </span>
      </div>

      {/* Spacious Chronological Timeline */}
      <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[1px] before:bg-border-strong">
        {events.map((evt) => {
          const severityDot = {
            CRITICAL: 'bg-critical',
            HIGH: 'bg-brick',
            MEDIUM: 'bg-brass',
            LOW: 'bg-steel',
          }[evt.severity] || 'bg-steel';

          return (
            <div key={evt.event_id} className="relative space-y-2 text-sm">
              {/* Timeline Marker Dot */}
              <div
                className={`absolute -left-[23px] top-1.5 w-2.5 h-2.5 rounded-full border-2 border-surface ${severityDot}`}
                aria-hidden="true"
              />

              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs font-bold text-green-950 bg-paper-subtle border border-border px-2 py-0.5">
                  {new Date(evt.timestamp).toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
                <span className="px-2 py-0.5 text-[11px] font-mono bg-paper border border-border uppercase text-ink-muted">
                  {evt.event_type.replace('_', ' ')}
                </span>
                {evt.evidence_id && (
                  <span className="px-2 py-0.5 text-[11px] font-mono bg-green-50 border border-green-200 text-green-900 font-semibold">
                    {evt.evidence_id}
                  </span>
                )}
              </div>

              <p className="text-ink leading-relaxed font-sans font-normal text-sm sm:text-base">
                {evt.description}
              </p>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs font-mono text-ink-subtle pt-1 border-t border-border/40">
                {evt.provider_ids.length > 0 && (
                  <span>Providers: <strong className="text-ink">{evt.provider_ids.join(', ')}</strong></span>
                )}
                {evt.claim_ids.length > 0 && (
                  <div className="flex items-center gap-1">
                    <span>Claims:</span>
                    {evt.claim_ids.map((cid) => (
                      <button
                        key={cid}
                        type="button"
                        onClick={() => onSelectClaim?.(cid)}
                        className="text-green-900 hover:text-green-950 underline font-semibold"
                      >
                        {cid}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

