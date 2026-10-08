import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { PageContainer } from '@/components/layout/PageContainer';
import {
  CaseHeader,
  RiskSummary,
  CaseTabs,
  DecisionModal,
  CaseLoadingState,
  CaseNotFoundState,
  CaseErrorState,
} from '@/components/case';
import {
  getCase,
  getCaseEvidence,
  getCaseTimeline,
  getCaseNetwork,
} from '@/services/caseService';
import { ApiError } from '@/services/apiClient';
import { DecisionAction, DecisionResponse } from '@/types/case';

export const CaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [isDecisionModalOpen, setIsDecisionModalOpen] = useState<boolean>(false);
  const [selectedAction, setSelectedAction] = useState<DecisionAction>('accept');
  const [decisionFeedback, setDecisionFeedback] = useState<DecisionResponse | null>(null);

  // 1. Fetch Core Case Dossier
  const {
    data: caseItem,
    isLoading: isCaseLoading,
    isError: isCaseError,
    error: caseError,
    refetch: refetchCase,
  } = useQuery({
    queryKey: ['case', id],
    queryFn: () => getCase(id!),
    enabled: Boolean(id),
    retry: false,
  });

  // 2. Fetch Evidence Ledger
  const {
    data: evidenceList = [],
    isLoading: isEvidenceLoading,
  } = useQuery({
    queryKey: ['case-evidence', id],
    queryFn: () => getCaseEvidence(id!),
    enabled: Boolean(id && caseItem),
  });

  // 3. Fetch Timeline Events
  const {
    data: timelineEvents = [],
  } = useQuery({
    queryKey: ['case-timeline', id],
    queryFn: () => getCaseTimeline(id!),
    enabled: Boolean(id && caseItem),
  });

  // 4. Fetch Network Subgraph Summary
  const {
    data: network,
  } = useQuery({
    queryKey: ['case-network', id],
    queryFn: () => getCaseNetwork(id!),
    enabled: Boolean(id && caseItem),
  });

  const handleOpenDecision = (act: DecisionAction = 'accept') => {
    setSelectedAction(act);
    setIsDecisionModalOpen(true);
  };

  const handleDecisionRecorded = (response: DecisionResponse) => {
    setDecisionFeedback(response);
    queryClient.invalidateQueries({ queryKey: ['case', id] });
  };

  if (!id) {
    return (
      <PageContainer>
        <CaseNotFoundState requestedId="None" />
      </PageContainer>
    );
  }

  if (isCaseLoading) {
    return (
      <PageContainer>
        <CaseLoadingState />
      </PageContainer>
    );
  }

  if (isCaseError) {
    const isNotFound =
      (caseError instanceof ApiError && caseError.statusCode === 404) ||
      caseError?.message?.includes('not found');

    return (
      <PageContainer>
        {isNotFound ? (
          <CaseNotFoundState requestedId={id} />
        ) : (
          <CaseErrorState
            message={caseError instanceof Error ? caseError.message : undefined}
            onRetry={() => refetchCase()}
          />
        )}
      </PageContainer>
    );
  }

  if (!caseItem) {
    return (
      <PageContainer>
        <CaseNotFoundState requestedId={id} />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="space-y-4 pb-16">
        {/* Decision Feedback Confirmation Banner */}
        {decisionFeedback && (
          <div
            data-testid="decision-confirmation-banner"
            className="p-3 bg-green-50 border border-green-300 text-green-950 text-xs flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <strong className="font-mono uppercase text-green-900">Decision Recorded:</strong>
              <span>
                {decisionFeedback.action.toUpperCase()} · &ldquo;{decisionFeedback.reason}&rdquo;
              </span>
            </div>
            <button
              type="button"
              onClick={() => setDecisionFeedback(null)}
              className="text-green-800 hover:text-green-950 font-bold px-1.5"
            >
              &times;
            </button>
          </div>
        )}

        {/* 1. Case Document Header */}
        <CaseHeader
          caseItem={caseItem}
          onOpenDecisionModal={() => handleOpenDecision('accept')}
        />

        {/* 2. Main Two-Column Dossier Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Left Column (4/12): Risk, Financial Exposure & Conflicting Signals */}
          <div className="lg:col-span-4">
            <RiskSummary caseItem={caseItem} />
          </div>

          {/* Right Column (8/12): Chapters Workspace */}
          <div className="lg:col-span-8">
            {isEvidenceLoading ? (
              <div className="p-8 bg-surface border border-border text-center text-xs text-ink-muted animate-pulse font-mono">
                Loading evidence ledger records...
              </div>
            ) : (
              <CaseTabs
                caseItem={caseItem}
                evidenceList={evidenceList}
                timelineEvents={timelineEvents}
                network={network}
              />
            )}
          </div>
        </div>

        {/* 3. Docked Bottom Decision Bar */}
        <div
          data-testid="docked-decision-bar"
          className="fixed bottom-0 left-0 right-0 z-40 bg-surface border-t border-border px-4 sm:px-8 py-2.5 flex flex-wrap items-center justify-between gap-3 shadow-none"
        >
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="font-bold text-green-950">{caseItem.id}</span>
            <span className="text-border-strong">·</span>
            <span className="text-ink-muted hidden sm:inline">Human-in-the-Loop Determination</span>
            <span className="text-border-strong hidden sm:inline">·</span>
            <span className="text-[10px] text-ink-subtle uppercase">Rationale Mandatory</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleOpenDecision('accept')}
              className="px-3 py-1 bg-green-800 text-white hover:bg-green-900 border border-green-700 text-xs font-semibold transition-colors"
            >
              Accept
            </button>
            <button
              type="button"
              onClick={() => handleOpenDecision('escalate')}
              className="px-3 py-1 bg-paper-subtle border border-border text-ink hover:bg-surface text-xs font-medium transition-colors"
            >
              Escalate
            </button>
            <button
              type="button"
              onClick={() => handleOpenDecision('needs_info')}
              className="px-3 py-1 bg-paper-subtle border border-border text-ink hover:bg-surface text-xs font-medium transition-colors"
            >
              Needs info
            </button>
            <button
              type="button"
              onClick={() => handleOpenDecision('reject')}
              className="px-3 py-1 bg-paper-subtle border border-border text-ink hover:bg-surface text-xs font-medium transition-colors"
            >
              Reject
            </button>
          </div>
        </div>

        {/* 4. Human Decision Modal Dialog */}
        <DecisionModal
          caseId={caseItem.id}
          isOpen={isDecisionModalOpen}
          initialAction={selectedAction}
          onClose={() => setIsDecisionModalOpen(false)}
          onSuccess={handleDecisionRecorded}
        />
      </div>
    </PageContainer>
  );
};
