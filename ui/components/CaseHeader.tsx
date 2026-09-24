'use client';

import React from 'react';
import { CaseFileAnswer, CaseMetadata } from '@/lib/types';

interface CaseHeaderProps {
  metadata: CaseMetadata;
  answer: CaseFileAnswer;
}

export function CaseHeader({ metadata, answer }: CaseHeaderProps) {
  const c = answer.case || {};
  const prob = c.fraud_probability ?? 0.5;
  const exposure = c.exposure_usd ?? 0.0;
  const pattern = c.pattern || 'none';
  const toolCalls = answer.tool_calls || 10;
  const verdict = c.verdict || 'uncertain';
  const status = c.status || 'open';

  // Risk Scale Color
  let probColor = '#30A46C'; // green < 0.30
  if (prob >= 0.70) {
    probColor = '#E5484D'; // red >= 0.70
  } else if (prob >= 0.30) {
    probColor = '#F5A524'; // amber 0.30 - 0.70
  }

  // Status Pill Styling
  let statusBadgeColor = 'text-[#F5A524] border-[#F5A524]/30 bg-[#F5A524]/10';
  if (verdict === 'fraud' || status === 'closed_fraud') {
    statusBadgeColor = 'text-[#E5484D] border-[#E5484D]/30 bg-[#E5484D]/10';
  } else if (verdict === 'legitimate' || status === 'closed_legitimate') {
    statusBadgeColor = 'text-[#30A46C] border-[#30A46C]/30 bg-[#30A46C]/10';
  }

  // Probability position percentage
  const pPercent = Math.min(Math.max(prob * 100, 0), 100);

  return (
    <div className="bg-[#10161D] border-b border-[#1E2933] p-5 flex flex-col gap-4 select-none">
      {/* Top Row: Case Identity & Stat Cluster */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left: Case ID, Status Pill, Trigger text */}
        <div className="flex flex-col gap-1.5 max-w-2xl">
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-xl font-bold text-[#E8EEF4] tracking-tight">
              {metadata.case_id}
            </h1>
            <span
              className={`font-mono text-[11px] font-semibold px-2 py-0.5 rounded-full border uppercase ${statusBadgeColor}`}
            >
              {status}
            </span>
            <span className="font-mono text-xs text-[#5C6B7A]">
              Card: {metadata.card_id}
            </span>
            {answer.sar?.file && (
              <span className="font-mono text-[11px] font-semibold px-2 py-0.5 rounded-full border border-[#E5484D]/40 text-[#E5484D] bg-[#E5484D]/10">
                SAR MANDATORY §3A
              </span>
            )}
          </div>
          <p className="text-[13px] text-[#9AA8B5] leading-snug line-clamp-2 italic">
            &ldquo;{metadata.trigger_text}&rdquo;
          </p>
        </div>

        {/* Right: Stat Cluster (4 Tiles) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {/* Tile 1: Fraud Probability */}
          <div className="bg-[#0D1319] border border-[#1E2933] rounded-[6px] px-3.5 py-2.5 flex flex-col justify-between min-w-[110px]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              Fraud Prob
            </span>
            <div className="flex items-baseline gap-1 mt-1">
              <span
                className="font-mono text-[18px] font-bold"
                style={{ color: probColor }}
              >
                {prob.toFixed(2)}
              </span>
              <span className="font-mono text-[10px] text-[#5C6B7A]">p</span>
            </div>
          </div>

          {/* Tile 2: Exposure USD */}
          <div className="bg-[#0D1319] border border-[#1E2933] rounded-[6px] px-3.5 py-2.5 flex flex-col justify-between min-w-[110px]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              Exposure
            </span>
            <span className="font-mono text-[18px] font-bold text-[#E8EEF4] mt-1">
              ${exposure.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>

          {/* Tile 3: Pattern */}
          <div className="bg-[#0D1319] border border-[#1E2933] rounded-[6px] px-3.5 py-2.5 flex flex-col justify-between min-w-[130px]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              Pattern
            </span>
            <span
              className="font-mono text-[13px] text-[#9AA8B5] truncate mt-1.5"
              title={pattern}
            >
              {pattern}
            </span>
          </div>

          {/* Tile 4: Tool Calls */}
          <div className="bg-[#0D1319] border border-[#1E2933] rounded-[6px] px-3.5 py-2.5 flex flex-col justify-between min-w-[90px]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              Tool Calls
            </span>
            <span className="font-mono text-[18px] font-bold text-[#E8EEF4] mt-1">
              {toolCalls}
            </span>
          </div>
        </div>
      </div>

      {/* Bottom: Probability Bar (6px, Segmented at Policy Thresholds 0.30 / 0.70 / 0.85) */}
      <div className="flex flex-col gap-1.5 pt-1">
        <div className="relative w-full h-[6px] bg-[#0D1319] border border-[#1E2933] rounded-full overflow-visible">
          {/* Active fill segment up to current prob */}
          <div
            className="h-full rounded-full transition-all duration-300"
            style={{
              width: `${pPercent}%`,
              backgroundColor: probColor,
            }}
          />

          {/* Policy §6 Threshold markers (0.30, 0.70, 0.85) */}
          <div
            className="absolute top-0 bottom-0 w-[1px] bg-[#1E2933]"
            style={{ left: '30%' }}
          />
          <div
            className="absolute top-0 bottom-0 w-[1px] bg-[#1E2933]"
            style={{ left: '70%' }}
          />
          <div
            className="absolute top-0 bottom-0 w-[1px] bg-[#1E2933]"
            style={{ left: '85%' }}
          />

          {/* Current p marker dot */}
          <div
            className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border border-[#0A0E13] shadow transition-all duration-300 -ml-1.5"
            style={{
              left: `${pPercent}%`,
              backgroundColor: probColor,
            }}
          />
        </div>

        {/* Threshold Labels Underneath */}
        <div className="relative w-full flex justify-between text-[10px] font-mono text-[#5C6B7A]">
          <span>0.00</span>
          <span className="absolute -translate-x-1/2" style={{ left: '30%' }}>
            0.30 · R1 OPEN
          </span>
          <span className="absolute -translate-x-1/2" style={{ left: '70%' }}>
            0.70 · R2 BLOCK
          </span>
          <span className="absolute -translate-x-1/2" style={{ left: '85%' }}>
            0.85 · R4 TIMEOUT
          </span>
          <span>1.00</span>
        </div>
      </div>
    </div>
  );
}
