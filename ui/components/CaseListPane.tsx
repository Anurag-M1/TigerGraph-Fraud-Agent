'use client';

import React from 'react';
import { Gauge, MessageSquareWarning, UserSearch } from 'lucide-react';
import { CaseSummaryItem } from '@/lib/types';

export type FilterCategory =
  | 'all'
  | 'risk_score'
  | 'customer_report'
  | 'analyst_request'
  | 'fraud'
  | 'legitimate'
  | 'uncertain';

interface CaseListPaneProps {
  cases: CaseSummaryItem[];
  selectedCaseId: string;
  onSelectCase: (caseId: string) => void;
  activeFilter: FilterCategory;
  onFilterChange: (filter: FilterCategory) => void;
}

export function CaseListPane({
  cases,
  selectedCaseId,
  onSelectCase,
  activeFilter,
  onFilterChange,
}: CaseListPaneProps) {
  // Count by trigger & verdict
  const countRisk = cases.filter((c) => c.trigger_type === 'risk_score').length;
  const countCustomer = cases.filter((c) => c.trigger_type === 'customer_report').length;
  const countAnalyst = cases.filter((c) => c.trigger_type === 'analyst_request').length;

  const filteredCases = cases.filter((c) => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'risk_score') return c.trigger_type === 'risk_score';
    if (activeFilter === 'customer_report') return c.trigger_type === 'customer_report';
    if (activeFilter === 'analyst_request') return c.trigger_type === 'analyst_request';
    if (activeFilter === 'fraud') return c.verdict === 'fraud';
    if (activeFilter === 'legitimate') return c.verdict === 'legitimate';
    if (activeFilter === 'uncertain') return c.verdict === 'uncertain';
    return true;
  });

  return (
    <div className="w-[340px] bg-[#10161D] border-r border-[#1E2933] flex flex-col h-[calc(100vh-56px)] select-none">
      {/* Pane Header */}
      <div className="p-3 border-b border-[#1E2933] flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-[#E8EEF4]">
            Cases
          </span>
          <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-[#0D1319] border border-[#1E2933] text-[#9AA8B5]">
            {filteredCases.length} / {cases.length}
          </span>
        </div>

        {/* Filter Chips Row */}
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => onFilterChange('all')}
            className={`text-[11px] px-2 py-0.5 rounded-[6px] border transition-colors ${
              activeFilter === 'all'
                ? 'text-[#F5A524] border-[#F5A524] bg-[#161E27]'
                : 'text-[#9AA8B5] border-[#1E2933] bg-[#0D1319] hover:border-[#2A3642]'
            }`}
          >
            All
          </button>
          <button
            onClick={() => onFilterChange('risk_score')}
            className={`text-[11px] px-2 py-0.5 rounded-[6px] border transition-colors flex items-center gap-1 ${
              activeFilter === 'risk_score'
                ? 'text-[#F5A524] border-[#F5A524] bg-[#161E27]'
                : 'text-[#9AA8B5] border-[#1E2933] bg-[#0D1319] hover:border-[#2A3642]'
            }`}
          >
            <span>risk_score</span>
            <span className="font-mono text-[10px] text-[#5C6B7A]">{countRisk}</span>
          </button>
          <button
            onClick={() => onFilterChange('customer_report')}
            className={`text-[11px] px-2 py-0.5 rounded-[6px] border transition-colors flex items-center gap-1 ${
              activeFilter === 'customer_report'
                ? 'text-[#F5A524] border-[#F5A524] bg-[#161E27]'
                : 'text-[#9AA8B5] border-[#1E2933] bg-[#0D1319] hover:border-[#2A3642]'
            }`}
          >
            <span>customer_report</span>
            <span className="font-mono text-[10px] text-[#5C6B7A]">{countCustomer}</span>
          </button>
          <button
            onClick={() => onFilterChange('analyst_request')}
            className={`text-[11px] px-2 py-0.5 rounded-[6px] border transition-colors flex items-center gap-1 ${
              activeFilter === 'analyst_request'
                ? 'text-[#F5A524] border-[#F5A524] bg-[#161E27]'
                : 'text-[#9AA8B5] border-[#1E2933] bg-[#0D1319] hover:border-[#2A3642]'
            }`}
          >
            <span>analyst_request</span>
            <span className="font-mono text-[10px] text-[#5C6B7A]">{countAnalyst}</span>
          </button>
          <button
            onClick={() => onFilterChange('fraud')}
            className={`text-[11px] px-2 py-0.5 rounded-[6px] border transition-colors ${
              activeFilter === 'fraud'
                ? 'text-[#F5A524] border-[#F5A524] bg-[#161E27]'
                : 'text-[#9AA8B5] border-[#1E2933] bg-[#0D1319] hover:border-[#2A3642]'
            }`}
          >
            fraud
          </button>
          <button
            onClick={() => onFilterChange('legitimate')}
            className={`text-[11px] px-2 py-0.5 rounded-[6px] border transition-colors ${
              activeFilter === 'legitimate'
                ? 'text-[#F5A524] border-[#F5A524] bg-[#161E27]'
                : 'text-[#9AA8B5] border-[#1E2933] bg-[#0D1319] hover:border-[#2A3642]'
            }`}
          >
            legitimate
          </button>
          <button
            onClick={() => onFilterChange('uncertain')}
            className={`text-[11px] px-2 py-0.5 rounded-[6px] border transition-colors ${
              activeFilter === 'uncertain'
                ? 'text-[#F5A524] border-[#F5A524] bg-[#161E27]'
                : 'text-[#9AA8B5] border-[#1E2933] bg-[#0D1319] hover:border-[#2A3642]'
            }`}
          >
            uncertain
          </button>
        </div>
      </div>

      {/* Case Rows List */}
      <div className="flex-1 overflow-y-auto divide-y divide-[#1E2933]">
        {filteredCases.map((c) => {
          const isSelected = selectedCaseId === c.case_id;

          // Trigger Icon
          let TriggerIcon = Gauge;
          if (c.trigger_type === 'customer_report') TriggerIcon = MessageSquareWarning;
          else if (c.trigger_type === 'analyst_request') TriggerIcon = UserSearch;

          // Verdict Dot
          let verdictColor = '#F5A524'; // amber for uncertain
          if (c.verdict === 'fraud') verdictColor = '#E5484D'; // red
          else if (c.verdict === 'legitimate') verdictColor = '#30A46C'; // green

          // Format date
          const dateStr = c.opened_at ? c.opened_at.replace(' ', ' · ') : '2016-12-01';

          return (
            <div
              key={c.case_id}
              onClick={() => onSelectCase(c.case_id)}
              className={`h-[72px] px-3.5 py-2 cursor-pointer transition-colors flex flex-col justify-between relative ${
                isSelected
                  ? 'bg-[#161E27]'
                  : 'hover:bg-[#161E27]/60'
              }`}
            >
              {/* Selected amber left-edge 2px indicator */}
              {isSelected && (
                <span className="absolute left-0 top-0 bottom-0 w-[2px] bg-[#F5A524]" />
              )}

              {/* Row 1: Case ID, Trigger Icon, Verdict Dot */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[13px] font-semibold text-[#E8EEF4]">
                    {c.case_id}
                  </span>
                  <TriggerIcon className="w-3.5 h-3.5 text-[#5C6B7A]" strokeWidth={1.5} />
                </div>
                <div className="flex items-center gap-1.5">
                  {c.sar_file && (
                    <span className="font-mono text-[10px] text-[#E5484D] px-1 py-0.2 bg-[#E5484D]/10 border border-[#E5484D]/30 rounded">
                      SAR
                    </span>
                  )}
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: verdictColor }}
                    title={`Verdict: ${c.verdict}`}
                  />
                </div>
              </div>

              {/* Row 2: risk_score or —, exposure right-aligned */}
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-[#5C6B7A]">
                  {c.risk_score !== null && c.risk_score !== undefined
                    ? `risk ${c.risk_score.toFixed(2)}`
                    : '—'}
                </span>
                <span className="font-mono font-medium text-[#9AA8B5]">
                  ${c.exposure_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>

              {/* Row 3: Pattern chip if set + date */}
              <div className="flex items-center justify-between text-[11px]">
                {c.pattern && c.pattern !== 'none' ? (
                  <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#0D1319] border border-[#1E2933] text-[#9AA8B5] truncate max-w-[170px]">
                    {c.pattern}
                  </span>
                ) : (
                  <span className="text-[#5C6B7A] text-[10px]">no pattern</span>
                )}
                <span className="font-mono text-[10px] text-[#5C6B7A]">
                  {dateStr}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
