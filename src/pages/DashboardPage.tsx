import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getSummary } from '@/services/summaryService';
import { getQueue } from '@/services/queueService';
import {
  DashboardMetrics,
  DashboardPriorityQueue,
  DashboardWhyNexus,
  DashboardPosture,
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

  const isLoading = isSummaryLoading || isQueueLoading;

  if (isLoading) {
    return (
      <main className="w-full min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center p-8 bg-[#F3F8F4]">
        <div className="p-8 bg-white border border-[#D3E0D6] rounded-[3px] text-center max-w-md space-y-3">
          <div className="w-8 h-8 border-2 border-[#2A5A3F] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="font-serif text-[1.125rem] font-semibold text-[#0B1A12]">
            Loading Executive Investigation Overview...
          </p>
        </div>
      </main>
    );
  }

  return (
    <main
      className="w-full min-h-[calc(100vh-4rem)] flex flex-col bg-[#F3F8F4] pb-16"
      role="main"
    >
      {/* 1. Page Header */}
      <div className="w-full pt-7 px-6 md:px-12">
        <h1 className="font-serif text-[2.5rem] leading-[2.75rem] font-semibold text-[#0B1A12] tracking-tight">
          Investigation Overview
        </h1>
        <p className="text-[1.125rem] text-[#4F5F55] mt-1 font-normal max-w-4xl">
          Vigil dynamically prioritizes multi-provider investigation workload within investigator capacity, aligning high-exposure networks ahead of isolated rule flags.
        </p>
      </div>

      {/* 2. Main Dashboard Content Blocks */}
      <div className="w-full px-6 md:px-12 mt-6 space-y-6">
        {/* Four Primary Fact Cards */}
        <DashboardMetrics queueData={queueData} summary={summary} />

        {/* Priority Queue (Top 3 cases) */}
        <DashboardPriorityQueue items={queueData?.items || []} />

        {/* Two-Column Lower Sections: Why Nexus & Investigation Posture */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-7">
            <DashboardWhyNexus />
          </div>
          <div className="lg:col-span-5">
            <DashboardPosture summary={summary} queueData={queueData} />
          </div>
        </div>
      </div>
    </main>
  );
};
