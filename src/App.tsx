import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppShell } from '@/components/layout/AppShell';
import {
  DashboardPage,
  QueuePage,
  CaseDetailPage,
  NetworkPage,
  AuditPage,
  EvaluationPage,
  IngestPage,
  NotFoundPage,
} from '@/pages';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false,
      staleTime: 60 * 1000,
    },
  },
});

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="queue" element={<QueuePage />} />
        <Route path="cases/:id" element={<CaseDetailPage />} />
        <Route path="networks" element={<NetworkPage />} />
        <Route path="networks/:id" element={<NetworkPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="evaluation" element={<EvaluationPage />} />
        <Route path="ingest" element={<IngestPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
};

export default function App(): React.ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
