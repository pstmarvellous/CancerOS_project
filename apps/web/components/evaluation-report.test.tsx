import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EvaluationReport } from './evaluation-report';

describe('COS-080 evaluation report', () => {
  it('separates fixture evidence from unevaluated and blocked scope', () => {
    const { container } = render(<EvaluationReport />);
    expect(screen.getByText(/Passing interface checks do not prove clinical suitability/)).toBeVisible();
    expect(screen.getByText(/Synthetic branches are never counted as independent real/)).toBeVisible();
    expect(screen.getAllByText('Not evaluated').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Blocked').length).toBeGreaterThan(0);
    expect(container.textContent).not.toMatch(/%/);
  });
});
