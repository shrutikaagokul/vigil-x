import React from 'react';

export const DashboardDetectionIntelligence: React.FC = () => {
  const pillars = [
    {
      title: 'Rule Engine (R01–R10)',
      tag: 'Deterministic Logic',
      desc: '10 clinical coding and billing violation patterns spanning unbundled procedures, phantom services, and duplicate billing.',
      signal: '176 Active Alerts Fired',
    },
    {
      title: 'Claim-Level Machine Learning',
      tag: 'Supervised LightGBM',
      desc: 'Supervised gradient boosted decision tree evaluating line-level procedure characteristics and claim anomalies.',
      signal: '0.942 ROC-AUC Ground Truth Benchmark',
    },
    {
      title: 'Provider Anomaly Profiling',
      tag: 'Unsupervised Outlier',
      desc: 'Isolation Forest anomaly detection benchmarking provider billing velocity against specialty peer distributions.',
      signal: 'Top 5% Statistical Outliers Flagged',
    },
    {
      title: 'Network Intelligence',
      tag: 'Graph Projection & Louvain',
      desc: 'Bipartite provider graph projections identifying organized collusion rings and entity-resolved shared identifiers.',
      signal: '5 Multi-Entity Collusion Rings',
    },
    {
      title: 'Temporal Dynamics & Velocity',
      tag: 'Timing & Trajectory',
      desc: 'Transit velocity tracking, weekend-to-weekday service shifts, and impossible travel times between clinical facilities.',
      signal: 'Impossible Transit Velocities Flagged',
    },
    {
      title: 'Future-Risk Forecasting',
      tag: '30 / 60 / 90-Day Projections',
      desc: 'Forward-looking exposure velocity modeling estimating financial acceleration if suspect patterns remain unworked.',
      signal: '+$384K Projected 30-Day Risk Escalation',
    },
  ];

  return (
    <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-6 shadow-xs">
      <div className="border-b border-[#E0E8DF] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 className="font-serif text-2xl font-bold text-[#183B2A] tracking-tight">
            Detection Intelligence
          </h2>
          <p className="text-base text-[#68766B] mt-1">
            Synthesis of deterministic rules, machine learning classifiers, graph topology, and temporal forecasting.
          </p>
        </div>
        <span className="text-xs font-mono font-semibold px-3 py-1 rounded bg-[#E8F2E8] text-[#285239] border border-[#B8D2B8] self-start sm:self-auto">
          Unified Risk Architecture
        </span>
      </div>

      {/* Clearly Separated Text-Based Sections (Zero Icons) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {pillars.map((p, idx) => (
          <div
            key={idx}
            className="p-6 bg-[#F5F8F4] border border-[#E0E8DF] rounded-xl flex flex-col justify-between hover:bg-[#E8F2E8]/30 transition-colors space-y-4"
          >
            <div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-mono font-semibold uppercase text-[#285239] bg-white px-2 py-0.5 rounded border border-[#E0E8DF]">
                  {p.tag}
                </span>
                <span className="text-xs font-mono text-[#68766B]">
                  Pillar 0{idx + 1}
                </span>
              </div>
              <h3 className="text-lg font-bold text-[#183B2A] mt-2.5">
                {p.title}
              </h3>
              <p className="text-[15px] text-[#68766B] mt-2 leading-relaxed">
                {p.desc}
              </p>
            </div>

            <div className="pt-3 border-t border-[#E0E8DF] flex flex-col text-sm font-mono space-y-1">
              <span className="text-xs text-[#8B998E] uppercase tracking-wider">Detection Signal:</span>
              <span className="font-semibold text-[#183B2A]">
                {p.signal}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
