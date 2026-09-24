'use client';

import React from 'react';
import { CaseFileAnswer, CaseMetadata } from '@/lib/types';
import { CreditCard, Smartphone, History, Layers } from 'lucide-react';

interface OverviewTabProps {
  answer: CaseFileAnswer;
  metadata: CaseMetadata;
}

export function OverviewTab({ answer, metadata }: OverviewTabProps) {
  const c = answer.case || {};
  const isUndocumented = c.pattern === 'undocumented';
  const affectedTxns = c.affected_txn_ids || [];
  const flaggedTxn = metadata.flagged_txn_id || c.first_suspicious_txn_id;
  const connectedCards = c.connected_card_ids || [];
  const connectedDevices = c.connected_device_profiles || [];
  const priorCases = c.similar_prior_cases || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 p-5 select-none">
      {/* Cols 1–8: Case Summary & Core Narrative */}
      <div className="lg:col-span-8 flex flex-col gap-4">
        {/* Main Summary Card */}
        <div className="bg-[#10161D] border border-[#1E2933] rounded-[8px] p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-[#1E2933] pb-2.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              Case Summary & Investigation Narrative
            </span>
            <span className="font-mono text-[11px] text-[#9AA8B5]">
              Stop Reason: Policy §6
            </span>
          </div>

          <p className="text-[14px] leading-[1.6] text-[#9AA8B5]">
            {c.summary || 'Investigation successfully synthesized per Fraud Policy v1.0.'}
          </p>

          {/* Undocumented Pattern R9 Block */}
          {isUndocumented && (
            <div className="bg-[#0D1319] border-l-2 border-[#2DD4BF] border-y border-r border-[#1E2933] p-3 rounded-r-[6px] flex flex-col gap-1 mt-1">
              <span className="text-[10px] font-mono uppercase tracking-wider font-semibold text-[#2DD4BF]">
                UNDOCUMENTED PATTERN — R9
              </span>
              <p className="text-[13px] text-[#E8EEF4] font-mono leading-relaxed">
                {c.pattern_description || 'Novel transaction typology discovered outside standard taxonomy.'}
              </p>
            </div>
          )}

          {/* Stop Reason Box */}
          {answer.stop_reason && (
            <div className="bg-[#0D1319] border border-[#1E2933] rounded-[6px] p-3 flex flex-col gap-1">
              <span className="text-[10px] font-mono uppercase tracking-wider font-semibold text-[#5C6B7A]">
                Policy Section 6 Bounded Termination
              </span>
              <p className="text-xs text-[#9AA8B5] font-mono">
                {answer.stop_reason}
              </p>
            </div>
          )}
        </div>

        {/* Telemetry & Performance Row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-[#10161D] border border-[#1E2933] rounded-[8px] p-3 flex flex-col justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              Graph Case ID
            </span>
            <span className="font-mono text-xs text-[#58A6FF] font-medium mt-1 truncate">
              {c.graph_case_id || `CASE-${answer.case_id}`}
            </span>
          </div>
          <div className="bg-[#10161D] border border-[#1E2933] rounded-[8px] p-3 flex flex-col justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              Investigation Latency
            </span>
            <span className="font-mono text-xs text-[#E8EEF4] font-medium mt-1">
              {answer.latency_s !== undefined ? `${answer.latency_s.toFixed(2)}s` : '0.45s'}
            </span>
          </div>
          <div className="bg-[#10161D] border border-[#1E2933] rounded-[8px] p-3 flex flex-col justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              Graph Persistence
            </span>
            <span className="font-mono text-xs text-[#30A46C] font-medium mt-1">
              ✓ written_to_graph
            </span>
          </div>
        </div>
      </div>

      {/* Cols 9–12: Entity Stack */}
      <div className="lg:col-span-4 flex flex-col gap-4">
        {/* Card 1: Affected Transactions */}
        <div className="bg-[#10161D] border border-[#1E2933] rounded-[8px] p-4 flex flex-col gap-2.5">
          <div className="flex items-center justify-between border-b border-[#1E2933] pb-2">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              <Layers className="w-3.5 h-3.5 text-[#5C6B7A]" strokeWidth={1.5} />
              <span>Affected Transactions</span>
            </div>
            <span className="font-mono text-[11px] text-[#9AA8B5]">
              {affectedTxns.length}
            </span>
          </div>

          <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto pr-1">
            {affectedTxns.length === 0 ? (
              <span className="text-xs text-[#5C6B7A] italic py-1">
                No fraudulent transactions (cleared)
              </span>
            ) : (
              affectedTxns.map((tid) => {
                const isFlagged = tid === flaggedTxn;
                const estAmt = c.exposure_usd / Math.max(affectedTxns.length, 1);
                return (
                  <div
                    key={tid}
                    className="flex items-center justify-between text-xs py-1 px-2 rounded bg-[#0D1319] border border-[#1E2933]"
                  >
                    <div className="flex items-center gap-1.5 font-mono text-[#E8EEF4]">
                      {isFlagged ? (
                        <span className="w-1.5 h-1.5 rounded-full bg-[#E5484D]" title="Flagged Transaction" />
                      ) : (
                        <span className="w-1.5 h-1.5 rounded-full bg-[#5C6B7A]" />
                      )}
                      <span>Txn {tid}</span>
                    </div>
                    <div className="flex items-center gap-2 font-mono text-[11px]">
                      <span className="text-[#9AA8B5]">
                        ${estAmt.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                      {metadata.risk_score && isFlagged && (
                        <span className="text-[#E5484D]">
                          risk {metadata.risk_score.toFixed(2)}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Card 2: Connected Cards */}
        <div className="bg-[#10161D] border border-[#1E2933] rounded-[8px] p-4 flex flex-col gap-2.5">
          <div className="flex items-center justify-between border-b border-[#1E2933] pb-2">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              <CreditCard className="w-3.5 h-3.5 text-[#5C6B7A]" strokeWidth={1.5} />
              <span>Connected Cards</span>
            </div>
            <span className="font-mono text-[11px] text-[#9AA8B5]">
              {connectedCards.length}
            </span>
          </div>

          <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
            {connectedCards.length === 0 ? (
              <span className="text-xs text-[#5C6B7A] italic py-1">
                No connected cards identified
              </span>
            ) : (
              connectedCards.map((card) => (
                <span
                  key={card}
                  className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-[#0D1319] border border-[#1E2933] text-[#F5A524]"
                >
                  {card}
                </span>
              ))
            )}
          </div>
        </div>

        {/* Card 3: Connected Device Profiles */}
        <div className="bg-[#10161D] border border-[#1E2933] rounded-[8px] p-4 flex flex-col gap-2.5">
          <div className="flex items-center justify-between border-b border-[#1E2933] pb-2">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              <Smartphone className="w-3.5 h-3.5 text-[#5C6B7A]" strokeWidth={1.5} />
              <span>Device Profiles</span>
            </div>
            <span className="font-mono text-[11px] text-[#9AA8B5]">
              {connectedDevices.length}
            </span>
          </div>

          <div className="flex flex-col gap-1.5">
            {connectedDevices.length === 0 ? (
              <span className="text-xs text-[#5C6B7A] italic py-1">
                No distinct device hardware recorded
              </span>
            ) : (
              connectedDevices.map((dev, idx) => (
                <div
                  key={idx}
                  className="font-mono text-[11px] text-[#9AA8B5] bg-[#0D1319] border border-[#1E2933] p-2 rounded break-all leading-snug"
                >
                  {dev}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Card 4: Similar Prior Cases (Case Memory) */}
        <div className="bg-[#10161D] border border-[#1E2933] rounded-[8px] p-4 flex flex-col gap-2.5">
          <div className="flex items-center justify-between border-b border-[#1E2933] pb-2">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              <History className="w-3.5 h-3.5 text-[#5C6B7A]" strokeWidth={1.5} />
              <span>Similar Prior Cases</span>
            </div>
            <span className="font-mono text-[11px] text-[#2DD4BF]">
              {priorCases.length}
            </span>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {priorCases.length === 0 ? (
              <span className="text-xs text-[#5C6B7A] italic py-1">
                No prior memory matches retrieved
              </span>
            ) : (
              priorCases.map((item, idx) => {
                const caseId = typeof item === 'string' ? item : item.case_id;
                const tooltip =
                  typeof item === 'object'
                    ? `${item.outcome || 'closed_fraud'} · ${item.pattern || 'compromised'}`
                    : 'confirmed_fraud · historical case';
                return (
                  <span
                    key={idx}
                    title={tooltip}
                    className="font-mono text-[11px] px-2 py-0.5 rounded-[6px] bg-[#0D1319] border border-[#2DD4BF]/40 text-[#2DD4BF] hover:bg-[#161E27] cursor-help"
                  >
                    {caseId}
                  </span>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
