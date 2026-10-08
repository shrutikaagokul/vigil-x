import React from 'react';

export const EvaluationLimitations: React.FC = () => {
  return (
    <div
      data-testid="eval-limitations"
      className="bg-white border border-[#D3E0D6] rounded-[3px] p-5 space-y-3"
    >
      <div className="border-b border-[#D3E0D6] pb-2">
        <h3 className="font-serif text-[1.125rem] font-semibold text-[#0B1A12]">
          Evaluation Methodology & Benchmark Limitations
        </h3>
        <p className="text-[0.8125rem] text-[#4F5F55]">
          Important technical context regarding benchmark evaluation scope and operational applicability.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[0.8125rem] text-[#4F5F55]">
        <div className="p-3 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[3px] space-y-1">
          <strong className="text-[#14201A] font-semibold block text-[0.875rem]">
            Synthetic Ground Truth Environment
          </strong>
          <p className="leading-relaxed">
            Evaluation metrics are computed against controlled synthetic claim datasets with mathematically modeled anomalous topologies (e.g. shared bank routing rings, kickback referral corridors, impossible velocity trips).
          </p>
        </div>

        <div className="p-3 bg-[#F3F8F4] border border-[#D3E0D6] rounded-[3px] space-y-1">
          <strong className="text-[#14201A] font-semibold block text-[0.875rem]">
            Human-in-the-Loop Triage Guardrails
          </strong>
          <p className="leading-relaxed">
            Prioritization scores assist human Special Investigation Unit (SIU) investigators in sequencing audit review. Benchmark performance should not be construed as automated fraud determination without clinical documentation audit.
          </p>
        </div>
      </div>
    </div>
  );
};
