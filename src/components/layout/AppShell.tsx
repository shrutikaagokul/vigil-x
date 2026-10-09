import React from 'react';
import { Outlet } from 'react-router-dom';
import { Masthead } from './Masthead';
import { Sidebar } from './Sidebar';

export const AppShell: React.FC = () => {
  const isDev = import.meta.env.DEV;

  return (
    <div className="h-screen flex bg-[#F5F8F4] text-[#24352A] font-sans antialiased overflow-hidden">
      {/* 1. Left Sidebar Navigation */}
      <Sidebar />

      {/* 2. Main Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#F5F8F4] h-screen overflow-y-auto">
        <Masthead />
        <main className="flex-1 w-full p-8 md:p-10 max-w-[1680px] mx-auto">
          <Outlet />
        </main>
        <footer className="w-full border-t border-[#E0E8DF] bg-white py-4 px-10 text-sm text-[#68766B] select-none shadow-[0_-1px_2px_rgba(0,0,0,0.02)]">
          <div className="flex flex-wrap items-center justify-between gap-y-2">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <span className="text-[#68766B] font-medium">Synthetic data only</span>
              <span className="text-[#B8D2B8]">|</span>
              <span>Sample values</span>
              <span className="text-[#B8D2B8]">|</span>
              <span className="text-[#285239] font-semibold">Prioritized for human investigation</span>
              {isDev && (
                <>
                  <span className="text-[#B8D2B8]">|</span>
                  <span className="font-mono text-xs text-[#285239] font-semibold bg-[#E8F2E8] px-2.5 py-0.5 rounded border border-[#B8D2B8]">
                    Mock API
                  </span>
                </>
              )}
            </div>
            <div className="font-mono text-xs text-[#8B998E]">
              ClaimShield Nexus | Healthcare Fraud, Waste & Abuse Intelligence
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};
