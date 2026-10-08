import React from 'react';
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
  return (
    <Tabs.Root defaultValue="why_flagged" className="w-full space-y-3">
      {/* Thin Horizontal Document Navigation */}
      <Tabs.List
        className="flex border-b border-border bg-surface px-1 gap-1 text-xs font-medium overflow-x-auto no-scrollbar"
        aria-label="Case Dossier Chapters"
      >
        <Tabs.Trigger
          value="why_flagged"
          className="py-2 px-3 border-b-2 border-transparent data-[state=active]:border-brass data-[state=active]:text-green-950 data-[state=active]:font-semibold text-ink-muted hover:text-ink transition-colors outline-none focus-visible:bg-paper-subtle flex items-center gap-1.5 uppercase font-sans tracking-wide text-[11px]"
        >
          <span>WHY FLAGGED</span>
        </Tabs.Trigger>

        <Tabs.Trigger
          value="evidence"
          className="py-2 px-3 border-b-2 border-transparent data-[state=active]:border-brass data-[state=active]:text-green-950 data-[state=active]:font-semibold text-ink-muted hover:text-ink transition-colors outline-none focus-visible:bg-paper-subtle flex items-center gap-1.5 uppercase font-sans tracking-wide text-[11px]"
        >
          <span>EVIDENCE</span>
          <span className="font-mono text-[10px] px-1 py-0.2 bg-paper-subtle border border-border text-ink">
            {evidenceList.length}
          </span>
        </Tabs.Trigger>

        <Tabs.Trigger
          value="network"
          className="py-2 px-3 border-b-2 border-transparent data-[state=active]:border-brass data-[state=active]:text-green-950 data-[state=active]:font-semibold text-ink-muted hover:text-ink transition-colors outline-none focus-visible:bg-paper-subtle flex items-center gap-1.5 uppercase font-sans tracking-wide text-[11px]"
        >
          <span>NETWORK</span>
          {network?.summary && (
            <span className="font-mono text-[10px] px-1 py-0.2 bg-paper-subtle border border-border text-ink">
              {network.summary.n_nodes}
            </span>
          )}
        </Tabs.Trigger>

        <Tabs.Trigger
          value="score"
          className="py-2 px-3 border-b-2 border-transparent data-[state=active]:border-brass data-[state=active]:text-green-950 data-[state=active]:font-semibold text-ink-muted hover:text-ink transition-colors outline-none focus-visible:bg-paper-subtle flex items-center gap-1.5 uppercase font-sans tracking-wide text-[11px]"
        >
          <span>SCORE</span>
          <span className="font-mono text-[10px] px-1 py-0.2 bg-paper-subtle border border-border text-ink">
            {caseItem.risk_index}
          </span>
        </Tabs.Trigger>

        <Tabs.Trigger
          value="context"
          className="py-2 px-3 border-b-2 border-transparent data-[state=active]:border-brass data-[state=active]:text-green-950 data-[state=active]:font-semibold text-ink-muted hover:text-ink transition-colors outline-none focus-visible:bg-paper-subtle flex items-center gap-1.5 uppercase font-sans tracking-wide text-[11px]"
        >
          <span>CONTEXT</span>
          <span className="font-mono text-[10px] px-1 py-0.2 bg-paper-subtle border border-border text-ink">
            {timelineEvents.length}
          </span>
        </Tabs.Trigger>

        <Tabs.Trigger
          value="brief"
          className="py-2 px-3 border-b-2 border-transparent data-[state=active]:border-brass data-[state=active]:text-green-950 data-[state=active]:font-semibold text-ink-muted hover:text-ink transition-colors outline-none focus-visible:bg-paper-subtle flex items-center gap-1.5 uppercase font-sans tracking-wide text-[11px]"
        >
          <span>BRIEF</span>
          <span className="font-mono text-[10px] px-1 py-0.2 bg-green-100 text-green-900 border border-green-300 font-semibold">
            AI
          </span>
        </Tabs.Trigger>
      </Tabs.List>

      {/* Chapter 1: Why Flagged */}
      <Tabs.Content value="why_flagged" className="space-y-3 focus:outline-none">
        <WhyFlagged caseItem={caseItem} evidenceList={evidenceList} />
        <EvidenceLedger evidenceList={evidenceList} />
      </Tabs.Content>

      {/* Chapter 2: Evidence Ledger */}
      <Tabs.Content value="evidence" className="space-y-3 focus:outline-none">
        <EvidenceLedger evidenceList={evidenceList} />
      </Tabs.Content>

      {/* Chapter 3: Network Topology */}
      <Tabs.Content value="network" className="focus:outline-none">
        <NetworkPlaceholder network={network} />
      </Tabs.Content>

      {/* Chapter 4: Risk Score Breakdown */}
      <Tabs.Content value="score" className="focus:outline-none">
        <RiskSummary caseItem={caseItem} />
      </Tabs.Content>

      {/* Chapter 5: Investigation Timeline & Context */}
      <Tabs.Content value="context" className="space-y-3 focus:outline-none">
        <TimelinePanel events={timelineEvents} />
      </Tabs.Content>

      {/* Chapter 6: AI Brief Generation */}
      <Tabs.Content value="brief" className="focus:outline-none">
        <CopilotPlaceholder />
      </Tabs.Content>
    </Tabs.Root>
  );
};

