import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getEvaluation } from '@/services/evaluationService';
import {
  EvaluationHeader,
  EvaluationCoreMetrics,
  EvaluationComparisonCenterpiece,
  EvaluationScenarioBreakdown,
  EvaluationRulePerformance,
  EvaluationLimitations,
} from '@/components/evaluation';

export const EvaluationPage: React.FC = () => {
  const {
    data: summary,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['evaluation-summary'],
    queryFn: () => getEvaluation(),
  });

  if (isLoading) {
    return (
      <main className="w-full min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center p-8 bg-[#F5F8F4]">
        <div className="p-8 bg-white border border-[#E0E8DF] rounded text-center max-w-md space-y-3 shadow-xs">
          <div className="w-8 h-8 border-2 border-[#477A58] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="font-serif text-lg font-semibold text-[#183B2A]">
            Loading Ground Truth Evaluation Metrics...
          </p>
        </div>
      </main>
    );
  }

  if (isError || !summary) {
    return (
      <main className="w-full min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center p-8 bg-[#F5F8F4]">
        <div className="p-8 bg-white border border-[#FCA5A5] rounded text-center max-w-md space-y-3 shadow-xs">
          <h2 className="font-serif text-lg font-bold text-[#B91C1C]">
            Unable to Load Evaluation Report
          </h2>
          <p className="text-xs text-[#68766B]">
            {error instanceof Error ? error.message : 'Evaluation service unavailable.'}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 bg-[#477A58] text-white text-xs font-semibold rounded hover:bg-[#285239] transition-colors"
          >
            Retry
          </button>
        </div>
      </main>
    );
  }

  return (
    <main
      className="w-full min-h-[calc(100vh-8rem)] flex flex-col bg-[#F5F8F4] pb-16"
      role="main"
    >
      {/* 1. Page Header with Fact Strip */}
      <EvaluationHeader summary={summary} />

      {/* 2. Main Content Stack */}
      <div className="w-full px-6 md:px-12 mt-6 space-y-6">
        {/* Core Benchmark Metric Cards */}
        <EvaluationCoreMetrics summary={summary} />

        {/* Visual Centerpiece: Rules-Only vs Nexus Comparison */}
        <EvaluationComparisonCenterpiece />

        {/* Scenario & Rule Level Performance Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <EvaluationScenarioBreakdown scenarios={summary.scenario_breakdown} />
          <EvaluationRulePerformance rulePerformance={summary.rule_performance} />
        </div>

        {/* Methodology & Limitations Statement */}
        <EvaluationLimitations />
      </div>
    </main>
  );
};
