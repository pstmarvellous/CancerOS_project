'use client';

const TERMS: { term: string; help: string }[] = [
  { term: 'mm³', help: 'Cubic millimeters: the unit for modeled region volume. One mm³ is a cube one millimeter on each side.' },
  { term: 'Synthetic baseline', help: 'The shared starting measurement (216 mm³) that every hypothetical scenario in this demo is compared against. It is a geometric phantom, not a patient scan.' },
  { term: 'Relative day', help: 'Days counted from the synthetic baseline (day 0). These are scenario steps, not calendar appointments.' },
  { term: 'Mask', help: 'The labeled 3D region the backend measured. Volumes come from counting mask voxels, never from the displayed surface or an AI estimate.' },
  { term: 'Derived measurement', help: 'A value CancerOS computed from retained records, such as a percentage change. The source values stay shown alongside it.' },
  { term: 'Synthetic observation', help: 'Generated demonstration data with no real patient behind it. Authentic records and derived measurements are labeled separately wherever they appear.' },
  { term: 'Case reference', help: 'The unique code for this case within its project, e.g. DEMO-001. Letters, numbers, dots, hyphens and underscores only.' },
  { term: 'Participant code', help: 'A study code that stands in for a person. It prevents duplicate linkage. Never enter a real name, contact detail or government ID.' },
  { term: 'Source record', help: 'The registered artifact this case was created from. Only sources your project administrator made eligible can be selected.' },
  { term: 'Source reference', help: 'Where the value was documented: the report, page or entry locator exactly as written in the source.' },
  { term: 'Record type', help: 'Whether new entries in this case are labeled artificial demonstration or source-backed research records. It follows the selected source and is never invented.' },
  { term: 'Assertion', help: 'How the documented statement stands: affirmed means stated as true, negated means stated as not present, unspecified means the source does not say.' },
  { term: 'Revision', help: 'Each save creates a new numbered revision. Corrections append a replacement; the previous revision is always retained and reviewable.' },
  { term: 'Missingness', help: 'Why a value is absent: not recorded, not collected, unknown, withheld or not applicable. Missing values are never filled in or shown as zero.' },
];

export function TermHelp({ terms = TERMS.map(t => t.term) }: { terms?: string[] }) {
  const items = TERMS.filter(t => terms.includes(t.term));
  if (!items.length) return null;
  return (
    <details className="term-help" style={{ marginTop: 8 }}>
      <summary style={{ cursor: 'pointer', fontWeight: 600 }}>What do these terms mean?</summary>
      <dl>
        {items.map(item => (
          <div key={item.term}>
            <dt style={{ fontWeight: 700 }}>{item.term}</dt>
            <dd style={{ margin: '0 0 8px' }}>{item.help}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
