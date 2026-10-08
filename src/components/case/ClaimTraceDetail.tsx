import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getClaim } from '@/services/claimService';

interface ClaimTraceDetailProps {
  readonly claimId: string;
  readonly onClose: () => void;
}

export const ClaimTraceDetail: React.FC<ClaimTraceDetailProps> = ({ claimId, onClose }) => {
  const { data: claim, isLoading, isError } = useQuery({
    queryKey: ['claim', claimId],
    queryFn: () => getClaim(claimId),
  });

  return (
    <div className="bg-paper-subtle border border-hairline p-4 shadow-subtle space-y-3 mt-3">
      <div className="flex items-center justify-between border-b border-hairline pb-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-ink-subtle uppercase tracking-wider">
            Claim Audit Inspection:
          </span>
          <span className="font-mono text-xs font-bold text-green-950">
            {claimId}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-xs font-mono text-ink-subtle hover:text-ink px-1.5 py-0.5 border border-hairline bg-surface"
        >
          &times; Close Trace
        </button>
      </div>

      {isLoading && (
        <p className="text-xs font-mono text-ink-muted animate-pulse">Loading claim audit fields...</p>
      )}

      {isError && (
        <p className="text-xs font-mono text-brick">Unable to load claim record {claimId}.</p>
      )}

      {claim && (
        <div className="space-y-2.5 text-xs">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div className="bg-surface p-2 border border-hairline">
              <span className="text-[10px] font-mono text-ink-subtle block">Service Date</span>
              <span className="font-mono font-semibold text-ink">{claim.service_date}</span>
            </div>
            <div className="bg-surface p-2 border border-hairline">
              <span className="text-[10px] font-mono text-ink-subtle block">Procedure Code</span>
              <span className="font-mono font-bold text-green-950">{claim.procedure_code}</span>
            </div>
            <div className="bg-surface p-2 border border-hairline">
              <span className="text-[10px] font-mono text-ink-subtle block">Paid / Billed</span>
              <span className="font-mono font-bold text-ink">
                ${claim.paid_amount.toFixed(2)} <span className="text-ink-subtle font-normal">/ ${claim.billed_amount.toFixed(2)}</span>
              </span>
            </div>
            <div className="bg-surface p-2 border border-hairline">
              <span className="text-[10px] font-mono text-ink-subtle block">Place of Service</span>
              <span className="font-mono text-ink">POS {claim.pos_code}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] font-mono text-ink-muted pt-1">
            <span>Diagnosis: <strong className="text-ink">{claim.diagnosis_code}</strong></span>
            <span>Billing Provider: <strong className="text-ink">{claim.provider_id}</strong></span>
            <span>Member: <strong className="text-ink">{claim.member_id}</strong></span>
            {claim.referring_provider_id && (
              <span>Referring Provider: <strong className="text-ink">{claim.referring_provider_id}</strong></span>
            )}
          </div>

          {claim.flags && claim.flags.length > 0 && (
            <div className="flex items-center gap-1.5 pt-1">
              <span className="text-[10px] font-mono text-ink-subtle uppercase">Flags:</span>
              {claim.flags.map((f) => (
                <span key={f} className="px-1.5 py-0.2 text-[10px] font-mono bg-paper border border-hairline text-brick">
                  {f}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
