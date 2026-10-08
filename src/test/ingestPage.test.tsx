import { render, screen, waitFor, fireEvent, cleanup } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { IngestPage } from '@/pages/IngestPage';
import * as ingestService from '@/services/ingestService';

function renderIngestPage(initialRoute = '/ingest') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/" element={<div data-testid="dashboard-page">Dashboard</div>} />
          <Route path="/queue" element={<div data-testid="queue-page">Queue</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Ingest Page (/ingest)', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('1. renders heading "Load claims batch" and contextual description', () => {
    renderIngestPage();
    expect(screen.getByRole('heading', { level: 1, name: /Load claims batch/i })).toBeInTheDocument();
    expect(
      screen.getByText(/Load a synthetic claims batch and run the detection, network clustering, and SIU prioritization pipeline/i),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Back to Dashboard/i })).toBeInTheDocument();
  });

  it('2. renders batch configuration controls and baseline reference', () => {
    renderIngestPage();
    expect(screen.getByLabelText(/Claims Batch Dataset/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Total Claims Volume/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Scenario Focus/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Dry Run/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Start batch/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Reset to baseline/i })).toBeInTheDocument();
    expect(screen.getByText('RUN-2024-0918-01')).toBeInTheDocument();
  });

  it('3. selects different batch presets correctly', () => {
    renderIngestPage();
    const select = screen.getByLabelText(/Claims Batch Dataset/i);
    fireEvent.change(select, { target: { value: 'BATCH-COLLUSION-RING-01' } });

    const claimsInput = screen.getByLabelText(/Total Claims Volume/i) as HTMLInputElement;
    expect(claimsInput.value).toBe('1200');
  });

  it('4. clicking Start batch calls startIngest and displays completed metrics', async () => {
    const startIngestSpy = vi.spyOn(ingestService, 'startIngest').mockResolvedValue({
      run_id: 'RUN-TEST-999',
      status: 'completed',
      started_at: '2024-10-09T00:00:00Z',
      completed_at: '2024-10-09T00:00:02Z',
      claims_processed: 5000,
      providers_evaluated: 150,
      alerts_generated: 18,
      cases_updated: 2,
      execution_time_ms: 1500,
    });

    renderIngestPage();
    const startBtn = screen.getByRole('button', { name: /Start batch/i });
    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(startIngestSpy).toHaveBeenCalled();
      expect(screen.getByText('RUN-TEST-999')).toBeInTheDocument();
      expect(screen.getByText(/Batch Ingestion & Analysis Finished/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Open Priority Queue →/i })).toBeInTheDocument();
    });
  });

  it('5. clicking Reset to baseline triggers resetIngest and displays feedback', async () => {
    const resetSpy = vi.spyOn(ingestService, 'resetIngest').mockResolvedValue({
      success: true,
      message: 'State reset successfully.',
      timestamp: '2024-10-09T00:00:00Z',
    });

    renderIngestPage();
    const resetBtn = screen.getByRole('button', { name: /Reset to baseline/i });
    fireEvent.click(resetBtn);

    await waitFor(() => {
      expect(resetSpy).toHaveBeenCalled();
      expect(screen.getByText('State reset successfully.')).toBeInTheDocument();
    });
  });

  it('6. handles ingestion failure gracefully and displays direct offline pipeline instructions', async () => {
    vi.spyOn(ingestService, 'startIngest').mockRejectedValue(new Error('Endpoint /api/ingest/batch not found on backend.'));

    renderIngestPage();
    const startBtn = screen.getByRole('button', { name: /Start batch/i });
    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(screen.getByText(/Batch Ingestion Offline \/ Managed CLI Mode/i)).toBeInTheDocument();
      expect(screen.getByText(/Endpoint \/api\/ingest\/batch not found on backend/i)).toBeInTheDocument();
      expect(screen.getByText('python scripts/build_db.py')).toBeInTheDocument();
    });
  });

  it('7. navigates to Queue from completed state', async () => {
    vi.spyOn(ingestService, 'startIngest').mockResolvedValue({
      run_id: 'RUN-TEST-123',
      status: 'completed',
      started_at: '2024-10-09T00:00:00Z',
      completed_at: '2024-10-09T00:00:01Z',
      claims_processed: 1200,
      providers_evaluated: 40,
      alerts_generated: 8,
      cases_updated: 1,
      execution_time_ms: 1000,
    });

    renderIngestPage();
    fireEvent.click(screen.getByRole('button', { name: /Start batch/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Open Priority Queue →/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Open Priority Queue →/i }));
    expect(screen.getByTestId('queue-page')).toBeInTheDocument();
  });
});
