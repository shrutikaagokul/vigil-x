import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { DashboardPage } from '@/pages/DashboardPage';
import { CaseDetailPage } from '@/pages/CaseDetailPage';
import { QueuePage } from '@/pages/QueuePage';
import * as summaryService from '@/services/summaryService';
import * as queueService from '@/services/queueService';

function renderDashboardWithRouter(initialRoute = '/') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/queue" element={<QueuePage />} />
          <Route path="/cases/:id" element={<CaseDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Checkpoint 7 — Dashboard Executive Overview (/)', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // 1. Loads summary and queue data through service layer
  it('1. loads summary and queue data through service layer', async () => {
    const summarySpy = vi.spyOn(summaryService, 'getSummary');
    const queueSpy = vi.spyOn(queueService, 'getQueue');
    renderDashboardWithRouter('/');

    await waitFor(() => {
      expect(summarySpy).toHaveBeenCalled();
      expect(queueSpy).toHaveBeenCalled();
    });
  });

  // 2. Renders page title and contextual statement
  it('2. renders heading Investigation Overview and contextual statement', async () => {
    renderDashboardWithRouter('/');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /Investigation Overview/i })).toBeInTheDocument();
      expect(screen.getByText(/Vigil dynamically prioritizes multi-provider investigation workload/i)).toBeInTheDocument();
    });
  });

  // 3. Renders four primary metric cards
  it('3. renders 4 primary metrics computed from real data', async () => {
    renderDashboardWithRouter('/');

    await waitFor(() => {
      const metrics = screen.getByTestId('dashboard-metrics');
      expect(metrics).toHaveTextContent(/Cases Requiring Investigation/i);
      expect(metrics).toHaveTextContent(/Exposure in Queue/i);
      expect(metrics).toHaveTextContent(/Addressable This Week/i);
      expect(metrics).toHaveTextContent(/Nexus Prioritization Lift/i);
      expect(metrics).toHaveTextContent('+37 ranks');
    });
  });

  // 4. Renders top 3 priority queue cases
  it('4. renders top 3 prioritized cases in Priority Queue section', async () => {
    renderDashboardWithRouter('/');

    await waitFor(() => {
      const queueSection = screen.getByTestId('dashboard-priority-queue');
      expect(queueSection).toBeInTheDocument();
      expect(queueSection).toHaveTextContent('Mercer Pain & Toxicology Network');
      expect(queueSection).toHaveTextContent('Dr. Sarah Chen');
      expect(queueSection).toHaveTextContent('Dr. Gregory House');
      expect(queueSection).toHaveTextContent('#38 → #1');
    });
  });

  // 5. Clicking a case opens /cases/:id
  it('5. clicking a priority case navigates to /cases/:id', async () => {
    renderDashboardWithRouter('/');

    await waitFor(() => {
      expect(screen.getByText('Mercer Pain & Toxicology Network')).toBeInTheDocument();
    });

    const openButtons = screen.getAllByRole('button', { name: /Open case →/i });
    await userEvent.click(openButtons[0]);

    await waitFor(() => {
      expect(screen.getByTestId('case-id')).toHaveTextContent('CASE-2024-0042');
    });
  });

  // 6. View full queue link navigates to /queue
  it('6. provides link to view full queue', async () => {
    renderDashboardWithRouter('/');

    await waitFor(() => {
      expect(screen.getByText(/View full queue/i)).toBeInTheDocument();
    });

    const fullQueueLink = screen.getByText(/View full queue/i);
    await userEvent.click(fullQueueLink);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /Queue/i })).toBeInTheDocument();
    });
  });

  // 7. Renders Why Nexus Changes the Order section
  it('7. renders Why Nexus Changes the Order section', async () => {
    renderDashboardWithRouter('/');

    await waitFor(() => {
      const whyNexus = screen.getByTestId('dashboard-why-nexus');
      expect(whyNexus).toBeInTheDocument();
      expect(whyNexus).toHaveTextContent(/Capacity-Aware Prioritization/i);
      expect(whyNexus).toHaveTextContent(/Network Context & Entity Resolution/i);
      expect(whyNexus).toHaveTextContent(/Multi-Rule Evidence Cross-Corroboration/i);
      expect(whyNexus).toHaveTextContent(/Exposure Yield per Investigation Hour/i);
    });
  });

  // 8. Renders Investigation Posture section
  it('8. renders Investigation Posture with severity and top categories', async () => {
    renderDashboardWithRouter('/');

    await waitFor(() => {
      const posture = screen.getByTestId('dashboard-posture');
      expect(posture).toBeInTheDocument();
      expect(posture).toHaveTextContent(/Queue Severity Breakdown/i);
      expect(posture).toHaveTextContent(/Critical Severity/i);
      expect(posture).toHaveTextContent(/Top Risk Pattern Categories/i);
      expect(posture).toHaveTextContent(/Shared Banking & Entity Rings/i);
    });
  });
});
