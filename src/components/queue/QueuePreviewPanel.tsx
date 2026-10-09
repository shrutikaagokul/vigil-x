import React from 'react';
import { useNavigate } from 'react-router-dom';
import { QueueItem } from '@/types/queue';
import { formatCurrency } from '@/utils/currency';

interface QueuePreviewPanelProps {
  readonly selectedCase: QueueItem | null;
  readonly rank: number;
  readonly isDeferred?: boolean;
}

export const QueuePreviewPanel: React.FC<QueuePreviewPanelProps> = ({
  selectedCase,
  rank,
  isDeferred = false,
}) => {
  const navigate = useNavigate();

  if (!selectedCase) {
    return (
      <aside
        className="w-[440px] shrink-0 ml-[2rem] p-8 bg-white border border-[#E0E8DF] rounded-xl flex flex-col justify-center text-center text-[#68766B] text-base shadow-xs"
        aria-label="Case Preview"
      >
        Select a case from the worklist to view details.
      </aside>
    );
  }

  const displayName = selectedCase.name || selectedCase.focal_provider_name || selectedCase.title;
  const rankLabel = rank === 1 ? 'Why it is first' : `Why it is ranked #${rank}`;

  const reasons = selectedCase.top_reasons && selectedCase.top_reasons.length > 0
    ? selectedCase.top_reasons.slice(0, 3)
    : selectedCase.priority_reasons && selectedCase.priority_reasons.length > 0
    ? selectedCase.priority_reasons.slice(0, 3).map((r, idx) => ({
        text: r,
        evidence_chip: selectedCase.rules_triggered[idx] || `E${idx + 1}`,
      }))
    : [
        {
          text: selectedCase.primary_indicator,
          evidence_chip: selectedCase.rules_triggered[0] || 'E1',
        },
      ];

  const handleOpenCase = () => {
    navigate(`/cases/${selectedCase.case_id}`);
  };

  return (
    <aside
      className="w-[400px] shrink-0 ml-[2rem] p-6 bg-white border border-[#E0E8DF] rounded-xl flex flex-col space-y-4 select-text shadow-xs"
      aria-label={`Preview of ${displayName}`}
    >
      {/* Title */}
      <h2 className="text-[1.375rem] font-bold text-[#183B2A] tracking-tight font-serif">
        {displayName}
      </h2>

      {/* Why it is ranked label */}
      <div className="space-y-3">
        <span className="block text-[0.875rem] font-semibold uppercase tracking-wider text-[#285239]">
          {rankLabel}
        </span>

        {/* Up to 3 reasons with mono evidence chips */}
        <div className="space-y-3">
          {reasons.map((r, idx) => (
            <p
              key={idx}
              className="text-[0.9375rem] leading-[1.45rem] text-[#24352A] font-normal"
            >
              {r.text}{' '}
              <span className="inline-block font-mono text-[0.75rem] font-semibold border border-[#E0E8DF] rounded px-1.5 py-0.5 align-baseline ml-1 bg-[#F5F8F4] text-[#285239]">
                {r.evidence_chip}
              </span>
            </p>
          ))}
        </div>
      </div>

      {/* Cost of delay for deferred cases */}
      {isDeferred && (
        <div className="text-[0.875rem] text-[#B91C1C] font-medium pt-1">
          Waiting 4 weeks puts about {formatCurrency(selectedCase.cost_of_delay_4w, 'compact')} more at risk
        </div>
      )}

      {/* Divider */}
      <div className="w-full border-t border-[#E0E8DF]" />

      {/* Confidence & Members affected */}
      <div className="text-[0.875rem] leading-[1.4rem] text-[#68766B]">
        Confidence <strong className="font-semibold text-[#183B2A]">{selectedCase.confidence}</strong>
        {' · '}
        Members affected <strong className="font-semibold text-[#183B2A]">{selectedCase.members_affected != null ? selectedCase.members_affected.toLocaleString() : '—'}</strong>
      </div>

      {/* Primary Action Button */}
      <div className="pt-2">
        <button
          type="button"
          onClick={handleOpenCase}
          className="w-full bg-[#477A58] text-white text-[0.9375rem] font-semibold px-4 py-2.5 rounded-lg hover:bg-[#285239] transition-all shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-[#477A58]"
        >
          Open case
        </button>
      </div>
    </aside>
  );
};
