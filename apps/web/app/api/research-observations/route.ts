import { researchProxy } from '../../../lib/research-proxy';
export const dynamic = 'force-dynamic';
export async function POST(request: Request) { return researchProxy(request, 'manual-observations', true); }
