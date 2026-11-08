'use client';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { readCaseSelection, withCaseSelection, type CaseSelection } from '../lib/case-selection';

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
  const stored = readCaseSelection(params);
  return {
    project: pick('project') ?? stored.project ?? undefined,
    patient: pick('patient') ?? stored.patient ?? undefined,
    branch: pick('branch'), run: pick('run'), state: pick('state'), lesion: pick('lesion'),
    panel: pick('panel'), compare: pick('compare'),
  };
}

function selectionLabel(selection: Selection): string | null {
  if (selection.patient && selection.project) return `Research case active — project and patient selected`;
  if (selection.project) return `Research project selected`;
  return null;
}

function ShellInner() {
  const pathname = usePathname();
  const params = useSearchParams();
  const selection = readSelection(params);
  const label = selectionLabel(selection);
  const showCaseNav = selection.patient && ['/cases/detail', '/twin', '/states', '/charts', '/insights', '/simulation', '/timeline'].some(r => pathname.startsWith(r));
  return <>
    <a className="skip-link" href="#main">Skip to main content</a>
    <header className="header">
      <div className="brand-row">
        <Link className="brand" href="/">CancerOS <span>Research digital twin</span></Link>
        {label ? <span className="selection" style={{fontSize:12, color:'#64748b'}}>{label} {pathname.startsWith('/demo') ? '· synthetic demo mode' : ''} — selection persisted via secure cookie + local storage</span> : null}
        {selection.project && selection.patient ? <details className="selection" style={{fontSize:11, color:'#94a3b8'}}><summary>Technical selection reference (advanced)</summary><span>Project {selection.project.slice(0,8)}… · Patient {selection.patient.slice(0,8)}…{selection.lesion?` · Lesion ${selection.lesion.slice(0,8)}…`:''}</span></details> : null}
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
            } else if(selection.project && selection.patient) {
              if (item.href === '/cases/detail') target = withCaseSelection(item.href, selection as CaseSelection);
              else if (item.href === '/cases') target = `/cases?project=${encodeURIComponent(selection.project)}`;
              else if (['/twin','/charts','/simulation','/insights','/states','/timeline'].includes(item.href)) {
                target = withCaseSelection(item.href, selection as CaseSelection);
              }
            } else if(selection.project && item.href === '/cases') {
              target = `/cases?project=${encodeURIComponent(selection.project)}`;
            }
            return <li key={item.href}><Link href={target} aria-current={active ? 'page' : undefined}>{item.label}</Link></li>;
          })}
        </ul>
      </nav>
    </header>
    {showCaseNav ? <nav aria-label="Case workspace" className="case-nav">
      <ul className="nav-list">
        <li><span style={{fontSize:11, color:'#94a3b8', textTransform:'uppercase', letterSpacing:'0.6px', marginRight:8}}>Case workspace</span></li>
        {CASE_NAV.map(item => {
          if (item.href === '/sources') return null;
          const href = preserveSelection(item.href, selection);
          const isActive = pathname.startsWith(item.href);
          return <li key={item.label}><Link href={href} aria-current={isActive ? 'page' : undefined}>{item.label}</Link></li>;
        })}
        <li><Link href={`/cases?project=${encodeURIComponent(selection.project!)}`} title="Return to case library">← Library</Link></li>
      </ul>
    </nav> : null}
    {pathname !== '/' && <div className="safety-notice" role="note">Research prototype. Not validated for diagnosis or treatment decisions. Missing values stay “Not recorded”; synthetic hypotheticals stay labeled.</div>}
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
