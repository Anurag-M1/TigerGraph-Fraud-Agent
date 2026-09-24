'use client';

import React from 'react';
import {
  Inbox,
  Waypoints,
  History,
  FileText,
  Activity,
  Settings,
} from 'lucide-react';

export type NavView = 'cases' | 'graph' | 'memory' | 'sars' | 'runs' | 'settings';

interface LeftRailProps {
  activeView: NavView;
  onViewChange: (view: NavView) => void;
}

const NAV_ITEMS: { id: NavView; label: string; icon: React.ComponentType<{ className?: string; strokeWidth?: number }> }[] = [
  { id: 'cases', label: 'Cases (Inbox)', icon: Inbox },
  { id: 'graph', label: 'Graph Explorer (Waypoints)', icon: Waypoints },
  { id: 'memory', label: 'Case Memory (History)', icon: History },
  { id: 'sars', label: 'SARs (FileText)', icon: FileText },
  { id: 'runs', label: 'Runs (Activity)', icon: Activity },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function LeftRail({ activeView, onViewChange }: LeftRailProps) {
  return (
    <aside className="w-[60px] bg-[#10161D] border-r border-[#1E2933] flex flex-col items-center py-3 select-none z-30">
      <div className="flex flex-col w-full gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive = activeView === item.id;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => onViewChange(item.id)}
              title={item.label}
              className={`w-full h-11 flex items-center justify-center relative transition-colors group ${
                isActive
                  ? 'text-[#F5A524] bg-[#161E27]'
                  : 'text-[#5C6B7A] hover:text-[#9AA8B5] hover:bg-[#161E27]'
              }`}
            >
              {/* Active 2px amber left-edge indicator */}
              {isActive && (
                <span className="absolute left-0 top-0 bottom-0 w-[2px] bg-[#F5A524]" />
              )}
              <Icon className="w-[18px] h-[18px]" strokeWidth={1.5} />
            </button>
          );
        })}
      </div>
    </aside>
  );
}
