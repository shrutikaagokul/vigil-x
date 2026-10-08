import React, { useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { Case, TimelineEvent } from '@/types/case';
import { Evidence } from '@/types/alert';
import { Network } from '@/types/network';
import { WhyFlagged } from './WhyFlagged';
import { EvidenceLedger } from './EvidenceLedger';
import { TimelinePanel } from './TimelinePanel';
import { NetworkPlaceholder } from './NetworkPlaceholder';
import { CopilotPlaceholder } from './CopilotPlaceholder';
import { RiskSummary } from './RiskSummary';
import { ClaimTraceDetail } from './ClaimTraceDetail';

interface CaseTabsProps {
  readonly caseItem: Case;
  readonly evidenceList: readonly Evidence[];
  readonly timelineEvents: readonly TimelineEvent[];
  readonly network?: Network;
}

export const CaseTabs: React.FC<CaseTabsProps> = ({
  caseItem,
  evidenceList,
  timelineEvents,
  network,
}) => {
  const [activeTab, setActiveTab] = useState<string>('why_flagged');
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(
    evidenceList[0]?.evidence_id || null,
  );
  const [activeClaimId, setActiveClaimId] = useState<string | null>(null);

  const handleSelectEvidenceFromWhy = (evidenceId: string) => {
    setSelectedEvidenceId(evidenceId);
    setActiveTab('evidence');
  };

  return (
    <div className="space-y-4">
      {/* Global Claim Trace Inspection Drawer if active in any chapter */}
      {activeClaimId && (
        <ClaimTraceDetail
          claimId={activeClaimId}
          onClose={() => setActiveClaimId(null)}
        />
      )}

      <Tabs.Root value={activeTab} onValueChange={setActiveTab} className="w-full space-y-4">
        {/* Quiet, Clear Chapter Navigation Bar */}
        <Tabs.List
          className="flex border-b border-border bg-surface px-2 gap-2 text-xs font-medium overflow-x-auto no-scrollbar"
          aria-label="Case Dossier Chapters"
        >
          <Tabs.Trigger
            value="why_flagged"
            className="py-2.5 px-3.5 border-b-2 border-transparent data-[state=active]:border-green-800 data-[state=active]:text-green-950 data-[state=active]:font-bold text-ink-muted hover:text-ink transition-colors outline-none flex items-center gap-1.5 uppercase font-sans tracking-wide text-xs"
          >
            <span>WHY FLAGGED</span>
          </Tabs.Trigger>

          <Tabs.Trigger
            value="evidence"
            className="py-2.5 px-3.5 border-b-2 border-transparent data-[state=active]:border-green-800 data-[state=active]:text-green-950 data-[state=active]:font-bold text-ink-muted hover:text-ink transition-colors outline-none flex items-center gap-1.5 uppercase font-sans tracking-wide text-xs"
          >
            <span>EVIDENCE</span>
            <span className="font-mono text-[11px] px-1.5 py-0.2 bg-paper-subtle border border-border text-ink">
              {evidenceList.length}
            </span>
          </Tabs.Trigger>

          <Tabs.Trigger
            value="network"
            className="py-2.5 px-3.5 border-b-2 border-transparent data-[state=active]:border-green-800 data-[state=active]:text-green-950 data-[state=active]:font-bold text-ink-muted hover:text-ink transition-colors outline-none flex items-center gap-1.5 uppercase font-sans tracking-wide text-xs"
          >
            <span>NETWORK</span>
            {network?.summary && (
              <span className="font-mono text-[11px] px-1.5 py-0.2 bg-paper-subtle border border-border text-ink">
                {network.summary.n_nodes}
              </span>
            )}
          </Tabs.Trigger>

          <Tabs.Trigger
            value="score"
            className="py-2.5 px-3.5 border-b-2 border-transparent data-[state=active]:border-green-800 data-[state=active]:text-green-950 data-[state=active]:font-bold text-ink-muted hover:text-ink transition-colors outline-none flex items-center gap-1.5 uppercase font-sans tracking-wide text-xs"
          >
            <span>SCORE</span>
            <span className="font-mono text-[11px] px-1.5 py-0.2 bg-paper-subtle border border-border text-ink">
              {caseItem.risk_index}
            </span>
          </Tabs.Trigger>

          <Tabs.Trigger
            value="context"
            className="py-2.5 px-3.5 border-b-2 border-transparent data-[state=active]:border-green-800 data-[state=active]:text-green-950 data-[state=active]:font-bold text-ink-muted hover:text-ink transition-colors outline-none flex items-center gap-1.5 uppercase font-sans tracking-wide text-xs"
          >
            <span>CONTEXT</span>
            <span className="font-mono text-[11px] px-1.5 py-0.2 bg-paper-subtle border border-border text-ink">
              {timelineEvents.length}
            </span>
          </Tabs.Trigger>

          <Tabs.Trigger
            value="brief"
            className="py-2.5 px-3.5 border-b-2 border-transparent data-[state=active]:border-green-800 data-[state=active]:text-green-950 data-[state=active]:font-bold text-ink-muted hover:text-ink transition-colors outline-none flex items-center gap-1.5 uppercase font-sans tracking-wide text-xs"
          >
            <span>BRIEF</span>
            <span className="font-mono text-[11px] px-1.5 py-0.2 bg-green-100 text-green-900 border border-green-300 font-semibold">
              AI
            </span>
          </Tabs.Trigger>
        </Tabs.List>

        {/* Chapter 1: Why Flagged (Default Primary Investigation View) */}
        <Tabs.Content value="why_flagged" className="focus:outline-none">
          <WhyFlagged
            caseItem={caseItem}
            evidenceList={evidenceList}
            onSelectEvidence={handleSelectEvidenceFromWhy}
            onSelectClaim={(cid) => setActiveClaimId(cid)}
          />
        </Tabs.Content>

        {/* Chapter 2: Evidence Ledger Table */}
        <Tabs.Content value="evidence" className="focus:outline-none">
          <EvidenceLedger
            evidenceList={evidenceList}
            selectedEvidenceId={selectedEvidenceId}
            onSelectEvidence={(id) => setSelectedEvidenceId(id)}
            activeClaimId={activeClaimId}
            onSelectClaim={(cid) => setActiveClaimId(cid)}
          />
        </Tabs.Content>

        {/* Chapter 3: Network Context */}
        <Tabs.Content value="network" className="focus:outline-none">
          <NetworkPlaceholder network={network} caseId={caseItem.id} />
        </Tabs.Content>

        {/* Chapter 4: Risk Score Breakdown */}
        <Tabs.Content value="score" className="focus:outline-none">
          <RiskSummary caseItem={caseItem} />
        </Tabs.Content>

        {/* Chapter 5: Investigation Timeline & Context */}
        <Tabs.Content value="context" className="focus:outline-none">
          <TimelinePanel
            events={timelineEvents}
            onSelectClaim={(cid) => setActiveClaimId(cid)}
          />
        </Tabs.Content>

        {/* Chapter 6: AI Brief Generation */}
        <Tabs.Content value="brief" className="focus:outline-none">
          <CopilotPlaceholder />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
};

