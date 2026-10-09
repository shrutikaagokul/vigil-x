import React from 'react';
import { NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getHealth } from '@/services/healthService';

interface NavSection {
  title: string;
  items: {
    label: string;
    to: string;
    badge?: string;
    exact?: boolean;
  }[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: 'OVERVIEW',
    items: [
      {
        label: 'Command Center',
        to: '/',
        exact: true,
      },
    ],
  },
  {
    title: 'DETECTION INTELLIGENCE',
    items: [
      {
        label: 'Rule Engine (R01-R10)',
        to: '/rules',
        badge: '10 Rules',
      },
      {
        label: 'Claim Intelligence',
        to: '/claims',
      },
      {
        label: 'Network Intelligence',
        to: '/networks/NET-RING-001',
        badge: 'Rings',
      },
      {
        label: 'Temporal Intelligence',
        to: '/temporal',
        badge: '30-90d',
      },
    ],
  },
  {
    title: 'INVESTIGATION',
    items: [
      {
        label: 'SIU Priority Queue',
        to: '/queue',
        badge: 'Ranked',
      },
      {
        label: 'Case Investigations',
        to: '/cases',
      },
      {
        label: 'Investigation Assistant',
        to: '/assistant',
        badge: 'GenAI',
      },
    ],
  },
  {
    title: 'GOVERNANCE',
    items: [
      {
        label: 'Model Evaluation',
        to: '/evaluation',
        badge: 'Ground Truth',
      },
      {
        label: 'Audit Trail',
        to: '/audit',
      },
    ],
  },
];

export const Sidebar: React.FC = () => {
  const { data: health } = useQuery({
    queryKey: ['system-health'],
    queryFn: () => getHealth(),
    staleTime: 30000,
  });

  return (
    <aside
      className="w-72 bg-[#183B2A] border-r border-[#285239] flex flex-col h-screen sticky top-0 select-none z-40 shrink-0 text-[#E8F2E8]"
      aria-label="Sidebar Navigation"
    >
      {/* Brand Header */}
      <div className="h-20 px-5 border-b border-[#285239] flex items-center gap-3 bg-[#183B2A]">
        <img
          src="/vigilx-logo.png"
          alt="VIGIL-X Medical Intelligence Emblem"
          className="h-12 w-auto object-contain shrink-0 select-none"
          style={{ height: '48px', width: 'auto', objectFit: 'contain' }}
        />
        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-2 leading-none">
            <span className="font-serif font-bold text-xl tracking-tight text-white">Vigil-X</span>
            <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-[#285239] text-[#D5E6D5] font-semibold border border-[#356345]">Nexus</span>
          </div>
          <span className="text-xs text-[#B8D2B8] mt-1.5 tracking-wide truncate">Healthcare Fraud Intelligence</span>
        </div>
      </div>

      {/* Nav Section Links */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-7">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className="space-y-2">
            <div className="px-3 pb-1 text-xs font-mono uppercase tracking-wider text-[#8FB88F] font-semibold">
              {section.title}
            </div>
            <div className="space-y-1">
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.exact}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3.5 py-3 rounded-lg text-[15px] font-medium transition-all outline-none focus-visible:ring-2 focus-visible:ring-[#B8D2B8] ${
                      isActive
                        ? 'bg-[#E8F2E8] text-[#183B2A] font-semibold shadow-xs'
                        : 'text-[#D5E6D5] hover:text-white hover:bg-[#285239]/70'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <span className="truncate">{item.label}</span>
                      {item.badge && (
                        <span
                          className={`text-xs font-mono px-2 py-0.5 rounded shrink-0 font-medium ${
                            isActive
                              ? 'bg-[#285239] text-[#E8F2E8]'
                              : 'bg-[#285239]/80 text-[#B8D2B8] border border-[#356345]'
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* System Status Footer */}
      <div className="p-4 border-t border-[#285239] bg-[#132F21] space-y-2.5">
        <div className="flex items-center justify-between px-3 py-2 rounded-md bg-[#183B2A] border border-[#285239]">
          <span className="text-xs font-medium text-white">
            System: {health?.status ? health.status.toUpperCase() : 'OPERATIONAL'}
          </span>
          <span className="text-xs font-mono text-[#B8D2B8]">
            {health?.database ? `${health.database} Live` : 'SQLite live'}
          </span>
        </div>

        <div className="flex items-center justify-between text-xs text-[#8FB88F] px-1 font-mono">
          <span>Database: app.db</span>
          <span className="text-[#B8D2B8]">Queue Active</span>
        </div>
      </div>
    </aside>
  );
};
