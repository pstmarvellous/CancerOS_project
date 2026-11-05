import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  const base = process.env.API_BASE_URL ?? 'http://127.0.0.1:8000';
  const project = new URL(request.url).searchParams.get('project');
  if (!project) return NextResponse.json({title: 'Missing project'}, {status: 400});
  const url = new URL(`/api/v1/projects/${encodeURIComponent(project)}/source-patient-resolutions`, base);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
    return NextResponse.json({title: 'Invalid API configuration'}, {status: 500});
  }
  const authorization = request.headers.get('authorization');
  try {
    const response = await fetch(url, {
      method: 'POST',
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
      headers: {...(authorization ? {authorization} : {}), 'content-type': 'application/json'},
      body: await request.text(),
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
