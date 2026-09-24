'use client';

import React from 'react';
import { ShieldAlert, Search } from 'lucide-react';

interface TopBarProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

export function TopBar({ searchQuery, onSearchChange }: TopBarProps) {
  return (
    <header className="h-14 bg-[#0A0E13] border-b border-[#1E2933] flex items-center justify-between px-4 z-40 select-none">
      {/* Left: Brand */}
      <div className="flex items-center gap-2.5">
        <div className="w-7 h-7 rounded bg-[#10161D] border border-[#1E2933] flex items-center justify-center text-[#F5A524]">
          <ShieldAlert className="w-4 h-4" strokeWidth={1.5} />
        </div>
        <span className="text-[13px] font-semibold tracking-[0.08em] uppercase text-[#E8EEF4]">
          FRAUD CONSOLE
        </span>
      </div>

      {/* Center: Search input (Cmd+K) */}
      <div className="w-96 max-w-md relative">
        <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-[#5C6B7A]">
          <Search className="w-3.5 h-3.5" strokeWidth={1.5} />
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search case, card, txn id... (⌘K)"
          className="w-full bg-[#10161D] border border-[#1E2933] rounded-[6px] pl-9 pr-8 py-1.5 text-xs text-[#E8EEF4] font-mono placeholder:text-[#5C6B7A] focus:outline-none focus:border-[#F5A524] transition-colors"
        />
        <kbd className="absolute right-2.5 top-2 text-[10px] font-mono text-[#5C6B7A] bg-[#0D1319] border border-[#1E2933] px-1.5 py-0.5 rounded">
          ⌘K
        </kbd>
      </div>

      {/* Right: Env Badge + Avatar */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-[#0D1319] border border-[#1E2933] px-2.5 py-1 rounded-[6px]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#30A46C]" />
          <span className="font-mono text-[11px] text-[#9AA8B5]">
            HHGOA · TigerGraph
          </span>
        </div>
        <div
          className="w-7 h-7 rounded-full bg-[#161E27] border border-[#1E2933] flex items-center justify-center font-mono text-xs text-[#E8EEF4] font-medium"
          title="Senior Fraud Operations Lead (L2)"
        >
          AL
        </div>
      </div>
    </header>
  );
}
