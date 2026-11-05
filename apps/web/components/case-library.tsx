'use client';
import Link from 'next/link';
import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import type { components } from '../../../packages/contracts/generated/api';
import { ErrorSummary, LoadingState } from './research';

type PatientSummary = components['schemas']['PatientSummary'];
type PatientPage = components['schemas']['PatientPage'];

type CaseState =
  | {kind: 'needs-project'}
  | {kind: 'loading'}
  | {kind: 'empty'}
  | {kind: 'failed'; message: string}
  | {kind: 'ready'; items: PatientSummary[]};

function explain(response: Response, body: string): string {
  if (response.status === 401) return 'Sign in with an authorized project session, then retry.';
  if (response.status === 403) return 'This project is restricted for your role. Ask an administrator for access.';
  if (response.status === 404) return 'The project was not found or is not visible to you.';
  if (response.status === 428 || response.status === 412) return 'The list changed while loading. Reload the cases library to restart safely.';
  return `The case list could not load (status ${response.status}). ${body.slice(0, 160)}`;
}

export function CaseLibrary({initialProject, detailBase = '/cases/detail'}: {initialProject?: string | null; detailBase?: string}) {
  if (initialProject !== undefined) return <CaseLibraryBody initialProject={initialProject} detailBase={detailBase}/>;
  return <Suspense fallback={<LoadingState/>}><CaseLibraryFromQuery detailBase={detailBase}/></Suspense>;
}

function CaseLibraryFromQuery({detailBase = '/cases/detail'}: {detailBase?: string}) {
  const params = useSearchParams();
  return <CaseLibraryBody initialProject={params.get('project')} detailBase={detailBase}/>;
}

function CaseLibraryBody({initialProject, detailBase = '/cases/detail'}: {initialProject: string | null; detailBase?: string}) {
  const [project] = useState<string | null>(initialProject);
  const [state, setState] = useState<CaseState>(() =>
    initialProject ? {kind: 'loading'} : {kind: 'needs-project'},
  );
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!project) return;
    if (state.kind !== 'loading') return;
    const controller = new AbortController();
    const signal = controller.signal;
    void (async () => {
      try {
        const response = await fetch(
          `/api/cases?project=${encodeURIComponent(project)}`,
          {cache: 'no-store', signal},
        );
        if (signal.aborted) return;
        if (!response.ok) {
          const body = await response.text().catch(() => '');
          setState({kind: 'failed', message: explain(response, body)});
          return;
        }
        const page = (await response.json()) as PatientPage;
        if (!page.items.length) setState({kind: 'empty'});
        else setState({kind: 'ready', items: page.items});
      } catch (error) {
        if (signal.aborted) return;
        setState({kind: 'failed', message: error instanceof Error ? error.message : 'The case list could not load.'});
      }
    })();
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt, project]);

  if (state.kind === 'needs-project') {
    return <section className="card"><h2>No project selected</h2>
      <p>Add <code>?project=&lt;project-id&gt;</code> to the URL to list authorized cases. The browser never guesses a project.</p></section>;
  }
  if (state.kind === 'loading') return <LoadingState/>;
  if (state.kind === 'failed') {
    return <section className="card"><ErrorSummary message={state.message}/>
      {project ? <p><button onClick={() => {
        setState({kind: 'loading'});
        setAttempt(a => a + 1);
      }}>Retry loading cases</button></p> : null}</section>;
  }
  if (state.kind === 'empty') {
    return <section className="card"><h2>No approved cases yet</h2>
      <p>No cases are visible for this project and role. An administrator can review imports; a viewer can follow the guided demo instead.</p>
      <p><Link href="/guided-demo">Start guided demo</Link></p></section>;
  }
  return <>
    <p role="status" aria-live="polite">{state.items.length} authorized case{state.items.length === 1 ? '' : 's'} shown. Counts come only from records your role may see.</p>
    <div className="case-grid">
      {state.items.map(item => <article className="card case-card" key={item.patient_id}>
        <h2>{item.display_code}</h2>
        <dl className="case-fields">
          <div><dt>Case</dt><dd>{item.display_code}</dd></div>
          <div><dt>Data revision</dt><dd>{item.data_revision}</dd></div>
        </dl>
        <p>Examination, branch and modality availability appear after opening the case. The list never invents them.</p>
        <p><Link href={`${detailBase}?project=${encodeURIComponent(project ?? '')}&patient=${encodeURIComponent(item.patient_id)}`}>Open case</Link></p>
      </article>)}
    </div>
  </>;
}
