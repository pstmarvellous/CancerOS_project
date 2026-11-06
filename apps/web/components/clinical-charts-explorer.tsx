'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import type { components } from '../../../packages/contracts/generated/api';
import { ErrorSummary, LoadingState } from './research';
import { clinicalTime, clinicalValue } from '../lib/clinical-presentation';

type S = components['schemas'];
type ObservationPage = S['ObservationPage'];
type ObservationSummary = S['ObservationSummary'];
type ClinicalRecord = S['ClinicalRecord'];

type Status = 'needs-selection' | 'loading' | 'ready' | 'failed';

type Row = {
  summary: ObservationSummary;
  record: ClinicalRecord | null;
  error: string | null;
};

type Panel = {
  key: string;
  title: string;
  kinds: string[];
  description: string;
};

const PANELS: Panel[] = [
  { key: 'laboratory', title: 'Laboratory small multiples', kinds: ['laboratory'], description: 'One small panel per laboratory concept. Missing and censored values stay labeled; no gap is filled or smoothed.' },
  { key: 'vitals', title: 'Vital-sign panels', kinds: ['vital'], description: 'Systolic and diastolic components stay separate with readable labels. No mixed-unit dual axes.' },
  { key: 'symptoms', title: 'Symptom observations', kinds: ['symptom'], description: 'Presence, instrument and ordinal meaning stay attached to each rating. No cross-symptom aggregation.' },
  { key: 'treatments', title: 'Treatment and exposure tracks', kinds: ['treatment'], description: 'Recorded and hypothetical exposures stay distinct. Unknown stop dates stay open, never fabricated.' },
];

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function initialParams(params: URLSearchParams): { project: string | null; patient: string | null; visit: string | null } {
  return { project: params.get('project'), patient: params.get('patient'), visit: params.get('visit') };
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { raw: text.slice(0, 500) };
  }
}

function explain(response: Response): string {
  if (response.status === 401) return 'Sign in with an authorized session, then retry. Charts never bypass project rights.';
  if (response.status === 403) return 'These observations are restricted for your role. Ask an administrator for access.';
  if (response.status === 404) return 'The case or observation batch is unavailable in this authorized context. Check the selection.';
  return `The authorized read failed (status ${response.status}).`;
}

function recordConcept(record: ClinicalRecord | null): string {
  if (!record) return 'unlinked concept';
  const item = record.item as { concept?: unknown; original_term?: unknown };
  if (typeof item.concept === 'string' && item.concept) return item.concept;
  if (typeof item.original_term === 'string' && item.original_term) return item.original_term;
  return 'unlinked concept';
}

function recordUnit(record: ClinicalRecord): string {
  const itemWithResult = record.item;
  if (itemWithResult.kind === 'laboratory' || itemWithResult.kind === 'vital') {
    const result = itemWithResult.result;
    if (result?.form === 'exact') return result.quantity.unit;
    if (result?.form === 'censored') return result.threshold.unit;
  }
  const item = record.item as { original_unit?: unknown };
  return typeof item.original_unit === 'string' && item.original_unit ? item.original_unit : 'unit not recorded';
}

function recordValue(record: ClinicalRecord): string {
  if (record.item.time?.reference && ('result' in record.item || !['laboratory','vital'].includes(record.item.kind))) return clinicalValue(record);
  const legacy = record.item as { original_value?: string };
  return legacy.original_value ?? 'Not recorded';
}

function recordTime(record: ClinicalRecord): string {
  return record.item.time?.reference ? clinicalTime(record) : 'actual collection time not recorded';
}

function groupKey(record: ClinicalRecord | null, summary: ObservationSummary): string {
  if (record) {
    const item = record.item as { concept?: unknown; instrument?: unknown };
    const concept = typeof item.concept === 'string' ? item.concept : summary.concept;
    const instrument = typeof item.instrument === 'string' && item.instrument ? ` · ${item.instrument}` : '';
    return `${concept}${instrument} · ${recordUnit(record)}`;
  }
  return summary.concept;
}

export function recordDay(record: ClinicalRecord | null): number | null {
  if (!record) return null;
  const reference = record.item.time?.reference as { basis?: string; value?: unknown } | undefined;
  if (reference?.basis === 'relative_day' && typeof reference.value === 'number' && Number.isFinite(reference.value)) return reference.value;
  if (reference?.basis === 'relative_day' && typeof reference.value === 'string' && reference.value.trim() !== '' && Number.isFinite(Number(reference.value))) return Number(reference.value);
  return null;
}

export function ClinicalChartsExplorer({ stateFilter }: { stateFilter?: { day: number | null; label: string } | null } = {}) {
  return <Suspense fallback={<LoadingState/>}><ClinicalChartsFromQuery stateFilter={stateFilter ?? null} /></Suspense>;
}

function ClinicalChartsFromQuery({ stateFilter }: { stateFilter: { day: number | null; label: string } | null }) {
  const params = useSearchParams();
  const initial = initialParams(params);
  const { project, patient } = initial;
  const [visit] = useState(initial.visit);
  const [rows, setRows] = useState<Row[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [loadedPages, setLoadedPages] = useState(0);
  const [panel, setPanel] = useState('laboratory');
  const [status, setStatus] = useState<Status>('needs-selection');
  const [message, setMessage] = useState('This view loads up to 100 source records. Plots keep concepts and units separate; the table includes retained history.');
  const [selectedState] = useState<string | null>(() => params.get('state'));
  const requestId = useRef(0);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  useEffect(() => {
    if (project && patient) void loadAll(project, patient, visit);
    // One-shot case bind; later filtering uses panel pickers, not repeated case guessing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchPage(nextProject: string, nextPatient: string, nextVisit: string | null, nextCursor: string | null, signal: AbortSignal): Promise<ObservationPage> {
    const response = await fetch(
      `/api/clinical-charts?project=${encodeURIComponent(nextProject)}&patient=${encodeURIComponent(nextPatient)}`,
      {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ kind: null, concept: null, visit_id: nextVisit && UUID.test(nextVisit) ? nextVisit : null, cursor: nextCursor, limit: 100 }),
        cache: 'no-store',
        signal,
      },
    );
    if (!response.ok) throw new Error(explain(response));
    return (await readJson(response)) as ObservationPage;
  }

  async function fetchRecord(nextProject: string, nextPatient: string, recordId: string, signal: AbortSignal): Promise<ClinicalRecord | null> {
    try {
      const response = await fetch(
        `/api/case-record?project=${encodeURIComponent(nextProject)}&patient=${encodeURIComponent(nextPatient)}&record=${encodeURIComponent(recordId)}`,
        { cache: 'no-store', signal },
      );
      if (!response.ok) return null;
      return (await readJson(response)) as ClinicalRecord;
    } catch {
      return null;
    }
  }

  async function loadAll(nextProject: string, nextPatient: string, nextVisit: string | null) {
    const key = ++requestId.current;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setStatus('loading');
    setRows([]);
    setCursor(null);
    setTotal(null);
    setLoadedPages(0);
    setMessage('Loading up to 100 authorized clinical records…');
    const collected: Row[] = [];
    let pages = 0;
    try {
      const page = await fetchPage(nextProject, nextPatient, nextVisit, null, controller.signal);
      if (controller.signal.aborted || key !== requestId.current) return;
      pages += 1;
      for (const summary of page.items ?? []) {
        if (controller.signal.aborted || key !== requestId.current) return;
        const record = await fetchRecord(nextProject, nextPatient, summary.record_id, controller.signal);
        if (controller.signal.aborted || key !== requestId.current) return;
        collected.push({ summary, record, error: record ? null : 'Record detail unavailable in this page; summary retained without invented values.' });
      }
      setRows([...collected]);
      setLoadedPages(pages);
      setCursor(page.snapshot_cursor ?? null);
      setTotal(collected.length);
      if (controller.signal.aborted || key !== requestId.current) return;
      setStatus('ready');
      setMessage(
        collected.length
          ? `${collected.length} authorized records across ${pages} bounded page(s). Tables preserve exact decimal strings; plots use bounded numeric conversion only. This bounded view is not a complete patient-history export.`
          : 'No laboratory, vital, symptom or treatment records are available in this authorized history. Missing records are not zero or normal.',
      );
    } catch (error) {
      if (controller.signal.aborted || key !== requestId.current) return;
      setStatus('failed');
      setMessage(error instanceof Error ? error.message : 'The clinical history could not load.');
    }
  }

  if (!project || !patient) {
    return (
      <section className="card">
        <h2>Open a case to inspect its clinical charts</h2>
        <p>
          Charts bind to the active workspace case. <Link href="/cases">Open an authorized case</Link>, then use its
          Charts tab. The browser never guesses a project or patient.
        </p>
      </section>
    );
  }

  const active = PANELS.find(item => item.key === panel) ?? PANELS[0];
  const inStateWindow = (row: Row): boolean => {
    if (!stateFilter || stateFilter.day === null) return true;
    const day = recordDay(row.record);
    if (day === null) return false;
    return day <= stateFilter.day;
  };
  const scoped = rows.filter(inStateWindow);
  const filtered = scoped.filter(row => active.kinds.includes(row.summary.kind) && !row.summary.superseded);
  const groups = new Map<string, Row[]>();
  for (const row of filtered) {
    const key = groupKey(row.record, row.summary);
    const list = groups.get(key) ?? [];
    list.push(row);
    groups.set(key, list);
  }

  return (
    <div>
      <p role="status" aria-live="polite">{message}</p>
      {stateFilter ? <p className="field-hint">Timeline filter: {stateFilter.label}. Records without a relative day stay outside the filtered view; select All records to restore them. Server values, units, and missingness are unchanged.</p> : null}
      <p>
        Case: {patient.slice(0, 8)}… · Pages loaded: {loadedPages} · Records: {total ?? 0} ·{' '}
        {selectedState ? `Selected state cursor: ${selectedState.slice(0, 8)}… (observations keep their own times)` : stateFilter ? `Timeline filter: ${stateFilter.label}` : 'All records (no timeline filter)'} ·{' '}
        <Link href={`/cases/detail?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&tab=overview`}>Back to case workspace</Link>
      </p>
      {status === 'loading' && rows.length === 0 ? <LoadingState /> : null}
      {status === 'failed' && rows.length === 0 ? (
        <section className="card">
          <ErrorSummary message={message} />
          <p><button type="button" onClick={() => void loadAll(project, patient, visit)}>Retry authorized load</button></p>
        </section>
      ) : null}
      <p>
        <label htmlFor="chart-panel">Chart panel </label>
        <select id="chart-panel" value={active.key} onChange={event => setPanel(event.target.value)} aria-label="Chart panel">
          {PANELS.map(item => <option key={item.key} value={item.key}>{item.title}</option>)}
        </select>
      </p>
      <section aria-label={active.title}>
        <h2>{active.title}</h2>
        <p>{active.description}</p>
        {filtered.length === 0 && status === 'ready' ? <p>No {active.key} records are available. Missing records are not zero, normal or imputed.</p> : null}
        {[...groups.entries()].map(([concept, list]) => (
          <article key={concept} aria-label={`${concept} small panel`}>
            <h3>{concept}</h3>
            <ClinicalSmallMultiple rows={list} />
          </article>
        ))}
      </section>
      <section aria-label="Clinical record parity table">
        <h2>Exact record table</h2>
        <p>Decimal strings below are exact server values; chart coordinates are bounded display approximations. Plots omit superseded revisions; retained records remain in the table.</p>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <caption>Authorized clinical records · exact values and missingness</caption>
            <thead>
              <tr>
                <th scope="col">Record</th>
                <th scope="col">Concept</th>
                <th scope="col">Exact value</th>
                <th scope="col">Unit</th>
                <th scope="col">Actual time</th>
                <th scope="col">Origin</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(row => (
                <tr key={row.summary.record_id}>
                  <th scope="row">
                          <Link href={`/cases/detail?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&tab=clinical`}>Open {row.summary.record_id.slice(0, 8)}…</Link>
                  </th>
                  <td>{row.record ? recordConcept(row.record) : row.summary.concept}</td>
                  <td>{row.record ? recordValue(row.record) : 'Not loaded; no value invented'}</td>
                  <td>{row.record ? recordUnit(row.record) : 'Not loaded'}</td>
                  <td>{row.record ? recordTime(row.record) : 'Not loaded'}</td>
                  <td>{row.record ? String(row.record.origin) : 'Not loaded'}{row.summary.superseded ? ' · superseded' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {cursor ? <p>Snapshot cursor: {cursor.slice(0, 12)}… Partial status is explicit until needed pages resolve.</p> : null}
      </section>
    </div>
  );
}

function coordinate(value: string | null | undefined): number | null {
  if (value == null || value.trim() === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function numericOf(record: ClinicalRecord | null): { text: string; value: number | null; censored: string | null } {
  if (!record) return { text: 'Not loaded', value: null, censored: null };
  if (record.item.kind === 'laboratory' || record.item.kind === 'vital') {
    const result = record.item.result;
    if (result?.form === 'missing') return {text: `Missing: ${result.missing_reason}`, value:null, censored:null};
    if (result?.form === 'censored') return {text: `${result.comparator}${result.threshold.value}`, value:null, censored:result.threshold.value};
    if (result?.form === 'exact') return {text:result.quantity.value, value:coordinate(result.quantity.value), censored:null};
  }
  const item = record.item as { original_value?: unknown; value?: unknown; comparator?: unknown; threshold?: unknown };
  const text = typeof item.original_value === 'string' ? item.original_value : typeof item.value === 'string' ? item.value : null;
  if (text == null) {
    if (typeof item.threshold === 'string' || typeof item.threshold === 'number') {
      return { text: `${typeof item.comparator === 'string' ? item.comparator : '<'}${String(item.threshold)} (censored)`, value: null, censored: String(item.threshold) };
    }
    return { text: 'Missing · not zero', value: null, censored: null };
  }
  return { text, value: coordinate(text), censored: null };
}

function ClinicalSmallMultiple({ rows }: { rows: Row[] }) {
  const usable = rows.map(row => ({ row, parsed: numericOf(row.record) }));
  const finite = usable.filter(item => item.parsed.value !== null).map(item => item.parsed.value as number);
  const canPlot = finite.length > 0;
  const min = canPlot ? Math.min(...finite) : 0;
  const max = canPlot ? Math.max(...finite) : 1;
  return (
    <div>
      {canPlot ? (
        <figure>
          <svg viewBox="0 0 300 120" role="img" aria-label={`${rows.length} observations; exact values in the table below`} style={{ width: '100%', maxWidth: 480 }}>
            <line x1="30" y1="100" x2="290" y2="100" stroke="currentColor" />
            <line x1="30" y1="10" x2="30" y2="100" stroke="currentColor" />
            {usable.map((item, index) => {
              if (item.parsed.value === null) return null;
              const x = usable.length === 1 ? 160 : 30 + (index / Math.max(usable.length - 1, 1)) * 260;
              const y = max === min ? 55 : 100 - ((item.parsed.value - min) / (max - min)) * 90;
              return <circle key={item.row.summary.record_id} cx={x} cy={y} r="4" fill="#5b21b6"><title>{`${item.parsed.text} · actual time in table below`}</title></circle>;
            })}
          </svg>
          <figcaption>Each dot represents one returned exact observation. Horizontal positions show record order; collection times and exact values remain in the table.</figcaption>
        </figure>
      ) : (
        <p>No finite coordinates are available for plotting. The exact-value table below remains authoritative.</p>
      )}
      <ul>
        {usable.map(item => (
          <li key={item.row.summary.record_id}>
            {recordConcept(item.row.record as ClinicalRecord) === 'unlinked concept' ? item.row.summary.concept : recordConcept(item.row.record as ClinicalRecord)} ·{' '}
            {item.parsed.text} · {item.row.record ? recordUnit(item.row.record as ClinicalRecord) : 'unit pending'} ·{' '}
            {item.row.record ? recordTime(item.row.record as ClinicalRecord) : 'time pending'}
            {item.row.error ? ` · ${item.row.error}` : ''}
          </li>
        ))}
      </ul>
    </div>
  );
}
