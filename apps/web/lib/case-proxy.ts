import { NextResponse } from 'next/server';
import { allowedResearchWrite, deleteResearchSession, researchAuthorization } from './research-session';

const API = process.env.API_BASE_URL ?? 'http://127.0.0.1:8000';

export function caseUrl(project: string, patient: string, suffix: string): URL | null {
  if (!project || !patient) return null;
  const url = new URL(
    `/api/v1/projects/${encodeURIComponent(project)}/patients/${encodeURIComponent(patient)}${suffix}`,
    API,
  );
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return null;
  return url;
}

export function caseParams(request: Request): { project: string; patient: string } {
  const incoming = new URL(request.url);
  return {
    project: incoming.searchParams.get('project') ?? '',
    patient: incoming.searchParams.get('patient') ?? '',
  };
}

function forwardHeaders(request: Request): Record<string, string> {
  const headers: Record<string, string> = {};
  const authorization = researchAuthorization(request);
  if (authorization) headers.authorization = authorization;
  const idempotency = request.headers.get('idempotency-key');
  if (idempotency) headers['idempotency-key'] = idempotency;
  const match = request.headers.get('if-match');
  if (match) headers['if-match'] = match;
  return headers;
}

export async function proxyCase(request: Request, url: URL, method: string, bodyText?: string) {
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase()) && !allowedResearchWrite(request)) {
    return NextResponse.json({ title: 'Use CancerOS from the same origin to save changes.' },
      { status: 403, headers: { 'Cache-Control': 'private, no-store' } });
  }
  if (!researchAuthorization(request)) return NextResponse.json({ title: 'An authorized research session is required.' },
    { status: 401, headers: { 'Cache-Control': 'private, no-store' } });
  try {
    const headers = forwardHeaders(request);
    if (bodyText !== undefined) headers['content-type'] = 'application/json';
    const response = await fetch(url, {
      method,
      headers,
      body: bodyText,
      cache: 'no-store',
      redirect: 'error',
      signal: AbortSignal.timeout(15000),
    });
    const body = await response.text();
    if (response.status === 401) deleteResearchSession(request);
    const responseHeaders: Record<string, string> = { 'content-type': 'application/json', 'Cache-Control': 'private, no-store' };
    for (const name of ['etag', 'location', 'retry-after']) {
      const value = response.headers.get(name);
      if (value) responseHeaders[name] = value;
    }
    return new NextResponse(body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json({ title: 'API process unavailable' }, { status: 502, headers: { 'Cache-Control': 'private, no-store' } });
  }
}

export function missingSelection(): NextResponse {
  return NextResponse.json({ title: 'Missing project or patient' }, { status: 400 });
}
