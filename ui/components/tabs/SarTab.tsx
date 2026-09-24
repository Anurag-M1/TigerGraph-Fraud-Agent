'use client';

import React, { useState } from 'react';
import { FileX, Copy, Check, Download } from 'lucide-react';
import { CaseFileAnswer } from '@/lib/types';

interface SarTabProps {
  answer: CaseFileAnswer;
  caseId: string;
}

export function SarTab({ answer, caseId }: SarTabProps) {
  const sar = answer.sar || { file: false, reason: '' };
  const [copied, setCopied] = useState(false);

  function handleCopyNarrative() {
    if (!sar.narrative) return;
    navigator.clipboard.writeText(sar.narrative);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleDownloadJson() {
    const data = {
      case_id: caseId,
      timestamp: new Date().toISOString(),
      regulatory_sar: sar,
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${caseId}-SAR-Record.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // If no SAR required, render clean empty state
  if (!sar.file) {
    return (
      <div className="p-12 flex flex-col items-center justify-center min-h-[460px] gap-3 text-center select-none">
        <div className="w-12 h-12 rounded-full bg-[#10161D] border border-[#1E2933] flex items-center justify-center text-[#5C6B7A]">
          <FileX className="w-6 h-6" strokeWidth={1.5} />
        </div>
        <div className="flex flex-col gap-1 max-w-md">
          <span className="text-sm font-semibold text-[#E8EEF4]">
            No SAR Regulatory Filing Required
          </span>
          <p className="text-xs text-[#5C6B7A] leading-relaxed">
            {sar.reason || 'Transaction confirmed legitimate or sub-threshold exposure under $1,000 without shared syndicate origin.'}
          </p>
        </div>
      </div>
    );
  }

  const subjects = sar.subjects || ['Cardholder', 'Device Profile'];
  const dates = sar.activity_dates || ['2016-11-22', '2016-11-22'];
  const totalAmount = sar.total_amount_usd || answer.case?.exposure_usd || 0.0;

  return (
    <div className="p-8 flex flex-col items-center gap-6 select-none bg-[#0A0E13]">
      {/* Top Action Bar */}
      <div className="max-w-2xl w-full flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#E5484D]" />
          <span className="font-mono text-xs text-[#9AA8B5]">
            FinCEN §3a Regulatory Document
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopyNarrative}
            className="h-8 px-3 rounded-[6px] border border-[#1E2933] bg-[#10161D] text-[#9AA8B5] hover:text-[#E8EEF4] hover:border-[#2A3642] font-mono text-xs transition-colors flex items-center gap-1.5"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-[#30A46C]" strokeWidth={1.5} />
                <span className="text-[#30A46C]">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" strokeWidth={1.5} />
                <span>Copy Narrative</span>
              </>
            )}
          </button>
          <button
            onClick={handleDownloadJson}
            className="h-8 px-3 rounded-[6px] border border-[#1E2933] bg-[#10161D] text-[#9AA8B5] hover:text-[#E8EEF4] hover:border-[#2A3642] font-mono text-xs transition-colors flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" strokeWidth={1.5} />
            <span>Download JSON</span>
          </button>
        </div>
      </div>

      {/* Official White "Paper" View (Newsreader serif, #F7F5F0 bg, #1A1D21 text, 48px padding) */}
      <div className="max-w-2xl w-full bg-[#F7F5F0] text-[#1A1D21] rounded-[8px] p-12 shadow-[0_8px_24px_rgba(0,0,0,0.5)] flex flex-col gap-6 font-serif">
        {/* Document Header */}
        <div className="flex flex-col items-center text-center gap-1 border-b border-[#D8D4CC] pb-5">
          <span className="text-[11px] tracking-[0.2em] uppercase font-sans font-semibold text-[#666]">
            FINANCIAL CRIMES ENFORCEMENT NETWORK
          </span>
          <h2 className="text-xl font-bold tracking-tight text-[#1A1D21]">
            SUSPICIOUS ACTIVITY REPORT
          </h2>
          <span className="font-mono text-xs text-[#777] mt-0.5">
            INVESTIGATION REFERENCE: {caseId}
          </span>
        </div>

        {/* Metadata Bordered Table */}
        <div className="border border-[#D8D4CC] rounded overflow-hidden text-xs font-sans">
          <div className="grid grid-cols-2 bg-[#EFECE4] border-b border-[#D8D4CC] p-2 font-semibold text-[#555]">
            <span>REGULATORY ATTRIBUTE</span>
            <span>RECORD VALUE</span>
          </div>
          <div className="grid grid-cols-2 p-2 border-b border-[#D8D4CC] text-[#222]">
            <span className="font-medium text-[#666]">Filing Requirement:</span>
            <span className="font-mono font-semibold text-[#B91C1C]">MANDATORY (§3a / Rule R2)</span>
          </div>
          <div className="grid grid-cols-2 p-2 border-b border-[#D8D4CC] text-[#222]">
            <span className="font-medium text-[#666]">Total Confirmed Exposure:</span>
            <span className="font-mono font-semibold">
              ${totalAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD
            </span>
          </div>
          <div className="grid grid-cols-2 p-2 border-b border-[#D8D4CC] text-[#222]">
            <span className="font-medium text-[#666]">Activity Period:</span>
            <span className="font-mono">{dates[0]} to {dates[1] || dates[0]}</span>
          </div>
          <div className="grid grid-cols-2 p-2 text-[#222]">
            <span className="font-medium text-[#666]">Named Subjects:</span>
            <span className="font-mono text-[11px]">{subjects.join(', ')}</span>
          </div>
        </div>

        {/* 5 Essential Elements Narrative */}
        <div className="flex flex-col gap-2">
          <span className="text-[11px] font-sans font-semibold uppercase tracking-wider text-[#777]">
            Section V — Narrative (Who, What, When, Where, Why, and How)
          </span>
          <p className="text-[15px] leading-[1.7] text-justify text-[#1A1D21]">
            {sar.narrative}
          </p>
        </div>

        {/* Document Footer Signoff */}
        <div className="pt-4 border-t border-[#D8D4CC] flex items-center justify-between text-[11px] font-sans text-[#777]">
          <span>Generated by TigerGraph Fraud Defense Intelligence</span>
          <span className="font-mono">STATUS: PENDING L2 SIGN-OFF</span>
        </div>
      </div>
    </div>
  );
}
