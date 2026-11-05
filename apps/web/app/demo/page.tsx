import { Suspense } from 'react';
import { DemoWorkspace } from '../../components/demo-workspace';
export default function DemoPage() {
  return <Suspense fallback={<p role="status">Opening your digital twin workspace…</p>}><DemoWorkspace /></Suspense>;
}
