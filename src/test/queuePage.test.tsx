import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { QueuePage } from '@/pages/QueuePage';
import { CaseDetailPage } from '@/pages/CaseDetailPage';
import * as queueService from '@/services/queueService';

function renderQueueWithRouter(initialRoute = '/queue') {
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
          <Route path="/queue" element={<QueuePage />} />
          <Route path="/cases/:id" element={<CaseDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Vigil-X Queue Page (/queue)', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // 1. Queue page loads queue data through queueService
  it('1. loads queue data through queueService', async () => {
    const spy = vi.spyOn(queueService, 'getQueue');
    renderQueueWithRouter();

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          general_hours: 40,
          network_hours: 20,
          horizon: '30d',
          sort: 'priority',
        }),
      );
    });
  });

  // 2. Queue renders returned cases in worklist
  it('2. renders returned case rows in worklist', async () => {
    renderQueueWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Mercer Pain & Toxicology Network')).toBeInTheDocument();
      expect(screen.getByText('Dr. Sarah Chen')).toBeInTheDocument();
      expect(screen.getByText('Dr. Gregory House')).toBeInTheDocument();
    });
  });

  // 3. Capacity controls trigger queue service call with new parameters
  it('3. capacity controls trigger queue service call with new parameters', async () => {
    const spy = vi.spyOn(queueService, 'getQueue');
    renderQueueWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Mercer Pain & Toxicology Network')).toBeInTheDocument();
    });

    const netSlider = screen.getByLabelText(/Network specialist capacity in hours/i);
    // Trigger slider value change
    fireEvent.keyDown(netSlider, { key: 'ArrowRight' });

    await waitFor(() => {
      expect(spy).toHaveBeenCalled();
    });
  });

  // 4. Horizon buttons pass horizon parameter to service
  it('4. horizon buttons pass horizon parameter to service', async () => {
    const spy = vi.spyOn(queueService, 'getQueue');
    renderQueueWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Mercer Pain & Toxicology Network')).toBeInTheDocument();
    });

    const button90 = screen.getByRole('button', { name: '90' });
    await userEvent.click(button90);

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          horizon: '90d',
        }),
      );
    });
  });

  // 5. Search query filters cases by name
  it('5. search query filters cases by name or provider', async () => {
    renderQueueWithRouter();

    await waitFor(() => {
      expect(screen.getAllByText('Mercer Pain & Toxicology Network').length).toBeGreaterThan(0);
      expect(screen.getByText('Dr. Sarah Chen')).toBeInTheDocument();
    });

    const searchInput = screen.getByLabelText(/Search cases/i);
    await userEvent.type(searchInput, 'Mercer');

    await waitFor(() => {
      expect(screen.getAllByText('Mercer Pain & Toxicology Network').length).toBeGreaterThan(0);
      expect(screen.queryByText('Dr. Sarah Chen')).not.toBeInTheDocument();
    });
  });

  // 6. Row click selects case in preview panel
  it('6. clicking row selects case in preview panel without navigating', async () => {
    renderQueueWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Dr. Sarah Chen')).toBeInTheDocument();
    });

    const chenRow = screen.getByRole('row', { name: /Case Dr. Sarah Chen/i });
    await userEvent.click(chenRow);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Dr. Sarah Chen' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Open case/i })).toBeInTheDocument();
    });
  });

  // 7. Open case button in preview panel navigates to /cases/:id
  it('7. clicking Open case button in preview panel navigates to /cases/:id', async () => {
    renderQueueWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Mercer Pain & Toxicology Network')).toBeInTheDocument();
    });

    const openCaseBtn = screen.getByRole('button', { name: /Open case/i });
    await userEvent.click(openCaseBtn);

    await waitFor(() => {
      expect(screen.getByTestId('case-id')).toHaveTextContent('CASE-2024-0042');
    });
  });

  // 8. Hero case CASE-2024-0042 naturally ranks #1
  it('8. hero case CASE-2024-0042 naturally ranks #1 under default capacity', async () => {
    renderQueueWithRouter();

    await waitFor(() => {
      const rows = screen.getAllByRole('row');
      // header row is rows[0], first data row is rows[1]
      expect(rows[1]).toHaveTextContent('1');
      expect(rows[1]).toHaveTextContent('Mercer Pain & Toxicology Network');
      expect(rows[1]).toHaveTextContent('94');
    });
  });

  // 9. Signature capacity line renders across left worklist
  it('9. signature dashed capacity line renders across worklist', async () => {
    renderQueueWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId('capacity-boundary-line')).toBeInTheDocument();
      expect(screen.getByText(/Capacity reached/i)).toBeInTheDocument();
    });
  });

  // 10. Empty state renders when filters match nothing
  it('10. renders empty state when no cases match filter', async () => {
    renderQueueWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Mercer Pain & Toxicology Network')).toBeInTheDocument();
    });

    const searchInput = screen.getByLabelText(/Search cases/i);
    await userEvent.type(searchInput, 'NonExistentDoctorQuery123');

    await waitFor(() => {
      expect(screen.getByText(/No Investigations Match Current Filters/i)).toBeInTheDocument();
    });
  });

  // 11. Error state renders when queue loading fails
  it('11. renders error state when queueService fails', async () => {
    vi.spyOn(queueService, 'getQueue').mockRejectedValueOnce(new Error('Database timeout'));
    renderQueueWithRouter();

    await waitFor(() => {
      expect(screen.getByText(/Unable to Load Investigation Queue/i)).toBeInTheDocument();
      expect(screen.getByText(/Database timeout/i)).toBeInTheDocument();
    });
  });

  // 12. No forbidden terminology appears in rendered queue content
  it('12. no forbidden terminology appears in rendered queue', async () => {
    const { container } = renderQueueWithRouter();

    await waitFor(() => {
      expect(screen.getByText('Mercer Pain & Toxicology Network')).toBeInTheDocument();
    });

    const text = container.textContent?.toLowerCase() || '';
    expect(text).not.toContain('fraud detected');
    expect(text).not.toContain('confirmed fraud');
    expect(text).not.toContain('ai says fraud');
  });
});
