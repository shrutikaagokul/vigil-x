import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';
import { startIngest, resetIngest } from '@/services/ingestService';
import { isMockMode } from '@/services/apiClient';
import { BatchIngestRequest, IngestRun, IngestStatus } from '@/types/ingest';

const PRESET_BATCHES = [
  {
    id: 'BATCH-2024-Q3-SYNTHETIC',
    name: 'Standard Payer Claims Batch',
    claimsCount: 5000,
    scenario: 'Multi-rule baseline evaluation (R01–R10)',
    description: 'Comprehensive sample of commercial and Medicare claim lines spanning 150 providers.',
  },
  {
    id: 'BATCH-COLLUSION-RING-01',
    name: 'Coordinated Provider Ring Inject',
    claimsCount: 1200,
    scenario: 'Collusion Ring & Shared Identity Focus (R09)',
    description: 'Simulated multi-clinic referral ring sharing tax identifiers and bank accounts.',
  },
  {
    id: 'BATCH-HIGH-VOLUME-EM',
    name: 'High-Volume E/M Upcoding Batch',
    claimsCount: 10000,
    scenario: 'Billing Bursts & Time Inversion Anomalies (R02, R06, R10)',
    description: 'High-throughput evaluation testing capacity-aware triage with intensive time constraints.',
  },
];

export const IngestPage: React.FC = () => {
  const navigate = useNavigate();
  const mockMode = isMockMode();

  // Form State
  const [selectedBatchId, setSelectedBatchId] = useState<string>(PRESET_BATCHES[0].id);
  const [claimsCount, setClaimsCount] = useState<number>(5000);
  const [scenarioInject, setScenarioInject] = useState<string>('Standard Multi-Rule Evaluation (R01–R10)');
  const [isDryRun, setIsDryRun] = useState<boolean>(false);

  // Execution State
  const [status, setStatus] = useState<IngestStatus | 'idle'>('idle');
  const [runResult, setRunResult] = useState<IngestRun | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState<boolean>(false);

  const handleBatchSelect = (batchId: string) => {
    setSelectedBatchId(batchId);
    const preset = PRESET_BATCHES.find((b) => b.id === batchId);
    if (preset) {
      setClaimsCount(preset.claimsCount);
      setScenarioInject(preset.scenario);
    }
  };

  const handleStartBatch = async () => {
    setStatus('running');
    setErrorMessage(null);
    setResetMessage(null);
    setRunResult(null);

    const payload: BatchIngestRequest = {
      batch_id: selectedBatchId,
      claims_count: Number(claimsCount),
      scenario_inject: scenarioInject,
      dry_run: isDryRun,
    };

    try {
      const result = await startIngest(payload);
      setRunResult(result);
      setStatus(result.status);
    } catch (err: unknown) {
      setStatus('failed');
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to execute batch ingestion against the current environment.');
      }
    }
  };

  const handleReset = async () => {
    setIsResetting(true);
    setErrorMessage(null);
    setRunResult(null);
    setStatus('idle');
    try {
      const res = await resetIngest();
      setResetMessage(res.message);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to reset engine state.');
      }
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <PageContainer>
      {/* Top Header Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <Link
            to="/"
            className="text-[0.875rem] font-medium text-ink-muted hover:text-ink-primary transition-colors flex items-center space-x-1.5 focus:outline-none focus-visible:underline"
          >
            <span>Back to Dashboard</span>
          </Link>
          <div className="flex items-center space-x-2">
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-[2px] text-[0.8125rem] font-mono font-medium border ${
                mockMode
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-amber-50 text-amber-900 border-amber-200'
              }`}
            >
              {mockMode ? 'SYNTHETIC DEMO PIPELINE' : 'LIVE BACKEND PIPELINE'}
            </span>
          </div>
        </div>

        <div className="border-b border-hairline pb-4 flex flex-col md:flex-row md:items-baseline md:justify-between gap-2">
          <div>
            <span className="text-[0.8125rem] font-mono text-ink-subtle uppercase tracking-wider block mb-1">
              Data Pipeline & Simulation
            </span>
            <h1 className="font-serif text-[1.75rem] md:text-[2rem] font-bold text-[#12291C] leading-tight">
              Load claims batch
            </h1>
          </div>
          <p className="text-[0.9375rem] text-ink-muted max-w-xl">
            Load a synthetic claims batch and run the detection, network clustering, and SIU prioritization pipeline.
          </p>
        </div>
      </div>

      {/* Reset Notification Toast */}
      {resetMessage && (
        <div
          role="status"
          className="mb-6 bg-emerald-50 border border-emerald-300 text-emerald-900 px-4 py-3 rounded-[3px] text-[0.9375rem] flex items-center justify-between"
        >
          <div className="flex items-center space-x-2">
            <span>{resetMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setResetMessage(null)}
            className="text-emerald-700 hover:text-emerald-900 font-medium text-[0.875rem]"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main 2-Column Content */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Batch Configuration Controls */}
        <div className="lg:col-span-6 flex flex-col space-y-6">
          <div className="bg-surface border border-hairline p-6 shadow-subtle rounded-[3px]">
            <h2 className="font-serif text-[1.1875rem] font-semibold text-[#12291C] mb-4">
              Batch Configuration
            </h2>

            {/* Batch Dataset Selection */}
            <div className="mb-5">
              <label htmlFor="batch-select" className="block text-[0.875rem] font-medium text-ink-primary mb-1.5">
                Claims Batch Dataset
              </label>
              <select
                id="batch-select"
                value={selectedBatchId}
                onChange={(e) => handleBatchSelect(e.target.value)}
                disabled={status === 'running'}
                className="w-full bg-paper border border-hairline rounded-[3px] px-3.5 py-2.5 text-[0.9375rem] text-ink-primary focus:outline-none focus:border-[#12291C] disabled:opacity-60"
              >
                {PRESET_BATCHES.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name} ({b.claimsCount.toLocaleString()} claims)
                  </option>
                ))}
              </select>
              <p className="mt-1.5 text-[0.875rem] text-ink-muted">
                {PRESET_BATCHES.find((b) => b.id === selectedBatchId)?.description}
              </p>
            </div>

            {/* Claims Count */}
            <div className="mb-5">
              <label htmlFor="claims-count" className="block text-[0.875rem] font-medium text-ink-primary mb-1.5">
                Total Claims Volume
              </label>
              <div className="flex items-center space-x-3">
                <input
                  id="claims-count"
                  type="number"
                  min={100}
                  max={50000}
                  step={100}
                  value={claimsCount}
                  onChange={(e) => setClaimsCount(Number(e.target.value))}
                  disabled={status === 'running'}
                  className="w-40 bg-paper border border-hairline rounded-[3px] px-3.5 py-2 text-[0.9375rem] font-mono text-ink-primary focus:outline-none focus:border-[#12291C] disabled:opacity-60"
                />
                <div className="flex space-x-1.5">
                  {[1200, 5000, 10000].map((count) => (
                    <button
                      key={count}
                      type="button"
                      onClick={() => setClaimsCount(count)}
                      disabled={status === 'running'}
                      className={`px-2.5 py-1 text-[0.8125rem] font-mono rounded-[2px] border ${
                        claimsCount === count
                          ? 'bg-[#12291C] text-white border-[#12291C]'
                          : 'bg-paper text-ink-muted border-hairline hover:border-ink-subtle'
                      }`}
                    >
                      {count.toLocaleString()}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Target Scenario */}
            <div className="mb-5">
              <label htmlFor="scenario-inject" className="block text-[0.875rem] font-medium text-ink-primary mb-1.5">
                Scenario Focus / Detection Scope
              </label>
              <input
                id="scenario-inject"
                type="text"
                value={scenarioInject}
                onChange={(e) => setScenarioInject(e.target.value)}
                disabled={status === 'running'}
                className="w-full bg-paper border border-hairline rounded-[3px] px-3.5 py-2 text-[0.9375rem] text-ink-primary focus:outline-none focus:border-[#12291C] disabled:opacity-60"
              />
            </div>

            {/* Dry Run Toggle */}
            <div className="mb-6 pt-2 border-t border-hairline flex items-center space-x-3">
              <input
                id="dry-run-checkbox"
                type="checkbox"
                checked={isDryRun}
                onChange={(e) => setIsDryRun(e.target.checked)}
                disabled={status === 'running'}
                className="h-4 w-4 rounded border-hairline text-[#12291C] focus:ring-0"
              />
              <label htmlFor="dry-run-checkbox" className="text-[0.875rem] text-ink-primary cursor-pointer select-none">
                Dry Run (Evaluate rules and calculate risk without mutating queue state)
              </label>
            </div>

            {/* Primary Actions */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center space-y-3 sm:space-y-0 sm:space-x-4 pt-2">
              <button
                type="button"
                onClick={handleStartBatch}
                disabled={status === 'running'}
                className="flex-1 bg-[#12291C] text-white font-semibold text-[0.9375rem] px-5 py-2.5 rounded-[3px] hover:bg-[#1B3A29] disabled:opacity-60 transition-colors flex items-center justify-center space-x-2 focus:outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#12291C]"
              >
                {status === 'running' ? (
                  <>
                    <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Processing Batch...</span>
                  </>
                ) : (
                  <span>Start batch</span>
                )}
              </button>

              <button
                type="button"
                onClick={handleReset}
                disabled={isResetting || status === 'running'}
                className="bg-paper border border-hairline text-ink-secondary font-medium text-[0.9375rem] px-4 py-2.5 rounded-[3px] hover:bg-paper-subtle hover:text-ink-primary disabled:opacity-50 transition-colors focus:outline-none focus-visible:underline"
              >
                {isResetting ? 'Resetting...' : 'Reset to baseline'}
              </button>
            </div>
          </div>

          {/* Pipeline Architectural Context Card */}
          <div className="bg-surface border border-hairline p-5 rounded-[3px]">
            <h3 className="text-[0.875rem] font-bold text-ink-primary uppercase tracking-wider mb-3">
              Investigation Pipeline Architecture
            </h3>
            <ul className="space-y-2.5 text-[0.875rem] text-ink-secondary">
              <li className="flex items-start space-x-2.5">
                <span className="font-mono text-[0.8125rem] bg-paper-subtle px-1.5 py-0.5 border border-hairline text-ink-muted">1</span>
                <span><strong>Detection Engine:</strong> Executes rules R01–R10 (duplicate billing, unbundling, upcoding, impossible timing).</span>
              </li>
              <li className="flex items-start space-x-2.5">
                <span className="font-mono text-[0.8125rem] bg-paper-subtle px-1.5 py-0.5 border border-hairline text-ink-muted">2</span>
                <span><strong>Network Projection:</strong> Connects providers through shared identifiers, locations, and referral clusters.</span>
              </li>
              <li className="flex items-start space-x-2.5">
                <span className="font-mono text-[0.8125rem] bg-paper-subtle px-1.5 py-0.5 border border-hairline text-ink-muted">3</span>
                <span><strong>SIU Triage Optimization:</strong> Synthesizes multi-signal risk and assigns capacity-bounded investigation ranks.</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Right Column: Execution Monitor & Results Display */}
        <div className="lg:col-span-6 flex flex-col">
          {/* State 1: Idle */}
          {status === 'idle' && (
            <div className="bg-surface border border-hairline p-6 shadow-subtle rounded-[3px] flex-1 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-3 mb-4 border-b border-hairline">
                  <span className="text-[0.8125rem] font-mono text-ink-subtle uppercase tracking-wider">
                    Pipeline Execution Monitor
                  </span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-[2px] text-[0.8125rem] font-mono bg-paper text-ink-muted border border-hairline">
                    IDLE
                  </span>
                </div>
                <h3 className="font-serif text-[1.25rem] font-semibold text-[#12291C] mb-2">
                  Ready for Ingestion Run
                </h3>
                <p className="text-[0.9375rem] text-ink-muted mb-6">
                  Select a synthetic dataset and click &ldquo;Start batch&rdquo; to trigger the pipeline. Analytical outputs, provider signals, and queue allocations will be updated in real time.
                </p>

                <div className="bg-paper border border-hairline p-4 rounded-[3px]">
                  <h4 className="text-[0.8125rem] font-mono text-ink-subtle uppercase tracking-wider mb-2">
                    Recent Baseline Reference
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-[0.875rem]">
                    <div>
                      <span className="text-ink-muted block text-[0.8125rem]">Run ID</span>
                      <span className="font-mono font-medium text-ink-primary">RUN-2024-0918-01</span>
                    </div>
                    <div>
                      <span className="text-ink-muted block text-[0.8125rem]">Claims Processed</span>
                      <span className="font-mono font-medium text-ink-primary">12,500</span>
                    </div>
                    <div>
                      <span className="text-ink-muted block text-[0.8125rem]">Alerts Generated</span>
                      <span className="font-mono font-medium text-ink-primary">42</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-hairline text-[0.875rem] text-ink-muted flex items-center justify-between">
                <span>All operations prioritize human investigator review.</span>
                <span className="font-mono text-[0.8125rem]">SYNTHETIC DATA ONLY</span>
              </div>
            </div>
          )}

          {/* State 2: Running Progress */}
          {status === 'running' && (
            <div className="bg-surface border border-hairline p-6 shadow-subtle rounded-[3px] flex-1 flex flex-col justify-center items-center text-center">
              <div className="w-12 h-12 border-3 border-[#12291C] border-t-transparent rounded-full animate-spin mb-4" />
              <h3 className="font-serif text-[1.375rem] font-semibold text-[#12291C] mb-1">
                Processing Claims Batch
              </h3>
              <p className="text-[0.9375rem] text-ink-muted max-w-sm mb-6">
                Executing detection rules R01–R10, calculating graph projections, and ranking priority cases...
              </p>

              <div className="w-full max-w-md bg-paper border border-hairline p-4 rounded-[3px] text-left space-y-2 font-mono text-[0.875rem]">
                <div className="flex items-center justify-between text-emerald-800">
                  <span>1. Ingesting {claimsCount.toLocaleString()} claim lines</span>
                  <span>DONE</span>
                </div>
                <div className="flex items-center justify-between text-[#12291C] font-semibold animate-pulse">
                  <span>2. Evaluating rule signals & anomalies</span>
                  <span>RUNNING</span>
                </div>
                <div className="flex items-center justify-between text-ink-subtle">
                  <span>3. Resolving network entities & graph</span>
                  <span>WAITING</span>
                </div>
                <div className="flex items-center justify-between text-ink-subtle">
                  <span>4. Rebuilding capacity-aware queue</span>
                  <span>WAITING</span>
                </div>
              </div>
            </div>
          )}

          {/* State 3: Completed Success */}
          {status === 'completed' && runResult && (
            <div className="bg-surface border border-hairline p-6 shadow-subtle rounded-[3px] flex-1 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-3 mb-4 border-b border-hairline">
                  <span className="text-[0.8125rem] font-mono text-ink-subtle uppercase tracking-wider">
                    Pipeline Execution Monitor
                  </span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-[2px] text-[0.8125rem] font-mono font-medium bg-emerald-50 text-emerald-800 border border-emerald-300">
                    COMPLETED
                  </span>
                </div>

                <h3 className="font-serif text-[1.375rem] font-semibold text-[#12291C] mb-1">
                  Batch Ingestion & Analysis Finished
                </h3>
                <p className="text-[0.9375rem] text-ink-muted mb-6">
                  The claims batch has been ingested, analyzed, and prioritized for Special Investigation Unit review.
                </p>

                {/* Metrics Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 bg-paper border border-hairline p-4 rounded-[3px] mb-6">
                  <div>
                    <span className="text-ink-muted block text-[0.8125rem]">Run ID</span>
                    <span className="font-mono font-medium text-ink-primary text-[0.9375rem] truncate block">
                      {runResult.run_id}
                    </span>
                  </div>
                  <div>
                    <span className="text-ink-muted block text-[0.8125rem]">Claims Processed</span>
                    <span className="font-mono font-semibold text-ink-primary text-[1.125rem]">
                      {runResult.claims_processed.toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-ink-muted block text-[0.8125rem]">Providers Evaluated</span>
                    <span className="font-mono font-semibold text-ink-primary text-[1.125rem]">
                      {runResult.providers_evaluated}
                    </span>
                  </div>
                  <div>
                    <span className="text-ink-muted block text-[0.8125rem]">Alerts Generated</span>
                    <span className="font-mono font-semibold text-emerald-900 text-[1.125rem]">
                      {runResult.alerts_generated}
                    </span>
                  </div>
                  <div>
                    <span className="text-ink-muted block text-[0.8125rem]">Cases Updated</span>
                    <span className="font-mono font-semibold text-ink-primary text-[1.125rem]">
                      {runResult.cases_updated}
                    </span>
                  </div>
                  <div>
                    <span className="text-ink-muted block text-[0.8125rem]">Execution Duration</span>
                    <span className="font-mono font-medium text-ink-primary text-[0.9375rem]">
                      {(runResult.execution_time_ms / 1000).toFixed(2)}s
                    </span>
                  </div>
                </div>
              </div>

              {/* Navigation CTAs */}
              <div className="pt-4 border-t border-hairline flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => setStatus('idle')}
                  className="text-[0.875rem] text-ink-muted hover:text-ink-primary font-medium transition-colors text-left"
                >
                  Load another batch
                </button>
                <div className="flex space-x-3">
                  <button
                    type="button"
                    onClick={() => navigate('/')}
                    className="bg-paper border border-hairline text-ink-primary font-medium text-[0.9375rem] px-4 py-2 rounded-[3px] hover:bg-paper-subtle transition-colors"
                  >
                    View Dashboard
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate('/queue')}
                    aria-label="Open Priority Queue →"
                    className="bg-[#12291C] text-white font-semibold text-[0.9375rem] px-5 py-2.5 rounded-[3px] hover:bg-[#1B3A29] transition-colors"
                  >
                    <span>Open Priority Queue</span>
                    <span className="sr-only">→</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* State 4: Error or Unavailable in Live Mode */}
          {status === 'failed' && (
            <div className="bg-surface border border-hairline p-6 shadow-subtle rounded-[3px] flex-1 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-3 mb-4 border-b border-hairline">
                  <span className="text-[0.8125rem] font-mono text-ink-subtle uppercase tracking-wider">
                    Pipeline Execution Monitor
                  </span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-[2px] text-[0.8125rem] font-mono font-medium bg-amber-50 text-amber-900 border border-amber-300">
                    UNAVAILABLE / ERROR
                  </span>
                </div>

                <h3 className="font-serif text-[1.375rem] font-semibold text-[#12291C] mb-2">
                  Batch Ingestion Offline / Managed CLI Mode
                </h3>
                <p className="text-[0.9375rem] text-ink-secondary mb-4">
                  {errorMessage ||
                    'The live FastAPI backend is currently operating in query-serving mode against pre-computed SQLite analytical tables. Live HTTP batch ingestion endpoints (/api/ingest/batch) are not mounted.'}
                </p>

                <div className="bg-paper border border-hairline p-4 rounded-[3px] mb-6">
                  <h4 className="text-[0.8125rem] font-mono text-ink-subtle uppercase tracking-wider mb-2">
                    Direct Terminal Pipeline Execution
                  </h4>
                  <p className="text-[0.875rem] text-ink-muted mb-2">
                    To rebuild and ingest new analytical outputs into the SQLite database, run the offline backend pipeline:
                  </p>
                  <code className="block bg-[#12291C] text-[#A9CFB0] font-mono text-[0.875rem] p-2.5 rounded-[2px] select-all">
                    python scripts/build_db.py
                  </code>
                </div>
              </div>

              <div className="pt-4 border-t border-hairline flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setStatus('idle')}
                  className="text-[0.875rem] text-ink-muted hover:text-ink-primary font-medium"
                >
                  Back to parameters
                </button>
                <div className="flex space-x-3">
                  <button
                    type="button"
                    onClick={() => navigate('/')}
                    className="bg-paper border border-hairline text-ink-primary font-medium text-[0.9375rem] px-4 py-2 rounded-[3px] hover:bg-paper-subtle"
                  >
                    Dashboard
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate('/queue')}
                    className="bg-[#12291C] text-white font-semibold text-[0.9375rem] px-5 py-2.5 rounded-[3px] hover:bg-[#1B3A29]"
                  >
                    Open Queue
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  );
};
