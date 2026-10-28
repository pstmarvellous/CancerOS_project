'use client';
import { ErrorSummary } from '../components/research';
export default function ErrorBoundary({reset}: {reset: () => void}) {
  return <section className="card"><ErrorSummary message="The workspace could not load. No patient state was changed."/><button onClick={reset}>Try again</button></section>;
}
