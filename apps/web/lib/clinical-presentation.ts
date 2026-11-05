import type { components } from '../../../packages/contracts/generated/api';
type Record = components['schemas']['ClinicalRecord'];
export function clinicalTime(record:Record):string {
  const {reference}=record.item.time;
  if(reference.basis==='unknown')return `Not recorded (${reference.missing_reason.replaceAll('_',' ')})`;
  return reference.basis==='relative_day' ? `Day ${reference.value} · ${reference.time_domain.replaceAll('_',' ')}` : `${reference.value} · ${reference.time_domain.replaceAll('_',' ')}`;
}
export function clinicalValue(record:Record):string {
  const item=record.item;
  if(item.kind==='laboratory'||item.kind==='vital'){
    const result=item.result;
    return result.form==='missing' ? `Missing: ${result.missing_reason.replaceAll('_',' ')}` : result.form==='exact' ? `${result.quantity.value} ${result.quantity.unit}` : `${result.comparator} ${result.threshold.value} ${result.threshold.unit}`;
  }
  if(item.kind==='symptom')return `${item.presence.replaceAll('_',' ')}${item.severity ? ` · ${item.severity} (${item.instrument}/${item.instrument_version})` : ''}`;
  if(item.kind==='treatment')return `${item.event_type.replaceAll('_',' ')} · ${item.exposure_status.replaceAll('_',' ')}${item.regimen_text ? ` · ${item.regimen_text}` : ''}`;
  if(item.kind==='diagnosis')return `${item.histology ?? 'Histology not recorded'} · ${item.side} · ER ${item.er_status} / PR ${item.pr_status} / HER2 ${item.her2_status}`;
  if(item.kind==='visit')return item.label;
  return 'Private source note · exact content retained';
}
