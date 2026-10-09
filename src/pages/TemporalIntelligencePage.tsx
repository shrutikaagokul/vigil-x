import React from 'react';
import { Link } from 'react-router-dom';

export const TemporalIntelligencePage: React.FC = () => {
  const temporalAlerts = [
    {
      providerId: 'P0030',
      caseId: 'CASE-PRV-P0030',
      name: 'Dr. Provider_30',
      anomalyType: 'Billing Volume Burst (R10)',
      velocity: '4.8x baseline volume',
      exposure: '$114,980.08',
      riskTier: 'HIGH',
      trajectory: '+42% 30-day projected escalation',
      description: 'Exponential spike in claim volume over 14 calendar days exceeding 3 standard deviations from historical rolling mean.',
    },
    {
      providerId: 'P0012',
      caseId: 'CASE-PRV-P0012',
      name: 'Dr. Provider_12',
      anomalyType: 'Impossible Timing (R06)',
      velocity: '184 mph transit speed',
      exposure: '$38,240.00',
      riskTier: 'CRITICAL',
      trajectory: '+18% 30-day projected escalation',
      description: 'Consecutive same-day clinical encounters billed at clinic sites 162 miles apart with only 45 minutes between service timestamps.',
    },
    {
      providerId: 'P0045',
      caseId: 'CASE-PRV-P0045',
      name: 'Dr. Provider_45',
      anomalyType: 'Daily Face-Time Cap Overrun (R05)',
      velocity: '31.5 clinical hours / day',
      exposure: '$29,450.00',
      riskTier: 'HIGH',
      trajectory: 'Steady elevated plateau',
      description: 'Cumulative evaluation and management service times exceeded physical 24-hour daily human capacity on 6 consecutive billing dates.',
    },
  ];

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-[#285239] font-bold bg-[#E8F2E8] px-3 py-1 rounded border border-[#B8D2B8]">
              Behavioral & Trajectory Signals
            </span>
            <span className="text-xs text-[#68766B] font-mono">Temporal Intelligence</span>
          </div>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-[#183B2A] tracking-tight">
            Temporal & Velocity Intelligence
          </h1>
          <p className="text-base text-[#68766B] mt-1.5 max-w-4xl leading-relaxed">
            Monitor clinical transit velocities, billing volume bursts, weekend service shifts, and forward-looking 30/60/90-day risk escalation projections.
          </p>
        </div>

        <div className="p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg text-right shrink-0">
          <div className="text-xs text-[#68766B] uppercase font-mono font-semibold">Temporal Signals</div>
          <div className="font-serif text-3xl font-bold text-[#B45309] tabular-nums mt-0.5">
            61 Alerts (R06 & R10)
          </div>
        </div>
      </div>

      {/* Trajectory Forecast Horizon Sections (Zero Icons) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-3 shadow-xs">
          <span className="text-xs font-bold uppercase font-mono text-[#68766B] block">
            30-Day Exposure Horizon
          </span>
          <div className="font-serif text-3xl font-bold text-[#285239]">
            +$384,000
          </div>
          <p className="text-sm text-[#68766B] leading-relaxed">
            Projected near-term overpayment accumulation across top 10 prioritized providers if unaddressed.
          </p>
        </div>

        <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-3 shadow-xs">
          <span className="text-xs font-bold uppercase font-mono text-[#68766B] block">
            60-Day Exposure Horizon
          </span>
          <div className="font-serif text-3xl font-bold text-[#B45309]">
            +$820,000
          </div>
          <p className="text-sm text-[#68766B] leading-relaxed">
            Mid-term acceleration curve incorporating ring referral recirculation and new patient recruitment.
          </p>
        </div>

        <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-3 shadow-xs">
          <span className="text-xs font-bold uppercase font-mono text-[#68766B] block">
            90-Day Exposure Horizon
          </span>
          <div className="font-serif text-3xl font-bold text-[#B91C1C]">
            +$1,340,000
          </div>
          <p className="text-sm text-[#68766B] leading-relaxed">
            Full quarterly bust-out risk ceiling based on current week-over-week velocity multipliers.
          </p>
        </div>
      </div>

      {/* Flagged Velocity Signals */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-6 shadow-xs">
        <div className="border-b border-[#E0E8DF] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="font-serif text-2xl font-bold text-[#183B2A] tracking-tight">
              Active Velocity and Impossible Timing Anomaly Signals
            </h2>
            <p className="text-base text-[#68766B] mt-1">
              Live case files exhibiting severe temporal departures from physical clinical reality.
            </p>
          </div>
          <span className="text-xs font-mono px-3 py-1 rounded bg-[#E8F2E8] text-[#285239] border border-[#B8D2B8] font-semibold self-start sm:self-auto">
            Live Signal Feed
          </span>
        </div>

        <div className="space-y-4">
          {temporalAlerts.map((alert) => (
            <div
              key={alert.caseId}
              className="p-6 bg-[#F5F8F4] border border-[#E0E8DF] rounded-xl flex flex-col lg:flex-row lg:items-center justify-between gap-6 hover:border-[#B8D2B8] transition-colors"
            >
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="font-bold text-lg text-[#183B2A]">{alert.name}</span>
                  <span className="font-mono text-xs bg-white px-2.5 py-0.5 rounded border border-[#E0E8DF] text-[#285239] font-semibold">
                    {alert.caseId}
                  </span>
                  <span className="text-xs font-mono px-2.5 py-0.5 rounded bg-[#FEE2E2] border border-[#FCA5A5] text-[#B91C1C] font-semibold">
                    {alert.anomalyType}
                  </span>
                </div>
                <p className="text-base text-[#68766B] leading-relaxed">
                  {alert.description}
                </p>
                <div className="flex flex-wrap items-center gap-6 text-sm font-mono pt-1 text-[#68766B]">
                  <span>Velocity: <strong className="text-[#285239] font-bold">{alert.velocity}</strong></span>
                  <span>Exposure: <strong className="text-[#183B2A] font-bold">{alert.exposure}</strong></span>
                  <span>Trend: <strong className="text-[#B45309] font-bold">{alert.trajectory}</strong></span>
                </div>
              </div>

              <Link
                to={`/cases/${alert.caseId}`}
                className="px-5 py-2.5 bg-[#E8F2E8] hover:bg-[#477A58] text-[#285239] hover:text-white border border-[#B8D2B8] text-sm font-semibold rounded-lg transition-colors shrink-0 shadow-xs"
              >
                Investigate Case
              </Link>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
