import { expect, test } from '@playwright/test';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';

const path = '.local/mesh-browser-fixture.json';
test('real private synthetic mesh, camera controls and authorization recovery', async ({page}) => {
  test.skip(!existsSync(path), 'Explicit disposable browser fixture API is required; this is not a pass.');
  const fixture = JSON.parse(readFileSync(path, 'utf8'));
  const started = performance.now();
  await page.goto('http://127.0.0.1:3000/mesh-preview');
  await page.getByLabel('Project UUID', {exact:true}).fill(fixture.project_id);
  await page.getByLabel('Patient UUID', {exact:true}).fill(fixture.patient_id);
  await page.getByLabel('Mesh QC report UUID', {exact:true}).fill(fixture.mesh_qc_id);
  // Avoid putting a bearer token in locator action diagnostics or test evidence.
  await page.evaluate(value => {
    const input = document.querySelector<HTMLInputElement>('input[type=password]')!;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!;
    setter.call(input, value); input.dispatchEvent(new Event('input', {bubbles:true}));
  }, fixture.token);
  const assetResponse = page.waitForResponse(response => response.url().endsWith('/asset') && response.status() === 200);
  await page.getByRole('button', {name:'Load private mesh', exact:true}).click();
  const asset = await (await assetResponse).json();
  await expect(page.getByRole('status').filter({hasText:'Authorized private engineering geometry loaded'})).toBeVisible();
  const canvas = page.getByRole('img', {name:'Synthetic region, physical RAS coordinates in millimeters'});
  await expect(canvas).toBeVisible();
  await expect(canvas).toHaveAttribute('data-render-ready', 'true');
  const loadMs = performance.now() - started;
  await expect(page.getByText('Synthetic engineering fixture · private draft · scientific review pending', {exact:true})).toBeVisible();
  await expect(page.getByText(/No eligible patient-specific breast anatomy is available/)).toBeVisible();
  await expect(page.getByText(/Not recorded\. No follow-up time is inferred/)).toBeVisible();
  const union = page.getByRole('row').filter({has:page.getByRole('rowheader', {name:'Explicit selected-label union mask volume'})});
  await expect(union).toContainText(`${fixture.expected_volume_mm3} mm³`);
  const initialCamera = await canvas.getAttribute('data-camera-state');
  expect(initialCamera).toBeTruthy();
  const initialPixels = await canvas.screenshot();
  for (const label of ['Rotate left', 'Pan right', 'Zoom in']) {
    const before = await canvas.getAttribute('data-camera-state');
    const control = page.getByRole('button', {name:label, exact:true});
    await control.focus(); await control.press('Enter');
    await expect(canvas).not.toHaveAttribute('data-camera-state', before!);
  }
  expect((await canvas.screenshot()).equals(initialPixels)).toBe(false);
  await page.getByRole('button', {name:'Reset view', exact:true}).click();
  const resetCamera = await canvas.getAttribute('data-camera-state');
  const initial = JSON.parse(initialCamera!);
  const reset = JSON.parse(resetCamera!);
  for (let index=0; index<3; index++) {
    expect(reset.position[index]).toBeCloseTo(initial.position[index], 9);
    expect(reset.target[index]).toBeCloseTo(initial.target[index], 9);
  }
  expect(reset.zoom).toBe(initial.zoom);
  const selector = page.getByRole('combobox');
  const options = selector.locator('option');
  const optionCount = await options.count();
  expect(optionCount).toBe(asset.objects.length);
  for (let index=0; index<optionCount; index++) {
    await selector.selectOption({index});
    const id = await selector.inputValue();
    const object = asset.objects.find((item:{segmentation_id:string}) => item.segmentation_id === id);
    await expect(canvas).toHaveAttribute('data-selected-annotation', id);
    await expect(canvas).toHaveAttribute('data-camera-state', resetCamera!);
    const bounds = page.getByRole('row').filter({has:page.getByRole('rowheader', {name:'Selected surface bounds, RAS'})});
    await expect(bounds).toContainText(`${object.surface.bounds_min_mm.join(', ')} to ${object.surface.bounds_max_mm.join(', ')} mm`);
    const actualWorldBounds = JSON.parse((await canvas.getAttribute('data-world-bounds'))!);
    for (let axis=0; axis<3; axis++) {
      expect(Math.abs(actualWorldBounds.min[axis] - object.surface.bounds_min_mm[axis])).toBeLessThanOrEqual(1e-5);
      expect(Math.abs(actualWorldBounds.max[axis] - object.surface.bounds_max_mm[axis])).toBeLessThanOrEqual(1e-5);
    }
  }
  // A real graphics-context loss must retain authoritative scalar data and recover.
  await canvas.evaluate(element => {
    const context = (element as HTMLCanvasElement).getContext('webgl2');
    const extension = context?.getExtension('WEBGL_lose_context');
    if (!extension) throw new Error('Actual browser context-loss extension is required');
    extension.loseContext();
  });
  await expect(page.getByRole('alert').filter({hasText:'3D is unavailable'})).toBeVisible();
  await expect(union).toContainText(`${fixture.expected_volume_mm3} mm³`);
  await page.getByRole('button', {name:'Retry 3D', exact:true}).click();
  await expect(canvas).toHaveAttribute('data-render-ready', 'true');
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.setViewportSize({width:1280,height:1100});
  // Hide all identifiers/credential input fields in exported fixture-only evidence.
  await page.locator('form').evaluate(element => { (element as HTMLElement).style.display='none'; });
  await page.screenshot({path:'docs/engineering/evidence/mesh-preview.png', fullPage:true});
  await page.locator('form').evaluate(element => { (element as HTMLElement).style.display=''; });
  await page.getByText('Private connection', {exact:true}).click();
  await page.getByLabel('Access token', {exact:true}).fill('invalid');
  await expect(canvas).toHaveCount(0);
  await page.getByRole('button', {name:'Load private mesh', exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Access denied');
  await expect(page.getByRole('region', {name:'Authorized engineering mesh'})).toHaveCount(0);
  expect(await page.evaluate(() => sessionStorage.length + localStorage.length)).toBe(0);
  writeFileSync('docs/engineering/evidence/mesh-browser-measurement.json', JSON.stringify({
    recorded_at:new Date().toISOString(),
    scope:'Real loopback HTTP, disposable PostgreSQL, private S3, synthetic engineering cuboid only; no clinical or large-study performance claim',
    actual_render_ready_load_ms:loadMs,
    displayed_objects:asset.objects.length,
    authorization_denial_clears_old_geometry:true,
    camera_controls_and_selection_preserve_physical_bounds:true,
    graphics_loss_preserves_scalar_and_retry_recovers:true,
    mobile_document_overflow:false,
  }, null, 2)+'\n');
});
