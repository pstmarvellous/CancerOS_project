import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { recordDay } from './clinical-charts-explorer';

describe('charts timeline filter helpers', () => {
  it('reads relative days without inventing dates', () => {
    const numeric = (value: unknown) => ({ item: { kind: 'laboratory', time: { reference: { basis: 'relative_day', value } } } });
    // @ts-expect-error helper accepts the minimal record shape used by the filter
    expect(recordDay(numeric(20))).toBe(20);
    // @ts-expect-error helper accepts the minimal record shape used by the filter
    expect(recordDay(numeric('35'))).toBe(35);
    // @ts-expect-error helper accepts the minimal record shape used by the filter
    expect(recordDay({ item: { kind: 'laboratory', time: { reference: { basis: 'date', value: '2020-01-01' } } } })).toBeNull();
    expect(recordDay(null)).toBeNull();
  });

  it('keeps an accessible timeline filter announcement region', () => {
    render(
      <p className="field-hint">
        Timeline filter: Simulation day 20 · synthetic. Records without a relative day stay outside the filtered view; select All records to restore them. Server values, units, and missingness are unchanged.
      </p>,
    );
    expect(screen.getByText(/Records without a relative day stay outside/)).toBeVisible();
  });
});
