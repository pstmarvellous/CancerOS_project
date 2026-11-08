import { describe, expect, it } from 'vitest';
import { familyPresentation, readableConcept, volumeComparison } from './scenario-presentation';

describe('scenario presentation', () => {
  it('names all five families in plain language with trajectory-faithful explanations', () => {
    expect(familyPresentation('SC-01').plainName).toBe('Continuous shrinkage');
    expect(familyPresentation('SC-02').plainName).toBe('Little or no size change');
    expect(familyPresentation('SC-03').plainName).toBe('Continued growth');
    expect(familyPresentation('SC-04').plainName).toBe('Shrinks, then grows again');
    expect(familyPresentation('SC-05').plainName).toBe('Stable size with worsening symptoms');
    for (const id of ['SC-01', 'SC-02', 'SC-03', 'SC-04', 'SC-05']) {
      const explanation = familyPresentation(id).explanation;
      expect(explanation).toMatch(/hypothetical example/i);
      expect(explanation).not.toMatch(/predict|prognos|diagnos|response categor|will /i);
    }
    expect(familyPresentation('SC-99').plainName).toContain('SC-99');
  });

  it('compares verified volumes deterministically against the stated baseline', () => {
    expect(volumeComparison('216', '64')).toBe('70% smaller than');
    expect(volumeComparison('216', '729')).toBe('238% larger than');
    expect(volumeComparison('216', '216')).toBe('the same size as');
    expect(volumeComparison(null, '64')).toBeNull();
    expect(volumeComparison('216', null)).toBeNull();
    expect(volumeComparison('0', '64')).toBeNull();
    expect(volumeComparison('unmeasured', '64')).toBeNull();
  });

  it('renders readable observation names without changing concepts', () => {
    expect(readableConcept('hemoglobin')).toBe('Hemoglobin');
    expect(readableConcept('heart_rate')).toBe('Heart rate');
    expect(readableConcept('source_note')).toBe('Source note');
  });
});
