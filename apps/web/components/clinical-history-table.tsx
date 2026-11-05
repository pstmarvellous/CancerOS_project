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
  return <section className="card workspace-section" aria-label="Clinical observation timeline"><div className="section-heading"><div><h2>Clinical observation timeline</h2><p className="field-hint" style={{margin:0}}>Source times retained, unknown unplaced — up to 100 records, revision status shown.</p></div><Link className="button-ghost" href={`/charts?project=${project}&patient=${patient}`}>Clinical charts →</Link></div>
    {error&&<ErrorSummary message={error}/>}{!records&&!error&&<LoadingState/>}
    {records&&!records.length&&<div className="card" style={{padding:16, borderStyle:'dashed'}}><h3 style={{margin:'0 0 8px'}}>No observations yet</h3><p>Add your first source-backed observation below. Fields are progressive: what → when & source → values. Missing stays missing; DCE phases are not visits.</p></div>}
    {records&&records.length>0&&<><p className="field-hint">{records.length} saved observation{records.length===1?'':'s'} — newest save refreshes this list. Saving does not publish a new scientific snapshot.</p><div className="table-scroll" style={{overflowX:'auto'}}><table style={{width:'100%', fontSize:14}}><caption style={{textAlign:'left', fontSize:12, color:'#64748b', marginBottom:8}}>Saved observations — what, when, value, provenance</caption><thead><tr><th scope="col">Collected</th><th scope="col">Observation</th><th scope="col">Value / missingness</th><th scope="col">Provenance</th></tr></thead><tbody>{records.map(record=><tr key={record.id}><td style={{whiteSpace:'nowrap'}}>{clinicalTime(record)}</td><td><strong>{record.item.original_term}</strong><br/><small style={{color:'#64748b'}}>{record.item.kind} · {record.item.concept.replaceAll('_',' ')}</small>{record.source_reference&&<><br/><small style={{color:'#94a3b8'}}>Source: {record.source_reference.slice(0,120)}</small></>}</td><td>{clinicalValue(record)}</td><td><span className={`badge ${record.origin==='SYNTHETIC_GENERATED'?'simulated':'observed'}`} style={{fontSize:11}}>{record.origin==='SYNTHETIC_GENERATED'?'Synthetic':'Source'}</span><br/><small style={{color:'#64748b'}}>{superseded.has(record.id)?'Superseded · history retained':`${record.context} · ${record.availability}`}</small>{onCorrect&&!superseded.has(record.id)&&(record.item.kind==='laboratory'||record.item.kind==='vital')&&record.availability==='available'&&<><br/><button className="button-ghost" style={{marginTop:4, minHeight:32, fontSize:12}} onClick={()=>onCorrect(record)}>Correct</button></>}</td></tr>)}</tbody></table></div></>}
  </section>;
}
