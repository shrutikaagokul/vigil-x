import React from 'react';
import { TimelineEvent } from '@/types/case';

interface TimelinePanelProps {
  readonly events: readonly TimelineEvent[];
}

export const TimelinePanel: React.FC<TimelinePanelProps> = ({ events }) => {
  if (events.length === 0) {
    return (
      <div className="bg-surface border border-border p-8 text-center text-xs text-ink-muted font-sans">
        No chronological timeline events recorded for this case dossier.
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border p-4 space-y-3">
      <div className="border-b border-border pb-2 flex items-center justify-between">
        <div>
          <span className="text-[10px] font-mono text-ink-subtle uppercase tracking-wider">
            Chapter 05 · Chronological Context
          </span>
          <h2 className="font-sans text-sm sm:text-base font-bold text-green-950 uppercase tracking-wide">
            Investigation Timeline
          </h2>
        </div>
        <span className="text-xs font-mono text-ink-muted">
          {events.length} Events Sequenced
        </span>
      </div>

      <div className="relative pl-4 space-y-4 before:absolute before:left-1 before:top-1.5 before:bottom-1.5 before:w-[1px] before:bg-border-strong">
        {events.map((evt) => {
          const severityDot = {
            CRITICAL: 'bg-critical',
            HIGH: 'bg-brick',
            MEDIUM: 'bg-brass',
            LOW: 'bg-steel',
          }[evt.severity] || 'bg-steel';

          return (
            <div key={evt.event_id} className="relative space-y-1 text-xs">
              {/* Timeline Marker Dot */}
              <div
                className={`absolute -left-[15px] top-1 w-2 h-2 rounded-full border border-surface ${severityDot}`}
                aria-hidden="true"
              />

              <div className="flex flex-wrap items-center gap-1.5">
                <span className="font-mono text-[11px] font-bold text-green-950">
                  {new Date(evt.timestamp).toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
                <span className="px-1.5 py-0.2 text-[10px] font-mono bg-paper-subtle border border-border uppercase text-ink-subtle">
                  {evt.event_type.replace('_', ' ')}
                </span>
                {evt.evidence_id && (
                  <span className="px-1.5 py-0.2 text-[10px] font-mono bg-paper border border-border text-green-900 font-semibold">
                    {evt.evidence_id}
                  </span>
                )}
              </div>

              <p className="text-ink leading-relaxed font-normal pt-0.5">
                {evt.description}
              </p>

              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] font-mono text-ink-subtle pt-0.5">
                {evt.provider_ids.length > 0 && (
                  <span>Providers: {evt.provider_ids.join(', ')}</span>
                )}
                {evt.claim_ids.length > 0 && (
                  <span>Claims: {evt.claim_ids.join(', ')}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

