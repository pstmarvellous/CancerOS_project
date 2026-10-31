import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AppShell } from './app-shell';

vi.mock('next/navigation', () => ({
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams('project=a&patient=b&branch=c&state=d&lesion=e'),
}));

describe('COS-072 shell selection ownership', () => {
  it('shows one active selection from the URL and keeps browser storage clear of payloads', () => {
    render(<AppShell/>);
    expect(screen.getByText(/Selection: a \/ b \/ c \/ d/)).toBeVisible();
    expect(window.sessionStorage.length).toBe(0);
    expect(window.localStorage.length).toBe(0);
  });
  it('exposes primary navigation with an active page marker and skip link', () => {
    render(<AppShell/>);
    expect(screen.getByRole('link', {name: 'Skip to main content'})).toBeVisible();
    expect(screen.getByRole('navigation', {name: 'Primary'})).toBeVisible();
    expect(screen.getByRole('link', {name: 'Research workspace'})).toHaveAttribute('aria-current', 'page');
    for (const label of ['Cases', 'Guided demo', 'Evaluation']) {
      expect(screen.getByRole('link', {name: label})).toBeVisible();
    }
  });
});
