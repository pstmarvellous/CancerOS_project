import { NextResponse } from 'next/server';
import { checkResearchWorkspace, credentialExpiry, deleteResearchSession, isSameResearchOrigin,
  newResearchSession, RESEARCH_COOKIE, researchSession, secureResearchTransport } from '../../../lib/research-session';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';
const PRIVATE = { 'Cache-Control': 'private, no-store' };
function problem(title: string, status: number) {
  return NextResponse.json({ title }, { status, headers: PRIVATE });
}
function clearCookie(response: NextResponse, request: Request) {
  response.cookies.set(RESEARCH_COOKIE, '', { httpOnly: true, sameSite: 'strict', path: '/',
    secure: new URL(request.url).protocol === 'https:', expires: new Date(0), maxAge: 0 });
  return response;
}

export async function GET(request: Request) {
  const session = researchSession(request);
  if (!session) return clearCookie(NextResponse.json({ authenticated: false, projects: [] }, { headers: PRIVATE }), request);
  const result = await checkResearchWorkspace(session.token);
  if (!result.ok) {
    if (result.status === 401 || result.status === 403) {
      deleteResearchSession(request);
      return clearCookie(NextResponse.json({ authenticated: false, projects: [] }, { headers: PRIVATE }), request);
    }
    return problem('Research access could not be checked. Retry when the API is available.', 502);
  }
  return NextResponse.json({ authenticated: true, ...result.workspace, expiresAt: new Date(session.expires).toISOString() }, { headers: PRIVATE });
}

export async function POST(request: Request) {
  if (!isSameResearchOrigin(request)) return problem('Sign in from CancerOS.', 403);
  if (!secureResearchTransport(request.url)) return problem('Research sign-in requires HTTPS outside local loopback development.', 403);
  if (!request.headers.get('content-type')?.toLowerCase().startsWith('application/json')) return problem('Use a JSON credential request.', 415);
  const raw = await request.text();
  if (raw.length > 20000) return problem('The credential request is too large.', 413);
  let token: unknown;
  try {
    const body = JSON.parse(raw);
    if (!body || Array.isArray(body) || Object.keys(body).join(',') !== 'token') return problem('Provide an existing research access token.', 400);
    token = body.token;
  } catch { return problem('Provide a valid JSON credential request.', 400); }
  const expires = credentialExpiry(token);
  if (expires === null || typeof token !== 'string') return problem('The credential must be a current RS256 research access token.', 400);
  const result = await checkResearchWorkspace(token);
  if (!result.ok) return problem(result.status === 502 ? 'Research access could not be checked. Retry when the API is available.' : 'The credential was not authorized by the research API.', result.status);
  if (expires <= Date.now()) return problem('The research credential expired. Use a current access token.', 401);
  // Always rotate the session identifier after successful authentication.
  deleteResearchSession(request);
  const session = newResearchSession(token, expires);
  const response = NextResponse.json({ authenticated: true, ...result.workspace, expiresAt: new Date(session.expires).toISOString() }, { headers: PRIVATE });
  response.cookies.set(RESEARCH_COOKIE, session.id, { httpOnly: true, sameSite: 'strict', path: '/',
    secure: new URL(request.url).protocol === 'https:', expires: new Date(session.expires),
    maxAge: Math.max(0, Math.floor((session.expires - Date.now()) / 1000)) });
  return response;
}

export async function DELETE(request: Request) {
  if (!isSameResearchOrigin(request)) return problem('Sign out from CancerOS.', 403);
  deleteResearchSession(request);
  return clearCookie(NextResponse.json({ authenticated: false, projects: [] }, { headers: PRIVATE }), request);
}
