import React from 'react';
import { Link } from 'react-router-dom';

interface CaseNotFoundStateProps {
  readonly requestedId: string;
}

export const CaseNotFoundState: React.FC<CaseNotFoundStateProps> = ({ requestedId }) => {
  return (
    <div className="bg-surface border border-hairline p-10 text-center shadow-subtle my-4 max-w-2xl mx-auto">
      <span className="text-xs font-mono text-brick uppercase tracking-wider font-semibold block mb-1">
        Dossier Lookup Notice
      </span>
      <h2 className="font-serif text-2xl font-bold text-green-950 mb-2">
        Case Record Not Found
      </h2>
      <p className="text-xs text-ink-muted mb-4 font-mono">
        The requested case ID <strong className="text-ink">{requestedId}</strong> does not match any active or historical investigation dossier in the system.
      </p>
      <Link
        to="/queue"
        className="inline-block px-4 py-2 bg-green-900 text-ink-inverse text-xs font-medium border border-green-800 hover:bg-green-800 transition-colors"
      >
        &larr; Return to Investigation Queue
      </Link>
    </div>
  );
};
