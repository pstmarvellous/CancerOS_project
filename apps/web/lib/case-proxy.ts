import { NextResponse } from 'next/server';

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
  const authorization = request.headers.get('authorization');
  if (authorization) headers.authorization = authorization;
  const idempotency = request.headers.get('idempotency-key');
  if (idempotency) headers['idempotency-key'] = idempotency;
  const match = request.headers.get('if-match');
  if (match) headers['if-match'] = match;
  return headers;
}

export async function proxyCase(request: Request, url: URL, method: string, bodyText?: string) {
  try {
    const headers = forwardHeaders(request);
    if (bodyText !== undefined) headers['content-type'] = 'application/json';
    const response = await fetch(url, {
      method,
      headers,
      body: bodyText,
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
    });
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { 'content-type': 'application/json', 'Cache-Control': 'private, no-store' },
    });
  } catch {
    return NextResponse.json({ title: 'API process unavailable' }, { status: 502 });
  }
}

export function missingSelection(): NextResponse {
  return NextResponse.json({ title: 'Missing project or patient' }, { status: 400 });
}
