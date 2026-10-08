import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, afterEach } from 'vitest';
import { AppRoutes } from './App';

function renderWithRouter(initialRoute = '/') {
  const testQueryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={testQueryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('App Shell, Masthead & Routing', () => {
  afterEach(() => {
    cleanup();
  });

  // 1. App renders Dashboard route
  it('1. renders Dashboard route at root /', async () => {
    renderWithRouter('/');
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /Investigation Overview/i })).toBeInTheDocument();
      expect(screen.getByText(/Vigil dynamically prioritizes multi-provider investigation workload/i)).toBeInTheDocument();
    });
  });

  // 2. Queue route renders
  it('2. renders Queue route at /queue', () => {
    renderWithRouter('/queue');
    expect(screen.getByRole('heading', { level: 1, name: 'Queue' })).toBeInTheDocument();
  });

  // 3. Case route reads and displays its dynamic ID
  it('3. case route reads and displays dynamic ID from URL', async () => {
    renderWithRouter('/cases/CASE-2024-0042');
    await waitFor(() => {
      expect(screen.getByTestId('case-id')).toHaveTextContent('CASE-2024-0042');
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Mercer/i);
    });
  });

  it('3b. case route handles non-existent custom ID gracefully', async () => {
    renderWithRouter('/cases/CASE-CUSTOM-999');
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: /Case Record Not Found/i })).toBeInTheDocument();
      expect(screen.getByText('CASE-CUSTOM-999')).toBeInTheDocument();
    });
  });

  // 4. Navigation links point to correct routes
  it('4. navigation links point to the correct routes', () => {
    renderWithRouter('/');
    const dashboardLink = screen.getByRole('link', { name: 'Dashboard' });
    const queueLink = screen.getByRole('link', { name: 'Queue' });
    const networksLink = screen.getByRole('link', { name: 'Networks' });
    const evalLink = screen.getByRole('link', { name: 'Evaluation' });

    expect(dashboardLink).toHaveAttribute('href', '/');
    expect(queueLink).toHaveAttribute('href', '/queue');
    expect(networksLink).toHaveAttribute('href', '/networks/NET-RING-001');
    expect(evalLink).toHaveAttribute('href', '/evaluation');
  });

  // 5. Active navigation state is marked correctly
  it('5. active navigation tab has aria-current="page"', () => {
    renderWithRouter('/queue');
    const queueLink = screen.getByRole('link', { name: 'Queue' });
    const dashboardLink = screen.getByRole('link', { name: 'Dashboard' });

    expect(queueLink).toHaveAttribute('aria-current', 'page');
    expect(dashboardLink).not.toHaveAttribute('aria-current', 'page');
  });

  // 6. Vigil-X Masthead brand and Load batch button
  it('6. renders Vigil-X brand and Load batch button in masthead', () => {
    renderWithRouter('/');
    expect(screen.getByRole('link', { name: /Vigil-X/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Load batch/i })).toBeInTheDocument();
    expect(screen.getByText(/Healthy/i)).toBeInTheDocument();
  });

  it('6b. clicking Load batch opens /ingest route', async () => {
    renderWithRouter('/ingest');
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: /Load claims batch/i })).toBeInTheDocument();
    });
  });

  // 7. Footer disclaimer is present
  it('7. footer displays synthetic data notice and dev mock indicator', () => {
    renderWithRouter('/');
    expect(screen.getByText(/Synthetic data only/i)).toBeInTheDocument();
    expect(screen.getByText(/Prioritized for human investigation/i)).toBeInTheDocument();
  });

  // 8. Unknown route renders NotFoundPage
  it('8. unknown route renders 404 NotFoundPage with dashboard link', () => {
    renderWithRouter('/some/non-existent/path');
    expect(screen.getByRole('heading', { level: 1, name: 'Page Not Found' })).toBeInTheDocument();
    expect(screen.getByText(/Error 404/i)).toBeInTheDocument();
    const returnLink = screen.getByRole('link', { name: 'Return to Dashboard' });
    expect(returnLink).toHaveAttribute('href', '/');
  });
});
