import React from 'react';
import { Evidence } from '@/types/alert';

interface EvidenceRowProps {
  readonly evidence: Evidence;
  readonly isSelected?: boolean;
  readonly onSelect: (evidenceId: string) => void;
  readonly onSelectClaim: (claimId: string) => void;
}

export const EvidenceRow: React.FC<EvidenceRowProps> = ({
  evidence,
  isSelected = false,
  onSelect,
  onSelectClaim,
}) => {
  const severityClass = {
    CRITICAL: 'bg-critical-soft text-critical border-critical/30',
    HIGH: 'bg-brick-soft text-brick border-brick/30',
    MEDIUM: 'bg-brass-soft text-ink border-brass/40',
    LOW: 'bg-paper-subtle text-ink-subtle border-border',
  }[evidence.severity] || 'bg-paper-subtle text-ink';

  const handleCopyId = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard?.writeText(evidence.evidence_id);
  };

  return (
    <div
      onClick={() => onSelect(evidence.evidence_id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(evidence.evidence_id);
        }
      }}
      className={`transition-colors p-3 text-left outline-none focus-visible:bg-green-50/70 cursor-pointer ${
        isSelected
          ? 'bg-paper-subtle'
          : 'bg-surface hover:bg-paper-subtle/50'
      }`}
    >
      {/* Top Evidence Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-1.5">
        <div className="flex flex-wrap items-center gap-2">
          {/* Evidence ID Chip */}
          <span
            data-testid="evidence-id-chip"
            onClick={handleCopyId}
            title="Click to copy Evidence ID"
            className="font-mono text-xs font-bold text-green-950 bg-paper border border-border px-1.5 py-0.2 hover:bg-paper-subtle cursor-copy"
          >
            {evidence.evidence_id}
          </span>

          {/* Rule ID & Version */}
          <span className="font-mono text-xs text-ink-muted px-1.5 py-0.2 bg-paper border border-border">
            {evidence.rule_id} · v{evidence.rule_version}
          </span>

          {/* Severity */}
          <span className={`px-1.5 py-0.2 text-[10px] font-mono font-bold uppercase border ${severityClass}`}>
            {evidence.severity}
          </span>
        </div>

        {/* Evidence Overpay Estimate */}
        <div className="text-right flex items-baseline gap-1.5">
          <span className="text-[10px] font-mono text-ink-subtle uppercase">
            Est. Overpayment:
          </span>
          <span
            data-testid="evidence-overpay"
            className="font-mono text-xs font-bold text-brick"
          >
            ${evidence.est_overpay.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
      </div>

      {/* Evidence Plain-Text Findings */}
      <div className="py-1">
        <p className="text-xs text-ink leading-relaxed font-normal">
          {evidence.plain_text}
        </p>
      </div>

      {/* Matched Fields & Claim Traces */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1.5 border-t border-border/60 text-xs">
        {/* Fields Matched */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] font-mono text-ink-subtle uppercase">Matched:</span>
          {evidence.fields_matched.map((field) => (
            <span
              key={field}
              className="px-1.5 py-0.2 text-[10px] font-mono bg-paper border border-border text-ink-muted"
            >
              {field}
            </span>
          ))}
        </div>

        {/* Associated Claims */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] font-mono text-ink-subtle uppercase">Claims:</span>
          {evidence.claim_ids.map((cid) => (
            <button
              key={cid}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSelectClaim(cid);
              }}
              title={`Trace claim ${cid}`}
              className="px-1.5 py-0.2 text-[10px] font-mono bg-green-50 hover:bg-green-100 text-green-900 border border-green-300 font-semibold"
            >
              {cid} →
            </button>
          ))}
        </div>
      </div>

      {/* False Positive Context Notes */}
      {evidence.fp_notes && (
        <div
          data-testid="fp-notes-box"
          className="mt-2 p-2 bg-paper border border-border text-[11px] text-ink-muted"
        >
          <strong className="font-mono text-[10px] text-green-950 uppercase block mb-0.5">
            False-Positive Context:
          </strong>
          <span>{evidence.fp_notes}</span>
        </div>
      )}
    </div>
  );
};

