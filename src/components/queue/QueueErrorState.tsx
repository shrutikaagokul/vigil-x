import React from 'react';

interface QueueErrorStateProps {
  readonly error: Error | null;
  readonly onRetry: () => void;
}

export const QueueErrorState: React.FC<QueueErrorStateProps> = ({ error, onRetry }) => {
  return (
    <div className="bg-surface border border-brick/40 p-8 text-center shadow-subtle my-2">
      <span className="text-[11px] font-mono text-brick uppercase tracking-wider font-semibold block mb-1">
        Service Communication Error
      </span>
      <h3 className="font-serif text-lg font-bold text-green-950 mb-2">
        Unable to Load Investigation Queue
      </h3>
      <p className="text-xs text-ink-muted max-w-md mx-auto mb-4 font-mono">
        {error ? error.message : 'An error occurred while communicating with the analytics engine.'}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="px-4 py-1.5 bg-green-900 text-ink-inverse text-xs font-medium hover:bg-green-800 transition-colors"
      >
        Retry Request
      </button>
    </div>
  );
};
