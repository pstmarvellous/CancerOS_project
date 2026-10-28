import type { paths } from '@canceros/contracts';

export type MeshAsset = paths['/api/v1/projects/{project_id}/patients/{patient_id}/mesh-qc-reports/{report_id}/asset']['get']['responses'][200]['content']['application/json'];
export type MeshQCReport = paths['/api/v1/projects/{project_id}/patients/{patient_id}/mesh-qc-reports/{report_id}']['get']['responses'][200]['content']['application/json'];
export type MeasurementReport = paths['/api/v1/projects/{project_id}/patients/{patient_id}/physical-measurements/{report_id}']['get']['responses'][200]['content']['application/json'];
