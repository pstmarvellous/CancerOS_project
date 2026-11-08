'use client';

const TERMS: { term: string; help: string }[] = [
  { term: 'mm³', help: 'Cubic millimeters: the unit for modeled region volume. One mm³ is a cube one millimeter on each side.' },
  { term: 'Synthetic baseline', help: 'The shared starting measurement (216 mm³) that every hypothetical scenario in this demo is compared against. It is a geometric phantom, not a patient scan.' },
  { term: 'Relative day', help: 'Days counted from the synthetic baseline (day 0). These are scenario steps, not calendar appointments.' },
  { term: 'Mask', help: 'The labeled 3D region the backend measured. Volumes come from counting mask voxels, never from the displayed surface or an AI estimate.' },
  { term: 'Derived measurement', help: 'A value CancerOS computed from retained records, such as a percentage change. The source values stay shown alongside it.' },
  { term: 'Synthetic observation', help: 'Generated demonstration data with no real patient behind it. Authentic records and derived measurements are labeled separately wherever they appear.' },
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
