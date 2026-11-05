import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CaseWorkspace } from './case-workspace';

const query = vi.hoisted(() => ({ search: '' }));
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(query.search),
}));

const DETAIL = {
  patient_id: '11111111-1111-1111-1111-111111111111',
  display_code: 'CASE-01',
  data_revision: 3,
  observation_count: 2,
  visit_count: 1,
  next_action: 'review_observations_or_stage_source_update',
};

function stubFetch() {
  const record={id:'22222222-2222-2222-2222-222222222222',item:{kind:'diagnosis',concept:'source_pathology',original_term:'Source pathology',side:'unknown',er_status:'not_recorded',pr_status:'not_recorded',her2_status:'not_recorded',time:{reference:{basis:'unknown',time_domain:'source_calendar',missing_reason:'not_recorded'},precision:'unknown'}},origin:'REAL_OBSERVED',context:'OBSERVED',publication:'draft',availability:'available',quality:'pass'};
  return vi.fn(async(input:unknown)=>{
    const url=String(input);
    let body:unknown;
    if(url.startsWith('/api/case-detail'))body=DETAIL;
    else if(url.startsWith('/api/case-visits'))body={items:[],next_action:'none'};
    else if(url.startsWith('/api/case-record'))body=record;
    else if(url.startsWith('/api/research-session'))body={projects:[]};
    else if(url.startsWith('/api/case-imaging'))body={studies:{items:[]},segmentations:[],segmentation_status:'not_loaded'};
    else if(url.startsWith('/api/research-profile'))body={title:'CASE-01',case_identifier:'CASE-01',pseudonym:'Research 01',origin:'real_source',sex:'not_recorded',status:'draft',profile_revision:1,profile_source_reference:'Source row 1',created_at:'2026-01-01T12:00:00Z',updated_at:'2026-01-01T12:00:00Z'};
    else body={items:[{record_id:record.id,kind:'diagnosis',concept:'source_pathology',source_hash:'a'.repeat(64),superseded:false}],snapshot_cursor:'b'.repeat(64)};
    return {ok:true,text:async()=>JSON.stringify(body),json:async()=>body};
  });
}

describe('COS-074 case workspace', () => {
  it('requires an explicit project and patient selection', () => {
    query.search = '';
    render(<CaseWorkspace />);
    expect(screen.getByText(/No case selected/)).toBeVisible();
  });

  it('shows observed facts with unknown values as not recorded', async () => {
    query.search = '?project=33333333-3333-3333-3333-333333333333&patient=11111111-1111-1111-1111-111111111111';
    vi.stubGlobal('fetch', stubFetch());
    render(<CaseWorkspace />);
    expect(await screen.findByRole('heading', { name: 'CASE-01' }, { timeout: 10000 })).toBeVisible();
    expect(screen.getByText(/Unknown values stay/)).toBeVisible();
    expect(screen.getAllByText('Not recorded').length).toBeGreaterThan(0);
    const toggle = await screen.findByText(/diagnosis · source_pathology/);
    fireEvent.click(toggle);
    await waitFor(() => expect(screen.getByText(/exact record revision/)).toBeVisible());
    vi.unstubAllGlobals();
  });
});
