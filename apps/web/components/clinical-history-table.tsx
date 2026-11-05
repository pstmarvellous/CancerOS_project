'use client';
import { useEffect,useState } from 'react';
import type { components } from '../../../packages/contracts/generated/api';
import Link from 'next/link';
import { researchJson,researchError } from '../lib/research-client';
import { clinicalTime,clinicalValue } from '../lib/clinical-presentation';
import { ErrorSummary,LoadingState } from './research';
type S=components['schemas'];
export function ClinicalHistoryTable({project,patient,onCorrect}:{project:string;patient:string;onCorrect?:(record:S['ClinicalRecord'])=>void}){
  const [records,setRecords]=useState<S['ClinicalRecord'][]|null>(null);
  const [superseded,setSuperseded]=useState<Set<string>>(new Set());
  const [error,setError]=useState('');
  useEffect(()=>{
    const controller=new AbortController();
    void(async()=>{
      try{
        const page=await researchJson<S['ObservationPage']>(`/api/case-observations?project=${project}&patient=${patient}`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({limit:100}),signal:controller.signal});
        if(!controller.signal.aborted)setSuperseded(new Set(page.items.filter(item=>item.superseded).map(item=>item.record_id)));
        const values=await Promise.all(page.items.map(item=>researchJson<S['ClinicalRecord']>(`/api/case-record?project=${project}&patient=${patient}&record=${item.record_id}`,{signal:controller.signal})));
        if(!controller.signal.aborted)setRecords(values.sort((a,b)=>{
          const left=a.item.time.reference,right=b.item.time.reference;
          const group=(r:typeof left)=>`${r.time_domain}:${r.basis}${r.basis==='relative_day'?`:${r.timeline_origin_id??r.anchor_state_id}`:''}`;
          if(group(left)!==group(right))return group(left).localeCompare(group(right));
          if(left.basis==='date'&&right.basis==='date')return left.value.localeCompare(right.value);
          if(left.basis==='timestamp'&&right.basis==='timestamp')return Date.parse(left.value)-Date.parse(right.value);
          if(left.basis==='relative_day'&&right.basis==='relative_day')return Number(left.value)-Number(right.value);
          return 0;
        }));
      }catch(cause){if(!controller.signal.aborted)setError(researchError(cause));}
    })();
    return()=>controller.abort();
  },[project,patient]);
  return <section className="card workspace-section" aria-label="Clinical observation timeline"><div className="section-heading"><h2>Clinical observation timeline</h2><Link href={`/charts?project=${project}&patient=${patient}`}>Clinical charts →</Link></div><p className="field-hint">Source collection times are retained; unknown times stay unplaced. This view shows up to 100 accepted records and their revision status. Saving an observation does not publish a new scientific snapshot.</p>
    {error&&<ErrorSummary message={error}/>}{!records&&!error&&<LoadingState/>}
    {records&&!records.length&&<p>No clinical observations recorded yet. Add your first source-supported observation below.</p>}
    {records&&records.length>0&&<div className="table-scroll"><table><caption>Saved clinical observations and source times</caption><thead><tr><th scope="col">Collected</th><th scope="col">Observation</th><th scope="col">Value / missingness</th><th scope="col">Provenance / status</th></tr></thead><tbody>{records.map(record=><tr key={record.id}><td>{clinicalTime(record)}</td><td>{record.item.original_term}<small>{record.item.kind} · {record.item.concept.replaceAll('_',' ')}</small>{record.source_reference&&<small>Source: {record.source_reference}</small>}</td><td>{clinicalValue(record)}</td><td>{record.origin==='SYNTHETIC_GENERATED'?'Synthetic engineering':'Source observation'}<small>{superseded.has(record.id)?'Superseded · history retained':`${record.context} · ${record.availability} · ${record.publication}`}</small>{onCorrect&&!superseded.has(record.id)&&(record.item.kind==='laboratory'||record.item.kind==='vital')&&record.availability==='available'&&<button className="button-ghost" onClick={()=>onCorrect(record)}>Correct observation</button>}</td></tr>)}</tbody></table></div>}
  </section>;
}
