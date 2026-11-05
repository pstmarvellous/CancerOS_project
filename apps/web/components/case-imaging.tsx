'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { components } from '../../../packages/contracts/generated/api';
import { LoadingState } from './research';

type Imaging = { studies: components['schemas']['StudyPage']; segmentations: components['schemas']['SegmentationDiscovery'][] | null };
const readable = (value: string) => value.replaceAll('_', ' ');
const qcStatuses: Record<string, string> = { pass: 'Passed', fail: 'Failed', pending: 'Pending' };
const qcLabel = (value: string) => qcStatuses[value] ?? readable(value);

export function CaseImaging({ project, patient }: { project: string; patient: string }) {
  const selection = `${project}:${patient}`;
  const [snapshot, setSnapshot] = useState<{ selection: string; data: Imaging } | null>(null);
  const [error, setError] = useState<{ selection: string; message: string } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const current = snapshot?.selection === selection ? snapshot.data : null;
  const failure = error?.selection === selection ? error.message : null;

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch(`/api/case-imaging?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`,
          { cache: 'no-store', credentials: 'same-origin', signal: controller.signal });
        if (!response.ok) {
          const message = response.status === 401 ? 'Sign in with an authorized research session to view imaging.' :
            response.status === 403 ? 'Imaging is restricted for your account. Ask the project owner for access.' :
            response.status === 404 ? 'This case or its imaging is not available to your account.' : 'Imaging could not load. Retry when the research service is available.';
          throw new Error(message);
        }
        const data = await response.json() as Imaging;
        if (!Array.isArray(data.studies?.items) || data.segmentations !== null && !Array.isArray(data.segmentations)) throw new Error('Imaging discovery returned an incomplete response. Retry loading imaging.');
        if (!controller.signal.aborted) { setSnapshot({ selection, data }); setError(null); }
      } catch (cause) {
        if (!controller.signal.aborted) setError({ selection, message: cause instanceof Error ? cause.message : 'Imaging could not load.' });
      }
    })();
    return () => controller.abort();
  }, [project, patient, selection, attempt]);

  return <section className="card workspace-section" aria-label="Case imaging">
    <h2>Medical imaging</h2>
    {failure ? <><p role="alert">{failure}</p><p>You can continue working on the case while imaging is unavailable.</p>
      <button type="button" className="button-ghost" onClick={() => { setError(null); setSnapshot(null); setAttempt(n => n + 1); }}>Retry imaging</button></> :
      !current ? <LoadingState/> : !current.studies.items.length ? <>
        <p>No imaging studies are associated with this case.</p>
        <p>Your saved case, research profile and clinical observations remain available.</p>
      </> : <>
        <p>{current.studies.items.length} associated {current.studies.items.length === 1 ? 'study' : 'studies'}. Counts and statuses below come from the imaging service.</p>
        <div className="table-scroll"><table><caption>Associated imaging studies</caption><thead><tr><th>Study</th><th>Series</th><th>Imports</th><th>Association status</th></tr></thead>
          <tbody>{current.studies.items.map((study, index) => <tr key={study.study_id}><th>Study {index + 1}</th><td>{study.series_count}</td><td>{study.import_count}</td><td>{readable(study.status)}</td></tr>)}</tbody></table></div>
        <p className="field-hint">Acquisition dates, imaging modality and sequence details are not supplied by this discovery view.</p>
        <h3>Segmentation review</h3>
        {current.segmentations === null ? <p>Segmentation status is unavailable. No accessible segmentation records were returned; this does not establish that no masks exist.</p> :
          !current.segmentations.length ? <p>No segmentation records were returned by the imaging service.</p> :
            <div className="table-scroll"><table><caption>Accessible segmentation records</caption><thead><tr><th>Mask</th><th>Recorded meaning</th><th>Label value</th><th>Technical QC</th></tr></thead>
              <tbody>{current.segmentations.map((mask, index) => <tr key={mask.segmentation_id}><th>Mask {index + 1}</th><td>{readable(mask.mask_type)}</td><td>{mask.label_value}</td><td>{qcLabel(mask.qc_status)}</td></tr>)}</tbody></table></div>}
        <p className="field-hint">A technical pass does not establish a clinically reviewed lesion contour. A 3D reconstruction requires eligible, reviewed geometry.</p>
        <p><Link className="button-secondary" href={`/twin?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`}>Open Digital Twin workspace</Link></p>
        <details><summary>Advanced imaging identifiers</summary>
          <ul>{current.studies.items.map((study, index) => <li key={study.study_id}>Study {index + 1}: {study.study_id}</li>)}</ul>
          {current.segmentations?.map((mask, index) => <p key={mask.segmentation_id}>Mask {index + 1}: {mask.segmentation_id} · Import batch: {mask.batch_id}</p>)}
        </details>
      </>}
    <p className="field-hint">This editor does not upload imaging files. Importing files requires a separate reviewed workflow for file-level source rights, patient identity and image/mask association.</p>
  </section>;
}
