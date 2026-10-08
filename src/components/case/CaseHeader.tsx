import React from 'react';
import { Link } from 'react-router-dom';
import { Case } from '@/types/case';
import { formatCurrency } from '@/utils/currency';

interface CaseHeaderProps {
  readonly caseItem: Case;
  readonly onOpenDecisionModal?: () => void;
}

export const CaseHeader: React.FC<CaseHeaderProps> = ({ caseItem }) => {
  const severityClass = {
    CRITICAL: 'bg-[#FCEBEA] text-[#9E1F14] border-[#F0C2BE]',
    HIGH: 'bg-[#FBEAE6] text-[#7D2D1B] border-[#F2C4B8]',
    MEDIUM: 'bg-[#F5EEDD] text-[#8C682A] border-[#E3D0A8]',
    LOW: 'bg-[#F0EDE6] text-[#4A574E] border-[#D5CDBC]',
  }[caseItem.severity] || 'bg-[#F0EDE6] text-[#1F2923] border-[#D5CDBC]';

  const statusClass = {
    open: 'bg-[#EAF3EC] text-[#1B3A29] border-[#C8DEC9]',
    under_investigation: 'bg-[#E3EFE5] text-[#12291C] border-[#B7D4BA]',
    decided: 'bg-[#F0EDE6] text-[#4A574E] border-[#D5CDBC]',
    escalated: 'bg-[#FBEAE6] text-[#7D2D1B] border-[#F2C4B8]',
    closed: 'bg-[#F0EDE6] text-[#6B7C70] border-[#D5CDBC]',
  }[caseItem.status] || 'bg-[#F0EDE6] text-[#1F2923] border-[#D5CDBC]';

  return (
    <header className="bg-surface border border-border p-5 sm:p-6 space-y-4">
      {/* Top Meta Bar: Breadcrumb + Mandatory Human Investigation Notice */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-3">
        <div className="flex items-center gap-2 text-xs font-sans">
          <Link
            to="/queue"
            className="text-green-800 hover:text-green-950 font-semibold flex items-center gap-1 hover:underline"
          >
            ← Queue
          </Link>
          <span className="text-border-strong">/</span>
          <span className="font-mono text-ink-subtle text-xs">
            {caseItem.id}
          </span>
        </div>

        {/* Prominent Mandatory Human Investigation Notice Banner */}
        <div
          data-testid="human-investigation-banner"
          className="flex items-center gap-2 px-2.5 py-1 bg-masthead text-ink-inverse border border-green-800 text-xs font-mono select-none"
        >
          <span className="w-2 h-2 rounded-full bg-green-400" aria-hidden="true" />
          <span className="tracking-wide uppercase font-medium">Prioritized for human investigation</span>
        </div>
      </div>

      {/* Main Document Case Info & Risk Header */}
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
        {/* Left Column: Title, Identity & Provider Context */}
        <div className="space-y-3 flex-1">
          {/* Identity & Status Badges */}
          <div className="flex flex-wrap items-center gap-2">
            <span
              data-testid="case-id"
              className="font-mono text-sm font-bold text-green-950 bg-paper-subtle border border-border px-2.5 py-0.5"
            >
              {caseItem.id}
            </span>
            <span className={`px-2 py-0.5 text-[11px] font-mono font-bold uppercase border ${severityClass}`}>
              {caseItem.severity}
            </span>
            <span className={`px-2 py-0.5 text-[11px] font-mono uppercase border ${statusClass}`}>
              {caseItem.status.replace('_', ' ')}
            </span>
            {caseItem.decision && (
              <span className="px-2 py-0.5 text-[11px] font-mono bg-green-100 text-green-900 border border-green-300 font-semibold">
                Decision: {caseItem.decision.action.toUpperCase()}
              </span>
            )}
          </div>

          {/* Large Readable Case Title */}
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-green-950 tracking-tight leading-snug">
            {caseItem.title}
          </h1>

          {/* Focal Provider & Secondary Context */}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm text-ink-muted">
            <span className="text-ink">
              <strong className="font-semibold text-green-950">{caseItem.focal_provider_name}</strong>{' '}
              <span className="font-mono text-xs text-ink-subtle">· {caseItem.focal_provider_id}</span>
            </span>
            <span className="text-border-strong">·</span>
            <span className="font-mono text-xs uppercase text-ink">
              {caseItem.specialty.replace('_', ' ')}
            </span>
            {caseItem.sla_due_date && (
              <>
                <span className="text-border-strong">·</span>
                <span className="font-mono text-xs text-ink-subtle">
                  SLA Due: {new Date(caseItem.sla_due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Right Column: Prominent Risk & Financial Exposure Block */}
        <div className="shrink-0 flex items-center justify-between gap-6 p-4 bg-paper-subtle border border-border">
          <div className="text-left">
            <span className="text-[11px] font-mono font-semibold uppercase text-ink-subtle block tracking-wider">
              Risk Index
            </span>
            <div className="flex items-baseline gap-1 mt-0.5">
              <span
                data-testid="risk-index-value"
                className="font-serif text-3xl sm:text-4xl font-bold text-green-950 leading-none"
              >
                {caseItem.risk_index}
              </span>
              <span className="font-mono text-sm text-ink-subtle">/100</span>
            </div>
          </div>

          <div className="border-l border-border pl-6 text-left">
            <span className="text-[11px] font-mono font-semibold uppercase text-ink-subtle block tracking-wider">
              Total Exposure
            </span>
            <span className="font-mono text-lg sm:text-xl font-bold text-green-950 block mt-0.5">
              {formatCurrency(caseItem.est_dollars, 'full')}
            </span>
            {caseItem.est_overpay > 0 && (
              <span className="text-xs text-brick font-mono font-semibold">
                {formatCurrency(caseItem.est_overpay, 'full')} overpayment
              </span>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

