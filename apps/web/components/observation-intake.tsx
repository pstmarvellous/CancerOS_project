'use client';
import { useState } from 'react';
import { ErrorSummary } from './research';
import { researchJson, researchError } from '../lib/research-client';
import { TermHelp } from './term-help';
import type { components } from '../../../packages/contracts/generated/api';

const concepts = {
  laboratory:['hemoglobin','wbc','anc','platelets','creatinine','alt','ast'],
  vital:['heart_rate','temperature','weight','systolic_bp','diastolic_bp'],
  symptom:['fatigue','pain','nausea','swelling','other'],
  treatment:['chemotherapy','endocrine','her2_targeted','immunotherapy','surgery','radiotherapy','other','unknown'],
  diagnosis:['source_pathology'], visit:['clinical_visit','imaging_exam','source_occasion','unknown'], note:['source_note'],
};
const units:Record<string,string[]> = {hemoglobin:['g/dL','g/L'],wbc:['10[9]/L'],anc:['10[9]/L'],platelets:['10[9]/L'],creatinine:['mg/dL'],alt:['U/L'],ast:['U/L'],heart_rate:['/min'],temperature:['Cel'],weight:['kg'],systolic_bp:['mmHg'],diastolic_bp:['mmHg']};
type Kind = keyof typeof concepts;
const labels:Record<Kind,{label:string; hint:string}> = {
  laboratory:{label:'Laboratory', hint:'Blood counts, chemistry — exact value with unit'},
  vital:{label:'Vital signs', hint:'Heart rate, temp, weight, BP'},
  symptom:{label:'Symptoms', hint:'Fatigue, pain, nausea — presence + severity'},
  treatment:{label:'Treatment event', hint:'Chemo, endocrine, surgery — recorded event only'},
  diagnosis:{label:'Cancer diagnosis', hint:'Histology, side, ER/PR/HER2, stage'},
  visit:{label:'Visit / exam', hint:'Clinical visit or imaging occasion'},
  note:{label:'Clinical note', hint:'Private source note, no identifiers'},
};

export function ObservationIntake({project,patient,revision,origin,onSaved,correction,onCancelCorrection}:{project:string;patient:string;revision:number;origin:'real_source'|'synthetic_engineering_fixture';onSaved:(message:string)=>void;correction?:components['schemas']['ClinicalRecord']|null;onCancelCorrection?:()=>void}) {
  const initial=correction?.item;
  const quantity=initial && (initial.kind==='laboratory'||initial.kind==='vital') ? initial.result : null;
  const [step, setStep] = useState<1|2|3>(1);
  const [kind,setKind]=useState<Kind>(initial?.kind ? initial.kind as Kind : 'laboratory');
  const [concept,setConcept]=useState<string>(typeof initial?.concept === 'string' ? initial.concept : 'hemoglobin');
  const [result,setResult]=useState<string>(quantity?.form ?? 'exact');
  const basis=initial?.time?.reference?.basis;
  const [timeBasis,setTimeBasis]=useState<string>(basis==='date'||basis==='timestamp'?basis:'date');
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [key,setKey]=useState(()=>crypto.randomUUID());
  const numeric=kind==='laboratory'||kind==='vital';

  async function save(event:React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if(busy)return;
    const form=event.currentTarget, data=new FormData(form);
    const get=(k:string)=>String(data.get(k)??'').trim();
    setError('');
    const domain=origin==='synthetic_engineering_fixture'?'simulation':'source_calendar';
    const time = timeBasis==='unknown' ? {reference:{basis:'unknown',time_domain:domain,missing_reason:'not_recorded'},precision:'unknown'} : {reference:{basis:timeBasis,value:get('time'),time_domain:domain},precision:timeBasis==='date'?'day':'second'};
    if (timeBasis==='timestamp' && !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(get('time'))) {setError('Enter documented timestamp with seconds and timezone, e.g., 2026-11-05T09:30:00+01:00.');return;}
    if (!get('source') || !get('term')) { setError('Source reference and original term are required.'); return; }
    const observation:Record<string,unknown>={kind,concept,time,original_term:get('term'),certainty:get('certainty'),negation:get('negation')};
    if(numeric){
      if(result!=='missing' && (!/^-?(0|[1-9]\d*)(\.\d{1,9})?$/.test(get('value')) || !Number.isFinite(Number(get('value'))) || Math.abs(Number(get('value')))>=1e15)){setError('Enter finite decimal ≤9 decimals, or choose missing.');return;}
      observation.result=result==='missing'?{form:'missing',missing_reason:get('missing_reason')}:result==='censored'?{form:'censored',comparator:get('comparator'),threshold:{value:get('value'),unit:get('unit')}}:{form:'exact',quantity:{value:get('value'),unit:get('unit')}};
      if(result!=='missing'){observation.original_value=(result==='censored'?get('comparator'):'')+get('value');observation.original_unit=get('unit');}
    } else if(kind==='symptom'){
      Object.assign(observation,{presence:get('presence'),reporter:get('reporter')});
      if(get('severity')){
        if(!/^-?(0|[1-9]\d*)(\.\d{1,9})?$/.test(get('severity'))||!get('instrument')||!get('instrument_version')){setError('Severity requires decimal + instrument name + version.');return;}
        Object.assign(observation,{severity:get('severity'),instrument:get('instrument'),instrument_version:get('instrument_version')});
      }
    } else if(kind==='treatment'){
      Object.assign(observation,{event_type:get('event_type'),exposure_status:get('exposure_status'),regimen_text:get('regimen')||null});
    } else if(kind==='diagnosis'){
      Object.assign(observation,{histology:get('histology')||null,side:get('side'),er_status:get('er'),pr_status:get('pr'),her2_status:get('her2'),clinical_stage:get('clinical_stage')||null,pathologic_stage:get('pathologic_stage')||null,staging_system:get('staging_system')||null});
    } else if(kind==='visit') observation.label=get('label');
    else { delete observation.concept; observation.text=get('note'); }
    setBusy(true);
    try{
      const report=await researchJson<{status:string;accepted_count:number;next_action:string}>(`/api/research-observations?project=${project}&patient=${patient}`,{method:'POST',headers:{'content-type':'application/json','idempotency-key':key},body:JSON.stringify({expected_revision:revision,source_reference:get('source'),observation,...(correction?{corrects_record_id:correction.id}:{})})});
      if(report.status!=='accepted')throw new Error(`Observation was ${report.status}; not added. Review fields.`);
      (form as HTMLFormElement).reset();setKey(crypto.randomUUID());onSaved(`Saved ${report.accepted_count} observation — history refreshed.`);
      setStep(1);
    }catch(cause){setError(researchError(cause));}finally{setBusy(false);}
  }

  return <section className="card workspace-section" aria-label="Clinical observation entry">
    <p className="eyebrow">SOURCE-BACKED DATA ENTRY — PROGRESSIVE FORM</p>
    <h2>Add a clinical observation</h2>
    <p className="field-hint">All sections remain visible so nothing is hidden from assistive tech; the stepper highlights where you are. Enter documented values only. Source, time, revision retained.</p>
    {correction&&<p role="status">Correcting {correction.item.original_term}. Saving appends replacement; original retained. <button className="button-ghost" onClick={onCancelCorrection}>Cancel correction</button></p>}
    <div style={{display:'flex', gap:8, marginBottom:16}} aria-hidden="true">
      <span className={`badge ${step>=1?'observed':'warning'}`}>1. What</span>
      <span className={`badge ${step>=2?'observed':'warning'}`}>2. When & source</span>
      <span className={`badge ${step>=3?'observed':'warning'}`}>3. Values</span>
    </div>
    {origin === 'synthetic_engineering_fixture'
      ? <p role="note" className="field-hint"><strong>Artificial demonstration record.</strong> Saved entries are labeled synthetic and never presented as authentic clinical observations.</p>
      : <p role="note" className="field-hint"><strong>Source-backed research record.</strong> Enter documented values exactly as written in the source.</p>}    <div role="status" className="field-hint" style={{marginBottom:12}}>Currently on step {step} of 3 — Continue buttons advance; Back returns without losing entries.</div>
    <form onSubmit={save} onChange={()=>setKey(crypto.randomUUID())} aria-label="Save clinical observation">
      <section className="card" style={{padding:16, marginBottom:12}} aria-label="Step 1 — what kind of observation">
        <div style={{display:'flex', gap:8, alignItems:'center'}}><h3 style={{margin:0}}>What kind of observation?</h3><span className="badge observed">Step 1 of 3</span></div>
        <h3>What kind of observation?</h3>
        <p className="field-hint">Pick category, then specific concept. Lab = blood work, vital = physiology, etc.</p>
        <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(180px,1fr))', gap:8, marginTop:12}}>
          {(Object.keys(labels) as Kind[]).map(k=> <button type="button" key={k} className={kind===k ? 'button-secondary' : 'button-ghost'} style={{textAlign:'left', minHeight:72, display:'flex', flexDirection:'column', alignItems:'flex-start', gap:2}} onClick={()=>{setKind(k); setConcept(concepts[k][0]); setError('');}}>
            <strong>{labels[k].label}</strong><span style={{fontSize:11, color:'var(--muted)', fontWeight:400, textAlign:'left'}}>{labels[k].hint}</span>
          </button>)}
        </div>
        <label style={{marginTop:16, display:'flex', flexDirection:'column', gap:6, fontWeight:600, fontSize:14}}>Specific concept
          <select value={concept} onChange={e=>setConcept(e.target.value)}>{concepts[kind].map(v=><option key={v} value={v}>{v.replaceAll('_',' ')}</option>)}</select>
        </label>
        <div style={{marginTop:12}}><button type="button" className="button-primary" onClick={()=>setStep(2)}>Continue to time & source</button></div>
      </section>

      <section className="card" style={{padding:16, marginBottom:12}} aria-label="Step 2 — when and source">
        <div style={{display:'flex', gap:8, alignItems:'center'}}><h3 style={{margin:0}}>When and where documented?</h3><span className="badge observed">Step 2 of 3</span></div>
        <h3>When and where documented?</h3>
        <p className="field-hint">Original term = exact label from report. Source ref = page/entry locator.</p>
        <div className="form-grid">
          <label>Source original term *<input name="term" required maxLength={300} placeholder="e.g., HGB 13.2 g/dL" defaultValue={initial?.original_term}/><span className="field-hint">Exact observed label.</span></label>
          <label>Source reference *<input name="source" required maxLength={500} placeholder="Source report / page / entry" defaultValue={correction?.source_reference??''}/><span className="field-hint">Where documented.</span></label>
          <label>Time precision<select value={timeBasis} onChange={e=>setTimeBasis(e.target.value)}><option value="date">Date only</option><option value="timestamp">Exact timestamp with TZ</option><option value="unknown">Not recorded</option></select></label>
          {timeBasis!=='unknown'&&<label>{timeBasis==='date'?'Collection date *':'Timestamp with TZ *'}<input key={timeBasis} name="time" type={timeBasis==='date'?'date':'text'} required placeholder={timeBasis==='date'?'2025-06-12':'2026-11-05T09:30:00+01:00'} defaultValue={initial?.time?.reference?.basis!=='unknown'&&initial?.time?.reference && 'value' in initial.time.reference?String((initial.time.reference as {value:string}).value):''}/></label>}
          <label>Certainty<select name="certainty" defaultValue={initial?.certainty??'documented'}><option value="documented">Documented</option><option value="reported">Reported</option><option value="uncertain">Uncertain</option><option value="unknown">Unknown</option></select></label>
          <label>Assertion<select name="negation" defaultValue={initial?.negation??'affirmed'}><option value="affirmed">Affirmed</option><option value="negated">Negated</option><option value="unspecified">Unspecified</option></select></label>
        </div>
        <div style={{display:'flex', gap:8, marginTop:12}}><button type="button" className="button-ghost" onClick={()=>setStep(1)}>Back</button><button type="button" className="button-primary" onClick={()=>setStep(3)}>Continue to values</button></div>
      </section>

      <section className="card" style={{padding:16}} aria-label="Step 3 — values">
        <div style={{display:'flex', gap:8, alignItems:'center'}}><h3 style={{margin:0}}>Enter values</h3><span className="badge simulated">Step 3 of 3</span></div>
        <h3>Enter values</h3>
        <fieldset disabled={busy} style={{border:0, padding:0}}>
          <legend style={{fontSize:14, fontWeight:600}}>Values for {labels[kind].label.toLowerCase()}</legend>
          {numeric&&<div className="form-grid"><label>Result type<select value={result} onChange={e=>setResult(e.target.value)}><option value="exact">Exact value</option><option value="censored">Censored / threshold</option><option value="missing">Missing / not collected</option></select></label>
            {result==='missing'?<label>Missing reason<select name="missing_reason" defaultValue={quantity?.form==='missing'?quantity.missing_reason:'not_recorded'}>{['not_recorded','not_collected','unknown','withheld','not_applicable'].map(v=><option key={v} value={v}>{v.replaceAll('_',' ')}</option>)}</select></label>:<>
              {result==='censored'&&<label>Comparator<select name="comparator" defaultValue={quantity?.form==='censored'?quantity.comparator:'<'}>{['<','<=','>','>='].map(v=><option key={v}>{v}</option>)}</select></label>}
              <label>{result==='censored'?'Threshold *':'Measured value *'}<input name="value" inputMode="decimal" required placeholder="13.2" defaultValue={quantity?.form==='exact'?quantity.quantity.value:quantity?.form==='censored'?quantity.threshold.value:''}/><span className="field-hint">Finite decimal, ≤9 decimals.</span></label>
              <label>Unit<select name="unit" key={concept} defaultValue={quantity?.form==='exact'?quantity.quantity.unit:quantity?.form==='censored'?quantity.threshold.unit:undefined}>{(units[concept]??[]).map(v=><option key={v}>{v}</option>)}</select></label>
            </>}
          </div>}
          {kind==='symptom'&&<div className="form-grid"><label>Presence<select name="presence">{['present','absent','unknown','not_assessed'].map(v=><option key={v}>{v}</option>)}</select></label><label>Reporter<select name="reporter">{['patient','clinician','unknown'].map(v=><option key={v}>{v}</option>)}</select></label><label>Severity if recorded<input name="severity" inputMode="decimal" placeholder="e.g., 3"/><span className="field-hint">Requires instrument + version if set.</span></label><label>Instrument<input name="instrument" maxLength={100} placeholder="Instrument name"/></label><label>Version<input name="instrument_version" maxLength={50} placeholder="Version"/></label></div>}
          {kind==='treatment'&&<div className="form-grid"><label>Event type<select name="event_type">{['unknown','ordered','prescribed','administered','reported_exposure','stopped'].map(v=><option key={v}>{v}</option>)}</select></label><label>Exposure evidence<select name="exposure_status">{['unknown','ordered_only','documented_delivery','reported'].map(v=><option key={v}>{v}</option>)}</select></label><label>Regimen text<input name="regimen" maxLength={500} placeholder="Source regimen"/><span className="field-hint">Records existing event; does not recommend.</span></label></div>}
          {kind==='diagnosis'&&<div className="form-grid"><label>Histology<input name="histology" maxLength={200} placeholder="Ductal, lobular…"/></label><label>Laterality<select name="side">{['unknown','left','right','bilateral'].map(v=><option key={v}>{v}</option>)}</select></label>{[['er','ER'],['pr','PR'],['her2','HER2']].map(([name,label])=><label key={name}>{label}<select name={name}>{['not_recorded','not_tested','unknown','positive','negative','equivocal','invalid'].map(v=><option key={v}>{v}</option>)}</select></label>)}<label>Clinical stage<input name="clinical_stage" maxLength={100} placeholder="cT2N0M0"/></label><label>Pathologic stage<input name="pathologic_stage" maxLength={100}/></label><label>Staging system<input name="staging_system" maxLength={100} placeholder="AJCC 8th"/><span className="field-hint">Required when stage entered.</span></label></div>}
          {kind==='visit'&&<label style={{display:'flex', flexDirection:'column', gap:6}}>Visit label *<input name="label" required maxLength={200} placeholder="Clinical visit 2025-06-12"/><span className="field-hint">Records occasion; MRI import separate.</span></label>}
          {kind==='note'&&<label style={{display:'flex', flexDirection:'column', gap:6}}>Research note *<textarea name="note" required maxLength={16000} rows={5} placeholder="Research summary, no direct identifiers"/><span className="field-hint">Stored privately; no external AI.</span></label>}
        </fieldset>
        <div style={{marginTop:12, display:'flex', gap:8}}><button type="button" className="button-ghost" onClick={()=>setStep(2)}>Back</button><button className="button-primary" type="submit" disabled={busy}>{busy?'Saving…':'Save observation'}</button></div>
        {error&&<div style={{marginTop:12}}><ErrorSummary message={error}/></div>}
        <p className="field-hint" style={{marginTop:12}}>Saving appends evidence with source, time, revision. Corrections retain original. Idempotency key rotates.</p>
        <TermHelp terms={['Source reference', 'Assertion', 'Revision', 'Missingness', 'Synthetic observation']} />
      </section>
    </form>
  </section>;
}
