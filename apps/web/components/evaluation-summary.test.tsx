import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import EvaluationPage from '../app/evaluation/page';

describe('researcher evaluation summary', () => {
  it('leads with workspace capabilities and honest optional-dependency limits', () => {
    render(<EvaluationPage />);
    expect(screen.getByText('What this build supports for researchers')).toBeVisible();
    expect(screen.getByLabelText('Researcher summary')).toBeVisible();
    expect(screen.getByText(/Optional dependencies:/)).toBeVisible();
    expect(screen.getAllByText(/Missing evidence reads Not evaluated/).length).toBeGreaterThan(0);
  });
});
