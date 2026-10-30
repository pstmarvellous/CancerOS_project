import Link from 'next/link';
import { ObservationTimeline } from '../../components/observation-timeline';

export default function TimelinePage() {
  return <main id="main-content" tabIndex={-1}><p><Link href="/">← Research workspace</Link> · <Link href="/simulation">Simulation workflow</Link></p><div className="intro"><p className="eyebrow">Private research history</p><h1>Inspect an exact observation timeline</h1><p className="lead">Choose a source or published simulation context and inspect immutable observations at a declared revision and knowledge cutoff.</p></div><ObservationTimeline/></main>;
}
