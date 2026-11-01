import Link from 'next/link';
import { GuidedDemo } from '../../components/guided-demo';

export default function GuidedDemoPage() {
  return <>
    <div className="intro"><p className="eyebrow">Guided demonstration</p><h1>Follow a pinned authorized path</h1><p className="lead">A read-only sequence across the completed Phase 5 journey with preflight checks and safe reset. Nothing here runs a model or changes patient state.</p></div>
    <GuidedDemo />
    <p><Link href="/">← Research workspace</Link> · <Link href="/evaluation">Evaluation report</Link></p>
  </>;
}
