import { NextRequest, NextResponse } from 'next/server';
import { DEMO_COOKIE, demoBundle, hasDemoSession } from '../../../lib/synthetic-demo';
export const dynamic = 'force-dynamic';
export async function GET(request: NextRequest) {
  const headers = { 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff' };
  const prepared = demoBundle();
  if (!prepared) return NextResponse.json({ title: 'Synthetic demo unavailable. If you run this computer, validate it with: uv run python scripts/prepare_synthetic_demo.py --check.' }, { status: 503, headers });
  if (!hasDemoSession(request.cookies.get(DEMO_COOKIE)?.value, prepared.fingerprint)) {
    return NextResponse.json({ title: 'Your demo session ended. Launch the demo again.' }, { status: 401, headers });
  }
  const params = request.nextUrl.searchParams;
  if ([...params.keys()].some(key => key !== 'scenario') || params.getAll('scenario').length > 1) {
    return NextResponse.json({ title: 'Unknown demo selection.' }, { status: 400, headers });
  }
  const id = params.get('scenario');
  if (id) {
    if (!Object.hasOwn(prepared.bundle.scenarios, id)) return NextResponse.json({ title: 'Choose an available scenario.' }, { status: 404, headers });
    return NextResponse.json(prepared.bundle.scenarios[id], { headers });
  }
  const { caseLabel, preparedAt, expiresAt, scenarios } = prepared.bundle;
  return NextResponse.json({ caseLabel, preparedAt, expiresAt,
    scenarios: Object.values(scenarios).map(({ id, label, description }) => ({ id, label, description })) }, { headers });
}
