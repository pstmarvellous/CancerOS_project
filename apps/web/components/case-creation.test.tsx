import { fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CaseCreator } from './case-creator';
import { ObservationIntake } from './observation-intake';
const push=vi.fn();
vi.mock('next/navigation',()=>({useRouter:()=>({push})}));
const source={source_version_id:'10000000-0000-0000-0000-000000000001',title:'Synthetic source',origin:'synthetic_engineering_fixture' as const,creation_permitted:true,clinical_entry_permitted:true,reason:'allowed'};
afterEach(()=>{cleanup();vi.unstubAllGlobals();push.mockReset();});
describe('Research case creation and clinical entry',()=>{
  it('keeps unavailable source and role states explicit',()=>{
    const {rerender}=render(<CaseCreator project="p" sources={[]} allowed/>);
    expect(screen.getByText(/No eligible source/)).toBeVisible();
    rerender(<CaseCreator project="p" sources={[source]} allowed={false}/>);
    expect(screen.getByText(/Admin role required/)).toBeVisible();
  });
  it('uses server-generated patient identity and retains idempotency on retry',async()=>{
    const fetch=vi.fn().mockResolvedValueOnce(new Response('{}',{status:409})).mockResolvedValueOnce(new Response(JSON.stringify({patient_id:'20000000-0000-0000-0000-000000000002'})));
    vi.stubGlobal('fetch',fetch);
    render(<CaseCreator project="p" sources={[source]} allowed/>);
    fireEvent.change(screen.getByLabelText(/Research case identifier/),{target:{value:'STUDY-042'}});
    fireEvent.change(screen.getByLabelText(/Case title/),{target:{value:'Research label'}});
    fireEvent.change(screen.getByLabelText(/Source pseudonym/),{target:{value:'Participant 042'}});
    fireEvent.change(screen.getByLabelText(/Profile source reference/),{target:{value:'Register row 42'}});
    fireEvent.submit(screen.getByRole('form',{name:'Create research case'}));
    await screen.findByText(/identifier already exists/);
    expect(screen.getByDisplayValue('STUDY-042')).toBeVisible();
    fireEvent.submit(screen.getByRole('form',{name:'Create research case'}));
    await waitFor(()=>expect(push).toHaveBeenCalled());
    expect(fetch.mock.calls[0][1].headers['idempotency-key']).toBe(fetch.mock.calls[1][1].headers['idempotency-key']);
    expect(JSON.parse(fetch.mock.calls[0][1].body)).not.toHaveProperty('patient_id');
  });
  it('refuses empty numeric value and never turns it into zero',async()=>{
    const fetch=vi.fn();vi.stubGlobal('fetch',fetch);
    render(<ObservationIntake project="p" patient="u" revision={1} origin="real_source" onSaved={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText(/Source original term/),{target:{value:'Documented HGB'}});
    fireEvent.change(screen.getByLabelText(/Source reference/),{target:{value:'Report row 1'}});
    fireEvent.change(screen.getByLabelText(/Collection date/),{target:{value:'2026-11-01'}});
    fireEvent.submit(screen.getByRole('form',{name:'Save clinical observation'}));
    expect(await screen.findByText(/finite decimal/)).toBeVisible();expect(fetch).not.toHaveBeenCalled();
  });
  it('saves exact decimal strings through the canonical manual endpoint',async()=>{
    const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({status:'accepted',accepted_count:1})));vi.stubGlobal('fetch',fetch);
    const onSaved=vi.fn();render(<ObservationIntake project="p" patient="u" revision={3} origin="real_source" onSaved={onSaved}/>);
    fireEvent.change(screen.getByLabelText(/Source original term/),{target:{value:'Documented HGB'}});
    fireEvent.change(screen.getByLabelText(/Source reference/),{target:{value:'Report row 1'}});
    fireEvent.change(screen.getByLabelText(/Collection date/),{target:{value:'2026-11-01'}});
    fireEvent.change(screen.getByLabelText(/Measured value/),{target:{value:'13.200000001'}});
    fireEvent.submit(screen.getByRole('form',{name:'Save clinical observation'}));
    await waitFor(()=>expect(onSaved).toHaveBeenCalled());
    const body=JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.observation.result.quantity.value).toBe('13.200000001');
    expect(body.expected_revision).toBe(3);
    expect(body.observation).not.toHaveProperty('source_locator_id');
    expect(body.observation).not.toHaveProperty('origin');
  });
  it('retains missingness instead of a numeric quantity',async()=>{
    const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({status:'accepted',accepted_count:1})));vi.stubGlobal('fetch',fetch);
    render(<ObservationIntake project="p" patient="u" revision={1} origin="real_source" onSaved={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText(/Source original term/),{target:{value:'Documented HGB'}});
    fireEvent.change(screen.getByLabelText(/Source reference/),{target:{value:'Report row 1'}});
    fireEvent.change(screen.getByLabelText(/Collection date/),{target:{value:'2026-11-01'}});
    fireEvent.change(screen.getByLabelText('Result type'),{target:{value:'missing'}});
    fireEvent.submit(screen.getByRole('form',{name:'Save clinical observation'}));
    await waitFor(()=>expect(fetch).toHaveBeenCalled());
    const body=JSON.parse(fetch.mock.calls[0][1].body);expect(body.observation.result).toEqual({form:'missing',missing_reason:'not_recorded'});
  });
  it('does not claim quarantined observations were saved',async()=>{
    const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({status:'quarantined',accepted_count:0})));vi.stubGlobal('fetch',fetch);
    const onSaved=vi.fn();render(<ObservationIntake project="p" patient="u" revision={1} origin="real_source" onSaved={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText(/Source original term/),{target:{value:'Documented HGB'}});
    fireEvent.change(screen.getByLabelText(/Source reference/),{target:{value:'Report row 1'}});
    fireEvent.change(screen.getByLabelText(/Collection date/),{target:{value:'2026-11-01'}});
    fireEvent.change(screen.getByLabelText(/Measured value/),{target:{value:'13.2'}});
    fireEvent.submit(screen.getByRole('form',{name:'Save clinical observation'}));
    await screen.findByText(/not added/);expect(onSaved).not.toHaveBeenCalled();
  });
});
