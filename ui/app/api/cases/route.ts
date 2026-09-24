import { NextResponse } from 'next/server';
import { getAllCasesSummary } from '@/lib/cases';

export async function GET() {
  try {
    const cases = getAllCasesSummary();
    return NextResponse.json(cases);
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: errorMsg }, { status: 500 });
  }
}
