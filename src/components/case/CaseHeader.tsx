import React from 'react';
import { Link } from 'react-router-dom';
import { Case } from '@/types/case';

interface CaseHeaderProps {
  readonly caseItem: Case;
  readonly onOpenDecisionModal: () => void;
}

export const CaseHeader: React.FC<CaseHeaderProps> = ({ caseItem, onOpenDecisionModal }) => {
  const severityClass = {
    CRITICAL: 'bg-critical-soft text-critical border-critical/30',
    HIGH: 'bg-brick-soft text-brick border-brick/30',
    MEDIUM: 'bg-brass-soft text-ink border-brass/40',
    LOW: 'bg-paper-subtle text-ink-subtle border-border',
  }[caseItem.severity] || 'bg-paper-subtle text-ink';

  const statusClass = {
    open: 'bg-green-50 text-green-900 border-green-300',
    under_investigation: 'bg-green-100 text-green-950 border-green-400',
    decided: 'bg-paper-subtle text-ink-muted border-border',
    escalated: 'bg-brick-soft text-brick border-brick/30',
    closed: 'bg-paper text-ink-subtle border-border',
  }[caseItem.status] || 'bg-paper-subtle text-ink';

  return (
    <div className="bg-surface border border-border p-4 space-y-3">
      {/* Top Bar: Breadcrumb + Mandatory Human Investigation Notice */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-2.5">
        <div className="flex items-center gap-2 text-xs font-sans">
          <Link
            to="/queue"
            className="text-green-800 hover:text-green-950 font-medium flex items-center gap-1 hover:underline"
          >
            ← QUEUE
          </Link>
          <span className="text-border-strong">/</span>
          <span className="font-mono text-ink-subtle uppercase text-[11px]">
            CASE FILE
          </span>
        </div>

        {/* Mandatory Human Investigation Notice Banner */}
        <div
          data-testid="human-investigation-banner"
          className="flex items-center gap-1.5 px-2 py-0.5 bg-masthead text-ink-inverse border border-green-800 text-[11px] font-mono select-none"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-green-300" aria-hidden="true" />
          <span className="tracking-wide uppercase">Prioritized for human investigation</span>
        </div>
      </div>

      {/* Main Case Title & Entity Details */}
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-3">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <span
              data-testid="case-id"
              className="font-mono text-sm font-bold text-green-950 bg-paper-subtle border border-border px-2 py-0.5"
            >
              {caseItem.id}
            </span>
            <span className={`px-2 py-0.5 text-[10px] font-mono font-bold uppercase border ${severityClass}`}>
              {caseItem.severity}
            </span>
            <span className={`px-2 py-0.5 text-[10px] font-mono uppercase border ${statusClass}`}>
              {caseItem.status.replace('_', ' ')}
            </span>
            {caseItem.decision && (
              <span className="px-2 py-0.5 text-[10px] font-mono bg-green-100 text-green-900 border border-green-300 font-semibold">
                Decision: {caseItem.decision.action.toUpperCase()}
              </span>
            )}
          </div>

          <h1 className="font-serif text-xl sm:text-2xl font-bold text-green-950 tracking-tight leading-snug">
            {caseItem.title}
          </h1>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-muted">
            <span>
              <strong className="text-ink font-semibold">{caseItem.focal_provider_name}</strong>{' '}
              <span className="font-mono text-[11px] text-ink-subtle">· {caseItem.focal_provider_id}</span>
            </span>
            <span className="text-border-strong">·</span>
            <span className="font-mono text-[11px] uppercase">
              {caseItem.specialty.replace('_', ' ')}
            </span>
            <span className="text-border-strong">·</span>
            <span className="font-mono text-[11px]">
              SLA Due: {new Date(caseItem.sla_due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </span>
          </div>

          {/* Compact Case Fact Line */}
          <div className="pt-2 border-t border-border flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs font-sans text-ink">
            <div className="flex items-center gap-1">
              <span className="text-ink-subtle uppercase text-[10px] font-mono">Risk:</span>
              <strong className="font-mono font-bold text-green-950">{caseItem.risk_index}/100</strong>
            </div>
            <span className="text-border-strong" aria-hidden="true">·</span>
            <div className="flex items-center gap-1">
              <span className="text-ink-subtle uppercase text-[10px] font-mono">Exposure:</span>
              <strong className="font-mono font-bold text-green-950">${caseItem.est_dollars.toLocaleString()}</strong>
            </div>
            <span className="text-border-strong" aria-hidden="true">·</span>
            <div className="flex items-center gap-1">
              <span className="text-ink-subtle uppercase text-[10px] font-mono">Identifiable Overpay:</span>
              <strong className="font-mono font-bold text-brick">${caseItem.est_overpay.toLocaleString()}</strong>
            </div>
            <span className="text-border-strong" aria-hidden="true">·</span>
            <div className="flex items-center gap-1">
              <span className="text-ink-subtle uppercase text-[10px] font-mono">Claims:</span>
              <strong className="font-mono font-semibold text-ink">{caseItem.claim_count}</strong>
            </div>
            <span className="text-border-strong" aria-hidden="true">·</span>
            <div className="flex items-center gap-1">
              <span className="text-ink-subtle uppercase text-[10px] font-mono">Rule Models:</span>
              <strong className="font-mono font-semibold text-ink">{caseItem.rules_triggered.length}</strong>
            </div>
          </div>
        </div>

        {/* Compact Decision Action Trigger */}
        <div className="shrink-0 flex items-center gap-2 self-start lg:self-center">
          <button
            type="button"
            onClick={onOpenDecisionModal}
            className="px-3 py-1.5 bg-green-800 text-ink-inverse text-xs font-semibold hover:bg-green-900 border border-green-700 transition-colors flex items-center gap-1"
          >
            <span>Record Human Decision</span>
            <span aria-hidden="true">→</span>
          </button>
        </div>
      </div>
    </div>
  );
};

