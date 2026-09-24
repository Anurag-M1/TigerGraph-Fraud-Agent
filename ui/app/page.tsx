'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { TopBar } from '@/components/TopBar';
import { LeftRail, NavView } from '@/components/LeftRail';
import { CaseListPane, FilterCategory } from '@/components/CaseListPane';
import { CaseHeader } from '@/components/CaseHeader';
import { OverviewTab } from '@/components/tabs/OverviewTab';
import { TimelineTab } from '@/components/tabs/TimelineTab';
import { GraphTab } from '@/components/tabs/GraphTab';
import { ActionsTab } from '@/components/tabs/ActionsTab';
import { EvidenceTab } from '@/components/tabs/EvidenceTab';
import { SarTab } from '@/components/tabs/SarTab';
import { CaseSummaryItem, CaseFileAnswer, CaseMetadata, TimelineStepItem } from '@/lib/types';

export type TabKey = 'overview' | 'timeline' | 'graph' | 'evidence' | 'actions' | 'sar';

export default function FraudConsolePage() {
  const [activeNav, setActiveNav] = useState<NavView>('cases');
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [activeFilter, setActiveFilter] = useState<FilterCategory>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Cases state
  const [cases, setCases] = useState<CaseSummaryItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('HHG-014');
  const [caseDetail, setCaseDetail] = useState<{
    case_id: string;
    metadata: CaseMetadata;
    answer: CaseFileAnswer;
    timeline_steps: TimelineStepItem[];
  } | null>(null);
  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // 1. Fetch case list on mount
  useEffect(() => {
    fetch('/api/cases')
      .then((res) => res.json())
      .then((data: CaseSummaryItem[]) => {
        setCases(data);
        setLoadingCases(false);
        // Default select HHG-014 if present, else first
        if (data.some((c) => c.case_id === 'HHG-014')) {
          setSelectedCaseId('HHG-014');
        } else if (data.length > 0) {
          setSelectedCaseId(data[0].case_id);
        }
      })
      .catch((err) => {
        console.error('Failed to load cases:', err);
        setLoadingCases(false);
      });
  }, []);

  // 2. Fetch case detail when selectedCaseId changes
  useEffect(() => {
    if (!selectedCaseId) return;
    setLoadingDetail(true);

    fetch(`/api/cases/${selectedCaseId}`)
      .then((res) => res.json())
      .then((data) => {
        setCaseDetail(data);
        setLoadingDetail(false);
      })
      .catch((err) => {
        console.error(`Failed to load case ${selectedCaseId}:`, err);
        setLoadingDetail(false);
      });
  }, [selectedCaseId]);

  // Keyboard shortcut: Cmd+K focuses search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        const input = document.querySelector('input[type="text"]') as HTMLInputElement;
        input?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Filter cases based on search input
  const filteredCases = useMemo(() => {
    if (!searchQuery.trim()) return cases;
    const q = searchQuery.toLowerCase();
    return cases.filter(
      (c) =>
        c.case_id.toLowerCase().includes(q) ||
        c.card_id.toLowerCase().includes(q) ||
        c.trigger_text.toLowerCase().includes(q) ||
        (c.pattern && c.pattern.toLowerCase().includes(q))
    );
  }, [cases, searchQuery]);

  // Handle Nav clicks
  function handleNavChange(view: NavView) {
    setActiveNav(view);
    if (view === 'graph') {
      setActiveTab('graph');
    } else if (view === 'sars') {
      setActiveTab('sar');
    } else if (view === 'runs') {
      setActiveTab('timeline');
    } else if (view === 'memory') {
      setActiveTab('overview');
    }
  }

  const TABS: { id: TabKey; label: string }[] = [
    { id: 'overview', label: 'OVERVIEW' },
    { id: 'timeline', label: 'TIMELINE' },
    { id: 'graph', label: 'GRAPH' },
    { id: 'evidence', label: 'EVIDENCE' },
    { id: 'actions', label: 'ACTIONS' },
    { id: 'sar', label: 'SAR' },
  ];

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0A0E13] text-[#E8EEF4] select-none">
      {/* 1. Top Bar (56px) */}
      <TopBar searchQuery={searchQuery} onSearchChange={setSearchQuery} />

      {/* 2. Main Shell Layout: Left Rail (60px) + Case List Pane (340px) + Workspace (Fluid) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Rail (60px) */}
        <LeftRail activeView={activeNav} onViewChange={handleNavChange} />

        {/* Case List Pane (340px) */}
        <CaseListPane
          cases={filteredCases}
          selectedCaseId={selectedCaseId}
          onSelectCase={(id) => setSelectedCaseId(id)}
          activeFilter={activeFilter}
          onFilterChange={setActiveFilter}
        />

        {/* Workspace (Flex-1) */}
        <main className="flex-1 flex flex-col bg-[#0A0E13] overflow-y-auto">
          {loadingDetail || !caseDetail ? (
            /* Skeleton Shimmer Loading State */
            <div className="p-8 flex flex-col gap-6 animate-pulse">
              <div className="h-28 bg-[#10161D] border border-[#1E2933] rounded-[8px]" />
              <div className="h-10 bg-[#10161D] border border-[#1E2933] rounded-[6px]" />
              <div className="grid grid-cols-12 gap-4">
                <div className="col-span-8 h-80 bg-[#10161D] border border-[#1E2933] rounded-[8px]" />
                <div className="col-span-4 h-80 bg-[#10161D] border border-[#1E2933] rounded-[8px]" />
              </div>
            </div>
          ) : (
            <>
              {/* Case Header Block */}
              <CaseHeader
                metadata={caseDetail.metadata}
                answer={caseDetail.answer}
              />

              {/* Navigation Tabs Header (12px uppercase, 600, active = amber underline 2px) */}
              <div className="bg-[#10161D] border-b border-[#1E2933] px-5 flex items-center gap-6 sticky top-0 z-30">
                {TABS.map((tab) => {
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`py-3 text-[12px] font-semibold tracking-wider transition-colors relative ${
                        isActive
                          ? 'text-[#E8EEF4]'
                          : 'text-[#5C6B7A] hover:text-[#9AA8B5]'
                      }`}
                    >
                      {tab.label}
                      {/* Active 2px amber underline */}
                      {isActive && (
                        <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#F5A524]" />
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Tab Contents Pane */}
              <div className="flex-1">
                {activeTab === 'overview' && (
                  <OverviewTab
                    answer={caseDetail.answer}
                    metadata={caseDetail.metadata}
                  />
                )}
                {activeTab === 'timeline' && (
                  <TimelineTab
                    steps={caseDetail.timeline_steps}
                    caseId={caseDetail.case_id}
                  />
                )}
                {activeTab === 'graph' && (
                  <GraphTab caseId={caseDetail.case_id} />
                )}
                {activeTab === 'evidence' && (
                  <EvidenceTab answer={caseDetail.answer} />
                )}
                {activeTab === 'actions' && (
                  <ActionsTab
                    answer={caseDetail.answer}
                    caseId={caseDetail.case_id}
                  />
                )}
                {activeTab === 'sar' && (
                  <SarTab
                    answer={caseDetail.answer}
                    caseId={caseDetail.case_id}
                  />
                )}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
