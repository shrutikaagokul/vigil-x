import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { CaseDetailPage } from '@/pages/CaseDetailPage';
import * as caseService from '@/services/caseService';

function renderCaseWithRouter(initialRoute = '/cases/CASE-2024-0042') {
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
          <Route path="/cases/:id" element={<CaseDetailPage />} />
          <Route path="/queue" element={<div>Queue Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Checkpoint 5 — Case Dossier & Evidence Ledger (/cases/:id)', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // 1. Case page loads the case using caseService
  it('1. loads the case using caseService.getCase', async () => {
    const spy = vi.spyOn(caseService, 'getCase');
    renderCaseWithRouter('/cases/CASE-2024-0042');

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith('CASE-2024-0042');
    });
  });

  // 2. Case ID comes from route parameter
  it('2. case ID is extracted dynamically from route parameter', async () => {
    renderCaseWithRouter('/cases/CASE-2024-0042');

    await waitFor(() => {
      expect(screen.getByTestId('case-id')).toHaveTextContent('CASE-2024-0042');
    });
  });

  // 3. Hero case renders its real risk index
  it('3. hero case renders its real risk index (94/100)', async () => {
    renderCaseWithRouter('/cases/CASE-2024-0042');

    await waitFor(() => {
      expect(screen.getByTestId('risk-index-value')).toHaveTextContent('94');
    });
  });

  // 4. "Prioritized for human investigation" is displayed
  it('4. displays prominent "Prioritized for human investigation" banner', async () => {
    renderCaseWithRouter('/cases/CASE-2024-0042');

    await waitFor(() => {
      const banner = screen.getByTestId('human-investigation-banner');
      expect(banner).toBeInTheDocument();
      expect(banner).toHaveTextContent(/Prioritized for human investigation/i);
    });
  });

  // 5 & 6. Evidence is loaded and Evidence IDs render correctly
  it('5 & 6. evidence is loaded and Evidence IDs render correctly', async () => {
    renderCaseWithRouter('/cases/CASE-2024-0042');

    await waitFor(() => {
      expect(screen.getByText('E-R06-TIMING-001')).toBeInTheDocument();
      expect(screen.getByText('E-R07-RECLOOP-003')).toBeInTheDocument();
      expect(screen.getByText('E-R09-SHARDBK-006')).toBeInTheDocument();
    });
  });

  // 7. Rule ID and rule version render
  it('7. rule ID and rule version render on evidence chips', async () => {
    renderCaseWithRouter('/cases/CASE-2024-0042');

    await waitFor(() => {
      expect(screen.getAllByText(/R06 · v1/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/R07 · v1/i).length).toBeGreaterThan(0);
    });
  });

  // 8. Claim IDs are traceable
  it('8. claim IDs are rendered as clickable trace buttons in evidence ledger', async () => {
    renderCaseWithRouter('/cases/CASE-2024-0042');

    const evidenceTab = await screen.findByRole('tab', { name: /EVIDENCE/i });
    await userEvent.click(evidenceTab);

    await waitFor(() => {
      const claimButtons = screen.getAllByRole('button', { name: /C1023/i });
      expect(claimButtons.length).toBeGreaterThan(0);
    });
  });

  // 9. est_overpay is displayed as evidence-level overpayment
  it('9. est_overpay is displayed as evidence-level overpayment', async () => {
    renderCaseWithRouter('/cases/CASE-2024-0042');

    await waitFor(() => {
      const overpayElements = screen.getAllByTestId('evidence-overpay');
      expect(overpayElements.length).toBeGreaterThan(0);
      expect(overpayElements[0]).toHaveTextContent(/\$\d+/);
    });
  });

  // 10. fp_notes render when present
  it('10. false positive notes render on evidence cards in evidence ledger', async () => {
    renderCaseWithRouter('/cases/CASE-2024-0042');

    const evidenceTab = await screen.findByRole('tab', { name: /EVIDENCE/i });
    await userEvent.click(evidenceTab);

    await waitFor(() => {
      const fpBoxes = screen.getAllByTestId('fp-notes-box');
      expect(fpBoxes.length).toBeGreaterThan(0);
      expect(fpBoxes[0]).toHaveTextContent(/False-Positive Context/i);
    });
  });

  // 11. Timeline loads and renders in Context chapter
  it('11. timeline tab loads and renders chronological events', async () => {
    renderCaseWithRouter('/cases/CASE-2024-0042');

    const contextTab = await screen.findByRole('tab', { name: /CONTEXT/i });
    await userEvent.click(contextTab);

    await waitFor(() => {
      expect(screen.getByText(/Dr. Mercer billed 75 min evaluation/i)).toBeInTheDocument();
    });
  });

  // 12. Network tab displays real network summary data
  it('12. network tab displays real typed network summary values', async () => {
    renderCaseWithRouter('/cases/CASE-2024-0042');

    const networkTab = await screen.findByRole('tab', { name: /NETWORK/i });
    await userEvent.click(networkTab);

    await waitFor(() => {
      expect(screen.getByText(/Network Subgraph Summary/i)).toBeInTheDocument();
      expect(screen.getByText('Entities (Nodes)')).toBeInTheDocument();
    });
  });

  // 13. AI Copilot is clearly a placeholder and does not fabricate answers
  it('13. AI copilot tab indicates grounded architecture without fake answers', async () => {
    renderCaseWithRouter('/cases/CASE-2024-0042');

    const briefTab = await screen.findByRole('tab', { name: /BRIEF/i });
    await userEvent.click(briefTab);

    await waitFor(() => {
      expect(screen.getByText(/AI Copilot & Executive Brief/i)).toBeInTheDocument();
      expect(screen.getByText(/Guaranteed Grounding Architecture/i)).toBeInTheDocument();
    });
  });

  // 14, 15, 16, 17. Decision modal flow: open -> validate -> submit -> confirm
  it('14-17. human decision workflow enforces reason, submits, and shows confirmation', async () => {
    const submitSpy = vi.spyOn(caseService, 'submitDecision');
    renderCaseWithRouter('/cases/CASE-2024-0042');

    // 14. Open decision modal from docked bottom decision bar
    const acceptButton = await screen.findByRole('button', { name: /^Accept$/i });
    await userEvent.click(acceptButton);

    expect(screen.getByRole('heading', { level: 2, name: /Record Investigation Decision/i })).toBeInTheDocument();

    // 15. Attempt submission without reason
    const submitBtn = screen.getByRole('button', { name: /Submit Human Decision/i });
    await userEvent.click(submitBtn);

    expect(screen.getByText(/A specific human justification reason is mandatory/i)).toBeInTheDocument();
    expect(submitSpy).not.toHaveBeenCalled();

    // 16. Enter reason and submit
    const reasonInput = screen.getByLabelText(/Determination Reason/i);
    await userEvent.type(reasonInput, 'Confirmed 4-provider banking link via state registry search.');
    await userEvent.click(submitBtn);

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith(
        'CASE-2024-0042',
        expect.objectContaining({
          action: 'accept',
          reason: 'Confirmed 4-provider banking link via state registry search.',
        }),
      );
    });

    // 17. Confirmation banner appears
    await waitFor(() => {
      expect(screen.getByTestId('decision-confirmation-banner')).toBeInTheDocument();
      expect(screen.getByText(/Decision Recorded:/i)).toBeInTheDocument();
    });
  });

  // 18. Case not found state renders
  it('18. renders CaseNotFoundState when case does not exist', async () => {
    renderCaseWithRouter('/cases/CASE-NONEXISTENT-999');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: /Case Record Not Found/i })).toBeInTheDocument();
      expect(screen.getByText('CASE-NONEXISTENT-999')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Return to Investigation Queue/i })).toHaveAttribute('href', '/queue');
    });
  });

  // 19. API error state renders
  it('19. renders CaseErrorState when caseService throws non-404 error', async () => {
    vi.spyOn(caseService, 'getCase').mockRejectedValueOnce(new Error('Internal engine crash'));
    renderCaseWithRouter('/cases/CASE-2024-0042');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: /Unable to Load Case Details/i })).toBeInTheDocument();
      expect(screen.getByText(/Internal engine crash/i)).toBeInTheDocument();
    });
  });

  // 20. No forbidden terminology appears in rendered case content
  it('20. no forbidden terminology appears in rendered case dossier', async () => {
    const { container } = renderCaseWithRouter('/cases/CASE-2024-0042');

    await waitFor(() => {
      expect(screen.getByTestId('case-id')).toHaveTextContent('CASE-2024-0042');
    });

    const text = container.textContent?.toLowerCase() || '';
    expect(text).not.toContain('fraud detected');
    expect(text).not.toContain('confirmed fraud');
    expect(text).not.toContain('ai says fraud');
  });

  // 21. Docked decision bar renders with canonical actions
  it('21. renders docked bottom decision bar with canonical actions', async () => {
    renderCaseWithRouter('/cases/CASE-2024-0042');

    await waitFor(() => {
      const bar = screen.getByTestId('docked-decision-bar');
      expect(bar).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Accept' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Reject' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Needs info' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Escalate' })).toBeInTheDocument();
    });
  });
});
