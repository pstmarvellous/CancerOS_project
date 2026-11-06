import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { LesionViewer } from './lesion-viewer';

vi.mock('three', async importOriginal => {
  const actual = await importOriginal<typeof import('three')>();
  return { ...actual, WebGLRenderer: class {
    domElement = document.createElement('canvas');
    setPixelRatio() {} setSize() {} render() {} dispose() {}
  } };
});
vi.mock('three/addons/controls/OrbitControls.js', async () => {
  const actual = await vi.importActual<typeof import('three')>('three');
  return { OrbitControls: class {
    target = new actual.Vector3(); enabled = true; enableDamping = false; screenSpacePanning = true;
    minZoom = 0.1; maxZoom = 20;
    mouseButtons = { LEFT: actual.MOUSE.ROTATE }; touches = { ONE: actual.TOUCH.ROTATE };
    constructor() {}
    update() {} addEventListener() {} removeEventListener() {} dispose() {}
  } };
});

const project = '11111111-1111-1111-1111-111111111111';
const patient = '22222222-2222-2222-2222-222222222222';
const LESION = '44444444-4444-4444-4444-444444444444';
const REPORT = '55555555-5555-5555-5555-555555555555';
const MEASUREMENT = '66666666-6666-6666-6666-666666666666';

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(''),
}));

function stubFetch() {
  return vi.fn(async (input: unknown) => {
    const url = String(input);
    if (url.includes('resource=lesions')) {
      return { ok: true, text: async () => JSON.stringify([{ id: LESION }]) };
    }
    if (url.includes('resource=geometry')) {
      return {
        ok: true,
        text: async () => JSON.stringify({
          id: REPORT, measurement_id: MEASUREMENT, input_revision: 1, status: 'validated', output_artifact_id: REPORT,
          selected_byte_size: 2048, selected_triangles: 12, budget_met: true, origin: 'SYNTHETIC_GENERATED', objects: [],
        }),
      };
    }
    if (url.includes('resource=measurement')) {
      return {
        ok: true,
        text: async () => JSON.stringify({
          id: MEASUREMENT, input_revision: 1, origin: 'SYNTHETIC_GENERATED', source_time_basis: 'not_recorded',
          values: { volume_mm3: 120.5, volume_cm3: 0.1205, centroid_ras_mm: [1, 2, 3] },
        }),
      };
    }
    return {
      ok: true,
      text: async () => JSON.stringify({
        format: 'canceros-mesh-json/1',
        objects: [{
          segmentation_id: '77777777-7777-7777-7777-777777777777', label: 1, annotation_class: 'verified_lesion', mask_sha256: 'a'.repeat(64),
          surface: { vertices: [[0, 0, 0]], normals: [[0, 0, 1]], triangles: [[0, 0, 0]], unit: 'mm', frame: 'RAS', display_to_patient: [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], patient_to_display: [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], bounds_min_mm: [0, 0, 0], bounds_max_mm: [1, 1, 1] },
        }],
      }),
    };
  });
}

afterEach(() => vi.unstubAllGlobals());

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });
});

describe('workspace-routed lesion viewer without manual UUID entry', () => {
  it('accepts case context as props and shows the server measurement overlay', async () => {
    const fetch = stubFetch();
    vi.stubGlobal('fetch', fetch);
    render(<LesionViewer project={project} patient={patient} />);
    await waitFor(() => expect(screen.getByLabelText('Server measurement')).toBeVisible(), { timeout: 15000 });
    expect(screen.getByText(/Server measurement 120\.5 mm³/)).toBeVisible();
    expect(screen.getByText(/server mask measurement/)).toBeVisible();
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining(`project=${project}&patient=${patient}&resource=lesions`), expect.anything());
  });
});
