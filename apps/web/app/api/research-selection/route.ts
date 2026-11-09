import { NextResponse } from 'next/server';
import { caseUrl, proxyCase } from '../../../lib/case-proxy';
import { researchSession } from '../../../lib/research-session';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';
const headers = { 'Cache-Control': 'private, no-store' };

export async function GET(request: Request) {
  const session = researchSession(request);
  if (!session || request.headers.has('authorization')) return NextResponse.json({}, { status: 401, headers });
  const selected = session.lastCase;
  if (!selected) return NextResponse.json({}, { headers });
  const url = caseUrl(selected.project, selected.patient, '');
  if (!url) return NextResponse.json({}, { status: 400, headers });
  // A retained identifier never substitutes for current membership and grant checks.
  const authorized = await proxyCase(request, url, 'GET');
  if (!authorized.ok) {
    if ([401, 403, 404].includes(authorized.status)) delete session.lastCase;
    return NextResponse.json({}, { status: authorized.status, headers });
  }
  return NextResponse.json(selected, { headers });
}
