/** Plain-language presentation for the five hypothetical scenario families.
 *  Names and explanations describe only the generated trajectories in the
 *  synthetic bundle. They assert no clinical meaning, prediction or outcome. */

export type FamilyPresentation = {
  plainName: string;
  explanation: string;
};

export const FAMILY_PRESENTATION: Record<string, FamilyPresentation> = {
  'SC-01': {
    plainName: 'Continuous shrinkage',
    explanation:
      'In this hypothetical example, the modeled region keeps getting smaller over time.',
  },
  'SC-02': {
    plainName: 'Little or no size change',
    explanation:
      'In this hypothetical example, the modeled region stays about the same size at every measured point.',
  },
  'SC-03': {
    plainName: 'Continued growth',
    explanation:
      'In this hypothetical example, the modeled region keeps getting larger over time.',
  },
  'SC-04': {
    plainName: 'Shrinks, then grows again',
    explanation:
      'In this hypothetical example, the modeled region becomes smaller before increasing in size at a later point.',
  },
  'SC-05': {
    plainName: 'Stable size with worsening symptoms',
    explanation:
      'In this hypothetical example, the region stays the same size while the reported fatigue rating rises over time.',
  },
};

export function familyPresentation(id: string): FamilyPresentation {
  return (
    FAMILY_PRESENTATION[id] ?? {
      plainName: `Hypothetical scenario ${id}`,
      explanation: 'In this hypothetical example, the modeled region follows generated assumptions.',
    }
  );
}

function toNumber(value: string | null | undefined): number | null {
  if (value == null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/** Deterministic baseline comparison from verified backend values only.
 *  Returns null when either value is missing or the baseline is zero. */
export function volumeComparison(
  baseline: string | null | undefined,
  selected: string | null | undefined,
): string | null {
  const base = toNumber(baseline);
  const current = toNumber(selected);
  if (base === null || current === null || base === 0) return null;
  if (current === base) return 'the same size as';
  const percent = Math.abs(((current - base) / base) * 100);
  const rounded = percent >= 10 ? Math.round(percent) : Math.round(percent * 10) / 10;
  return `${rounded}% ${current < base ? 'smaller than' : 'larger than'}`;
}

/** Human-readable observation name without changing the underlying concept. */
export function readableConcept(concept: string): string {
  const words = concept.replaceAll('_', ' ').split(' ').filter(Boolean);
  return words.map((word, index) => (index === 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word)).join(' ');
}
