import { NextResponse } from 'next/server';
import { proxyCase } from './case-proxy';
const UUID = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;
export async function researchProxy(request: Request, suffix: string, patientOwned = false) {
  const incoming = new URL(request.url);
  const project = incoming.searchParams.get('project') ?? '';
  const patient = incoming.searchParams.get('patient') ?? '';
  if (!UUID.test(project) || patientOwned && !UUID.test(patient) || [...incoming.searchParams.keys()].some(key => incoming.searchParams.getAll(key).length > 1)) return NextResponse.json({title:'Select a valid research project and case'}, {status:400, headers:{'Cache-Control':'private, no-store'}});
  const url = new URL(`/api/v1/projects/${project}${patientOwned ? `/patients/${patient}` : ''}/${suffix}`, process.env.API_BASE_URL ?? 'http://127.0.0.1:8000');
  if (!['http:','https:'].includes(url.protocol) || url.username || url.password) return NextResponse.json({title:'Invalid research service configuration'}, {status:500});
  for (const key of ['cursor','search']) { const value = incoming.searchParams.get(key); if (value) url.searchParams.set(key,value); }
  return proxyCase(request, url, request.method, request.method === 'GET' ? undefined : await request.text());
}
