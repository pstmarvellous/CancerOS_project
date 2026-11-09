'use client';

import Link from 'next/link';
import { useState } from 'react';

type Step = {
  title: string;
  where: string;
  href: string;
  what: string;
  check: string;
};

const STEPS: Step[] = [
  {
    title: 'Open an authorized case',
    where: 'Case library',
    href: '/cases',
    what: 'Open a case from the library with an authorized project and patient. The workspace never guesses a selection.',
    check: 'Preflight: case library loads; an unauthorized case shows a blocked state with a next action, not a silent substitution.',
  },
  {
    title: 'Inspect measured geometry and sources',
    where: 'Twin workspace',
    href: '/twin',
    what: 'Rotate, pan, zoom, fit and reset one authorized lesion with server mask measurements authoritative.',
    check: 'Preflight: QC-validated geometry present; expired or blocked geometry shows tables with Retry 3D, never a placeholder tumor.',
  },
  {
    title: 'Select and compare saved timepoints',
    where: 'History & states',
    href: '/states',
    what: 'Move the discrete state slider or pick Previous/Next, then pin a second state for sequential comparison.',
    check: 'Preflight: only persisted discrete snapshots exist; unknown-time records stay unplaced; no autoplay or interpolation.',
  },
  {
    title: 'Read charts and exact tables',
    where: 'Clinical charts',
    href: '/charts',
    what: 'Open laboratory, vital, symptom and treatment panels with exact decimal tables beside bounded plots.',
    check: 'Preflight: missing stays missing; censored keeps comparator and threshold; no smoothed or gap-filled series.',
  },
  {
    title: 'Explore a labeled hypothetical branch',
    where: 'Scenarios',
    href: '/simulation',
    what: 'Review the five explicitly hypothetical scenario families and follow generate, validate and separate private publication.',
    check: 'Preflight: draft inputs preserved; 202 starts a durable job without changing actual history; unpublished runs never reach judges.',
  },
  {
    title: 'Inspect grounded findings',
    where: 'Insights',
    href: '/insights',
    what: 'Open the snapshot-bound context, generate the labeled rule-based summary and check grounding before saving.',
    check: 'Preflight: case evidence separate from background passages; unknown uncertainty is never a confidence gauge.',
  },
  {
    title: 'Review measured evaluation limits',
    where: 'Evaluation',
    href: '/evaluation',
    what: 'Read the compact evaluation report: what was measured, denominators, versions, failures and open gates.',
    check: 'Preflight: missing evidence reads Not evaluated; no decorative accuracy percentages; real follow-up gates stay visible.',
  },
];

export function GuidedDemo() {
  const [index, setIndex] = useState(0);
  const [confirmed, setConfirmed] = useState(false);
  const step = STEPS[index];
  function restart() {
    setIndex(0);
    setConfirmed(false);
  }
  return (
    <div>
      <p role="status" aria-live="polite">
        Step {index + 1} of {STEPS.length}: {step.title}. Restart resets UI selection, camera and progress only; it
        cannot delete observations, cancel jobs or regenerate branches.
      </p>
      <ol>
        {STEPS.map((item, position) => (
          <li key={item.title} aria-current={position === index ? 'step' : undefined}>
            <button type="button" onClick={() => setIndex(position)}>
              {position + 1}. {item.title}
            </button>
          </li>
        ))}
      </ol>
      <section aria-label={`Demo step ${index + 1}: ${step.title}`}>
        <h2>{step.title}</h2>
        <p>Location: {step.where}. Approximate pacing: about five minutes for the full read-only sequence in rehearsal; not verified organizer timing.</p>
        <p>{step.what}</p>
        <p>{step.check}</p>
        <p>
          <Link href={step.href}>Open {step.where} in this step&apos;s context</Link>
        </p>
        <p>
          <label>
            <input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} /> I
            understand this is a read-only research walkthrough. Editor live-write demonstrations stay explicit and
            isolated.
          </label>
        </p>
        <div>
          <button type="button" onClick={() => setIndex(value => Math.max(0, value - 1))} disabled={index === 0}>Previous</button>{' '}
          <button type="button" onClick={() => setIndex(value => Math.min(STEPS.length - 1, value + 1))} disabled={index === STEPS.length - 1 || !confirmed}>Next</button>{' '}
          <button type="button" onClick={restart}>Restart</button>{' '}
          <Link href="/">Exit</Link>
        </div>
      </section>
      <section aria-label="Demo safety">
        <h2>Safety and reset behavior</h2>
        <p>Nothing here runs a model or changes patient state. A static preview or recording is labeled and never presented as a live result.</p>
        <p>Prepared summaries are labeled with their snapshot hash and execution mode before display.</p>
      </section>
    </div>
  );
}
