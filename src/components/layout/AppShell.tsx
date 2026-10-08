import React from 'react';
import { Outlet } from 'react-router-dom';
import { Masthead } from './Masthead';

export const AppShell: React.FC = () => {
  const isDev = import.meta.env.DEV;

  return (
    <div className="min-h-screen flex flex-col bg-[#F3F8F4] text-[#14201A] font-sans antialiased overflow-x-hidden">
      <Masthead />
      <div className="flex-1 w-full">
        <Outlet />
      </div>
      <footer className="w-full border-t border-[#D3E0D6] py-3.5 px-[3rem] text-[0.8125rem] text-[#4F5F55] select-none">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span>Synthetic data only</span>
          <span>·</span>
          <span>Sample values</span>
          <span>·</span>
          <span>Prioritized for human investigation</span>
          {isDev && (
            <>
              <span>·</span>
              <span className="font-mono text-[0.75rem] text-[#2A5A3F] font-semibold">Mock API</span>
            </>
          )}
        </div>
      </footer>
    </div>
  );
};
