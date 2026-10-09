import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { PageContainer } from '@/components/layout/PageContainer';
import {
  CaseHeader,
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
      <div className="space-y-5 pb-20 max-w-7xl mx-auto">
        {/* Decision Feedback Confirmation Banner */}
        {decisionFeedback && (
          <div
            data-testid="decision-confirmation-banner"
            className="p-3.5 bg-[#E8F2E8] border border-[#B8D2B8] text-[#183B2A] text-xs font-sans rounded-lg flex items-center justify-between shadow-xs"
          >
            <div className="flex items-center gap-2">
              <strong className="font-mono uppercase text-[#285239] font-bold">Decision Recorded:</strong>
              <span>
                {decisionFeedback.action.toUpperCase()} · &ldquo;{decisionFeedback.reason}&rdquo;
              </span>
            </div>
            <button
              type="button"
              onClick={() => setDecisionFeedback(null)}
              className="text-[#68766B] hover:text-[#183B2A] font-bold px-2 py-0.5 text-base"
              aria-label="Dismiss banner"
            >
              &times;
            </button>
          </div>
        )}

        {/* 1. Spacious Case Document Header */}
        <CaseHeader
          caseItem={caseItem}
          onOpenDecisionModal={() => handleOpenDecision('accept')}
        />

        {/* 2. Main Chapter Navigation Workspace */}
        {isEvidenceLoading ? (
          <div className="p-10 bg-white border border-[#E0E8DF] rounded-xl text-center text-xs text-[#68766B] animate-pulse font-mono shadow-xs">
            Loading investigation evidence ledger...
          </div>
        ) : (
          <CaseTabs
            caseItem={caseItem}
            evidenceList={evidenceList}
            timelineEvents={timelineEvents}
            network={network}
          />
        )}

        {/* 3. Docked Persistent Bottom Decision Bar */}
        <div
          data-testid="docked-decision-bar"
          className="fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-[#E0E8DF] px-4 sm:px-8 py-3 flex flex-wrap items-center justify-between gap-3 shadow-md"
        >
          <div className="flex items-center gap-2.5 text-xs font-mono">
            <span className="font-bold text-[#285239] bg-[#F5F8F4] border border-[#E0E8DF] px-2.5 py-1 rounded">{caseItem.id}</span>
            <span className="text-[#E0E8DF]">·</span>
            <span className="text-[#183B2A] font-medium hidden sm:inline">Human-in-the-Loop Determination</span>
            <span className="text-[#E0E8DF] hidden sm:inline">·</span>
            <span className="text-[11px] text-[#68766B] uppercase tracking-wider">Rationale Mandatory</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleOpenDecision('accept')}
              className="px-4 py-2 bg-[#477A58] hover:bg-[#285239] text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
            >
              Accept
            </button>
            <button
              type="button"
              onClick={() => handleOpenDecision('needs_info')}
              className="px-3.5 py-2 bg-white border border-[#E0E8DF] text-[#183B2A] hover:bg-[#F5F8F4] text-xs font-medium rounded-lg transition-colors shadow-xs"
            >
              Needs info
            </button>
            <button
              type="button"
              onClick={() => handleOpenDecision('escalate')}
              className="px-3.5 py-2 bg-white border border-[#E0E8DF] text-[#183B2A] hover:bg-[#F5F8F4] text-xs font-medium rounded-lg transition-colors shadow-xs"
            >
              Escalate
            </button>
            <button
              type="button"
              onClick={() => handleOpenDecision('reject')}
              className="px-3.5 py-2 bg-white border border-[#E0E8DF] text-[#183B2A] hover:bg-[#F5F8F4] text-xs font-medium rounded-lg transition-colors shadow-xs"
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
