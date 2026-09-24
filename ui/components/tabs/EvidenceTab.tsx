'use client';

import React, { useState } from 'react';
import { Database, FileText, MessageSquare, Globe, UserCheck } from 'lucide-react';
import { CaseFileAnswer } from '@/lib/types';

interface EvidenceTabProps {
  answer: CaseFileAnswer;
}

export function EvidenceTab({ answer }: EvidenceTabProps) {
  const c = answer.case || {};
  const evidenceList = c.evidence || [];
  const [selectedSource, setSelectedSource] = useState<string>('all');

  // Group evidence by source
  const sourceGroups: Record<string, number> = { all: evidenceList.length };
  evidenceList.forEach((ev) => {
    const src = ev.source || 'graph';
    sourceGroups[src] = (sourceGroups[src] || 0) + 1;
  });

  const filteredEvidence = evidenceList.filter((ev) => {
    if (selectedSource === 'all') return true;
    return ev.source === selectedSource;
  });

  function getSourceIcon(src: string) {
    switch (src) {
      case 'graph':
        return Database;
      case 'doc':
      case 'document':
        return FileText;
      case 'customer':
        return MessageSquare;
      case 'analyst':
        return UserCheck;
      default:
        return Globe;
    }
  }

  function getSourceBadgeColor(src: string) {
    switch (src) {
      case 'graph':
        return 'text-[#58A6FF] border-[#58A6FF]/40 bg-[#58A6FF]/10';
      case 'customer':
        return 'text-[#30A46C] border-[#30A46C]/40 bg-[#30A46C]/10';
      case 'analyst':
        return 'text-[#F5A524] border-[#F5A524]/40 bg-[#F5A524]/10';
      case 'doc':
      case 'document':
        return 'text-[#2DD4BF] border-[#2DD4BF]/40 bg-[#2DD4BF]/10';
      default:
        return 'text-[#9AA8B5] border-[#1E2933] bg-[#0D1319]';
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto flex flex-col gap-5 select-none">
      {/* Header and Source Filter Chips */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1E2933] pb-3">
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
            Investigative Evidence Trail
          </span>
          <span className="text-xs text-[#9AA8B5]">
            Corroborated graph queries, regulatory references, and simulated customer feedback
          </span>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          {Object.entries(sourceGroups).map(([src, count]) => {
            const isActive = selectedSource === src;
            return (
              <button
                key={src}
                onClick={() => setSelectedSource(src)}
                className={`text-[11px] font-mono px-2 py-0.5 rounded-[6px] border transition-colors flex items-center gap-1 ${
                  isActive
                    ? 'text-[#F5A524] border-[#F5A524] bg-[#161E27]'
                    : 'text-[#9AA8B5] border-[#1E2933] bg-[#0D1319] hover:border-[#2A3642]'
                }`}
              >
                <span>{src}</span>
                <span className="text-[10px] text-[#5C6B7A]">({count})</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Evidence Cards List */}
      <div className="flex flex-col gap-3">
        {filteredEvidence.length === 0 ? (
          <div className="p-8 text-center text-xs text-[#5C6B7A] italic bg-[#10161D] border border-[#1E2933] rounded-[8px]">
            No evidence records found for selected filter
          </div>
        ) : (
          filteredEvidence.map((ev, i) => {
            const SourceIcon = getSourceIcon(ev.source);
            const badgeColor = getSourceBadgeColor(ev.source);

            return (
              <div
                key={i}
                className="bg-[#10161D] border border-[#1E2933] rounded-[8px] p-4 flex flex-col gap-2.5 transition-colors hover:border-[#2A3642]"
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2">
                    <span
                      className={`font-mono text-[10px] uppercase font-semibold px-2 py-0.5 rounded border flex items-center gap-1 ${badgeColor}`}
                    >
                      <SourceIcon className="w-3 h-3" strokeWidth={1.5} />
                      <span>{ev.source}</span>
                    </span>

                    <span className="font-mono text-[11px] text-[#5C6B7A] bg-[#0D1319] border border-[#1E2933] px-2 py-0.5 rounded">
                      {ev.ref}
                    </span>
                  </div>

                  {ev.entity_ids && ev.entity_ids.length > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] font-mono text-[#5C6B7A]">Entities:</span>
                      <span className="font-mono text-[11px] text-[#9AA8B5]">
                        {ev.entity_ids.length} linked
                      </span>
                    </div>
                  )}
                </div>

                <p className="text-[14px] text-[#E8EEF4] leading-relaxed">
                  {ev.claim}
                </p>

                {ev.entity_ids && ev.entity_ids.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1 pt-2 border-t border-[#1E2933]">
                    {ev.entity_ids.slice(0, 10).map((id, idx) => (
                      <span
                        key={idx}
                        className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#0D1319] border border-[#1E2933] text-[#9AA8B5]"
                      >
                        {id}
                      </span>
                    ))}
                    {ev.entity_ids.length > 10 && (
                      <span className="font-mono text-[10px] px-1.5 py-0.5 text-[#5C6B7A]">
                        +{ev.entity_ids.length - 10} more
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
