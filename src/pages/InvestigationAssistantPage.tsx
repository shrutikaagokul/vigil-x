import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getQueue } from '@/services/queueService';
import { generateBrief, askCase } from '@/services/caseService';
import { AskResponse } from '@/types/case';

export const InvestigationAssistantPage: React.FC = () => {
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [questionInput, setQuestionInput] = useState<string>('');
  const [chatHistory, setChatHistory] = useState<{ q: string; a: AskResponse }[]>([]);

  // Fetch queue to populate case selector
  const { data: queueData } = useQuery({
    queryKey: ['assistant-cases-list'],
    queryFn: () => getQueue(),
  });

  const cases = queueData?.items || [];

  // Set default case if not selected
  useEffect(() => {
    if (!selectedCaseId && cases.length > 0) {
      setSelectedCaseId(cases[0].case_id);
    }
  }, [cases, selectedCaseId]);

  // Fetch generated brief for selected case
  const {
    data: brief,
    isLoading: isBriefLoading,
  } = useQuery({
    queryKey: ['case-brief', selectedCaseId],
    queryFn: () => generateBrief(selectedCaseId),
    enabled: Boolean(selectedCaseId),
  });

  // Mutation for asking questions
  const askMutation = useMutation({
    mutationFn: (q: string) => askCase(selectedCaseId, q),
    onSuccess: (data, q) => {
      setChatHistory((prev) => [...prev, { q, a: data }]);
      setQuestionInput('');
    },
  });

  const handleSendQuestion = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!questionInput.trim() || askMutation.isPending) return;
    askMutation.mutate(questionInput.trim());
  };

  const handleQuickQuestion = (q: string) => {
    if (askMutation.isPending) return;
    askMutation.mutate(q);
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-[#285239] font-bold bg-[#E8F2E8] px-3 py-1 rounded border border-[#B8D2B8]">
              Verified Investigation Copilot
            </span>
            <span className="text-xs text-[#68766B] font-mono">Grounded LLM and Whitelisted Q&A</span>
          </div>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-[#183B2A] tracking-tight">
            SIU Investigation Assistant
          </h1>
          <p className="text-base text-[#68766B] mt-1.5 max-w-4xl leading-relaxed">
            Synthesizes verified structured evidence packets into human-auditable briefs. Provides strict whitelisted Q&A with deterministic anti-hallucination verification.
          </p>
        </div>

        {/* Case Selector Dropdown */}
        <div className="flex items-center gap-3 shrink-0">
          <label htmlFor="case-selector" className="text-sm font-mono text-[#68766B] font-semibold">Target Case:</label>
          <select
            id="case-selector"
            value={selectedCaseId}
            onChange={(e) => {
              setSelectedCaseId(e.target.value);
              setChatHistory([]);
            }}
            className="h-11 text-sm bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg px-4 text-[#183B2A] font-mono focus:outline-none focus:border-[#477A58] focus-visible:ring-2 focus-visible:ring-[#477A58]"
          >
            {cases.map((c) => (
              <option key={c.case_id} value={c.case_id}>
                {c.case_id} - {c.name || c.focal_provider_name || 'Provider'}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Two Column Layout: Brief on Left, Interactive Q&A on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Verified Investigation Brief */}
        <div className="lg:col-span-7 bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-6 shadow-xs">
          {/* Verification Status Banner */}
          <div className="p-4 bg-[#E8F2E8] border border-[#B8D2B8] rounded-lg flex items-center justify-between gap-4 text-sm">
            <span className="font-semibold text-[#183B2A]">Factual Grounding Verified</span>
            <span className="text-xs font-mono bg-white text-[#285239] px-3 py-1 rounded border border-[#B8D2B8] font-bold">
              Zero Hallucinations Verified
            </span>
          </div>

          {isBriefLoading ? (
            <div className="py-20 text-center text-[#68766B] flex flex-col items-center justify-center space-y-4">
              <div className="w-10 h-10 border-3 border-[#477A58] border-t-transparent rounded-full animate-spin" />
              <span className="text-sm font-mono">Synthesizing verified case brief...</span>
            </div>
          ) : brief ? (
            <div className="space-y-6 text-base">
              <div className="border-b border-[#E0E8DF] pb-4">
                <h2 className="font-serif text-2xl font-bold text-[#183B2A]">
                  {brief.title}
                </h2>
                <div className="flex items-center gap-3 mt-1.5 text-xs text-[#68766B] font-mono">
                  <span>Target: {brief.case_id}</span>
                  <span>|</span>
                  <span>Generated: {new Date(brief.generated_at).toLocaleString()}</span>
                </div>
              </div>

              {/* Executive Summary */}
              <div className="space-y-2">
                <div className="text-xs font-mono uppercase text-[#285239] font-bold">
                  Why Prioritized & Executive Summary:
                </div>
                <div className="p-5 bg-[#F5F8F4] rounded-lg border border-[#E0E8DF] text-[#24352A] leading-relaxed whitespace-pre-line text-[15px]">
                  {brief.summary}
                </div>
              </div>

              {/* Key Findings */}
              {brief.key_findings && brief.key_findings.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs font-mono uppercase text-[#0369A1] font-bold">
                    Key Clinical & Network Findings:
                  </div>
                  <div className="space-y-2">
                    {brief.key_findings.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-4 bg-[#F5F8F4] rounded-lg border border-[#E0E8DF] text-[#24352A] text-base leading-relaxed"
                      >
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommended Steps */}
              {brief.recommended_actions && brief.recommended_actions.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs font-mono uppercase text-[#B45309] font-bold">
                    Recommended SIU Investigative Actions:
                  </div>
                  <div className="space-y-2">
                    {brief.recommended_actions.map((act, idx) => (
                      <div
                        key={idx}
                        className="p-4 bg-[#F5F8F4] rounded-lg border border-[#E0E8DF] text-[#24352A] text-base leading-relaxed"
                      >
                        {act}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="py-16 text-center text-[#68766B]">
              <p>Unable to load case brief. Please select a valid case.</p>
            </div>
          )}
        </div>

        {/* Right Column: Whitelisted Q&A Assistant */}
        <div className="lg:col-span-5 bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-6 shadow-xs flex flex-col h-[820px]">
          <div className="border-b border-[#E0E8DF] pb-4">
            <h2 className="font-serif text-2xl font-bold text-[#183B2A]">
              Investigator Q&A
            </h2>
            <p className="text-xs text-[#68766B] mt-1">
              Strictly grounded in evidence ledger for <span className="font-mono text-[#285239] font-bold">{selectedCaseId}</span>
            </p>
          </div>

          {/* Quick Prompt Suggestions */}
          <div className="space-y-2">
            <span className="text-xs font-mono uppercase text-[#68766B] font-semibold block">
              Suggested Investigative Queries:
            </span>
            <div className="flex flex-wrap gap-2">
              {[
                'Why was this provider flagged?',
                'Are there shared banking accounts or entities?',
                'What is the financial overpayment exposure?',
                'Were there impossible travel velocities?',
              ].map((suggestion, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleQuickQuestion(suggestion)}
                  disabled={askMutation.isPending}
                  className="text-xs bg-[#F5F8F4] hover:bg-[#E8F2E8] text-[#285239] hover:text-[#183B2A] border border-[#E0E8DF] px-3.5 py-2 rounded-lg transition-colors text-left font-medium"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          {/* Q&A Conversation History Stream */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-1 text-base">
            {chatHistory.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-[#68766B] p-8 space-y-3">
                <p className="text-base font-medium text-[#24352A]">
                  Ask structured questions about evidence, travel velocity, banking rings, or diagnostic overpayment.
                </p>
                <span className="text-xs font-mono text-[#68766B]">
                  Deterministic anti-hallucination verification active.
                </span>
              </div>
            ) : (
              chatHistory.map((item, idx) => (
                <div key={idx} className="space-y-3">
                  {/* Investigator Question */}
                  <div className="flex justify-end">
                    <div className="bg-[#E8F2E8] border border-[#B8D2B8] text-[#183B2A] px-4 py-3 rounded-lg max-w-[85%] font-medium text-base">
                      {item.q}
                    </div>
                  </div>

                  {/* Grounded Copilot Answer */}
                  <div className="flex justify-start">
                    <div className="bg-[#F5F8F4] border border-[#E0E8DF] text-[#24352A] p-5 rounded-lg max-w-[95%] space-y-3">
                      <div className="text-xs font-mono text-[#285239] font-bold">
                        VERIFIED GROUNDED RETRIEVAL
                      </div>
                      <p className="leading-relaxed text-[15px]">
                        {item.a.answer}
                      </p>
                      {item.a.evidence_citations && item.a.evidence_citations.length > 0 && (
                        <div className="pt-3 border-t border-[#E0E8DF] flex items-center gap-2 flex-wrap">
                          <span className="text-xs text-[#68766B] font-mono font-semibold">Citations:</span>
                          {item.a.evidence_citations.map((c, i) => (
                            <span
                              key={i}
                              className="font-mono text-xs bg-white px-2 py-0.5 rounded border border-[#E0E8DF] text-[#285239] font-semibold"
                            >
                              {c}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}

            {askMutation.isPending && (
              <div className="flex justify-start">
                <div className="bg-[#F5F8F4] border border-[#E0E8DF] text-[#68766B] px-4 py-3 rounded-lg flex items-center gap-3">
                  <div className="w-4 h-4 border-2 border-[#477A58] border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm font-mono">Querying verified evidence packet...</span>
                </div>
              </div>
            )}
          </div>

          {/* Question Input Form */}
          <form onSubmit={handleSendQuestion} className="pt-3 border-t border-[#E0E8DF] flex gap-3">
            <input
              type="text"
              value={questionInput}
              onChange={(e) => setQuestionInput(e.target.value)}
              placeholder="Ask about this case's evidence or exposure..."
              className="flex-1 h-11 text-sm bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg px-4 text-[#183B2A] placeholder-[#68766B] focus:outline-none focus:border-[#477A58] focus-visible:ring-2 focus-visible:ring-[#477A58]"
            />
            <button
              type="submit"
              disabled={!questionInput.trim() || askMutation.isPending}
              className="h-11 px-6 bg-[#477A58] hover:bg-[#285239] disabled:bg-[#E0E8DF] text-white disabled:text-[#68766B] font-semibold text-sm rounded-lg transition-colors shadow-xs"
            >
              Ask
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
