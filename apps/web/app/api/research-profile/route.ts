import { researchProxy } from '../../../lib/research-proxy';
export const dynamic = 'force-dynamic';
export async function GET(request: Request) { return researchProxy(request, 'research-profile', true); }
export async function POST(request: Request) { return researchProxy(request, 'research-profile', true); }
