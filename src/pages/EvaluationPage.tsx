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
      <main className="w-full min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center p-8 bg-[#F3F8F4]">
        <div className="p-8 bg-white border border-[#D3E0D6] rounded-[3px] text-center max-w-md space-y-3">
          <div className="w-8 h-8 border-2 border-[#2A5A3F] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="font-serif text-[1.125rem] font-semibold text-[#0B1A12]">
            Loading Ground Truth Evaluation Metrics...
          </p>
        </div>
      </main>
    );
  }

  if (isError || !summary) {
    return (
      <main className="w-full min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center p-8 bg-[#F3F8F4]">
        <div className="p-8 bg-white border border-[#9E3626] rounded-[3px] text-center max-w-md space-y-3">
          <h2 className="font-serif text-[1.25rem] font-bold text-[#701F14]">
            Unable to Load Evaluation Report
          </h2>
          <p className="text-[0.875rem] text-[#4F5F55]">
            {error instanceof Error ? error.message : 'Evaluation service unavailable.'}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 bg-[#2A5A3F] text-white text-[0.875rem] font-semibold rounded-[3px] hover:bg-[#1B3A29] transition-colors"
          >
            Retry
          </button>
        </div>
      </main>
    );
  }

  return (
    <main
      className="w-full min-h-[calc(100vh-4rem)] flex flex-col bg-[#F3F8F4] pb-16"
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
