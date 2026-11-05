'use client';
import { useState } from 'react';
import { ErrorSummary } from './research';
import { researchJson, researchError } from '../lib/research-client';
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
const labels:Record<Kind,string>={laboratory:'Laboratory results',vital:'Vital signs',symptom:'Symptoms',treatment:'Treatment records',diagnosis:'Cancer / pathology',visit:'Visits / imaging exams',note:'Medical history / source notes'};
export function ObservationIntake({project,patient,revision,origin,onSaved,correction,onCancelCorrection}:{project:string;patient:string;revision:number;origin:'real_source'|'synthetic_engineering_fixture';onSaved:(message:string)=>void;correction?:components['schemas']['ClinicalRecord']|null;onCancelCorrection?:()=>void}) {
  const initial=correction?.item;
  const quantity=initial&&(initial.kind==='laboratory'||initial.kind==='vital')?initial.result:null;
  const [kind,setKind]=useState<Kind>(initial?.kind??'laboratory');
  const [concept,setConcept]=useState<string>(initial?.concept??'hemoglobin');
  const [result,setResult]=useState<string>(quantity?.form??'exact');
  const basis=initial?.time.reference.basis;
  const [timeBasis,setTimeBasis]=useState<string>(basis==='date'||basis==='timestamp'?basis:'date');
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [key,setKey]=useState(()=>crypto.randomUUID());
  const numeric=kind==='laboratory'||kind==='vital';
  async function save(event:React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if(busy)return;
    const form=event.currentTarget, data=new FormData(form);
    const get=(key:string)=>String(data.get(key)??'').trim();
    setError('');
    const domain=origin==='synthetic_engineering_fixture'?'simulation':'source_calendar';
    const time = timeBasis==='unknown' ? {reference:{basis:'unknown',time_domain:domain,missing_reason:'not_recorded'},precision:'unknown'} : {reference:{basis:timeBasis,value:get('time'),time_domain:domain},precision:timeBasis==='date'?'day':'second'};
    if (timeBasis==='timestamp' && !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(get('time'))) {setError('Enter the documented timestamp with seconds and timezone, such as 2026-11-05T09:30:00+01:00. Use date only when no time is recorded.');return;}
    const observation:Record<string,unknown>={kind,concept,time,original_term:get('term'),certainty:get('certainty'),negation:get('negation')};
    if(numeric){
      if(result!=='missing' && (!/^-?(0|[1-9]\d*)(\.\d{1,9})?$/.test(get('value')) || !Number.isFinite(Number(get('value'))) || Math.abs(Number(get('value')))>=1e15)){setError('Enter a finite decimal with at most 9 decimal places, or choose an explicit missing result.');return;}
      observation.result=result==='missing'?{form:'missing',missing_reason:get('missing_reason')}:result==='censored'?{form:'censored',comparator:get('comparator'),threshold:{value:get('value'),unit:get('unit')}}:{form:'exact',quantity:{value:get('value'),unit:get('unit')}};
      if(result!=='missing'){observation.original_value=(result==='censored'?get('comparator'):'')+get('value');observation.original_unit=get('unit');}
    } else if(kind==='symptom'){
      Object.assign(observation,{presence:get('presence'),reporter:get('reporter')});
      if(get('severity')){
        if(!/^-?(0|[1-9]\d*)(\.\d{1,9})?$/.test(get('severity'))||!get('instrument')||!get('instrument_version')){setError('A severity value requires a decimal and its documented instrument name and version.');return;}
        Object.assign(observation,{severity:get('severity'),instrument:get('instrument'),instrument_version:get('instrument_version')});
      }
    } else if(kind==='treatment'){
      Object.assign(observation,{event_type:get('event_type'),exposure_status:get('exposure_status'),regimen_text:get('regimen')||null});
    } else if(kind==='diagnosis'){
      Object.assign(observation,{histology:get('histology')||null,side:get('side'),er_status:get('er'),pr_status:get('pr'),her2_status:get('her2'),clinical_stage:get('clinical_stage')||null,pathologic_stage:get('pathologic_stage')||null,staging_system:get('staging_system')||null});
    } else if(kind==='visit')observation.label=get('label');
    else {delete observation.concept; observation.text=get('note');}
    setBusy(true);
    try{
      const report=await researchJson<{status:string;accepted_count:number;next_action:string}>(`/api/research-observations?project=${project}&patient=${patient}`,{method:'POST',headers:{'content-type':'application/json','idempotency-key':key},body:JSON.stringify({expected_revision:revision,source_reference:get('source'),observation,...(correction?{corrects_record_id:correction.id}:{})})});
      if(report.status!=='accepted')throw new Error(`The observation was ${report.status}; it was not added to accepted history. Review the source and fields before retrying.`);
      form.reset();setKey(crypto.randomUUID());onSaved(`Saved ${report.accepted_count} clinical observation. The case history has been refreshed.`);
    }catch(cause){setError(researchError(cause));}finally{setBusy(false);}
  }
  return <section className="card workspace-section" aria-label="Clinical observation entry"><p className="eyebrow">SOURCE-BACKED DATA ENTRY</p><h2>Add a clinical observation</h2><p className="field-hint">Enter documented values only. A save retains the source, collection time and revision history. Your role and source eligibility are checked by the server.</p>
    {correction&&<p role="status">Correcting {correction.item.original_term}. Saving appends a replacement and retains the original evidence. <button className="button-ghost" onClick={onCancelCorrection}>Cancel correction</button></p>}
    <form onSubmit={save} onChange={()=>setKey(crypto.randomUUID())} aria-label="Save clinical observation"><fieldset disabled={busy}><legend>Observation</legend><div className="form-grid">
      <label>Observation type<select value={kind} onChange={event=>{const next=event.target.value as Kind;setKind(next);setConcept(concepts[next][0]);setError('');}}>{(Object.keys(labels) as Kind[]).map(value=><option key={value} value={value}>{labels[value]}</option>)}</select></label>
      <label>Observation concept<select value={concept} onChange={event=>setConcept(event.target.value)}>{concepts[kind].map(value=><option key={value} value={value}>{value.replaceAll('_',' ')}</option>)}</select></label>
      <label>Source original term *<input name="term" required maxLength={300} placeholder="Exact documented observation label" defaultValue={initial?.original_term}/></label>
      <label>Source reference *<input name="source" required maxLength={500} placeholder="Source report / page / entry" defaultValue={correction?.source_reference??''}/></label>
      <label>Observation time precision<select value={timeBasis} onChange={event=>setTimeBasis(event.target.value)}><option value="date">Date only</option><option value="timestamp">Exact timestamp with timezone</option><option value="unknown">Not recorded</option></select></label>
      {timeBasis!=='unknown'&&<label>{timeBasis==='date'?'Observation date *':'Observation timestamp *'}<input key={timeBasis} name="time" type={timeBasis==='date'?'date':'text'} required placeholder="2026-11-05T09:30:00+01:00" defaultValue={initial?.time.reference.basis===timeBasis&&'value' in initial.time.reference?String(initial.time.reference.value):''}/></label>}
      <label>Source certainty<select name="certainty" defaultValue={initial?.certainty??'documented'}>{['documented','reported','uncertain','unknown'].map(value=><option key={value}>{value}</option>)}</select></label>
      <label>Assertion<select name="negation" defaultValue={initial?.negation??'affirmed'}><option value="affirmed">Affirmed</option><option value="negated">Negated</option><option value="unspecified">Unspecified</option></select></label>
    </div>
    {numeric&&<div className="form-grid"><label>Result form<select value={result} onChange={event=>setResult(event.target.value)}><option value="exact">Exact value</option><option value="censored">Threshold / censored value</option><option value="missing">Missing / not collected</option></select></label>
      {result==='missing'?<label>Missing reason<select name="missing_reason" defaultValue={quantity?.form==='missing'?quantity.missing_reason:'not_recorded'}>{['not_recorded','not_collected','unknown','withheld','not_applicable'].map(value=><option key={value} value={value}>{value.replaceAll('_',' ')}</option>)}</select></label>:<>
        {result==='censored'&&<label>Comparator<select name="comparator" defaultValue={quantity?.form==='censored'?quantity.comparator:'<'}>{['<','<=','>','>='].map(value=><option key={value}>{value}</option>)}</select></label>}
        <label>{result==='censored'?'Threshold *':'Value *'}<input name="value" inputMode="decimal" required placeholder="13.2" defaultValue={quantity?.form==='exact'?quantity.quantity.value:quantity?.form==='censored'?quantity.threshold.value:''}/></label>
        <label>Unit<select name="unit" key={concept} defaultValue={quantity?.form==='exact'?quantity.quantity.unit:quantity?.form==='censored'?quantity.threshold.unit:undefined}>{(units[concept]??[]).map(value=><option key={value}>{value}</option>)}</select></label>
      </>}
    </div>}
    {kind==='symptom'&&<div className="form-grid"><label>Presence<select name="presence">{['present','absent','unknown','not_assessed'].map(value=><option key={value}>{value}</option>)}</select></label><label>Reporter<select name="reporter">{['patient','clinician','unknown'].map(value=><option key={value}>{value}</option>)}</select></label><label>Severity (if documented)<input name="severity" inputMode="decimal"/></label><label>Severity instrument<input name="instrument" maxLength={100}/></label><label>Instrument version<input name="instrument_version" maxLength={50}/></label></div>}
    {kind==='treatment'&&<div className="form-grid"><label>Event type<select name="event_type">{['unknown','ordered','prescribed','administered','reported_exposure','stopped'].map(value=><option key={value}>{value}</option>)}</select></label><label>Exposure evidence<select name="exposure_status">{['unknown','ordered_only','documented_delivery','reported'].map(value=><option key={value}>{value}</option>)}</select></label><label>Documented regimen<input name="regimen" maxLength={500}/><span className="field-hint">Records an existing source event; does not recommend treatment. Unknown stop time stays open.</span></label></div>}
    {kind==='diagnosis'&&<div className="form-grid"><label>Histology / cancer type<input name="histology" maxLength={200}/></label><label>Laterality<select name="side">{['unknown','left','right','bilateral'].map(value=><option key={value}>{value}</option>)}</select></label>{[['er','Estrogen receptor'],['pr','Progesterone receptor'],['her2','HER2']].map(([name,label])=><label key={name}>{label}<select name={name}>{['not_recorded','not_tested','unknown','positive','negative','equivocal','invalid'].map(value=><option key={value}>{value}</option>)}</select></label>)}<label>Clinical stage<input name="clinical_stage" maxLength={100}/></label><label>Pathologic stage<input name="pathologic_stage" maxLength={100}/></label><label>Staging system<input name="staging_system" maxLength={100}/><span className="field-hint">Required if a source stage is entered. No automatic staging.</span></label></div>}
    {kind==='visit'&&<label className="standalone-field">Visit / examination label *<input name="label" required maxLength={200}/><span className="field-hint">Records the examination occasion; importing MRI bytes and masks requires a separate eligible imaging workflow.</span></label>}
    {kind==='note'&&<label className="standalone-field">Source-supported research note *<textarea name="note" required maxLength={16000} rows={5}/><span className="field-hint">Omit direct identifiers. Note text is stored privately; no external AI is invoked.</span></label>}
    </fieldset>{error&&<ErrorSummary message={error}/>}<button className="button-primary" type="submit" disabled={busy}>{busy?'Saving observation…':'Save observation'}</button>
    </form>
  </section>;
}
