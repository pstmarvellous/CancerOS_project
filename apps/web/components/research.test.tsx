import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ErrorSummary, LoadingState, ModalityStatus, ProvenanceBadge, TimeLabel } from './research';
import { Connectivity } from './connectivity';

describe('research disclosure and missingness', () => {
  it.each([['REAL_OBSERVED','Real observed'],['REAL_DERIVED','Real derived'],['SYNTHETIC_GENERATED','Hypothetical simulation'],['INTERPOLATED','Interpolated'],['MODEL_PREDICTED','Model predicted'],['future','Unknown origin']])('labels %s', (origin,label) => {
    render(<ProvenanceBadge origin={origin}/>);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
  it('keeps unknown time and status explicit', () => {
    render(<><TimeLabel time={null}/><ModalityStatus label="MRI" availability="future"/></>);
    expect(screen.getByText(/Time unknown/)).toBeVisible();
    expect(screen.getByText('MRI: Unknown status')).toBeVisible();
  });
  it('does not invent a calendar date for a relative time', () => {
    render(<TimeLabel time={{basis:'relative_day',value:'0',time_domain:'source_relative',timeline_origin_id:'00000000-0000-4000-8000-000000000010'}}/>);
    expect(screen.getByText('Source-relative day 0')).toBeVisible();
  });
  it('escapes untrusted text and announces errors/loading', () => {
    const {container} = render(<><ErrorSummary message="<script>secret()</script>"/><LoadingState/></>);
    expect(container.querySelector('script')).toBeNull();
    expect(screen.getByRole('alert')).toBeVisible();
    expect(screen.getByRole('status')).toHaveTextContent('Loading');
  });
  it('provides a keyboard-focusable check and truthful network failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('unavailable')));
    render(<Connectivity/>);
    const button = screen.getByRole('button', {name:'Check API connection'});
    button.focus(); expect(button).toHaveFocus();
    fireEvent.click(button);
    expect(await screen.findByText(/API process unavailable/)).toBeVisible();
    vi.unstubAllGlobals();
  });
});
