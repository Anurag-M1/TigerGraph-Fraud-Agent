import { NextRequest, NextResponse } from 'next/server';
import { getCaseDetail } from '@/lib/cases';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await context.params;
    const detail = getCaseDetail(id);
    if (!detail) {
      return NextResponse.json({ error: `Case ${id} not found` }, { status: 404 });
    }
    return NextResponse.json(detail);
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: errorMsg }, { status: 500 });
  }
}
