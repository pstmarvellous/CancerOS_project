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
  {href: '/', label: 'Overview', exact: true},
  {href: '/cases', label: 'Research Cases'},
  {href: '/twin', label: 'Digital Twin'},
  {href: '/charts', label: 'Clinical Data'},
  {href: '/simulation', label: 'Hypothetical Scenarios'},
  {href: '/insights', label: 'AI Research Insights'},
  {href: '/evaluation', label: 'Evaluation / Technical Details'},
];

const CASE_NAV = [
  {href: '/cases/detail', label: 'Overview'},
  {href: '/twin', label: '3D Digital Twin'},
  {href: '/states', label: 'History & states'},
  {href: '/charts', label: 'Clinical Data'},
  {href: '/insights', label: 'AI Research Insights'},
  {href: '/simulation', label: 'Hypothetical Scenarios'},
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
        <Link className="brand" href="/">CancerOS <span>Research digital twin</span></Link>
        {label ? <details className="selection"><summary>{pathname.startsWith('/demo') ? 'Synthetic demonstration selected' : 'Research case selected'} · advanced identifiers</summary>{label}</details> : null}
      </div>
      <nav aria-label="Primary">
        <ul className="nav-list">
          {NAV.map(item => {
            const active = item.exact ? pathname === item.href : pathname.startsWith(item.href) && item.href !== '/';
            const demoViews:Record<string,string>={'/twin':'twin','/charts':'clinical','/simulation':'scenarios','/insights':'insights'};
            let target=item.href;
            if(pathname.startsWith('/demo')&&demoViews[item.href]){
              const demoQuery=new URLSearchParams({view:demoViews[item.href]});
              for(const key of ['scenario','state']){const value=params.get(key);if(value)demoQuery.set(key,value);}
              target=`/demo?${demoQuery}`;
            }else if(selection.patient&&demoViews[item.href])target=preserveSelection(item.href,selection);
            return <li key={item.href}><Link href={target} aria-current={active ? 'page' : undefined}>{item.label}</Link></li>;
          })}
        </ul>
      </nav>
    </header>
    {['/cases/detail', '/twin', '/states', '/charts', '/insights', '/simulation', '/timeline'].some(route => pathname.startsWith(route)) && selection.patient ? <nav aria-label="Case" className="case-nav">
      <ul className="nav-list">
        {CASE_NAV.map(item => {
          const href = preserveSelection(item.href, selection);
          return <li key={item.label}><Link href={href}>{item.label}</Link></li>;
        })}
      </ul>
    </nav> : null}
    {pathname !== '/' && <div className="safety-notice" role="note">Research prototype. Not validated for diagnosis or treatment decisions.</div>}
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
