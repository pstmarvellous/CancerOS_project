import { act, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ClinicalChartsExplorer } from './clinical-charts-explorer';

const query = vi.hoisted(() => ({ search: '' }));
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(query.search),
}));

const PROJECT = '11111111-1111-1111-1111-111111111111';
const PATIENT = '22222222-2222-2222-2222-222222222222';
const RECORD = '33333333-3333-3333-3333-333333333333';

function stubFetch() {
  return vi.fn(async (input: unknown) => {
    const url = String(input);
    if (url.includes('/api/clinical-charts')) {
      return {
        ok: true,
        text: async () =>
          JSON.stringify({
            items: [{ record_id: RECORD, kind: 'laboratory', concept: 'hemoglobin', source_hash: 'a'.repeat(64), superseded: false }],
            snapshot_cursor: 'b'.repeat(64),
          }),
      };
    }
    if (url.includes('/api/case-record')) {
      return {
        ok: true,
        text: async () =>
          JSON.stringify({
            id: RECORD,
            item: { kind: 'laboratory', concept: 'hemoglobin', original_term: 'Hemoglobin', original_unit: 'g/dL', original_value: '9.123456789' },
            availability: 'available',
            origin: 'REAL_OBSERVED',
            quality: { status: 'verified' },
          }),
      };
    }
    return { ok: false, status: 404, text: async () => '{}' };
  });
}

describe('COS-077 clinical charts explorer', () => {
  it('asks for a case instead of guessing one', () => {
    query.search = '';
    render(<ClinicalChartsExplorer />);
    expect(screen.getByText(/Open a case to inspect its clinical charts/)).toBeVisible();
  });

  it('loads bounded history and preserves exact decimal strings', async () => {
    query.search = `?project=${PROJECT}&patient=${PATIENT}`;
    vi.stubGlobal('fetch', stubFetch());
    render(<ClinicalChartsExplorer />);
    await waitFor(() => expect(screen.getByText(/authorized records across/)).toBeVisible(), { timeout: 10000 });
    expect(screen.getAllByText(/9.123456789/).length).toBeGreaterThan(0);
    vi.unstubAllGlobals();
  }, 15000);
});

it('rebinds to a changed case and ignores the old delayed chart batch', async()=>{
  query.search='';
  let finish!: (response:Response)=>void;
  const fetcher=vi.fn((url:unknown)=>String(url).includes(`patient=${PATIENT}`) ? new Promise<Response>(resolve=>{finish=resolve;}) : Promise.resolve(Response.json({items:[],snapshot_cursor:null})));
  vi.stubGlobal('fetch',fetcher);
  const view=render(<ClinicalChartsExplorer project={PROJECT} patient={PATIENT}/>);
  view.rerender(<ClinicalChartsExplorer project={PROJECT} patient="44444444-4444-4444-4444-444444444444"/>);
  expect(await screen.findByText(/No laboratory, vital, symptom or treatment records/)).toBeVisible();
  await act(async()=>finish(Response.json({items:[{record_id:RECORD,kind:'laboratory',concept:'stale protected concept'}]})));
  expect(screen.queryByText(/stale protected concept/)).not.toBeInTheDocument();
  expect(fetcher).toHaveBeenCalledTimes(2);
  vi.unstubAllGlobals();
});

it('retains superseded revisions in the exact table while omitting them from plots',async()=>{
  query.search=`?project=${PROJECT}&patient=${PATIENT}`;
  const original=stubFetch();
  vi.stubGlobal('fetch',vi.fn(async (input:unknown)=>String(input).includes('clinical-charts') ? Response.json({items:[{record_id:RECORD,kind:'laboratory',concept:'hemoglobin',superseded:true}],snapshot_cursor:null}) : original(input)));
  render(<ClinicalChartsExplorer/>);
  expect(await screen.findByText(/REAL_OBSERVED · superseded/)).toBeVisible();
  expect(screen.getByRole('table')).toHaveTextContent('9.123456789');
  expect(screen.queryByRole('img',{name:/observations; exact values/})).not.toBeInTheDocument();
  vi.unstubAllGlobals();
});
