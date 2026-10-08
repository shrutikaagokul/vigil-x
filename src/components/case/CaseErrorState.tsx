import React from 'react';

interface CaseErrorStateProps {
  readonly message?: string;
  readonly onRetry?: () => void;
}

export const CaseErrorState: React.FC<CaseErrorStateProps> = ({ message, onRetry }) => {
  return (
    <div className="bg-surface border border-brick/40 p-8 text-center shadow-subtle my-4 max-w-2xl mx-auto">
      <span className="text-xs font-mono text-brick uppercase tracking-wider font-semibold block mb-1">
        Dossier Retrieval Error
      </span>
      <h2 className="font-serif text-xl font-bold text-green-950 mb-2">
        Unable to Load Case Details
      </h2>
      <p className="text-xs text-ink-muted mb-4 font-mono">
        {message || 'An unexpected error occurred while communicating with the case service.'}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="px-4 py-1.5 bg-green-900 text-ink-inverse text-xs font-medium hover:bg-green-800 transition-colors"
        >
          Retry Retrieval
        </button>
      )}
    </div>
  );
};
