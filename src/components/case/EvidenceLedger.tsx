import React, { useState, useEffect } from 'react';
import { Evidence } from '@/types/alert';
import { EvidenceRow } from './EvidenceRow';
import { ClaimTraceDetail } from './ClaimTraceDetail';

interface EvidenceLedgerProps {
  readonly evidenceList: readonly Evidence[];
  readonly selectedEvidenceId?: string | null;
  readonly onSelectEvidence?: (evidenceId: string) => void;
  readonly activeClaimId?: string | null;
  readonly onSelectClaim?: (claimId: string | null) => void;
}

export const EvidenceLedger: React.FC<EvidenceLedgerProps> = ({
  evidenceList,
  selectedEvidenceId: propSelectedId,
  onSelectEvidence,
  activeClaimId: propClaimId,
  onSelectClaim,
}) => {
  const [internalSelectedId, setInternalSelectedId] = useState<string | null>(
    evidenceList[0]?.evidence_id || null,
  );
  const [internalClaimId, setInternalClaimId] = useState<string | null>(null);

  const selectedEvidenceId = propSelectedId !== undefined ? propSelectedId : internalSelectedId;
  const activeClaimId = propClaimId !== undefined ? propClaimId : internalClaimId;

  const handleSelectRow = (id: string) => {
    if (onSelectEvidence) {
      onSelectEvidence(id);
    } else {
      setInternalSelectedId(id);
    }
  };

  const handleSelectClaim = (cid: string | null) => {
    if (onSelectClaim) {
      onSelectClaim(cid);
    } else {
      setInternalClaimId(cid);
    }
  };

  useEffect(() => {
    if (propSelectedId) {
      setInternalSelectedId(propSelectedId);
    }
  }, [propSelectedId]);

  return (
    <section className="bg-surface border border-border p-5 sm:p-6 space-y-4">
      {/* Table Header & Record Counter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
        <div>
          <span className="text-[11px] font-mono text-ink-subtle uppercase tracking-wider block">
            Evidentiary Audit Trail · Chapter 02
          </span>
          <h2 className="font-serif text-lg sm:text-xl font-bold text-green-950">
            Evidence Ledger
          </h2>
        </div>
        <span className="text-xs font-mono text-ink-muted bg-paper-subtle border border-border px-2.5 py-1">
          {evidenceList.length} Grounded Records
        </span>
      </div>

      {/* Claim Trace Detail Drawer if active claim is selected */}
      {activeClaimId && (
        <ClaimTraceDetail
          claimId={activeClaimId}
          onClose={() => handleSelectClaim(null)}
        />
      )}

      {/* Structured Investigation Table */}
      <div className="border border-border divide-y divide-border bg-surface overflow-hidden">
        {evidenceList.map((ev) => (
          <EvidenceRow
            key={ev.evidence_id}
            evidence={ev}
            isSelected={selectedEvidenceId === ev.evidence_id}
            onSelect={handleSelectRow}
            onSelectClaim={(cid) => handleSelectClaim(cid)}
          />
        ))}
      </div>
    </section>
  );
};

