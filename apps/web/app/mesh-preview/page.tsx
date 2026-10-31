import Link from 'next/link';
import { MeshPreview } from '../../components/mesh-preview';

export default function MeshPreviewPage() {
  return <>
    <p><Link href="/">← Research workspace</Link></p>
    <div className="intro"><p className="eyebrow">Restricted engineering preview</p><h1>Inspect physical region geometry</h1><p className="lead">Rotate an authorized, QC-checked synthetic mesh and inspect its source-mask measurements. This fixture preview does not establish patient anatomy or clinical validity.</p></div>
    <MeshPreview/>
  </>;
}
