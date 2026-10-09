import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { NavTabs } from './NavTabs';

export const Masthead: React.FC = () => {
  const navigate = useNavigate();

  return (
    <header
      className="sticky top-0 z-30 w-full h-20 bg-white text-[#24352A] select-none border-b border-[#E0E8DF] shadow-[0_1px_3px_rgba(0,0,0,0.02)]"
      role="banner"
    >
      <div className="w-full h-full px-8 flex items-center justify-between">
        {/* Left: Brand "Vigil-X" and Top Navigation */}
        <div className="flex items-center space-x-10 h-full">
          <Link
            to="/"
            className="flex items-center gap-2 group outline-none focus-visible:ring-2 focus-visible:ring-[#477A58]"
            aria-label="Vigil-X Home"
          >
            <span className="font-serif text-2xl font-bold tracking-tight text-[#183B2A]">
              Vigil-X
            </span>
            <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-[#E8F2E8] text-[#285239] font-semibold border border-[#B8D2B8]">
              Nexus
            </span>
          </Link>

          <NavTabs />
        </div>

        {/* Right: Status and Action Button */}
        <div className="flex items-center space-x-5">
          <div
            className="flex items-center gap-3 px-4 py-2 rounded-lg bg-[#F5F8F4] border border-[#E0E8DF] text-sm font-medium text-[#285239]"
            aria-label="System status: Healthy"
          >
            <span className="font-mono font-semibold">Healthy</span>
            <span className="text-[#B8D2B8]">|</span>
            <span className="text-[#68766B] font-mono text-xs hidden sm:inline">Healthcare FWA Intelligence</span>
          </div>

          <button
            type="button"
            onClick={() => navigate('/ingest')}
            className="bg-[#477A58] hover:bg-[#285239] text-white font-medium text-sm px-5 py-2.5 rounded-lg border border-[#356345] shadow-xs transition-colors outline-none focus-visible:ring-2 focus-visible:ring-[#477A58]"
          >
            Load batch
          </button>
        </div>
      </div>
    </header>
  );
};
