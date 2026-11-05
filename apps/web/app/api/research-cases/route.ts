import { researchProxy } from '../../../lib/research-proxy';
export const dynamic = 'force-dynamic';
export async function GET(request: Request) { return researchProxy(request, new URL(request.url).searchParams.get('view') === 'sources' ? 'research-case-sources' : 'research-cases'); }
export async function POST(request: Request) { return researchProxy(request, 'research-cases'); }
