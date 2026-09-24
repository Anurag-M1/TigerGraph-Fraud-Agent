'use client';

import React, { useState } from 'react';
import { ArrowRight, GitCompare, Check, AlertTriangle, ShieldCheck, X } from 'lucide-react';
import { CaseFileAnswer, ActionItem, ActionApprovalRecord } from '@/lib/types';

interface ActionsTabProps {
  answer: CaseFileAnswer;
  caseId: string;
}

export function ActionsTab({ answer, caseId }: ActionsTabProps) {
  const nba = answer.next_best_actions || { initial: [], final: [], what_changed: '' };
  const initial = nba.initial || [];
  const final = nba.final || [];
  const whatChanged = nba.what_changed || 'No out-of-band policy modification occurred.';

  // State for executed actions
  const [executedMap, setExecutedMap] = useState<Record<string, ActionApprovalRecord>>({});
  const [pendingAction, setPendingAction] = useState<ActionItem | null>(null);
  const [executing, setExecuting] = useState(false);

  // Extract rule citation like "R1", "R2", "R6", "R7", "Policy 3a" from reason
  function getRuleChip(reason: string) {
    const match = reason.match(/(R[0-9]+|Policy 3[ab]|Section [0-9])/i);
    return match ? match[0] : 'RULE';
  }

  // Handle action execution via mock API
  async function handleConfirmExecution() {
    if (!pendingAction) return;
    setExecuting(true);

    try {
      const res = await fetch('/api/actions/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_id: caseId,
          action: pendingAction.action,
          route: pendingAction.route,
          approver: 'Senior Fraud Analyst (L2 Operations Lead)',
        }),
      });

      if (res.ok) {
        const record: ActionApprovalRecord = await res.json();
        setExecutedMap((prev) => ({
          ...prev,
          [`${caseId}:${pendingAction.action}`]: record,
        }));
      }
    } catch (err) {
      console.error('Approval failed:', err);
    } finally {
      setExecuting(false);
      setPendingAction(null);
    }
  }

  // Determine diff status for an action
  const initialNames = new Set(initial.map((a) => a.action));
  const finalNames = new Set(final.map((a) => a.action));

  return (
    <div className="p-6 max-w-5xl mx-auto flex flex-col gap-6 select-none">
      {/* SECTION 1: ROUTE DIFF BLOCK (Pre-Evidence vs Post-Evidence) */}
      <div className="bg-[#10161D] border border-[#1E2933] rounded-[8px] p-5 flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-[#1E2933] pb-3">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
              Policy Engine Route Diff
            </span>
            <span className="font-mono text-[11px] text-[#9AA8B5]">
              (Fraud Policy v1.0 Section 2)
            </span>
          </div>
          <span className="text-xs text-[#5C6B7A]">
            Evaluated Before (Step 6) vs After (Step 9) Out-of-Band Evidence
          </span>
        </div>

        {/* Dual Columns Side-by-Side */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr,32px,1fr] gap-3 items-center">
          {/* Column 1: BEFORE EVIDENCE */}
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between px-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
                BEFORE EVIDENCE
              </span>
              <span className="font-mono text-[10px] text-[#5C6B7A] bg-[#0D1319] border border-[#1E2933] px-1.5 py-0.5 rounded">
                Step 6 · {initial.length} Actions
              </span>
            </div>

            <div className="flex flex-col gap-2">
              {initial.length === 0 ? (
                <div className="p-3 text-xs text-[#5C6B7A] italic bg-[#0D1319] border border-[#1E2933] rounded-[6px]">
                  No pre-evidence actions recommended
                </div>
              ) : (
                initial.map((act, i) => {
                  const isRemoved = !finalNames.has(act.action);
                  return (
                    <div
                      key={i}
                      className={`bg-[#0D1319] border p-3 rounded-[6px] flex flex-col gap-1 transition-colors ${
                        isRemoved
                          ? 'border-l-2 border-l-[#E5484D] border-[#1E2933]'
                          : 'border-[#1E2933]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {isRemoved && (
                            <span className="font-mono text-xs font-bold text-[#E5484D]">-</span>
                          )}
                          <span className="font-mono text-[13px] font-semibold text-[#E8EEF4]">
                            {act.action}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-[10px] text-[#F5A524] border border-[#F5A524]/40 px-1.5 py-0.2 rounded">
                            {getRuleChip(act.reason)}
                          </span>
                          <span
                            className={`font-mono text-[10px] uppercase px-1.5 py-0.5 rounded ${
                              act.route === 'auto'
                                ? 'text-[#30A46C] border border-[#30A46C]/40 bg-[#30A46C]/10'
                                : act.route === 'L1'
                                ? 'text-[#F5A524] border border-[#F5A524]/40 bg-[#F5A524]/10'
                                : 'text-[#E5484D] border border-[#E5484D]/40 bg-[#E5484D]/10'
                            }`}
                          >
                            {act.route}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-[#9AA8B5] leading-snug">
                        {act.reason}
                      </p>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Center Divider Arrow */}
          <div className="hidden md:flex items-center justify-center text-[#5C6B7A]">
            <ArrowRight className="w-4 h-4" strokeWidth={1.5} />
          </div>

          {/* Column 2: AFTER EVIDENCE */}
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#F5A524]" />
                <span className="text-[11px] font-semibold uppercase tracking-wider text-[#E8EEF4]">
                  AFTER EVIDENCE
                </span>
              </div>
              <span className="font-mono text-[10px] text-[#F5A524] bg-[#0D1319] border border-[#F5A524]/30 px-1.5 py-0.5 rounded">
                Step 9 · Final
              </span>
            </div>

            <div className="flex flex-col gap-2">
              {final.length === 0 ? (
                <div className="p-3 text-xs text-[#5C6B7A] italic bg-[#0D1319] border border-[#1E2933] rounded-[6px]">
                  No post-evidence actions recommended
                </div>
              ) : (
                final.map((act, i) => {
                  const isAdded = !initialNames.has(act.action);
                  return (
                    <div
                      key={i}
                      className={`bg-[#0D1319] border p-3 rounded-[6px] flex flex-col gap-1 transition-colors ${
                        isAdded
                          ? 'border-l-2 border-l-[#30A46C] border-[#1E2933]'
                          : 'border-[#1E2933]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {isAdded && (
                            <span className="font-mono text-xs font-bold text-[#30A46C]">+</span>
                          )}
                          <span className="font-mono text-[13px] font-semibold text-[#E8EEF4]">
                            {act.action}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-[10px] text-[#F5A524] border border-[#F5A524]/40 px-1.5 py-0.2 rounded">
                            {getRuleChip(act.reason)}
                          </span>
                          <span
                            className={`font-mono text-[10px] uppercase px-1.5 py-0.5 rounded ${
                              act.route === 'auto'
                                ? 'text-[#30A46C] border border-[#30A46C]/40 bg-[#30A46C]/10'
                                : act.route === 'L1'
                                ? 'text-[#F5A524] border border-[#F5A524]/40 bg-[#F5A524]/10'
                                : 'text-[#E5484D] border border-[#E5484D]/40 bg-[#E5484D]/10'
                            }`}
                          >
                            {act.route}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-[#9AA8B5] leading-snug">
                        {act.reason}
                      </p>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Below Diff: what_changed callout with GitCompare icon */}
        <div className="bg-[#0D1319] border border-[#1E2933] rounded-[6px] p-3.5 flex items-start gap-3 mt-1">
          <GitCompare className="w-4 h-4 text-[#F5A524] shrink-0 mt-0.5" strokeWidth={1.5} />
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] font-mono uppercase tracking-wider text-[#5C6B7A]">
              WHAT CHANGED
            </span>
            <p className="text-[13px] text-[#9AA8B5] leading-relaxed">
              {whatChanged}
            </p>
          </div>
        </div>
      </div>

      {/* SECTION 2: APPROVAL QUEUE & EXECUTION */}
      <div className="bg-[#10161D] border border-[#1E2933] rounded-[8px] p-5 flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-[#1E2933] pb-3">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#5C6B7A]">
            Recommended Actions & Approval Queue
          </span>
          <span className="text-xs text-[#5C6B7A]">
            Core Banking Execution Service
          </span>
        </div>

        <div className="flex flex-col gap-3">
          {final.map((act, i) => {
            const executed = executedMap[`${caseId}:${act.action}`];

            return (
              <div
                key={i}
                className="bg-[#0D1319] border border-[#1E2933] rounded-[6px] p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="flex flex-col gap-1 max-w-xl">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-sm font-semibold text-[#E8EEF4]">
                      {act.action}
                    </span>

                    {/* Route Badge */}
                    {act.route === 'auto' ? (
                      <span className="font-mono text-[10px] font-semibold px-2 py-0.5 rounded-full border border-[#30A46C] text-[#30A46C]">
                        AUTO
                      </span>
                    ) : act.route === 'L1' ? (
                      <span className="font-mono text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#F5A524] text-[#0A0E13]">
                        L1 · TEAM LEAD
                      </span>
                    ) : (
                      <span className="font-mono text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#E5484D] text-[#FFFFFF]">
                        L2 · FRAUD MGR
                      </span>
                    )}

                    <span className="font-mono text-[11px] text-[#5C6B7A]">
                      ({getRuleChip(act.reason)})
                    </span>
                  </div>
                  <p className="text-xs text-[#9AA8B5] leading-snug">
                    {act.reason}
                  </p>
                </div>

                {/* Execution Button / Executed State */}
                <div className="shrink-0 flex items-center gap-2">
                  {executed ? (
                    <div className="flex items-center gap-1.5 font-mono text-xs text-[#30A46C] bg-[#30A46C]/10 border border-[#30A46C]/30 px-3 py-1.5 rounded-[6px]">
                      <Check className="w-3.5 h-3.5" strokeWidth={1.5} />
                      <span>{executed.auth_code}</span>
                    </div>
                  ) : act.route === 'auto' ? (
                    <button
                      onClick={() => setPendingAction(act)}
                      className="h-8 px-3.5 rounded-[6px] bg-[#30A46C] text-[#0A0E13] font-mono text-xs font-semibold hover:bg-[#30A46C]/90 transition-colors flex items-center gap-1.5 cursor-pointer"
                    >
                      <ShieldCheck className="w-3.5 h-3.5" strokeWidth={1.5} />
                      <span>Execute</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => setPendingAction(act)}
                      title={`Requires ${act.route} sign-off — policy §2`}
                      className="h-8 px-3.5 rounded-[6px] border border-[#1E2933] bg-[#161E27] text-[#9AA8B5] hover:text-[#E8EEF4] hover:border-[#F5A524]/50 font-mono text-xs transition-colors flex items-center gap-1.5 cursor-pointer"
                    >
                      <AlertTriangle className="w-3.5 h-3.5 text-[#F5A524]" strokeWidth={1.5} />
                      <span>Approve ({act.route})</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Confirmation Modal */}
      {pendingAction && (
        <div className="fixed inset-0 z-50 bg-[#0A0E13]/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#161E27] border border-[#2A3642] rounded-[8px] max-w-md w-full p-5 shadow-[0_8px_24px_rgba(0,0,0,0.5)] flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-[#1E2933] pb-2.5">
              <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[#F5A524]">
                Confirm Action Execution
              </span>
              <button
                onClick={() => setPendingAction(null)}
                className="text-[#5C6B7A] hover:text-[#E8EEF4] transition-colors"
              >
                <X className="w-4 h-4" strokeWidth={1.5} />
              </button>
            </div>

            <div className="flex flex-col gap-2 font-mono text-xs">
              <div className="flex justify-between py-1 border-b border-[#1E2933]">
                <span className="text-[#5C6B7A]">Action:</span>
                <span className="font-bold text-[#E8EEF4]">{pendingAction.action}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1E2933]">
                <span className="text-[#5C6B7A]">Approval Tier:</span>
                <span className="text-[#F5A524]">{pendingAction.route} Sign-off</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1E2933]">
                <span className="text-[#5C6B7A]">Target Case:</span>
                <span className="text-[#E8EEF4]">{caseId}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#5C6B7A]">Confirmed Exposure:</span>
                <span className="text-[#E8EEF4]">
                  ${answer.case?.exposure_usd?.toFixed(2) || '0.00'} USD
                </span>
              </div>
            </div>

            <p className="text-xs text-[#9AA8B5] leading-relaxed">
              Executing this action registers an immutable core banking authorization code and triggers downstream containment protocols per Fraud Policy v1.0.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-[#1E2933]">
              <button
                onClick={() => setPendingAction(null)}
                className="h-8 px-3 rounded-[6px] border border-[#1E2933] text-xs font-mono text-[#9AA8B5] hover:text-[#E8EEF4] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmExecution}
                disabled={executing}
                className="h-8 px-4 rounded-[6px] bg-[#30A46C] text-[#0A0E13] font-mono text-xs font-semibold hover:bg-[#30A46C]/90 transition-colors flex items-center gap-1.5"
              >
                {executing ? 'Registering...' : 'Confirm & Execute'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
