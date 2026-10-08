import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getHealth } from '@/services/healthService';
import { getApiMode } from '@/services/config';

export const SystemStatus: React.FC = () => {
  const apiMode = getApiMode();

  const { data: health, isError, isLoading } = useQuery({
    queryKey: ['systemHealth'],
    queryFn: getHealth,
    staleTime: 60 * 1000,
    retry: false,
  });

  const isHealthy = health?.status === 'healthy';
  const isDegraded = health?.status === 'degraded';

  return (
    <div className="flex items-center gap-3 text-[11px] font-mono tracking-wide select-none">
      {/* Permanent Synthetic Data Badge */}
      <div
        data-testid="synthetic-data-badge"
        className="px-2 py-0.5 border border-green-800 bg-green-900/60 text-green-300 font-medium rounded-none"
        title="Demonstration dataset — synthetic claims only"
      >
        Synthetic data only
      </div>

      {/* API Mode Indicator */}
      <div
        data-testid="api-mode-badge"
        className="px-2 py-0.5 border border-green-800/80 bg-green-950 text-ink-inverse flex items-center gap-1.5"
      >
        <span className="text-ink-subtle">API</span>
        <span className="text-green-400 font-semibold uppercase">{apiMode}</span>
      </div>

      {/* System Health Indicator */}
      <div
        data-testid="system-health-badge"
        className="px-2 py-0.5 border border-green-800/80 bg-green-950 text-ink-inverse flex items-center gap-1.5"
        title="SIU Analytics Engine & Database Status"
      >
        <span
          className={`inline-block w-1.5 h-1.5 rounded-full ${
            isLoading
              ? 'bg-blue-400 animate-pulse'
              : isHealthy
              ? 'bg-emerald-400'
              : isDegraded
              ? 'bg-amber-400'
              : 'bg-red-400'
          }`}
          aria-hidden="true"
        />
        <span className="text-ink-subtle uppercase">HEALTH</span>
        <span className="text-ink-inverse font-medium uppercase">
          {isLoading ? 'Checking' : isHealthy ? 'Operational' : isError ? 'Unavailable' : health?.status || 'Active'}
        </span>
      </div>
    </div>
  );
};
