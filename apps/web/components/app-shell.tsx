'use client';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';

export type Selection = {
  project?: string;
  patient?: string;
  branch?: string;
  run?: string;
  state?: string;
  lesion?: string;
  panel?: string;
  compare?: string;
};

const NAV = [
  {href: '/', label: 'Research workspace', exact: true},
  {href: '/cases', label: 'Cases'},
  {href: '/guided-demo', label: 'Guided demo'},
  {href: '/evaluation', label: 'Evaluation'},
];

const CASE_NAV = [
  {href: '/cases/detail', label: 'Overview'},
  {href: '/twin', label: 'Twin workspace'},
  {href: '/states', label: 'History & states'},
  {href: '/charts', label: 'Clinical charts'},
  {href: '/simulation', label: 'Scenarios'},
  {href: '/sources', label: 'Sources'},
];

function preserveSelection(href: string, selection: Selection): string {
  const params = new URLSearchParams();
  if (selection.project) params.set('project', selection.project);
  if (selection.patient) params.set('patient', selection.patient);
  if (selection.branch) params.set('branch', selection.branch);
  if (selection.run) params.set('run', selection.run);
  if (selection.state) params.set('state', selection.state);
  if (selection.lesion) params.set('lesion', selection.lesion);
  const query = params.toString();
  if (href === '/cases/detail') return `/cases/detail${query ? `?${query}` : ''}`;
  return `${href}${query ? `?${query}` : ''}`;
}

function readSelection(params: URLSearchParams): Selection {
  const pick = (key: keyof Selection) => params.get(key) ?? undefined;
  return {
    project: pick('project'), patient: pick('patient'), branch: pick('branch'),
    run: pick('run'), state: pick('state'), lesion: pick('lesion'),
    panel: pick('panel'), compare: pick('compare'),
  };
}

function selectionLabel(selection: Selection): string | null {
  const parts = [selection.project, selection.patient, selection.branch ?? selection.run, selection.state]
    .filter(Boolean);
  if (!parts.length) return null;
  return `Selection: ${parts.join(' / ')}${selection.lesion ? ` · lesion ${selection.lesion}` : ''}`;
}

function ShellInner() {
  const pathname = usePathname();
  const params = useSearchParams();
  const selection = readSelection(params);
  const label = selectionLabel(selection);
  return <>
    <a className="skip-link" href="#main">Skip to main content</a>
    <header className="header">
      <div className="brand-row">
        <Link className="brand" href="/">CancerOS <span>Research workspace</span></Link>
        {label ? <p className="selection">{label}</p> : null}
      </div>
      <nav aria-label="Primary">
        <ul className="nav-list">
          {NAV.map(item => {
            const active = item.exact ? pathname === item.href : pathname.startsWith(item.href) && item.href !== '/';
            return <li key={item.href}><Link href={item.href} aria-current={active ? 'page' : undefined}>{item.label}</Link></li>;
          })}
        </ul>
      </nav>
    </header>
    {(pathname.startsWith('/cases') || pathname.startsWith('/twin')) && selection.patient ? <nav aria-label="Case" className="case-nav">
      <ul className="nav-list">
        {CASE_NAV.map(item => {
          const href = preserveSelection(item.href, selection);
          return <li key={item.label}><Link href={href}>{item.label}</Link></li>;
        })}
      </ul>
    </nav> : null}
    <div className="safety-notice" role="note">Research prototype. Not validated for diagnosis or treatment decisions.</div>
  </>;
}

export function AppShell() {
  return <Suspense fallback={null}><ShellInner/></Suspense>;
}

export function SelectionNotice({selection}: {selection: Selection}) {
  const label = selectionLabel(selection);
  if (!label) return <p className="selection-empty">No case loaded. Open a case to bind the header, viewer, charts and insights to one selection.</p>;
  return <p className="selection" role="status">{label}</p>;
}
