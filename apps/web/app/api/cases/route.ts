import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const base = process.env.API_BASE_URL ?? 'http://127.0.0.1:8000';
  const incoming = new URL(request.url);
  const project = incoming.searchParams.get('project');
  if (!project) return NextResponse.json({title: 'Missing project', code: 'MISSING_PROJECT'}, {status: 400});
  const url = new URL(`/api/v1/projects/${encodeURIComponent(project)}/patients`, base);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
    return NextResponse.json({title: 'Invalid API configuration'}, {status: 500});
  }
  const authorization = request.headers.get('authorization');
  try {
    const response = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(8000),
      headers: authorization ? {authorization} : {},
    });
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: {'content-type': 'application/json', 'Cache-Control': 'private, no-store'},
    });
  } catch {
    return NextResponse.json({title: 'API process unavailable'}, {status: 502});
  }
}
