import React, { useState } from 'react';
import { Evidence } from '@/types/alert';
import { EvidenceRow } from './EvidenceRow';
import { ClaimTraceDetail } from './ClaimTraceDetail';

interface EvidenceLedgerProps {
  readonly evidenceList: readonly Evidence[];
}

export const EvidenceLedger: React.FC<EvidenceLedgerProps> = ({ evidenceList }) => {
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(
    evidenceList[0]?.evidence_id || null,
  );
  const [activeClaimId, setActiveClaimId] = useState<string | null>(null);

  return (
    <div className="bg-surface border border-border p-4 space-y-3">
      <div className="flex items-center justify-between border-b border-border pb-2">
        <div>
          <span className="text-[10px] font-mono text-ink-subtle uppercase tracking-wider">
            Chapter 02 · Evidence Records
          </span>
          <h2 className="font-sans text-sm sm:text-base font-bold text-green-950 uppercase tracking-wide">
            Evidence Ledger
          </h2>
        </div>
        <span className="text-xs font-mono text-ink-muted">
          Showing {evidenceList.length} evidence records
        </span>
      </div>

      {/* Claim Trace Detail Drawer if claim selected */}
      {activeClaimId && (
        <ClaimTraceDetail
          claimId={activeClaimId}
          onClose={() => setActiveClaimId(null)}
        />
      )}

      {/* Evidence Ledger List with Hairline Row Dividers */}
      <div className="border border-border divide-y divide-border bg-surface">
        {evidenceList.map((ev) => (
          <EvidenceRow
            key={ev.evidence_id}
            evidence={ev}
            isSelected={selectedEvidenceId === ev.evidence_id}
            onSelect={(id) => setSelectedEvidenceId(id)}
            onSelectClaim={(cid) => setActiveClaimId(cid)}
          />
        ))}
      </div>
    </div>
  );
};

