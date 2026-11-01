import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LesionViewer } from './lesion-viewer';

const LESION = '44444444-4444-4444-4444-444444444444';
const REPORT = '55555555-5555-5555-5555-555555555555';
const MEASUREMENT = '66666666-6666-6666-6666-666666666666';

function stubFetch() {
  return vi.fn(async (input: unknown) => {
    const url = String(input);
    if (url.includes('resource=lesions')) {
      return { ok: true, text: async () => JSON.stringify([{ id: LESION }]) };
    }
    if (url.includes('resource=geometry')) {
      return {
        ok: true,
        text: async () =>
          JSON.stringify({
            id: REPORT,
            measurement_id: MEASUREMENT,
            input_revision: 2,
            status: 'validated',
            output_artifact_id: REPORT,
            selected_byte_size: 2048,
            selected_triangles: 12,
            budget_met: true,
            origin: 'SYNTHETIC_GENERATED',
            objects: [],
          }),
      };
    }
    if (url.includes('resource=measurement')) {
      return {
        ok: true,
        text: async () =>
          JSON.stringify({
            id: MEASUREMENT,
            input_revision: 2,
            origin: 'SYNTHETIC_GENERATED',
            source_time_basis: 'not_recorded',
            values: { volume_mm3: 120.5, volume_cm3: 0.1205, centroid_ras_mm: [1, 2, 3] },
          }),
      };
    }
    return {
      ok: true,
      text: async () =>
        JSON.stringify({
          format: 'canceros-mesh-json/1',
          objects: [
            {
              segmentation_id: '77777777-7777-7777-7777-777777777777',
              label: 1,
              annotation_class: 'verified_lesion',
              mask_sha256: 'a'.repeat(64),
              surface: {
                vertices: [[0, 0, 0]],
                normals: [[0, 0, 1]],
                triangles: [[0, 0, 0]],
                unit: 'mm',
                frame: 'RAS',
                display_to_patient: [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
                patient_to_display: [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
                bounds_min_mm: [0, 0, 0],
                bounds_max_mm: [1, 1, 1],
              },
            },
          ],
        }),
    };
  });
}

describe('COS-075 lesion viewer', () => {
  it('asks for a case instead of guessing one', () => {
    Object.defineProperty(window, 'location', { value: { search: '' }, writable: true });
    render(<LesionViewer />);
    expect(screen.getByText(/Open a case to inspect its lesion/)).toBeVisible();
  });

  it('loads authorized geometry with server measurements', async () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?project=11111111-1111-1111-1111-111111111111&patient=22222222-2222-2222-2222-222222222222',
      },
      writable: true,
    });
    vi.stubGlobal('fetch', stubFetch());
    render(<LesionViewer />);
    await waitFor(() => expect(screen.getByText(/Authorized geometry ready/)).toBeVisible(), { timeout: 10000 });
    expect(screen.getByText(/source mask is authoritative/)).toBeVisible();
    expect(screen.getByText(/Observation time/)).toBeVisible();
    vi.unstubAllGlobals();
  });

  it('switches lesions without inventing geometry', async () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?project=11111111-1111-1111-1111-111111111111&patient=22222222-2222-2222-2222-222222222222',
      },
      writable: true,
    });
    const second = '88888888-8888-8888-8888-888888888888';
    const fetchMock = vi.fn(async (input: unknown) => {
      const url = String(input);
      if (url.includes('resource=lesions')) {
        return { ok: true, text: async () => JSON.stringify([{ id: LESION }, { id: second }]) };
      }
      return stubFetch()(input);
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<LesionViewer />);
    const picker = await screen.findByLabelText('Lesion', {}, { timeout: 10000 });
    fireEvent.change(picker, { target: { value: second } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining(second), expect.anything()));
    vi.unstubAllGlobals();
  });
});
