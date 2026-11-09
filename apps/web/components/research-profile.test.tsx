import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { ResearchProfile } from './research-profile';
const profile = (patient_id:string, title:string) => ({patient_id,title,case_identifier:patient_id,pseudonym:'Research pseudonym',profile_revision:1,origin:'synthetic',status:'draft',sex:'not_recorded',age_at_observation:null,age_observed_on:null,medical_history:null,profile_source_reference:'Artificial fixture',created_at:'2026-11-01',updated_at:'2026-11-01'});
afterEach(()=>vi.unstubAllGlobals());
it('clears the previous case and ignores a delayed response after selection changes', async()=>{
  let finish!: (value:Response)=>void;
  vi.stubGlobal('fetch',vi.fn((url:string)=> url.includes('patient=A') ? new Promise<Response>(resolve=>{finish=resolve;}) : Promise.resolve(Response.json(url.includes('research-session') ? {projects:[{project_id:'P',role:'admin'}]} : profile('B','Case B')))));
  const loaded=vi.fn();
  const view=render(<ResearchProfile project="P" patient="A" onLoaded={loaded}/>);
  view.rerender(<ResearchProfile project="P" patient="B" onLoaded={loaded}/>);
  expect(await screen.findByText('Case B')).toBeVisible();
  await act(async()=>finish(Response.json(profile('A','Case A'))));
  expect(screen.queryByText('Case A')).not.toBeInTheDocument();
  expect(loaded).toHaveBeenCalledTimes(1);
});
it('publishes the saved profile revision to the containing workspace', async()=>{
  const loaded=vi.fn();
  vi.stubGlobal('fetch',vi.fn((url:string,init?:RequestInit)=>Promise.resolve(Response.json(url.includes('research-session') ? {projects:[{project_id:'P',role:'admin'}]} : init?.method==='POST' ? {...profile('A','Saved case'),profile_revision:2} : profile('A','Case A')))));
  render(<ResearchProfile project="P" patient="A" onLoaded={loaded}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Edit profile'}));
  fireEvent.change(screen.getByRole('textbox',{name:/Case title/}),{target:{value:'Saved case'}});
  fireEvent.submit(screen.getByRole('form',{name:'Edit research profile'}));
  await waitFor(()=>expect(loaded).toHaveBeenLastCalledWith(expect.objectContaining({title:'Saved case',profile_revision:2}),true));
});
