import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import MeshRenderer, { type RenderableMesh } from './mesh-renderer';

const fixtures = vi.hoisted(() => ({ controls: [] as { mouseButtons: { LEFT: number }; touches: { ONE: number }; enabled: boolean }[] }));
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
    minZoom = 0.1; maxZoom = 20; mouseButtons = { LEFT: actual.MOUSE.ROTATE }; touches = { ONE: actual.TOUCH.ROTATE };
    constructor(private camera: THREE.Camera) { fixtures.controls.push(this); }
    update() { this.camera.lookAt(this.target); this.camera.updateMatrixWorld(); }
    addEventListener() {} removeEventListener() {} dispose() {}
  } };
});

function asset(): RenderableMesh {
  return { objects: [{ segmentation_id: 'first', surface: {
    vertices: [[0, 0, 0], [2, 0, 0], [0, 2, 0], [0, 0, 2]],
    normals: [[-1, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
    triangles: [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], bounds_min_mm: [0, 0, 0], bounds_max_mm: [2, 2, 2],
    frame: 'RAS', unit: 'mm', algorithm: 'skimage-0.26.0-lewiner/1',
    surface_convention: 'binary_0.5_isosurface_one_zero_pad_integer_voxel_centers', measurement_authority: 'source_mask_not_surface',
    display_to_patient: [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    patient_to_display: [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
  } }] };
}
beforeEach(() => {
  fixtures.controls.length = 0;
  vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} });
});
describe('3D camera interaction', () => {
  it('starts with direct interaction and switches pointer mode without changing geometry', () => {
    const data = asset(), before = structuredClone(data), failure = vi.fn();
    render(<MeshRenderer asset={data} selected="first" onFailure={failure}/>);
    expect(failure).not.toHaveBeenCalled();
    expect(fixtures.controls[0].enabled).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: /^Pan$/ }));
    expect(fixtures.controls[0].mouseButtons.LEFT).toBe(THREE.MOUSE.PAN);
    expect(fixtures.controls[0].touches.ONE).toBe(THREE.TOUCH.PAN);
    fireEvent.click(screen.getByRole('button', { name: /^Orbit$/ }));
    expect(fixtures.controls[0].mouseButtons.LEFT).toBe(THREE.MOUSE.ROTATE);
    expect(data).toEqual(before);
  });
  it('supports keyboard orbit, pan, zoom, reset and resuming after Escape', () => {
    render(<MeshRenderer asset={asset()} selected="first" onFailure={vi.fn()}/>);
    const viewport = screen.getByRole('group', { name: 'Interactive 3D viewport' });
    const canvas = screen.getByRole('img', { name: /physical RAS/ });
    const initial = canvas.getAttribute('data-camera-state');
    for (const event of [{ key: 'ArrowLeft' }, { key: 'ArrowRight', shiftKey: true }, { key: '+' }]) {
      const before = canvas.getAttribute('data-camera-state');
      fireEvent.keyDown(viewport, event);
      expect(canvas.getAttribute('data-camera-state')).not.toBe(before);
    }
    fireEvent.keyDown(viewport, { key: 'r' });
    expect(canvas.getAttribute('data-camera-state')).toBe(initial);
    fireEvent.keyDown(viewport, { key: 'Escape' });
    expect(fixtures.controls[0].enabled).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Interact with 3D' }));
    expect(fixtures.controls[0].enabled).toBe(true);
    expect(document.activeElement).toBe(viewport);
  });
  it('retains the existing physical-transform rejection', () => {
    const data = asset(), failure = vi.fn();
    data.objects[0].surface.display_to_patient[0][3] = 10;
    render(<MeshRenderer asset={data} selected="first" onFailure={failure}/>);
    expect(failure).toHaveBeenCalledOnce();
    expect(screen.queryByRole('img')).toBeNull();
  });
});
