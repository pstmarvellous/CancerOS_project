'use client';

import { useEffect, useId, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { MeshAsset } from './mesh-types';
import styles from './mesh-preview.module.css';

type CameraAction = 'left' | 'right' | 'up' | 'down' | 'pan-left' | 'pan-right' | 'pan-up' | 'pan-down' | 'in' | 'out' | 'fit' | 'reset';
export type RenderableMesh = {objects: Pick<MeshAsset['objects'][number], 'segmentation_id' | 'surface'>[]};
export type ViewerDisplayActions = {
  maximized: boolean;
  fullscreen: boolean;
  fullscreenAvailable: boolean;
  toggleMaximize: () => void;
  toggleFullscreen: () => Promise<void>;
};
export default function MeshRenderer({asset, selected, onFailure, displayActions, label = 'Synthetic region · mm · RAS frame · Z up'}: {asset: RenderableMesh; selected: string; onFailure: () => void; displayActions?: ViewerDisplayActions; label?: string}) {
  const host = useRef<HTMLDivElement>(null);
  const frame = useRef<HTMLElement>(null);
  const actions = useRef<((action: CameraAction) => void) | null>(null);
  const interaction = useRef<((enabled: boolean) => void) | null>(null);
  const pointerMode = useRef<((mode: 'orbit' | 'pan') => void) | null>(null);
  const [mode, setMode] = useState<'orbit' | 'pan'>('orbit');
  const [fullRenderer, setFullRenderer] = useState(false);
  const [fullscreenError, setFullscreenError] = useState('');
  const maximized = displayActions?.maximized ?? fullRenderer;
  const helpId = useId();
  const selection = useRef<((id: string) => void) | null>(null);

  useEffect(() => {
    const element = host.current;
    if (!element) return;
    let renderer: THREE.WebGLRenderer | undefined;
    let controls: OrbitControls | undefined;
    let observer: ResizeObserver | undefined;
    const geometries: THREE.BufferGeometry[] = [];
    const materials: THREE.Material[] = [];
    let disposed = false;
    const lost = (event: Event) => { event.preventDefault(); onFailure(); };
    try {
      const scene = new THREE.Scene();
      scene.background = new THREE.Color('#111827');
      renderer = new THREE.WebGLRenderer({antialias: true, alpha: false});
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      renderer.domElement.setAttribute('aria-label', 'Synthetic region, physical RAS coordinates in millimeters');
      renderer.domElement.setAttribute('role', 'img');
      renderer.domElement.addEventListener('webglcontextlost', lost);
      element.appendChild(renderer.domElement);
      const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 1000);
      camera.up.set(0, 0, 1);
      controls = new OrbitControls(camera, renderer.domElement);
      controls.enabled = true;
      controls.enableDamping = false;
      controls.screenSpacePanning = true;
      controls.minZoom = 0.1; controls.maxZoom = 20;
      renderer.domElement.style.touchAction = 'none';
      element.dataset.interacting = 'true';
      const activeControls = controls;
      const activeRenderer = renderer;
      const objects: THREE.Mesh[] = [];
      const bounds = new THREE.Box3();
      for (const object of asset.objects) {
        for (const point of object.surface.vertices) {
          if (point.length !== 3 || !point.every(Number.isFinite)) throw new Error('Unsupported coordinates');
          bounds.expandByPoint(new THREE.Vector3(...point));
        }
      }
      if (bounds.isEmpty()) throw new Error('Empty geometry');
      const center = bounds.getCenter(new THREE.Vector3());
      const span = Math.max(bounds.getSize(new THREE.Vector3()).length(), 0.001);
      let totalVertices = 0;
      let totalTriangles = 0;
      for (const object of asset.objects) {
        const surface = object.surface;
        const identityTransform = (matrix: number[][]) => matrix.length === 4 && matrix.every((row, i) => row.length === 4 && row.every((value, j) => value === (i === j ? 1 : 0)));
        totalVertices += surface.vertices.length;
        totalTriangles += surface.triangles.length;
        if (surface.unit !== 'mm' || surface.frame !== 'RAS' || !identityTransform(surface.display_to_patient) || !identityTransform(surface.patient_to_display) || totalVertices > 100_000 || totalTriangles > 200_000 || surface.normals.length !== surface.vertices.length || !surface.vertices.every(p => p.length === 3 && p.every(Number.isFinite)) || !surface.normals.every(p => p.length === 3 && p.every(Number.isFinite)) || !surface.triangles.every(f => f.length === 3 && f.every(i => Number.isInteger(i) && i >= 0 && i < surface.vertices.length))) throw new Error('Unsupported geometry');
        const geometry = new THREE.BufferGeometry();
        geometries.push(geometry);
        // A shared translation preserves small regions at large physical origins
        // before Float32 GPU upload. Model position restores the exact shared origin.
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(surface.vertices.flatMap(p => [p[0] - center.x, p[1] - center.y, p[2] - center.z]), 3));
        geometry.setAttribute('normal', new THREE.Float32BufferAttribute(surface.normals.flat(), 3));
        geometry.setIndex(surface.triangles.flat());
        // All objects retain their shared physical coordinates; no object scaling.
        const material = new THREE.MeshStandardMaterial({color: '#c4b5fd', roughness: 0.48, metalness: 0});
        materials.push(material);
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.copy(center);
        mesh.userData.annotationId = object.segmentation_id;
        objects.push(mesh);
        scene.add(mesh);
      }
      scene.add(new THREE.HemisphereLight('#ffffff', '#64748b', 2.5));
      const light = new THREE.DirectionalLight('#ffffff', 3);
      light.position.copy(center).add(new THREE.Vector3(span, -span, span));
      scene.add(light);
      const fill = new THREE.DirectionalLight('#c7d2fe', 0.85);
      fill.position.copy(center).add(new THREE.Vector3(-span, span, span * 0.4));
      scene.add(fill);
      const rim = new THREE.DirectionalLight('#ffffff', 0.6);
      rim.position.copy(center).add(new THREE.Vector3(0, span * 0.4, -span));
      scene.add(rim);
      const render = () => {
        if (!disposed && !document.hidden) {
          activeRenderer.render(scene, camera);
          activeRenderer.domElement.dataset.renderState = 'ready';
          activeRenderer.domElement.dataset.renderReady = 'true';
          activeRenderer.domElement.dataset.camera = JSON.stringify({position: camera.position.toArray(), target: activeControls.target.toArray(), zoom: camera.zoom});
          activeRenderer.domElement.dataset.cameraState = activeRenderer.domElement.dataset.camera;
          const visible = objects.find(mesh => mesh.visible);
          activeRenderer.domElement.dataset.selectedAnnotation = visible?.userData.annotationId ?? '';
          if (visible) {
            visible.updateWorldMatrix(true, false);
            const worldBounds = new THREE.Box3().setFromObject(visible, true);
            activeRenderer.domElement.dataset.worldBounds = JSON.stringify({min: worldBounds.min.toArray(), max: worldBounds.max.toArray()});
          }
          activeRenderer.domElement.dataset.renderCount = String(Number(activeRenderer.domElement.dataset.renderCount || 0) + 1);
        }
      };
      const fit = (reset: boolean) => {
        const direction = camera.position.clone().sub(activeControls.target).normalize();
        if (reset) {
          direction.set(2, -3, 2).normalize();
          camera.up.set(0, 0, 1);
        }
        camera.position.copy(center).add(direction.multiplyScalar(span * 3));
        activeControls.target.copy(center);
        camera.zoom = 1;
        camera.near = Math.max(span / 1000, 0.000001);
        camera.far = span * 20;
        camera.updateProjectionMatrix();
        activeControls.update();
        render();
      };
      const resize = () => {
        const width = Math.max(element.clientWidth, 1), height = Math.max(element.clientHeight, 1);
        const aspect = width / height;
        const halfHeight = span * 0.65 / Math.min(aspect, 1);
        camera.left = -halfHeight * aspect; camera.right = halfHeight * aspect;
        camera.top = halfHeight; camera.bottom = -halfHeight;
        camera.updateProjectionMatrix();
        activeRenderer.setSize(width, height, false);
        render();
      };
      actions.current = action => {
        if (action === 'reset' || action === 'fit') { fit(action === 'reset'); return; }
        if (action === 'in' || action === 'out') {
          camera.zoom = THREE.MathUtils.clamp(camera.zoom * (action === 'in' ? 1.2 : 1 / 1.2), 0.1, 20);
          camera.updateProjectionMatrix();
        } else if (action.startsWith('pan-')) {
          camera.updateMatrixWorld();
          const axis = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, action === 'pan-left' || action === 'pan-right' ? 0 : 1);
          const sign = action === 'pan-left' || action === 'pan-down' ? -1 : 1;
          axis.multiplyScalar(sign * span * 0.1 / camera.zoom);
          camera.position.add(axis); activeControls.target.add(axis);
        } else {
          const offset = camera.position.clone().sub(activeControls.target);
          const axis = action === 'left' || action === 'right' ? new THREE.Vector3(0, 0, 1) : new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
          offset.applyAxisAngle(axis, (action === 'left' || action === 'up' ? 1 : -1) * Math.PI / 12);
          camera.position.copy(activeControls.target).add(offset);
        }
        activeControls.update(); render();
      };
      interaction.current = enabled => {
        activeControls.enabled = enabled;
        element.dataset.interacting = String(enabled);
        renderer!.domElement.style.touchAction = enabled ? 'none' : 'pan-y';
      };
      pointerMode.current = value => {
        activeControls.mouseButtons.LEFT = value === 'pan' ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE;
        activeControls.touches.ONE = value === 'pan' ? THREE.TOUCH.PAN : THREE.TOUCH.ROTATE;
        interaction.current?.(true);
      };
      selection.current = id => { for (const mesh of objects) mesh.visible = mesh.userData.annotationId === id; render(); };
      activeControls.addEventListener('change', render);
      document.addEventListener('visibilitychange', render);
      observer = new ResizeObserver(resize);
      observer.observe(element);
      resize(); fit(true);
      // Selection updates never refit or normalize an individual region.
      return () => {
        disposed = true; observer?.disconnect();
        document.removeEventListener('visibilitychange', render);
        activeControls.removeEventListener('change', render);
        activeControls.dispose();
        activeRenderer.domElement.removeEventListener('webglcontextlost', lost);
        geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose());
        activeRenderer.dispose(); activeRenderer.domElement.remove();
        actions.current = null; interaction.current = null; pointerMode.current = null; selection.current = null;
      };
    } catch {
      observer?.disconnect(); controls?.dispose();
      geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose());
      renderer?.dispose(); renderer?.domElement.remove();
      onFailure();
    }
  }, [asset, onFailure]);

  useEffect(() => { selection.current?.(selected); }, [selected, asset]);
  useEffect(() => { pointerMode.current?.(mode); }, [mode, asset]);
  useEffect(() => {
    if (!fullRenderer) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setFullRenderer(false); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [fullRenderer]);
  async function toggleRendererFullscreen() {
    try {
      if (displayActions) await displayActions.toggleFullscreen();
      else if (document.fullscreenElement) await document.exitFullscreen();
      else await frame.current?.requestFullscreen();
      setFullscreenError('');
    } catch { setFullscreenError('Fullscreen is unavailable in this browser. Use Maximize viewer for more space.'); }
  }
  const steps: [CameraAction, string, string][] = [['left', 'Rotate left', '↶'], ['right', 'Rotate right', '↷'],
    ['pan-left', 'Pan left', '←'], ['pan-right', 'Pan right', '→'], ['in', 'Zoom in', '+'], ['out', 'Zoom out', '−'],
    ['fit', 'Fit view', 'Fit'], ['reset', 'Reset view', 'Reset']];
  return <section ref={frame} className={styles.renderer} aria-label="3D region controls" data-maximized={fullRenderer || undefined}>
    <div className={styles.controls} role="toolbar" aria-label="Camera controls">
      <span role="group" aria-label="Pointer mode">{(['orbit', 'pan'] as const).map(value =>
        <button key={value} type="button" aria-pressed={mode === value} title={`${value === 'orbit' ? 'Orbit' : 'Pan'} with pointer drag`}
          onClick={() => { setMode(value); pointerMode.current?.(value); }}>{value === 'orbit' ? 'Orbit' : 'Pan'}</button>)}</span>
      <span role="group" aria-label="Zoom">{(['out', 'in'] as const).map(action =>
        <button key={action} type="button" title={action === 'in' ? 'Zoom in' : 'Zoom out'} aria-label={action === 'in' ? 'Zoom in' : 'Zoom out'}
          onClick={() => actions.current?.(action)}>{action === 'in' ? '+' : '−'}</button>)}</span>
      <span role="group" aria-label="Framing">
        <button type="button" title="Fit view" aria-label="Fit view" onClick={() => actions.current?.('fit')}>Fit</button>
        <button type="button" title="Reset view" aria-label="Reset view" onClick={() => actions.current?.('reset')}>Reset</button>
      </span>
      <span role="group" aria-label="Display size">
        <button type="button" title={maximized ? 'Restore viewer size' : 'Maximize viewer'} aria-label={maximized ? 'Restore viewer size' : 'Maximize viewer'} aria-pressed={maximized}
          onClick={() => displayActions ? displayActions.toggleMaximize() : setFullRenderer(open => !open)}>{maximized ? '⤢' : '⛶'}</button>
        {(!displayActions || displayActions.fullscreenAvailable) && <button type="button" title={displayActions?.fullscreen ? 'Exit fullscreen' : 'Fullscreen viewer'} aria-label={displayActions?.fullscreen ? 'Exit fullscreen' : 'Fullscreen viewer'} aria-pressed={displayActions?.fullscreen}
          onClick={() => void toggleRendererFullscreen()}>{displayActions?.fullscreen ? 'Exit fullscreen' : 'Fullscreen'}</button>}
      </span>
      <details className={styles.extraControls}><summary>More camera controls</summary><div>
        {steps.map(([action, text, icon]) =>
          <button key={action} type="button" title={text} aria-label={text} onClick={() => actions.current?.(action)}>{icon} {text}</button>)}
        {([['up', 'Rotate up'], ['down', 'Rotate down'], ['pan-up', 'Pan up'], ['pan-down', 'Pan down']] as [CameraAction, string][]).map(([action, text]) =>
          <button key={action} type="button" title={text} aria-label={text} onClick={() => actions.current?.(action)}>{text}</button>)}
      </div></details>
    </div>
    {fullscreenError && <p role="status">{fullscreenError}</p>}
    <div className={styles.viewport} ref={host} tabIndex={0} role="group" aria-label="Interactive 3D viewport" aria-describedby={helpId}
      onPointerDown={event => { if (event.target instanceof HTMLCanvasElement) event.currentTarget.focus({ preventScroll: true }); }}
      onKeyDown={event => {
        if (event.target !== event.currentTarget) return;
        const arrow = { ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down' } as const;
        const direction = arrow[event.key as keyof typeof arrow];
        const action = direction ? (event.shiftKey ? `pan-${direction}` : direction) as CameraAction :
          ({ '+': 'in', '=': 'in', '-': 'out', f: 'fit', F: 'fit', r: 'reset', R: 'reset' } as Record<string, CameraAction>)[event.key];
        if (action) { event.preventDefault(); actions.current?.(action); }
        if (event.key === 'Escape') interaction.current?.(false);
      }}>
      <p className={styles.viewportLabel}>{label}</p>
      <button data-interact className={styles.interact} type="button" onClick={() => { interaction.current?.(true); host.current?.focus({ preventScroll: true }); }}>Interact with 3D</button>
    </div>
    <p id={helpId} className={styles.cameraHelp}>Drag to {mode}; right-drag to pan; scroll or pinch to zoom. Keyboard: arrows orbit, Shift + arrows pan, + / − zoom, F fit, R reset. Escape pauses pointer interaction. Scale stays shared across states.</p>
  </section>;
}
