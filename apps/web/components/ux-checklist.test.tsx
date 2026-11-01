import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { UxChecklist } from './ux-checklist';

describe('COS-080 UX checklist', () => {
  it('maps all eighteen checks with honest manual gaps', () => {
    render(<UxChecklist />);
    expect(screen.getByText(/UX-01–UX-18 acceptance evidence/)).toBeVisible();
    expect(screen.getByText(/without claiming conformance from an automated scan/)).toBeVisible();
    fireEvent.change(screen.getByLabelText('Show'), { target: { value: 'manual' } });
    expect(screen.getByText(/UX-18 · Measured performance and trials/)).toBeVisible();
    expect(screen.getByText('Not measured')).toBeVisible();
  });
});
