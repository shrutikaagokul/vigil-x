import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { EvaluationPage } from '@/pages/EvaluationPage';
import * as evaluationService from '@/services/evaluationService';

function renderEvaluationWithRouter(initialRoute = '/evaluation') {
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
          <Route path="/evaluation" element={<EvaluationPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Evaluation Page (/evaluation)', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // 1. Loads evaluation data through evaluationService
  it('1. loads evaluation data through evaluationService', async () => {
    const spy = vi.spyOn(evaluationService, 'getEvaluation');
    renderEvaluationWithRouter('/evaluation');

    await waitFor(() => {
      expect(spy).toHaveBeenCalled();
    });
  });

  // 2. Renders header and contextual statement
  it('2. renders heading Evaluation and contextual statement', async () => {
    renderEvaluationWithRouter('/evaluation');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /^Evaluation$/i })).toBeInTheDocument();
      expect(screen.getByText(/Vigil-X is evaluated directly against a rules-only prioritization baseline/i)).toBeInTheDocument();
      expect(screen.getByTestId('eval-fact-strip')).toHaveTextContent('154,200');
    });
  });

  // 3. Renders core benchmark metric cards
  it('3. renders core benchmark metric cards with real numbers', async () => {
    renderEvaluationWithRouter('/evaluation');

    await waitFor(() => {
      const coreMetrics = screen.getByTestId('eval-core-metrics');
      expect(coreMetrics).toHaveTextContent(/Claim-Level F1 Score/i);
      expect(coreMetrics).toHaveTextContent('92.8%');
      expect(coreMetrics).toHaveTextContent(/Provider-Level F1 Score/i);
      expect(coreMetrics).toHaveTextContent('95.3%');
      expect(coreMetrics).toHaveTextContent(/Scenario Detection Recall/i);
      expect(coreMetrics).toHaveTextContent('100%');
      expect(coreMetrics).toHaveTextContent(/Mean Ring Recovery Jaccard/i);
      expect(coreMetrics).toHaveTextContent('92.4%');
    });
  });

  // 4. Renders visual centerpiece comparison table
  it('4. renders comparison table showing Rules-only vs Nexus lift', async () => {
    renderEvaluationWithRouter('/evaluation');

    await waitFor(() => {
      const comparison = screen.getByTestId('eval-comparison-centerpiece');
      expect(comparison).toBeInTheDocument();
      expect(comparison).toHaveTextContent(/Precision @ Top 10 Triage/i);
      expect(comparison).toHaveTextContent('30.0% (3 / 10)');
      expect(comparison).toHaveTextContent('40.0% (4 / 10)');
      expect(comparison).toHaveTextContent('+33.3% relative (+10.0% abs)');
      expect(comparison).toHaveTextContent(/6-Provider Ring Prioritization/i);
      expect(comparison).toHaveTextContent('Rank #38');
      expect(comparison).toHaveTextContent('Rank #1');
      expect(comparison).toHaveTextContent('+37 rank promotion');
    });
  });

  // 5. Renders scenario breakdown table
  it('5. renders planted scenario recovery breakdown table', async () => {
    renderEvaluationWithRouter('/evaluation');

    await waitFor(() => {
      const scenarios = screen.getByTestId('eval-scenario-breakdown');
      expect(scenarios).toBeInTheDocument();
      expect(scenarios).toHaveTextContent('SCENARIO-01');
      expect(scenarios).toHaveTextContent('SCENARIO-02');
      expect(scenarios).toHaveTextContent('SCENARIO-03');
      expect(scenarios).toHaveTextContent('SCENARIO-04');
      expect(scenarios).toHaveTextContent('100%');
    });
  });

  // 6. Renders rule performance table
  it('6. renders individual detection rule performance table', async () => {
    renderEvaluationWithRouter('/evaluation');

    await waitFor(() => {
      const rulesTable = screen.getByTestId('eval-rule-performance');
      expect(rulesTable).toBeInTheDocument();
      expect(rulesTable).toHaveTextContent('R06');
      expect(rulesTable).toHaveTextContent('R07');
      expect(rulesTable).toHaveTextContent('R08');
      expect(rulesTable).toHaveTextContent('R09');
      expect(rulesTable).toHaveTextContent('R10');
    });
  });

  // 7. Renders methodology and limitations statement
  it('7. renders methodology and limitations statement without unsupported claims', async () => {
    renderEvaluationWithRouter('/evaluation');

    await waitFor(() => {
      const limitations = screen.getByTestId('eval-limitations');
      expect(limitations).toBeInTheDocument();
      expect(limitations).toHaveTextContent(/Synthetic Ground Truth Environment/i);
      expect(limitations).toHaveTextContent(/Human-in-the-Loop Triage Guardrails/i);
    });
  });

  // 8. Handles error state gracefully
  it('8. renders error state when evaluationService fails', async () => {
    vi.spyOn(evaluationService, 'getEvaluation').mockRejectedValueOnce(new Error('Evaluation report missing'));
    renderEvaluationWithRouter('/evaluation');

    await waitFor(() => {
      expect(screen.getByText(/Unable to Load Evaluation Report/i)).toBeInTheDocument();
      expect(screen.getByText(/Evaluation report missing/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
    });
  });
});
