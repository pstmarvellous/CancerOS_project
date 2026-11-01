import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { GuidedDemo } from './guided-demo';

describe('COS-080 guided demo', () => {
  it('walks a read-only pinned sequence with safe reset semantics', () => {
    render(<GuidedDemo />);
    expect(screen.getByText(/Step 1 of 7/)).toBeVisible();
    expect(screen.getByText(/cannot delete observations, cancel jobs or regenerate branches/)).toBeVisible();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByText(/Step 2 of 7/)).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Restart' }));
    expect(screen.getByText(/Step 1 of 7/)).toBeVisible();
  });

  it('labels pacing as rehearsal guidance and keeps editor writes isolated', () => {
    render(<GuidedDemo />);
    expect(screen.getByText(/not verified organizer timing/)).toBeVisible();
    expect(screen.getByText(/Editor live-write demonstrations stay explicit and isolated/)).toBeVisible();
  });
});
