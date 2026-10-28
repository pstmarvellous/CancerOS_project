# CancerOS — Reference Implementation Integration Blueprint

**Document ID:** COS-REF-001  
**Version:** 1.0  
**Status:** Implementation directive  
**Project:** CancerOS — Breast Cancer Digital Twin  
**Reference date:** October 24, 2026  
**Audience:** Coding agents, engineering reviewers, AI researchers  
**Execution scope:** Research, verification, integration and extension of established open-source projects

---

# 1. Engineering Mission

You are the engineering agent responsible for implementing CancerOS, a breast cancer digital twin research prototype.

The project's twelve engineering specifications define the desired product behavior.

This blueprint defines how you must use established open-source medical imaging and research implementations to accomplish that behavior.

Your responsibility is not merely to reproduce another project's functionality.

You must:

1. Identify proven implementations relevant to CancerOS.
2. Examine their actual source code and documentation.
3. Verify their dependencies, licenses and model assets.
4. Reproduce relevant functionality using authorized test data.
5. Determine which components can be adopted directly.
6. Adapt compatible implementations where appropriate.
7. Implement missing CancerOS-specific capabilities.
8. Integrate all components into one functioning architecture.
9. Verify every integration through executable tests.
10. Preserve scientific validity, provenance and application maintainability.

**Do not treat an upstream project as an upper limit on CancerOS functionality.**

Its role is to provide tested engineering foundations that CancerOS can extend.

---

# 2. Governing Engineering Principles

## REF-RULE-001 — Specifications remain authoritative

Use the twelve CancerOS engineering specifications as the source of product requirements.

Use reference repositories as possible implementations of those requirements.

If a reference implementation has additional features, do not automatically add them to CancerOS.

If a reference project lacks a CancerOS requirement, implement the missing capability independently.

## REF-RULE-002 — Inspect before implementing

Before building any complex imaging or AI capability, determine whether one of the approved reference projects already implements it.

Search the repository's:

- README and documentation.
- Source directories.
- Examples and tutorials.
- Tests.
- Model-loading code.
- Configuration files.
- Dependency manifests.
- Relevant release information.
- Known issues.

Do not claim a feature exists solely because a repository's description mentions it.

## REF-RULE-003 — Reproduce before adopting

Before integrating substantial upstream functionality:

1. Identify the supported release or commit.
2. Establish a reproducible environment.
3. Run the smallest relevant documented example.
4. Record actual inputs and outputs.
5. Verify compatibility with CancerOS test fixtures.
6. Document failures and limitations.

A repository that cannot be reproduced must not silently become a mandatory dependency.

## REF-RULE-004 — Licensing is a release gate

Verify licenses separately for:

- Source code.
- Model checkpoints.
- Medical imaging datasets.
- Annotations.
- Downloaded assets.
- Required third-party dependencies.

Check modification, redistribution, attribution, patent and commercial-use conditions where applicable.

Do not assume that a repository's code license automatically applies to its datasets or pretrained weights.

Do not copy code with an unknown or incompatible license.

## REF-RULE-005 — Preserve stable interfaces

Each adopted upstream component shall be accessed through a CancerOS-owned interface.

Do not allow upstream-specific internal representations to spread throughout the entire application.

## REF-RULE-006 — Prefer maintained APIs

Prefer supported package imports, documented APIs and stable extension mechanisms.

Avoid copying internal implementation files unless there is a demonstrated reason.

## REF-RULE-007 — Separate source and custom code

Maintain a clear distinction between:

- External dependencies.
- Vendored or adapted upstream code.
- CancerOS-specific application code.
- Research examples.
- Test fixtures.

Record the upstream repository and commit for every adapted implementation.

## REF-RULE-008 — Medical geometry must remain physically accurate

Never interpret voxel indices as physical coordinates without applying the correct image geometry.

Maintain spatial orientation, origin, spacing and transformation metadata.

## REF-RULE-009 — Clinical provenance is mandatory

A verified observation, synthetic state, interpolation and model prediction must remain distinguishable.

No upstream imaging library may override this requirement.

## REF-RULE-010 — Benchmark claims require local verification

Published Dice scores, throughput measurements or model claims are background evidence only.

Report CancerOS performance using results actually reproduced on our approved test cases.

## REF-RULE-011 — Maintain fallback implementations

If a pretrained segmentation model is unavailable or unsuitable, validated imported masks must remain usable.

If an external AI API fails, the digital twin and deterministic measurements must remain operational.

## REF-RULE-012 — Avoid unnecessary platform dependencies

Do not deploy a complete enterprise imaging ecosystem merely to reuse one algorithm.

Choose the smallest viable integration that meets the acceptance criteria.

---

# 3. Mandatory Reference Repository Investigation Procedure

For every designated repository, complete the following workflow.

## Stage A — Repository identification

Record:

- Repository URL.
- Maintainer and organization.
- Intended research or production use.
- Most recent relevant release.
- Selected commit SHA.
- License.
- Language and framework.
- Runtime requirements.
- Model or dataset requirements.
- Relevant supported features.

## Stage B — Source architecture inspection

Inspect:

- Main package structure.
- Entry points.
- Model-loading functions.
- Processing pipelines.
- Data models.
- Public APIs.
- Configuration management.
- Output serialization.
- Test structure.
- Error handling.

Identify the exact implementation that satisfies a CancerOS requirement.

## Stage C — Compatibility investigation

Determine:

- Required input types.
- Required image channels.
- Expected coordinate convention.
- Expected voxel spacing.
- Model/checkpoint compatibility.
- Memory and GPU requirements.
- Output formats.
- Deployment assumptions.
- License compatibility.

## Stage D — Reproduction

Execute a minimal documented test.

Capture:

- Commands executed.
- Dependencies installed.
- Input artifact identifiers.
- Output artifact identifiers.
- Runtime logs.
- Measured results.
- Errors encountered.

## Stage E — Integration decision

Classify the project or component as:

- `ADOPT_AS_DEPENDENCY`
- `ADAPT_WITH_ATTRIBUTION`
- `STUDY_AND_REIMPLEMENT`
- `REFERENCE_ONLY`
- `DEFER`
- `REJECT`

Provide a short evidence-based explanation.

## Stage F — CancerOS integration

Implement the selected functionality behind a defined CancerOS interface.

Add typed input/output contracts, provenance and error handling.

## Stage G — Regression verification

Run all relevant tests.

Record pass/fail outcomes.

Do not mark integration complete while critical correctness tests fail.

---

# 4. Repository REF-01 — MAMA-MIA

**Repository:** https://github.com/LidiaGarrucho/MAMA-MIA

**Primary purpose:** Breast DCE-MRI segmentation research and benchmark implementation.

**Priority:** P0.

## 4.1 Investigate

Inspect:

- Root README and project documentation.
- The repository's `nnUNet/` implementation.
- Dataset acquisition instructions.
- Expert segmentation descriptions.
- Pretrained checkpoint references.
- Inference commands.
- Image preprocessing instructions.
- Model evaluation procedures.
- Treatment-response challenge material.

Inspect the current tree to locate the actual inference and data-preparation scripts. Do not assume example filenames or historical paths still exist.

## 4.2 Specific implementation facts to verify

The documented workflow includes:

- Pretrained nnU-Net segmentation.
- Dataset ID 101 in the described inference configuration.
- 3D full-resolution inference.
- NIfTI-format model inputs.
- DCE-specific normalization.
- Resampling to a documented spacing.
- Checkpoints hosted through an external research distribution service.

Verify whether the checkpoints remain accessible.

Verify whether their license permits the intended use.

Verify the exact number and ordering of MRI channels.

Verify whether the preprocessing workflow matches the selected CancerOS dataset.

## 4.3 Adopt

Adopt where compatible:

- The supported pretrained segmentation inference workflow.
- Applicable model preprocessing requirements.
- Model output format and configuration.
- Relevant evaluation metrics.

Prefer calling a maintained package or command-line interface rather than embedding copied implementation internals.

## 4.4 Adapt

Adapt as needed:

- Patient-to-image manifest mapping.
- Source image preparation.
- Prediction output registration.
- Segmentation quality reporting.
- Conversion into CancerOS mask artifacts.

Every adaptation must preserve source geometry and provenance.

## 4.5 Copy restrictions

Do not copy entire research datasets into the application repository.

Do not redistribute model weights without verifying the checkpoint license.

Do not import the entire upstream nnU-Net fork merely because a smaller inference adapter can achieve the same outcome.

Any copied source implementation requires recorded licensing approval and attribution.

## 4.6 Required experiments

**EXP-MAMA-01**

Run documented model inference on one approved compatible image.

**EXP-MAMA-02**

Compare the resulting mask with an available reference segmentation.

**EXP-MAMA-03**

Compute tumor volume using the source physical geometry.

**EXP-MAMA-04**

Convert the segmentation into CancerOS's standard mask artifact.

**EXP-MAMA-05**

Generate a browser-compatible tumor mesh.

**EXP-MAMA-06**

Measure inference runtime and resource requirements.

## 4.7 Required output

Create a `BreastTumorSegmentationAdapter` implementation that:

- Accepts a validated imaging study reference.
- Prepares the compatible model input.
- Executes supported inference.
- Validates the returned mask.
- Preserves physical-space geometry.
- Produces a standard CancerOS segmentation artifact.
- Records model version and provenance.

## 4.8 Acceptance

This integration is successful when a valid breast MRI can produce a usable tumor segmentation that is correctly associated with the source patient and can be converted into a measurable 3D representation.

If the pretrained model cannot be executed, use approved reference masks for the initial prototype and document the blocker.

---

# 5. Repository REF-02 — nnU-Net v2

**Repository:** https://github.com/MIC-DKFZ/nnUNet

**Primary purpose:** Medical image segmentation framework.

**Priority:** P0.

## 5.1 Investigate

Study:

- Installation and environment requirements.
- Dataset preparation.
- Input filename and channel conventions.
- `dataset.json` format.
- Preprocessing and experiment planning.
- Model results directory.
- Inference execution.
- Output segmentation format.
- GPU and memory requirements.
- Fold selection and postprocessing.

Study the documented `nnUNetv2_predict` inference workflow.

## 5.2 Adopt

Adopt the official nnU-Net v2 package and supported inference mechanisms where compatible.

Do not implement a custom U-Net framework merely to reproduce the segmentation infrastructure.

## 5.3 Adapt

Build CancerOS-specific:

- Dataset-to-nnU-Net input adapter.
- Channel configuration validator.
- Inference job configuration.
- Output mask importer.
- Model registry entry.
- Quality-control reporting.

## 5.4 Do not copy

Do not copy nnU-Net's internal training engine into CancerOS.

Do not rewrite its preprocessing and model-planning algorithms without a documented compatibility reason.

Do not mix checkpoints trained with incompatible upstream versions.

## 5.5 Required tests

- Valid image input.
- Incorrect channel count.
- Missing checkpoint.
- Invalid model configuration.
- Prediction success.
- Output mask alignment.
- GPU resource exhaustion.
- CPU fallback feasibility where applicable.

## 5.6 Acceptance

CancerOS can execute or consume nnU-Net-compatible segmentation outputs behind its own model-service interface.

The main frontend and database must not depend on nnU-Net-specific file structures.

---

# 6. Repository REF-03 — 3D Slicer

**Repository:** https://github.com/Slicer/Slicer

**Primary purpose:** Medical imaging geometry, segmentation and visualization reference.

**Priority:** P0.

## 6.1 Investigate

Study the current source implementation and documentation for:

- Scalar volume representation.
- Segmentation data representation.
- Segment Editor architecture.
- Surface representations.
- Model nodes.
- Transform nodes.
- Volume measurements.
- Coordinate-space handling.
- Segmentation export.
- Python scripting interfaces.

Relevant architectural areas to locate in the current source tree include:

- `Libs/MRML/`
- `Modules/Loadable/Segmentations/`
- `Modules/Loadable/SegmentEditor/`
- Volume-related modules.
- Transform-related modules.
- Segment statistics implementation or extension.

Check the current repository tree before relying on these paths.

## 6.2 Adopt

Use stable libraries already employed by the medical-imaging ecosystem where feasible:

- VTK.
- SimpleITK.
- Supported mesh and volume formats.

3D Slicer itself may be used as a reference application for independent validation.

## 6.3 Study and reimplement

CancerOS should learn how Slicer represents:

- Image volumes.
- Segmentation masks.
- Surface meshes.
- Physical transformations.
- Lesion measurements.

Implement the necessary CancerOS service contracts without requiring the 3D Slicer desktop application on the production server.

## 6.4 Do not copy

Do not copy the full Slicer desktop UI.

Do not bring its entire scene-management infrastructure into the Next.js application.

Do not add unnecessary desktop runtime dependencies to the backend.

## 6.5 Required experiments

**EXP-SLICER-01**

Open one authentic MRI and segmentation in 3D Slicer.

**EXP-SLICER-02**

Generate a lesion surface model.

**EXP-SLICER-03**

Calculate lesion volume and dimensions.

**EXP-SLICER-04**

Export the mesh.

**EXP-SLICER-05**

Render the same mesh in the CancerOS browser.

**EXP-SLICER-06**

Compare physical dimensions, orientation and measurements between both applications.

## 6.6 Acceptance

The browser-rendered lesion must maintain correct physical geometry relative to the source image.

The reference application and CancerOS measurement pipeline must agree within documented numerical tolerances for equivalent masks and methods.

---

# 7. Repository REF-04 — OHIF Viewer

**Repository:** https://github.com/OHIF/Viewers

**Primary purpose:** Web medical imaging and longitudinal measurement tracking.

**Priority:** P0.

## 7.1 Inspect these architectural areas

Start with:

- `extensions/cornerstone/`
- `extensions/cornerstone-dicom-seg/`
- `extensions/measurement-tracking/`
- `modes/longitudinal/`
- `modes/basic-dev-mode/`
- `platform/core/`
- `platform/ui/`
- `platform/viewer/`

Verify current source paths and public APIs against the selected release.

## 7.2 Specific capabilities to investigate

- DICOMweb data loading.
- Display set management.
- Viewport control.
- Segmentation overlays.
- Measurement tracking.
- Image orientation.
- Cross-study navigation.
- Hanging protocols.
- Measurement service.
- Segmentation service.
- Extension registration.
- Event and state synchronization.

## 7.3 Important architectural pattern

OHIF uses an extension/mode architecture, with shared platform functionality and dedicated measurement-tracking capabilities.

CancerOS should preserve a similarly clean separation between medical imaging workspaces and patient-level clinical workflows.

## 7.4 Compare two implementation approaches

### Option A — Embed OHIF as a dedicated research imaging workspace

Benefits:

- Reuses mature medical image navigation.
- Supports established DICOMweb workflows.
- Reduces the need to recreate imaging controls.

Costs:

- More complex integration.
- Potentially heavier frontend deployment.
- Custom synchronization with CancerOS patient state.

### Option B — Use Cornerstone3D inside a custom CancerOS interface

Benefits:

- Greater control over product UI.
- Easier integration with the clinical timeline.
- Potentially smaller application surface.

Costs:

- More imaging-viewer engineering.
- More responsibility for annotation and measurement integrations.

Implement a proof of concept for both options if resources permit.

Select based on actual functionality, bundle size, ease of integration, performance and maintenance risk.

## 7.5 Adopt

Prefer documented OHIF extension mechanisms or public Cornerstone3D APIs.

## 7.6 Adapt

Implement CancerOS-specific:

- Patient-to-study mapping.
- Clinical timeline synchronization.
- Synthetic/observed state switching.
- External tumor mesh viewing.
- Provenance display.
- Branch selection.

## 7.7 Do not copy

Do not copy the entire OHIF frontend source into the CancerOS application simply to acquire a viewer.

Do not duplicate its viewer services if they can be consumed through supported extension interfaces.

Do not assume OHIF's longitudinal lesion-tracking semantics automatically support synthetic patient branching.

## 7.8 Required experiments

**EXP-OHIF-01**

Load one approved MRI study in a browser.

**EXP-OHIF-02**

Overlay a compatible segmentation.

**EXP-OHIF-03**

Change between two authentic imaging studies.

**EXP-OHIF-04**

Inspect measurement tracking across those studies.

**EXP-OHIF-05**

Synchronize CancerOS's selected patient/state with the viewer.

**EXP-OHIF-06**

Test missing studies and invalid segmentation artifacts.

## 7.9 Acceptance

The selected viewer approach must support reliable navigation of source imaging and lesion overlays without confusing authentic and synthetic states.

---

# 8. Repository REF-05 — NCI Imaging Data Commons Index

**Repository:** https://github.com/ImagingDataCommons/idc-index

**Primary purpose:** Reproducible imaging dataset discovery and acquisition.

**Priority:** P0.

## 8.1 Investigate

Study:

- `IDCClient`.
- Collection listing.
- Patient lookup.
- Study lookup.
- Series lookup.
- SQL metadata queries.
- Selected series downloading.
- Manifest generation.
- Viewer URL generation.

## 8.2 Adopt

Use the maintained `idc-index` package as a dependency for supported public imaging collection access.

## 8.3 Adapt

Create a CancerOS dataset acquisition service that:

- Accepts a dataset collection identifier.
- Identifies approved studies and series.
- Selects a bounded download subset.
- Records source identities.
- Generates reproducible manifests.
- Downloads authorized data.
- Calculates checksums.
- Updates the source registry.

## 8.4 Do not copy

Do not reproduce the IDC project's metadata catalog internally.

Do not download whole collections when a small selected subset is sufficient.

Do not assume all selected CancerOS datasets are present in IDC.

If a collection is unavailable, use that dataset's approved original distribution method.

## 8.5 Required experiments

- Discover available breast MRI collections.
- Query patient/study/series relationships.
- Download one selected small study.
- Verify DICOM metadata.
- Generate a reproducible manifest.
- Repeat the download from the manifest.

## 8.6 Acceptance

CancerOS can obtain a small approved imaging subset reproducibly, record where it came from, and link the files to the correct source patient identity.

---

# 9. Repository REF-06 — MONAI and MONAI Label

**Repositories:**

- https://github.com/Project-MONAI/MONAI
- https://github.com/Project-MONAI/MONAILabel

**Primary purpose:** Medical AI preprocessing, inference and assisted annotation.

**Priority:** P0 for MONAI transforms; P1 for MONAI Label server.

## 9.1 Investigate

Study:

- MONAI imaging transforms.
- Medical image metadata handling.
- Dataset loading.
- Model inference utilities.
- Postprocessing transforms.
- Evaluation metrics.
- MONAI Label radiology application.
- MONAI Label inference task interfaces.
- 3D Slicer integration.
- OHIF integration.

Specific paths to inspect:

- `sample-apps/radiology/`
- `sample-apps/monaibundle/`
- `plugins/`

Verify the current locations of relevant implementation files.

## 9.2 Adopt

Use maintained MONAI APIs where suitable for:

- Loading image data.
- Spatial preprocessing.
- Data transformations.
- Inference utilities.
- Segmentation evaluation.

## 9.3 Adapt

Study MONAI Label's model task architecture and adapt the pattern for a CancerOS imaging worker.

If annotation-assisted segmentation is needed, evaluate whether MONAI Label's service can be integrated directly.

## 9.4 Do not copy

Do not treat pretrained spleen, liver or abdominal-organ segmentation models as breast tumor models.

Do not train models unnecessarily when verified reference masks already satisfy the hackathon's core visualization requirement.

Do not deploy a full annotation platform merely to support one inference endpoint.

## 9.5 Required experiments

- Load and preprocess one MRI.
- Apply a documented spatial transform.
- Apply the same transformation to a segmentation mask.
- Verify image-mask alignment.
- Execute a small segmentation inference example.
- Compare processed image coordinates with original coordinates.
- Verify that annotation results can be exported into the CancerOS data contract.

## 9.6 Acceptance

CancerOS can reuse MONAI processing components while retaining its own patient, model, provenance and artifact interfaces.

---

# 10. Repository REF-07 — dcmqi

**Repository:** https://github.com/QIICR/dcmqi

**Primary purpose:** Standardized quantitative imaging interoperability.

**Priority:** P1.

## 10.1 Investigate

Study:

- DICOM SEG conversion.
- NIfTI segmentation conversion.
- Segmentation metadata schemas.
- DICOM structured reports.
- Measurement representation.
- Source-image references.
- Available command-line tools.

Inspect the documented tools:

- `itkimage2segimage`
- `segimage2itkimage`
- `tid1500writer`

Check available commands and version-specific options.

## 10.2 Adopt

Use the maintained conversion tools when standard DICOM output is required.

## 10.3 Adapt

Create a CancerOS interoperability adapter for:

- Image-linked segmentation exchange.
- Provenance mapping.
- Quantitative measurement export.
- Round-trip validation.

## 10.4 Do not copy

Do not build a custom DICOM SEG encoder from scratch when compatible tools already exist.

Do not include the entire dcmqi development environment in the routine web service unless necessary.

## 10.5 Required experiments

- Convert one supported segmentation to DICOM SEG.
- Validate its source-image references.
- Load the result in a compatible viewer.
- Perform a supported round-trip conversion.
- Confirm label and geometry preservation.

## 10.6 Acceptance

CancerOS can import or export standard segmentation objects without losing essential geometry or source linkage.

---

# 11. Repository REF-08 — BreastMRISegmentator

**Repository:** https://github.com/grenda623/BreastMRISegmentator

**Primary purpose:** Breast, fibroglandular tissue and tumor segmentation.

**Priority:** Investigate; optional integration.

## 11.1 Investigate

Study:

- README and current release status.
- `pyproject.toml`.
- `docs/usage.md`.
- `docs/training.md`.
- `docs/results.md`.
- Model weight distribution instructions.
- Example notebooks.
- Input channel conventions.
- Output label definitions.
- License.

Verify these paths in the selected commit.

## 11.2 Important limitation

The repository currently describes itself as a pre-release scaffold.

Published model-weight availability must be independently verified.

Do not assume its inference workflow is runnable because the README describes a future checkpoint distribution.

## 11.3 Potential advantage

Its described multi-structure segmentation may support:

- Breast tissue representation.
- Fibroglandular tissue representation.
- Tumor segmentation.

This could improve the anatomical context of the digital twin.

## 11.4 Adopt only if

- Working checkpoint files exist.
- License conditions are verified.
- Input requirements match available CancerOS MRI data.
- Inference can be reproduced.
- Output masks pass geometry and quality checks.
- Resource requirements are acceptable.

## 11.5 Fallback

Continue with MAMA-MIA or validated source tumor masks.

An illustrative breast shell may be used when labeled appropriately.

## 11.6 Acceptance

This repository is optional and must not become a blocker for the core digital twin.

---

# 12. Repository REF-09 — MONAI Deploy App SDK

**Repository:** https://github.com/Project-MONAI/monai-deploy-app-sdk

**Primary purpose:** Medical AI workflow orchestration.

**Priority:** P1.

## 12.1 Investigate

Study:

- Application operators.
- Input/output contracts.
- DICOM series loading.
- Inference operators.
- Segmentation output operators.
- Container packaging.
- Error handling.
- Workflow execution.

Relevant examples to inspect:

- `examples/apps/simple_imaging_app/`
- `examples/apps/dicom_series_to_image_app/`
- `examples/apps/ai_livertumor_seg_app/`
- `examples/apps/ai_spleen_seg_app/`

Verify exact paths in the current repository tree.

## 12.2 Adopt or adapt

Study its processing architecture:

Ingestion → preprocessing → inference → postprocessing → export.

Use this as the reference pattern for CancerOS imaging jobs.

Adopt the full SDK only if its runtime requirements are justified.

## 12.3 Do not copy

Do not install a heavyweight medical AI deployment framework solely for dependency injection or basic job scheduling.

Do not allow the entire CancerOS backend to depend on a GPU deployment runtime.

## 12.4 Acceptance

The CancerOS imaging pipeline remains modular, reproducible and independently executable.

---

# 13. Repository REF-10 — SlicerRadiomics

**Repository:** https://github.com/AIM-Harvard/SlicerRadiomics

**Primary purpose:** Quantitative image feature extraction.

**Priority:** Optional.

## 13.1 Investigate

Study:

- PyRadiomics integration.
- Feature extraction configuration.
- Mask/image alignment.
- Spacing and resampling requirements.
- Feature provenance.
- Validation examples.

## 13.2 Adopt

Where needed, use maintained PyRadiomics APIs rather than copying feature formulas.

## 13.3 Adapt

Create an optional CancerOS radiomics adapter.

## 13.4 Restrictions

Do not add numerous radiomic variables simply to increase the apparent sophistication of the prototype.

Do not claim biological interpretations that are not independently validated.

## 13.5 Acceptance

Any enabled radiomic feature must have a documented extraction method, compatible source imaging, and reproducible output.

---

# 14. CancerOS-Specific Components to Implement Independently

The reference repositories provide important foundations but do not replace the following core CancerOS subsystems.

## 14.1 Synthetic Longitudinal Research Engine

Implement:

- Five scenario families.
- Treatment-eligibility constraints.
- Dated treatment events.
- Tumor evolution functions.
- Laboratory and vital-sign simulation.
- Symptoms and toxicity.
- Seeded stochastic variability.
- Explicit missingness.
- Branch reproducibility.
- Simulation quality validation.

Use COS-SPEC-004 as the authoritative specification.

Do not treat any segmentation repository as a substitute for this engine.

## 14.2 Digital Twin State and Branching Engine

Implement:

- Real patient baseline.
- Actual observation states.
- Hypothetical scenario branches.
- Time-indexed lesion geometry.
- Clinical event synchronization.
- Observed/synthetic/predicted provenance.
- Immutable historical states.
- Branch comparison.
- Patient and branch isolation.

The engine shall not depend on the web viewer for authoritative state management.

## 14.3 Multimodal Patient-State Fusion

Implement:

- Imaging measurements.
- Clinical observations.
- Blood tests.
- Vital signs.
- Symptoms.
- Treatment timeline.
- Source-quality information.
- Missing-data flags.
- Conflict handling.
- Time-aligned state representation.

Use COS-SPEC-006.

## 14.4 Temporal Intelligence

Implement:

- Deterministic trend calculation.
- Change detection.
- Time-aware comparison.
- Basic forecasting baselines.
- Uncertainty representation.
- Model abstention.
- Held-out longitudinal evaluation.

Do not claim predictive accuracy using only simulator-generated outcomes.

## 14.5 Clinical Evidence and Interpretation

Implement:

- Authorized source retrieval.
- Structured note extraction.
- Verified clinical evidence retrieval.
- Numeric claim grounding.
- Source-citation validation.
- Synthetic data awareness.
- LLM explanation.
- Scientific safety constraints.

Do not delegate deterministic patient measurements to the language model.

---

# 15. CancerOS Canonical Integration Contracts

Every upstream component shall produce or consume CancerOS-owned structured contracts.

These contracts shall be finalized under COS-SPEC-008.

## 15.1 ImagingVolumeArtifact

Required:

- Artifact ID.
- Patient ID.
- Study ID.
- Series ID.
- Storage location.
- Format.
- Dimensions.
- Spacing.
- Orientation.
- Physical transformation.
- Source checksum.
- Provenance.

## 15.2 SegmentationArtifact

Required:

- Segmentation ID.
- Source image artifact ID.
- Lesion ID.
- Mask location.
- Label definitions.
- Segmentation method.
- Model or annotation reference.
- Physical coordinate metadata.
- Quality-control status.
- Provenance.

## 15.3 TumorGeometryArtifact

Required:

- Geometry ID.
- Segmentation ID.
- Lesion ID.
- Mesh location.
- Coordinate system.
- Physical measurements.
- Mesh generation version.
- Source state.
- Provenance.

## 15.4 TwinState

Required:

- State ID.
- Patient ID.
- Observation date or relative time.
- Real/synthetic branch ID.
- Geometry reference.
- Tumor measurements.
- Clinical observation references.
- Treatment-event references.
- State quality.
- Provenance.

## 15.5 ModelInferenceResult

Required:

- Inference ID.
- Model identifier.
- Model version.
- Input artifact references.
- Output artifact references.
- Processing parameters.
- Validation result.
- Execution metadata.
- Provenance.

## 15.6 ClinicalInterpretation

Required:

- Interpretation ID.
- Patient/state reference.
- Findings.
- Supporting observation IDs.
- Evidence references.
- Uncertainty.
- Limitations.
- Model version.
- Output validation status.

Upstream-specific data structures must be converted at the appropriate adapter boundary.

---

# 16. Reference Integration Architecture

Recommended implementation structure:

```text
canceros/
├── apps/
│   └── research-web/
│       ├── case-browser/
│       ├── patient-workspace/
│       ├── imaging-workspace/
│       ├── twin-viewer/
│       ├── scenario-explorer/
│       └── evidence-panel/
│
├── backend/
│   ├── api/
│   ├── clinical/
│   ├── imaging/
│   │   ├── ingestion/
│   │   ├── preprocessing/
│   │   ├── segmentation/
│   │   ├── measurement/
│   │   ├── registration/
│   │   └── geometry/
│   ├── simulation/
│   ├── temporal/
│   ├── knowledge/
│   ├── interpretation/
│   └── provenance/
│
├── integrations/
│   ├── mama_mia/
│   ├── nnunet/
│   ├── monai/
│   ├── idc/
│   ├── dicom/
│   └── model_api/
│
├── packages/
│   ├── schemas/
│   ├── imaging-contracts/
│   ├── clinical-contracts/
│   └── common-types/
│
├── research/
│   ├── reference-audits/
│   ├── compatibility-tests/
│   ├── dataset-manifests/
│   └── benchmarks/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── imaging/
│   ├── simulation/
│   ├── ai/
│   └── e2e/
│
├── docs/
├── deployment/
└── AGENTS.md
```

Each `integrations/` package shall implement a narrow external-provider adapter.

Do not create independent deployment services merely because separate directories exist.

Prefer a modular application backend with an optional isolated imaging worker for the hackathon.

---

# 17. Master Compatibility Matrix

Create `reference-compatibility-matrix.md`.

For every reference repository, record:

| Field                  | Required assessment                      |
| ---------------------- | ---------------------------------------- |
| Repository             | Exact URL                                |
| Commit                 | Pinned SHA                               |
| License                | Verified                                 |
| Model license          | Verified independently                   |
| Dataset license        | Verified independently                   |
| Intended use           | Documented                               |
| Input format           | Tested                                   |
| Output format          | Tested                                   |
| MRI compatibility      | Verified                                 |
| Geometry compatibility | Verified                                 |
| Memory requirements    | Measured                                 |
| GPU requirements       | Measured                                 |
| Installation           | Reproduced                               |
| Relevant tests         | Executed                                 |
| CancerOS adapter       | Identified                               |
| Decision               | Adopt, adapt, reference, defer or reject |
| Blocking issues        | Documented                               |
| Fallback               | Identified                               |

Do not mark fields verified unless corresponding evidence is available.

---

# 18. Required Repository Review Deliverables

For each reference repository, create:

`research/reference-audits/{repository-name}.md`

Each report shall contain:

1. Repository overview.
2. Maintainer and license assessment.
3. Selected commit and version.
4. Relevant implementation files.
5. Public APIs and execution entry points.
6. Input/output contracts.
7. Dependency requirements.
8. Reproduction procedure.
9. Actual experimental results.
10. Compatibility limitations.
11. Integration recommendation.
12. Proposed CancerOS adapter.
13. Required tests.
14. Final decision.

Also maintain:

- `reference-compatibility-matrix.md`
- `reference-license-register.md`
- `reference-model-register.md`
- `reference-reproduction-ledger.md`
- `reference-integration-backlog.md`

---

# 19. Mandatory Cross-Repository Integration Test

Before developing all five synthetic scenarios, execute one complete vertical-slice experiment.

## Test VERTICAL-REF-001

### Step 1

Acquire one authorized genuine breast MRI case.

### Step 2

Validate image geometry and associated source records.

### Step 3

Load or produce a suitable tumor segmentation.

### Step 4

Calculate the lesion's physical dimensions and volume.

### Step 5

Generate a 3D tumor mesh.

### Step 6

Render the lesion in the browser alongside appropriate imaging context.

### Step 7

Generate one explicitly synthetic follow-up lesion state.

### Step 8

Attach corresponding synthetic laboratory and treatment-event records.

### Step 9

Load both states in the digital twin timeline.

### Step 10

Generate a provenance-aware, evidence-linked research interpretation.

### Required results

- Correct patient identity.
- Valid image/mask alignment.
- Correct physical geometry.
- Functional web visualization.
- Distinct baseline and synthetic state identifiers.
- Accurate derived measurement changes.
- Synchronized clinical records.
- Proper data provenance labels.
- No unsupported AI claims.
- Repeatable execution.

If this test fails, prioritize correcting the integration before expanding features.

---

# 20. Execution Order

## Phase A — Upstream verification

1. Audit MAMA-MIA.
2. Audit nnU-Net v2.
3. Audit 3D Slicer geometry workflows.
4. Audit OHIF/Cornerstone3D.
5. Audit IDC Index.
6. Audit relevant MONAI modules.

The remaining references may be investigated concurrently or subsequently according to need.

## Phase B — First imaging vertical slice

1. Obtain approved imaging.
2. Import the source study.
3. Obtain or import a suitable mask.
4. Measure lesion geometry.
5. Reconstruct the tumor.
6. Render it in the browser.
7. Validate against an independent reference.

## Phase C — CancerOS evolution integration

1. Implement the immutable patient baseline.
2. Implement simulation branch storage.
3. Create one synthetic follow-up state.
4. Synchronize geometry and clinical observations.
5. Validate provenance.

## Phase D — Expand to complete scenarios

1. Implement all five scenario families.
2. Add treatment-exposure events.
3. Add laboratory, vital-sign and symptom generation.
4. Add validation and reproducibility tests.
5. Implement scenario exploration.

## Phase E — AI intelligence

1. Integrate structured clinical facts.
2. Calculate deterministic trends.
3. Retrieve supporting evidence.
4. Generate AI interpretations.
5. Validate outputs.
6. Evaluate limitations and abstention.

## Phase F — Product verification

1. Test all user journeys.
2. Execute imaging benchmarks.
3. Execute synthetic simulation checks.
4. Run security and scientific integrity tests.
5. Review deployment performance.
6. Prepare the final demonstration.

---

# 21. Requirements for Every Agent Implementation Task

Every implementation task derived from this blueprint shall identify:

- CancerOS requirement IDs.
- Reference repositories involved.
- Upstream version or commit.
- Selected integration method.
- Files or modules to inspect.
- Functionality to reuse.
- Functionality to extend.
- Functionality prohibited from copying.
- Input/output contracts.
- Expected tests.
- Scientific limitations.
- Definition of Done.

When relevant, link the task to the corresponding reference audit.

---

# 22. Final Rules for the Coding Agent

**Rule A:** Reuse proven engineering implementations wherever suitable.

**Rule B:** Do not trust repository descriptions without inspecting actual code.

**Rule C:** Do not confuse a research benchmark with an integrated production application.

**Rule D:** Do not assume pretrained weights are available.

**Rule E:** Do not copy software without verifying license compatibility.

**Rule F:** Do not lose medical imaging geometry during conversion.

**Rule G:** Do not use anatomical masks as though they represent unmeasured biological features.

**Rule H:** Do not present simulated patient states as real observations.

**Rule I:** Do not train new models unnecessarily when validated existing tools can satisfy the requirement.

**Rule J:** Do not allow an external AI model to invent clinical measurements.

**Rule K:** Do not turn every upstream repository into a separate microservice.

**Rule L:** Do not allow reference implementation limitations to define CancerOS's product scope.

**Rule M:** Every integration must have an executable test and reproducible evidence.

**Rule N:** Keep the central digital twin functional even when optional segmentation inference or external LLM services are unavailable.

**Rule O:** Report failures and unverified claims explicitly rather than fabricating successful outcomes.

---

# 23. Definition of Completion

This reference integration blueprint is fulfilled when:

1. All P0 repositories have been inspected.
2. Upstream licenses have been assessed.
3. Relevant versions or commits are pinned.
4. Selected examples have been reproduced.
5. CancerOS integration decisions are documented.
6. Core imaging components have standard interfaces.
7. One authentic MRI is correctly processed.
8. One verified lesion can be rendered and measured.
9. One synthetic follow-up geometry can be generated.
10. The clinical timeline can represent the two states.
11. The AI interpretation can reference the correct evidence.
12. Reproducible tests demonstrate the complete vertical slice.
13. All adopted or adapted upstream components have attribution and dependency records.
14. Unimplemented or unsuccessful reference integrations have explicit fallback plans.

**The final objective is to build CancerOS on verified engineering foundations while retaining full ownership of its distinctive longitudinal digital twin, synthetic clinical evolution, and multimodal intelligence architecture.**

---

**End of Document — COS-REF-001, Version 1.0**
