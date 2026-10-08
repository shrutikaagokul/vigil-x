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
        className="w-[400px] shrink-0 ml-[2rem] pl-[2rem] pt-[1.375rem] border-l border-[#D3E0D6] flex flex-col justify-center text-center text-[#4F5F55] text-[0.9375rem]"
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
      className="w-[400px] shrink-0 ml-[2rem] pl-[2rem] pt-[1.375rem] border-l border-[#D3E0D6] flex flex-col space-y-4 select-text"
      aria-label={`Preview of ${displayName}`}
    >
      {/* Title in Source Serif 4 */}
      <h2 className="font-serif text-[1.625rem] leading-[2rem] font-semibold text-[#0B1A12] tracking-tight">
        {displayName}
      </h2>

      {/* Why it is ranked label */}
      <div className="space-y-3">
        <span className="block text-[0.9375rem] font-medium text-[#4F5F55]">
          {rankLabel}
        </span>

        {/* Up to 3 reasons with mono evidence chips */}
        <div className="space-y-3">
          {reasons.map((r, idx) => (
            <p
              key={idx}
              className="text-[1.0625rem] leading-[1.5625rem] text-[#14201A] font-normal"
            >
              {r.text}{' '}
              <span className="inline-block font-mono text-[0.8125rem] font-medium border border-[#14201A] rounded-[3px] px-1.5 py-0.5 align-baseline ml-1 bg-white">
                {r.evidence_chip}
              </span>
            </p>
          ))}
        </div>
      </div>

      {/* Cost of delay for deferred cases */}
      {isDeferred && (
        <div className="text-[0.9375rem] text-[#9E3626] font-medium pt-1">
          Waiting 4 weeks puts about {formatCurrency(selectedCase.cost_of_delay_4w, 'compact')} more at risk
        </div>
      )}

      {/* Divider */}
      <div className="w-full border-t border-[#D3E0D6]" />

      {/* Confidence & Members affected */}
      <div className="text-[1rem] leading-[1.5rem] text-[#14201A] font-normal">
        Confidence <strong className="font-semibold text-[#14201A]">{selectedCase.confidence}</strong>
        {' · '}
        Members affected <strong className="font-semibold text-[#14201A]">{selectedCase.members_affected != null ? selectedCase.members_affected.toLocaleString() : '—'}</strong>
      </div>

      {/* Primary Action Button */}
      <div className="pt-2">
        <button
          type="button"
          onClick={handleOpenCase}
          className="bg-[#2A5A3F] text-white text-[1rem] font-semibold px-[1.125rem] py-[0.75rem] rounded-[3px] hover:bg-[#1B3A29] transition-colors outline-none focus-visible:ring-2 focus-visible:ring-[#2A5A3F] focus-visible:ring-offset-2"
        >
          Open case
        </button>
      </div>
    </aside>
  );
};
