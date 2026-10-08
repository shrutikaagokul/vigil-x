import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { NavTabs } from './NavTabs';

export const Masthead: React.FC = () => {
  const navigate = useNavigate();

  return (
    <header
      className="sticky top-0 z-50 w-full h-[4rem] bg-[#12291C] text-white select-none border-b border-[#1B3A29]"
      role="banner"
    >
      <div className="w-full h-full px-[3rem] flex items-center justify-between">
        {/* Left: Brand "Vigil-X" and Navigation */}
        <div className="flex items-center space-x-10 h-full">
          <Link
            to="/"
            className="flex items-center group outline-none focus-visible:outline-2 focus-visible:outline-[#A9CFB0]"
            aria-label="Vigil-X Home"
          >
            <span className="font-serif text-[1.625rem] font-semibold tracking-normal text-white">
              Vigil-X
            </span>
          </Link>

          <NavTabs />
        </div>

        {/* Right: Status and Action Button */}
        <div className="flex items-center space-x-6">
          <div
            className="flex items-center space-x-2 text-[0.9375rem] font-medium text-[#A9CFB0]"
            aria-label="System status: Healthy"
          >
            <span className="text-[0.875rem] text-[#A9CFB0]" aria-hidden="true">●</span>
            <span>Healthy</span>
          </div>

          <button
            type="button"
            onClick={() => navigate('/ingest')}
            className="bg-[#A9CFB0] text-[#0B1A12] font-semibold text-[0.9375rem] px-4 py-2.5 rounded-[3px] hover:bg-[#c2e2c7] transition-colors outline-none focus-visible:outline-2 focus-visible:outline-white"
          >
            Load batch
          </button>
        </div>
      </div>
    </header>
  );
};
