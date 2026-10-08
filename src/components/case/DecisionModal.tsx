import React, { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { DecisionAction, DecisionResponse } from '@/types/case';
import { submitDecision } from '@/services/caseService';

interface DecisionModalProps {
  readonly caseId: string;
  readonly isOpen: boolean;
  readonly initialAction?: DecisionAction;
  readonly onClose: () => void;
  readonly onSuccess: (res: DecisionResponse) => void;
}

export const DecisionModal: React.FC<DecisionModalProps> = ({
  caseId,
  isOpen,
  initialAction = 'accept',
  onClose,
  onSuccess,
}) => {
  const [action, setAction] = useState<DecisionAction>(initialAction);
  const [reason, setReason] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Sync action when modal opens with a specific action
  React.useEffect(() => {
    if (isOpen) {
      setAction(initialAction);
    }
  }, [isOpen, initialAction]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setErrorMsg('A specific human justification reason is mandatory.');
      return;
    }

    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      const response = await submitDecision(caseId, {
        action,
        reason: reason.trim(),
        notes: notes.trim() || undefined,
        assigned_investigator: 'SIU Lead Investigator',
      });
      setIsSubmitting(false);
      onSuccess(response);
      onClose();
    } catch (err) {
      setIsSubmitting(false);
      setErrorMsg(err instanceof Error ? err.message : 'Failed to record decision.');
    }
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-green-950/60 backdrop-blur-[1px] z-50 transition-opacity" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-surface border border-border p-5 shadow-none z-50 space-y-3 focus:outline-none">
          <div className="flex items-center justify-between border-b border-border pb-2.5">
            <div>
              <span className="text-[10px] font-mono text-ink-subtle uppercase tracking-wider">
                Human-in-the-Loop Governance
              </span>
              <Dialog.Title className="font-serif text-lg font-bold text-green-950">
                Record Investigation Decision
              </Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="text-xs font-mono text-ink-subtle hover:text-ink px-2 py-0.5 border border-border"
                aria-label="Close dialog"
              >
                &times;
              </button>
            </Dialog.Close>
          </div>

          <Dialog.Description className="text-xs text-ink-muted">
            Case <strong className="font-mono text-ink">{caseId}</strong>. Record the formal determination for this prioritized dossier. A clear human rationale is required for the audit trail.
          </Dialog.Description>

          <form onSubmit={handleSubmit} className="space-y-3 pt-1">
            {/* Action Radio Options */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-green-950 uppercase text-[11px] block">
                Investigation Determination
              </label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { value: 'accept', label: 'Accept', desc: 'Proceed with full SIU audit' },
                  { value: 'needs_info', label: 'Needs info', desc: 'Request clarifying medical records' },
                  { value: 'escalate', label: 'Escalate', desc: 'Medical Director clinical review' },
                  { value: 'reject', label: 'Reject', desc: 'Dismiss case / verified legitimate' },
                ].map((opt) => (
                  <label
                    key={opt.value}
                    className={`flex flex-col p-2 border cursor-pointer transition-colors text-xs ${
                      action === opt.value
                        ? 'bg-paper-subtle border-green-800'
                        : 'bg-surface border-border hover:bg-paper-subtle/50'
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <input
                        type="radio"
                        name="decisionAction"
                        value={opt.value}
                        checked={action === opt.value}
                        onChange={() => setAction(opt.value as DecisionAction)}
                        className="accent-green-800"
                      />
                      <span className="font-semibold text-ink">{opt.label}</span>
                    </div>
                    <span className="text-[10px] font-mono text-ink-subtle mt-0.5 pl-4">{opt.desc}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Mandatory Reason */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label htmlFor="decision-reason" className="text-xs font-semibold text-green-950 uppercase text-[11px]">
                  Determination Reason <span className="text-brick">*</span>
                </label>
                <span className="text-[10px] font-mono text-ink-subtle">Mandatory audit field</span>
              </div>
              <textarea
                id="decision-reason"
                rows={3}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Specify the clinical, geographic, or financial rationale for this determination..."
                className="w-full text-xs p-2 bg-paper-subtle border border-hairline focus:bg-surface focus:border-green-800 outline-none font-sans"
              />
            </div>

            {/* Optional Notes */}
            <div className="space-y-1">
              <label htmlFor="decision-notes" className="text-xs font-semibold text-ink-muted uppercase text-[11px] block">
                Internal Investigator Notes (Optional)
              </label>
              <textarea
                id="decision-notes"
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add internal cross-references or assigned reviewer instructions..."
                className="w-full text-xs p-2 bg-paper-subtle border border-hairline focus:bg-surface focus:border-green-800 outline-none font-sans"
              />
            </div>

            {/* Error Message */}
            {errorMsg && (
              <div className="p-2 bg-brick-soft border border-brick/40 text-brick text-xs font-mono">
                {errorMsg}
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-hairline">
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="px-3.5 py-1.5 bg-paper border border-hairline text-xs text-ink hover:bg-paper-subtle transition-colors"
                >
                  Cancel
                </button>
              </Dialog.Close>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-4 py-1.5 bg-green-900 text-ink-inverse text-xs font-semibold hover:bg-green-800 transition-colors disabled:opacity-50"
              >
                {isSubmitting ? 'Recording...' : 'Submit Human Decision'}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
