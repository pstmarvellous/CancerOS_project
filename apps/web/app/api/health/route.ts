export const dynamic = 'force-dynamic';

export async function GET() {
  const base = process.env.API_BASE_URL ?? 'http://127.0.0.1:8000';
  try {
    const url = new URL('/health/live', base);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error('Invalid API configuration');
    const response = await fetch(url, {cache: 'no-store', signal: AbortSignal.timeout(3000)});
    if (!response.ok) throw new Error('Unavailable');
    const value = await response.json();
    if (value.status !== 'ok') throw new Error('Invalid health response');
    return Response.json({status: 'ok'}, {headers: {'Cache-Control': 'private, no-store'}});
  } catch {
    return Response.json({status: 'unavailable'}, {status: 503, headers: {'Cache-Control': 'private, no-store'}});
  }
}
