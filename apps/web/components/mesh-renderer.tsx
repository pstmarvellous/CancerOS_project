'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { MeshAsset } from './mesh-types';
import styles from './mesh-preview.module.css';

type CameraAction = 'left' | 'right' | 'up' | 'down' | 'pan-left' | 'pan-right' | 'pan-up' | 'pan-down' | 'in' | 'out' | 'fit' | 'reset';
export type RenderableMesh = {objects: Pick<MeshAsset['objects'][number], 'segmentation_id' | 'surface'>[]};
export default function MeshRenderer({asset, selected, onFailure}: {asset: RenderableMesh; selected: string; onFailure: () => void}) {
  const host = useRef<HTMLDivElement>(null);
  const actions = useRef<((action: CameraAction) => void) | null>(null);
  const interaction = useRef<(() => void) | null>(null);
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
      renderer.domElement.setAttribute('aria-label', 'Private synthetic engineering region, physical RAS coordinates in millimeters');
      renderer.domElement.setAttribute('role', 'img');
      renderer.domElement.addEventListener('webglcontextlost', lost);
      element.appendChild(renderer.domElement);
      const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 1000);
      camera.up.set(0, 0, 1);
      controls = new OrbitControls(camera, renderer.domElement);
      controls.enabled = false;
      controls.enableDamping = false;
      controls.screenSpacePanning = true;
      controls.minZoom = 0.1; controls.maxZoom = 20;
      renderer.domElement.style.touchAction = 'pan-y';
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
        const material = new THREE.MeshStandardMaterial({color: '#c4b5fd', roughness: 0.55, metalness: 0});
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
      interaction.current = () => {
        activeControls.enabled = !activeControls.enabled;
        element.dataset.interacting = String(activeControls.enabled);
        renderer!.domElement.style.touchAction = activeControls.enabled ? 'none' : 'pan-y';
        const button = element.querySelector<HTMLButtonElement>('[data-interact]');
        if (button) {
          button.setAttribute('aria-pressed', String(activeControls.enabled));
          button.textContent = activeControls.enabled ? 'Done interacting' : 'Interact with 3D';
        }
      };
      selection.current = id => { for (const mesh of objects) mesh.visible = mesh.userData.annotationId === id; render(); };
      const outside = (event: PointerEvent) => {
        if (activeControls.enabled && event.target instanceof Node && !element.contains(event.target)) interaction.current?.();
      };
      document.addEventListener('pointerdown', outside);
      activeControls.addEventListener('change', render);
      document.addEventListener('visibilitychange', render);
      observer = new ResizeObserver(resize);
      observer.observe(element);
      resize(); fit(true);
      // Selection updates never refit or normalize an individual region.
      return () => {
        disposed = true; observer?.disconnect();
        document.removeEventListener('visibilitychange', render);
        document.removeEventListener('pointerdown', outside);
        activeControls.removeEventListener('change', render);
        activeControls.dispose();
        activeRenderer.domElement.removeEventListener('webglcontextlost', lost);
        geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose());
        activeRenderer.dispose(); activeRenderer.domElement.remove();
        actions.current = null; interaction.current = null; selection.current = null;
      };
    } catch {
      observer?.disconnect(); controls?.dispose();
      geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose());
      renderer?.dispose(); renderer?.domElement.remove();
      onFailure();
    }
  }, [asset, onFailure]);

  useEffect(() => { selection.current?.(selected); }, [selected, asset]);
  const buttons: [CameraAction, string][] = [['left', 'Rotate left'], ['right', 'Rotate right'], ['up', 'Rotate up'], ['down', 'Rotate down'], ['pan-left', 'Pan left'], ['pan-right', 'Pan right'], ['pan-up', 'Pan up'], ['pan-down', 'Pan down'], ['in', 'Zoom in'], ['out', 'Zoom out'], ['fit', 'Fit view'], ['reset', 'Reset view']];
  return <section aria-label="3D region controls">
    <div className={styles.viewport} ref={host} onKeyDown={event => { if (event.key === 'Escape' && host.current?.dataset.interacting === 'true') interaction.current?.(); }}>
      <p className={styles.viewportLabel}>Engineering region · synthetic · mm · RAS frame · Z up</p>
      <button data-interact className={styles.interact} aria-pressed="false" onClick={() => interaction.current?.()}>Interact with 3D</button>
    </div>
    <p>Use the buttons below, or enable viewport interaction to drag, pan and zoom. Escape ends viewport interaction. Camera scale is shared across all regions in this asset.</p>
    <div className={styles.controls}>{buttons.map(([action, label]) => <button key={action} onClick={() => actions.current?.(action)}>{label}</button>)}</div>
  </section>;
}
