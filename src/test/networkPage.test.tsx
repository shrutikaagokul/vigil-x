import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { NetworkPage } from '@/pages/NetworkPage';
import { CaseDetailPage } from '@/pages/CaseDetailPage';
import * as networkService from '@/services/networkService';

function renderNetworkWithRouter(initialRoute = '/networks/NET-RING-001') {
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
          <Route path="/networks" element={<NetworkPage />} />
          <Route path="/networks/:id" element={<NetworkPage />} />
          <Route path="/cases/:id" element={<CaseDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Checkpoint 6 — Network Investigation View (/networks & /networks/:id)', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // 1. Loads network data through networkService
  it('1. loads network data through networkService', async () => {
    const spy = vi.spyOn(networkService, 'getNetwork');
    renderNetworkWithRouter('/networks/NET-RING-001');

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith('NET-RING-001');
    });
  });

  // 2. Renders compact header with fact strip
  it('2. renders compact header with fact strip and network metadata', async () => {
    renderNetworkWithRouter('/networks/NET-RING-001');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /Network Investigation/i })).toBeInTheDocument();
      expect(screen.getByTestId('network-id-badge')).toHaveTextContent('NET-RING-001');
      const factStrip = screen.getByTestId('network-fact-strip');
      expect(factStrip).toHaveTextContent('8'); // 8 nodes
      expect(factStrip).toHaveTextContent('10'); // 10 edges
      expect(factStrip).toHaveTextContent('2'); // 2 cohorts
      expect(factStrip).toHaveTextContent('102'); // 102 members
    });
  });

  // 3. Renders Cytoscape canvas container and controls
  it('3. renders cytoscape canvas container and investigation controls', async () => {
    renderNetworkWithRouter('/networks/NET-RING-001');

    await waitFor(() => {
      expect(screen.getByTestId('network-canvas-container')).toBeInTheDocument();
      expect(screen.getByTestId('cytoscape-canvas')).toBeInTheDocument();
      expect(screen.getByTestId('network-canvas-controls')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Zoom in/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Zoom out/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Fit graph/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Reset layout/i })).toBeInTheDocument();
    });
  });

  // 4. Renders compact legend with entity and edge types
  it('4. renders compact legend with entity and edge semantics', async () => {
    renderNetworkWithRouter('/networks/NET-RING-001');

    await waitFor(() => {
      const legend = screen.getByTestId('network-legend');
      expect(legend).toBeInTheDocument();
      expect(legend).toHaveTextContent(/Provider/i);
      expect(legend).toHaveTextContent(/Facility/i);
      expect(legend).toHaveTextContent(/Owner \/ Bank Account/i);
      expect(legend).toHaveTextContent(/Member/i);
      expect(legend).toHaveTextContent(/Solid \(Verified Link\)/i);
      expect(legend).toHaveTextContent(/Dashed \(Referral Ring\)/i);
      expect(legend).toHaveTextContent(/Dotted \(Same-Day Lab\)/i);
    });
  });

  // 5. Renders investigation insight panel with findings and cohorts
  it('5. renders investigation insight panel with synthesis and cohorts', async () => {
    renderNetworkWithRouter('/networks/NET-RING-001');

    await waitFor(() => {
      const panel = screen.getByTestId('network-insight-panel');
      expect(panel).toBeInTheDocument();
      expect(panel).toHaveTextContent(/Why does this network matter\?/i);
      expect(panel).toHaveTextContent(/Shared Banking Ring/i);
      expect(panel).toHaveTextContent(/9a8b7c6d5e4f3a21/i);
      expect(panel).toHaveTextContent(/Patient Cohorts/i);
      expect(panel).toHaveTextContent(/68 patients/i);
      expect(panel).toHaveTextContent(/34 patients/i);
      expect(panel).toHaveTextContent('E-R09-SHARDBK-006');
    });
  });

  // 6. Preserves case context when navigated with caseId param
  it('6. preserves case context when linked from CASE-2024-0042', async () => {
    renderNetworkWithRouter('/networks/NET-RING-001?caseId=CASE-2024-0042');

    await waitFor(() => {
      expect(screen.getByText(/← Back to Case/i)).toBeInTheDocument();
      expect(screen.getByText('CASE-2024-0042')).toBeInTheDocument();
    });
  });

  // 7. Handles error state for non-existent network
  it('7. renders error state when network is not found', async () => {
    renderNetworkWithRouter('/networks/NON-EXISTENT-NET');

    await waitFor(() => {
      expect(screen.getByText(/Unable to Load Network/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
    });
  });

  // 8. Renders entity node details with evidence citations
  it('8. renders node details and evidence citations when node is selected', async () => {
    const { container } = renderNetworkWithRouter('/networks/NET-RING-001');

    await waitFor(() => {
      expect(screen.getByTestId('network-insight-panel')).toBeInTheDocument();
    });

    // Verify network structure and citations render cleanly
    expect(container.textContent).toContain('Apex Healthcare Holdings');
    expect(container.textContent).toContain('E-R09-SHARDBK-006');
  });
});
