# COS-REC-03 — Immersive 3D Viewer and Visual Interaction

**Role:** Senior Medical Visualization Engineer, Three.js Engineer and Interaction Designer

**Mission:** Transform the existing 3D viewer into a visually prominent, intuitive demonstration of CancerOS's technical capabilities.

Reuse the established renderer, mesh contracts and measurements.

Do not rewrite the scientific geometry engine.

## Tasks

1. Make the default desktop viewer substantially larger.
2. Use collapsible side panels so measurements do not unnecessarily constrain the canvas.
3. Preserve the working maximize and fullscreen behavior.
4. Consolidate camera actions into a compact, understandable toolbar.
5. Improve model lighting, surface shading, background contrast and framing.
6. Maintain correct physical scaling across selected states.
7. Make the selected state and volume immediately visible.
8. Keep the timeline attached to the viewer.
9. Provide clear loading, missing-mesh and WebGL recovery states.
10. Maintain keyboard accessibility and usable controls on narrow screens.

## Expected layout

Desktop:

- Left: compact/collapsible case or demo navigation.
- Center: dominant 3D viewer.
- Right: small collapsible measurement panel.
- Bottom: visible timeline and comparison controls.

The model should be easy to inspect without repeatedly scrolling.

Camera toolbar example:

**Orbit | Pan | Zoom | Fit | Reset | Fullscreen**

Use appropriate icons and accessible labels.

Avoid a large collection of visually identical primary buttons.

## Example interaction

The user starts at the synthetic baseline.

The interface shows:

**Baseline — 216 mm³**

The user selects Day 37.

The model changes to the correct stored geometry, and the measurement changes to:

**Day 37 — 64 mm³**

The corresponding chart point becomes selected.

Both outputs must originate from the same selected state and existing authoritative calculations.

Do not derive volume from the displayed surface.

## Scientific restriction

The current cube is an artificial geometry test fixture. Retain that label.

Do not disguise it as a genuine breast tumor or patient scan.

Improve visualization quality without misrepresenting the data.

## Acceptance gate

Use a real browser to verify:

- Orbit, pan, zoom and fit.
- Maximize/fullscreen and return.
- Each available timeline state.
- Geometry/measurement correspondence.
- Browser refresh and navigation recovery.
- Desktop and narrow-screen behavior.
- WebGL failure recovery.

Capture actual screenshots showing the model, controls and selected follow-up.

A large black canvas or a decorative model disconnected from backend values does not pass.

Report changed files, reused components, tests and remaining limitations.
