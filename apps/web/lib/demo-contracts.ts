import type { components } from '../../../packages/contracts/generated/api';
import type { RenderableMesh } from '../components/mesh-renderer';
type S = components['schemas'];
export type DemoScenario = {
  id: string; label: string; description: string;
  timeline: S['TimelinePage']; trends: S['TrendReport'];
  meshes: Record<string, RenderableMesh['objects'][number]['surface']>;
  meshBindings: Record<string, {
    point_id: string; patient_id: string; branch_id: string; run_id: string;
    state_ids: string[]; geometry_result_id: string | null; surface_sha256: string;
  }>;
};
export type DemoBundle = {
  version: 'synthetic-demo/2'; syntheticOnly: true;
  sourceOrigin: 'synthetic_engineering_fixture'; caseLabel: string;
  preparedAt: string; expiresAt: string; scenarios: Record<string, DemoScenario>;
};
export type DemoCatalog = Pick<DemoBundle, 'caseLabel' | 'preparedAt' | 'expiresAt'> & {
  scenarios: Pick<DemoScenario, 'id' | 'label' | 'description'>[];
};
