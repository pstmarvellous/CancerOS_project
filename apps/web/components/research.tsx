import type { FoundationEnvelope } from '@canceros/contracts';

type Origin = FoundationEnvelope['origin'];
const origins: Record<Origin, {label: string; symbol: string; kind: string}> = {
  REAL_OBSERVED: {label: 'Real observed', symbol: '●', kind: 'observed'},
  REAL_DERIVED: {label: 'Real derived', symbol: '■', kind: 'derived'},
  SYNTHETIC_GENERATED: {label: 'Hypothetical simulation', symbol: '◆', kind: 'simulated'},
  INTERPOLATED: {label: 'Interpolated', symbol: '◇', kind: 'warning'},
  MODEL_PREDICTED: {label: 'Model predicted', symbol: '△', kind: 'warning'},
};

export function ProvenanceBadge({origin}: {origin: string}) {
  const value = Object.prototype.hasOwnProperty.call(origins, origin)
    ? origins[origin as Origin]
    : {label: 'Unknown origin', symbol: '?', kind: 'warning'};
  return <span className={`badge ${value.kind}`}><span aria-hidden="true">{value.symbol}</span> {value.label}</span>;
}

export function TimeLabel({time}: {time: FoundationEnvelope['time'] | null}) {
  if (!time || time.basis === 'unknown') return <span>Time unknown · not placed on a timeline</span>;
  if (time.basis === 'relative_day') {
    return <span>{time.time_domain === 'simulation' ? 'Simulation' : 'Source-relative'} day {time.value}</span>;
  }
  return <span>{time.value}{time.time_domain === 'source_shifted' ? ' · shifted source date' : ''}</span>;
}

export function ModalityStatus({label, availability}: {label: string; availability: string}) {
  const statuses: Record<string, string> = {
    available: 'Available', unavailable: 'Unavailable', pending: 'Pending',
    invalid: 'Invalid', rejected: 'Rejected', not_applicable: 'Not applicable',
  };
  return <span>{label}: {statuses[availability] ?? 'Unknown status'}</span>;
}

export function ErrorSummary({message}: {message: string}) {
  return <div role="alert" className="error"><strong>Unable to complete this request.</strong><p>{message}</p></div>;
}

export function LoadingState() {
  return <p role="status" aria-live="polite">Loading research workspace…</p>;
}
