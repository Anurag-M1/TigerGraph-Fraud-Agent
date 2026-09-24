'use client';

import React, { useState } from 'react';
import {
  Database,
  FileSearch,
  MessageSquareWarning,
  Scale,
  GitBranch,
  Save,
  CheckCircle,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { TimelineStepItem } from '@/lib/types';

interface TimelineTabProps {
  steps: TimelineStepItem[];
  caseId: string;
}

export function TimelineTab({ steps, caseId }: TimelineTabProps) {
  const [expandedStep, setExpandedStep] = useState<number | null>(7); // default expand step 7 (out of band request)

  // Map node name to Lucide icon
  function getStepIcon(node: string) {
    switch (node) {
      case 'TRIGGER':
        return GitBranch;
      case 'OPEN_CASE_IN_GRAPH':
        return Save;
      case 'EVIDENCE_PLAN':
        return FileSearch;
      case 'COLLECT':
        return Database;
      case 'ASSESS':
      case 'RE_ASSESS':
        return Scale;
      case 'POLICY_EVAL':
      case 'POLICY_EVAL_FINAL':
        return Scale;
      case 'REQUEST_EVIDENCE':
        return MessageSquareWarning;
      case 'WRITE_CASE_TO_GRAPH':
        return Save;
      case 'EMIT_ANSWER':
        return CheckCircle;
      default:
        return Database;
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto flex flex-col gap-5 select-none">
      <div className="flex items-center justify-between border-b border-[#1E2933] pb-3">
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
            LangGraph State Machine Execution Log
          </span>
          <span className="text-xs text-[#9AA8B5]">
            Strict 11-step numbered lifecycle replay for case {caseId}
          </span>
        </div>
        <span className="font-mono text-[11px] text-[#9AA8B5] bg-[#10161D] border border-[#1E2933] px-2.5 py-1 rounded">
          {steps.length} Steps Logged
        </span>
      </div>

      {/* Stepper Vertical Tree */}
      <div className="relative pl-6 flex flex-col gap-6">
        {/* Left vertical rail line */}
        <div className="absolute left-[18px] top-3 bottom-3 w-[1px] bg-[#1E2933]" />

        {steps.map((item) => {
          const StepIcon = getStepIcon(item.node);
          const isExpanded = expandedStep === item.step;
          const isHighlight = item.highlight || item.node === 'REQUEST_EVIDENCE';

          return (
            <div key={item.step} className="relative flex items-start gap-3.5 group">
              {/* Numbered circle on the left rail */}
              <div
                className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center font-mono text-[11px] font-medium border shrink-0 transition-colors ${
                  isHighlight
                    ? 'bg-[#161E27] border-[#F5A524] text-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.3)]'
                    : 'bg-[#161E27] border-[#1E2933] text-[#9AA8B5] group-hover:border-[#2A3642]'
                }`}
              >
                {item.step}
              </div>

              {/* Step Card Body */}
              <div
                className={`flex-1 bg-[#10161D] border rounded-[8px] p-3.5 transition-colors ${
                  isHighlight
                    ? 'border-[#F5A524]/40 bg-[#161E27]/50'
                    : 'border-[#1E2933] hover:border-[#2A3642]'
                }`}
              >
                {/* Header: Title, node badge, timing, asked_after_step */}
                <div className="flex items-center justify-between gap-2 mb-1.5 flex-wrap">
                  <div className="flex items-center gap-2">
                    <StepIcon
                      className={`w-4 h-4 ${isHighlight ? 'text-[#F5A524]' : 'text-[#5C6B7A]'}`}
                      strokeWidth={1.5}
                    />
                    <span className="font-mono text-[13px] font-semibold text-[#E8EEF4]">
                      {item.node}
                    </span>
                    <span className="text-xs text-[#9AA8B5] font-medium">
                      · {item.title}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* asked_after_step badge matching answer file */}
                    {item.asked_after_step !== undefined && (
                      <span className="font-mono text-[10px] text-[#F5A524] border border-[#F5A524]/40 bg-[#F5A524]/10 px-2 py-0.5 rounded-full">
                        asked_after_step={item.asked_after_step}
                      </span>
                    )}
                    <span className="font-mono text-[11px] text-[#5C6B7A]">
                      {item.duration_ms}ms
                    </span>
                  </div>
                </div>

                {/* Description */}
                <p className="text-[13px] text-[#9AA8B5] leading-relaxed mb-2">
                  {item.description}
                </p>

                {/* Expandable JSON Telemetry Block */}
                {item.raw_payload && (
                  <div className="mt-2 pt-2 border-t border-[#1E2933]">
                    <button
                      onClick={() => setExpandedStep(isExpanded ? null : item.step)}
                      className="flex items-center gap-1.5 text-[11px] font-mono text-[#5C6B7A] hover:text-[#E8EEF4] transition-colors"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-3.5 h-3.5" strokeWidth={1.5} />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5" strokeWidth={1.5} />
                      )}
                      <span>{isExpanded ? 'Hide Payload' : 'Inspect Telemetry'}</span>
                    </button>

                    {isExpanded && (
                      <pre className="mt-2 p-3 bg-[#0D1319] border border-[#1E2933] rounded-[6px] font-mono text-[11px] text-[#9AA8B5] overflow-x-auto leading-relaxed">
                        {JSON.stringify(item.raw_payload, null, 2)}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
