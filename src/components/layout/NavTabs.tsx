import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';

interface NavItem {
  readonly label: string;
  readonly to: string;
  readonly exact?: boolean;
}

const NAV_ITEMS: readonly NavItem[] = [
  { label: 'Dashboard', to: '/', exact: true },
  { label: 'Queue', to: '/queue' },
  { label: 'Networks', to: '/networks/NET-RING-001' },
  { label: 'Evaluation', to: '/evaluation' },
];

export const NavTabs: React.FC = () => {
  const location = useLocation();

  return (
    <nav className="flex items-center h-full space-x-6" aria-label="Main Navigation">
      {NAV_ITEMS.map((item) => {
        const isNetworkTab = item.label === 'Networks';
        const isActive = item.exact
          ? location.pathname === item.to
          : isNetworkTab
          ? location.pathname.startsWith('/networks')
          : location.pathname.startsWith(item.to);

        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            aria-current={isActive ? 'page' : undefined}
            className={`relative h-full flex items-center text-[1rem] font-medium tracking-normal transition-colors outline-none focus-visible:outline-2 focus-visible:outline-[#A9CFB0] ${
              isActive
                ? 'text-white'
                : 'text-[#A9CFB0] hover:text-white'
            }`}
          >
            {item.label}
            {isActive && (
              <span
                className="absolute bottom-0 left-0 right-0 h-[3px] bg-[#A9CFB0]"
                aria-hidden="true"
              />
            )}
          </NavLink>
        );
      })}
    </nav>
  );
};
