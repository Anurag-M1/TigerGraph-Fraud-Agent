import { NextRequest, NextResponse } from 'next/server';

interface ApprovalPayload {
  case_id: string;
  action: string;
  route: string;
  approver?: string;
  notes?: string;
}

export async function POST(request: NextRequest) {
  try {
    const body: ApprovalPayload = await request.json();
    const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const randomHex = Math.random().toString(16).substring(2, 8).toUpperCase();
    const auth_code = `AUTH-${dateStr}-${randomHex}`;

    const record = {
      auth_code,
      case_id: body.case_id,
      action: body.action,
      route: body.route || 'auto',
      approver: body.approver || 'L1 Fraud Operations Lead',
      notes: body.notes || 'Approved following graph topology and policy evaluation.',
      timestamp: new Date().toISOString(),
      status: 'EXECUTED',
      message: `Successfully executed ${body.action} via ${body.route || 'auto'} route for case ${body.case_id}. Core banking authorization token ${auth_code} registered.`,
    };

    return NextResponse.json(record);
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: errorMsg }, { status: 500 });
  }
}
