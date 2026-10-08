import React from 'react';
import { Link } from 'react-router-dom';
import { PageContainer } from '@/components/layout/PageContainer';

export const NotFoundPage: React.FC = () => {
  return (
    <PageContainer maxWidth="narrow">
      <div className="bg-surface border border-hairline p-8 shadow-subtle text-center">
        <span className="text-xs font-mono text-brick uppercase tracking-wider font-semibold">
          Error 404 · Resource Not Found
        </span>
        <h1 className="font-serif text-2xl font-bold text-green-950 mt-2 mb-3">
          Page Not Found
        </h1>
        <p className="text-xs text-ink-muted max-w-md mx-auto mb-6">
          The requested route does not exist within the ClaimShield Nexus application. Verify the URL or return to the investigation dashboard.
        </p>
        <Link
          to="/"
          className="inline-block px-4 py-2 bg-green-900 text-ink-inverse text-xs font-medium border border-green-800 hover:bg-green-800 transition-colors"
        >
          Return to Dashboard
        </Link>
      </div>
    </PageContainer>
  );
};
