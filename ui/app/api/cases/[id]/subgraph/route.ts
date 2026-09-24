import { NextRequest, NextResponse } from 'next/server';
import { getCaseSubgraph } from '@/lib/cases';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await context.params;

    // 1. Try FastAPI backend if running on 8000
    try {
      const res = await fetch(`http://localhost:8000/api/cases/${id}/subgraph`, {
        signal: AbortSignal.timeout(1200),
      });
      if (res.ok) {
        const liveData = await res.json();
        if (liveData?.nodes?.length > 0) {
          return NextResponse.json(liveData);
        }
      }
    } catch {
      // Fallback below
    }

    // 2. Local fallback synthesis
    const localData = getCaseSubgraph(id);
    return NextResponse.json(localData);
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: errorMsg }, { status: 500 });
  }
}
