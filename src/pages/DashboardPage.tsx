import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getSummary } from '@/services/summaryService';
import { getQueue } from '@/services/queueService';
import { getHealth } from '@/services/healthService';
import {
  DashboardMetrics,
  DashboardPriorityQueue,
  DashboardWhyNexus,
  DashboardPosture,
  DashboardTopInvestigation,
  DashboardDetectionIntelligence,
  DashboardRuleActivity,
  DashboardNetworkOverview,
  DashboardEvaluationPreview,
  DashboardRiskDistribution,
} from '@/components/dashboard';

export const DashboardPage: React.FC = () => {
  // Fetch executive summary
  const {
    data: summary,
    isLoading: isSummaryLoading,
  } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => getSummary(),
  });

  // Fetch prioritized queue items
  const {
    data: queueData,
    isLoading: isQueueLoading,
  } = useQuery({
    queryKey: ['dashboard-queue'],
    queryFn: () => getQueue({ general_hours: 40, network_hours: 20, horizon: '30d' }),
  });

  // Fetch system health status
  const { data: health } = useQuery({
    queryKey: ['dashboard-health'],
    queryFn: () => getHealth(),
  });

  const isLoading = isSummaryLoading || isQueueLoading;

  if (isLoading) {
    return (
      <main className="w-full min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center p-10 bg-[#F5F8F4]">
        <div className="p-10 bg-white border border-[#E0E8DF] rounded-xl text-center max-w-lg space-y-4 shadow-sm">
          <div className="w-10 h-10 border-3 border-[#477A58] border-t-transparent rounded-full animate-spin mx-auto" />
          <h2 className="font-serif text-xl font-bold text-[#183B2A]">
            Loading Executive Investigation Overview...
          </h2>
          <p className="text-sm text-[#68766B]">
            Calibrating unified risk scores and SIU queue ranking
          </p>
        </div>
      </main>
    );
  }

  const topCase = queueData?.items?.[0];

  return (
    <div className="w-full space-y-10 pb-16" role="main">
      {/* A & B. Header: Page Title, Short Description, and Unobtrusive Text System Status */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 shadow-xs space-y-6">
        {/* A. Page title and description */}
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono uppercase tracking-wider text-[#285239] font-bold bg-[#E8F2E8] px-3 py-1 rounded border border-[#B8D2B8]">
              ClaimShield Nexus Command Center
            </span>
            <span className="text-xs text-[#68766B] font-mono">
              Healthcare Fraud, Waste and Abuse Intelligence
            </span>
          </div>

          <h1 className="font-serif text-3xl md:text-[32px] font-bold text-[#183B2A] tracking-tight">
            Investigation Overview
          </h1>
          <p className="text-base text-[#68766B] max-w-4xl leading-relaxed">
            Vigil dynamically prioritizes multi-provider investigation workload within investigator capacity, aligning high-exposure networks ahead of isolated rule flags.
          </p>
        </div>

        {/* B. System status, displayed unobtrusively using text */}
        <div className="pt-4 border-t border-[#E0E8DF] flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-[#24352A]">
          <div>
            <span className="text-[#68766B]">System Status:</span>{' '}
            <span className="font-semibold text-[#183B2A]">
              {health?.status ? health.status.toUpperCase() : 'HEALTHY'} (Operational)
            </span>
          </div>
          <span className="text-[#B8D2B8]">|</span>
          <div>
            <span className="text-[#68766B]">Database:</span>{' '}
            <span className="font-mono font-medium text-[#285239]">
              {health?.database ? `${health.database.toUpperCase()} LIVE` : 'SQLITE LIVE'}
            </span>
          </div>
          <span className="text-[#B8D2B8]">|</span>
          <div>
            <span className="text-[#68766B]">Mode:</span>{' '}
            <span className="font-medium text-[#24352A]">Calibrated Real Benchmark Data</span>
          </div>
          <span className="text-[#B8D2B8]">|</span>
          <div>
            <span className="text-[#68766B]">Active Budget:</span>{' '}
            <span className="font-medium text-[#24352A]">60 Weekly Hours Allocated</span>
          </div>
        </div>
      </div>

      {/* C. SIU Priority Queue (with Workload Summary Table and readable case details) */}
      <div className="space-y-6">
        <DashboardMetrics queueData={queueData} summary={summary} />
        <DashboardPriorityQueue items={queueData?.items || []} />
      </div>

      {/* D. Risk Distribution, with a large, readable chart */}
      <DashboardRiskDistribution queueData={queueData} />

      {/* E. Detection Intelligence, with clearly separated text-based sections */}
      <DashboardDetectionIntelligence />

      {/* F. Rule Activity, with a readable R01-R10 table */}
      <DashboardRuleActivity />

      {/* G. Network Intelligence overview */}
      <DashboardNetworkOverview />

      {/* H. Top Investigation, with important case details and a clear action button */}
      <DashboardTopInvestigation topCase={topCase} />

      {/* I. Model Evaluation summary */}
      <DashboardEvaluationPreview />

      {/* Governance & Analytical Foundations: Why Nexus & Investigation Posture */}
      <div className="space-y-6">
        <DashboardWhyNexus />
        <DashboardPosture summary={summary} queueData={queueData} />
      </div>
    </div>
  );
};
