import { NextRequest, NextResponse } from 'next/server';
import { DEMO_COOKIE, demoBundle, newDemoSession } from '../../../lib/synthetic-demo';
export const dynamic = 'force-dynamic';
export async function POST(request: NextRequest) {
  // NextURL canonicalizes loopback IPs to localhost. Compare the browser Origin
  // with the original Host header so both supported loopback URLs work, while
  // keeping cross-origin launches denied.
  const expectedOrigin = `${request.nextUrl.protocol}//${request.headers.get('host')}`;
  if (request.headers.get('origin') !== expectedOrigin ||
    request.headers.get('sec-fetch-site') === 'cross-site') {
    return NextResponse.json({ title: 'Launch the demo from CancerOS.' }, { status: 403 });
  }
  const prepared = demoBundle();
  if (!prepared) return NextResponse.json({ title: 'The synthetic demo is not ready. Please ask the presenter to prepare it, then retry.' },
    { status: 503, headers: { 'Cache-Control': 'private, no-store' } });
  const session = newDemoSession(prepared.fingerprint, prepared.bundle.expiresAt);
  const response = NextResponse.json({ synthetic: true }, { headers: { 'Cache-Control': 'private, no-store' } });
  response.cookies.set(DEMO_COOKIE, session.id, { httpOnly: true, sameSite: 'strict', path: '/',
    secure: request.nextUrl.protocol === 'https:', expires: new Date(session.expires) });
  return response;
}
