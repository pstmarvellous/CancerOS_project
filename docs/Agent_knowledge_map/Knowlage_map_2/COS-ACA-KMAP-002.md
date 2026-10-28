# COS-ACA-KMAP-002 — Academic-first CancerOS knowledge navigation

**Purpose:** Every engineering behavior points to academic reading, upstream code and research evidence. This is a reference index, not a substitute for studying cited work.

Includes **40 target behaviors**, **18 academic sources**, **12 repositories**, **5 paper/dataset entries**, and **171 typed source links**.

## Academic reading catalog

### A01 — MIT HST.582J
- Reading location: Lecture 14 — Introduction to medical image segmentation
- Access: https://ocw.mit.edu/courses/hst-582j-biomedical-signal-and-image-processing-spring-2007/pages/lecture-notes/
- Verification: verified section

### A02 — MIT HST.582J
- Reading location: Lectures 15–16 — Image registration I and II
- Access: https://ocw.mit.edu/courses/hst-582j-biomedical-signal-and-image-processing-spring-2007/pages/lecture-notes/
- Verification: verified section

### A03 — MIT HST.582J
- Reading location: Lecture 17 — Medical image modalities; Lectures 9,12 image processing
- Access: https://ocw.mit.edu/courses/hst-582j-biomedical-signal-and-image-processing-spring-2007/pages/lecture-notes/
- Verification: verified section

### A04 — MIT HST.582J
- Reading location: Lab 3 — Post-processing brain MRI images; Lab 4 — Registration of medical images
- Access: https://ocw.mit.edu/courses/hst-582j-biomedical-signal-and-image-processing-spring-2007/pages/labs/
- Verification: verified lab

### A05 — ITK Software Guide
- Reading location: Volume 2 — Image reading/writing, filtering, registration, segmentation and analysis; find exact subchapter in chosen edition
- Access: https://itk.org/ITKSoftwareGuide/html/
- Verification: verified topical volume; exact chapter pending

### A06 — Guide to Medical Image Analysis — Klaus D. Toennies
- Reading location: Segmentation, registration, shape analysis, validation; inspect edition table of contents for exact chapter
- Access: https://link.springer.com/book/10.1007/978-1-4471-7320-5
- Verification: topic verified; precise chapter pending

### A07 — Insight into Images — Terry S. Yoo (ed.)
- Reading location: Isosurfaces, medical segmentation, deformable models, registration; inspect chapter headings in accessible edition
- Access: https://www.routledge.com/Insight-into-Images/Yooah2/p/book/9781568812175
- Verification: topic indicated; precise chapter pending

### A08 — IBSI Reference Manuals
- Reading location: IBSI 1 reference manual — image preprocessing and biomarker feature definitions; select benchmark in documentation
- Access: https://theibsi.github.io/documentation/
- Verification: reference manual verified

### A09 — Stan User’s Guide
- Reading location: Posterior and Prior Predictive Checks
- Access: https://mc-stan.org/docs/stan-users-guide/ppcs.html
- Verification: verified section

### A10 — Stan User’s Guide
- Reading location: Hierarchical models and mixed replication; navigate from current official guide
- Access: https://mc-stan.org/docs/stan-users-guide/
- Verification: topical location; subsection pending

### A11 — Longitudinal Data Analysis — Wiley
- Reading location: Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles
- Access: https://onlinelibrary.wiley.com/doi/book/10.1002/0470036486
- Verification: precise chapter pending

### A12 — NCI Breast Cancer Treatment PDQ
- Reading location: Stage-specific treatment, receptor status and neoadjuvant therapy sections
- Access: https://www.cancer.gov/types/breast/hp/breast-treatment-pdq
- Verification: verified document; topic-specific revision required

### A13 — NCI CTCAE version 6.0
- Reading location: Adverse-event definitions, laboratory abnormalities and grading criteria
- Access: https://dctd.cancer.gov/research/ctep-trials/for-sites/adverse-events/ctcae-v6.pdf
- Verification: verified edition

### A14 — TRIPOD-LLM
- Reading location: Model/data/evaluation reporting checklist; consult full checklist and elaboration
- Access: https://pmc.ncbi.nlm.nih.gov/articles/PMC12104976/
- Verification: verified publication

### A15 — FDA Computational Model Credibility Guidance
- Reading location: Context of use; model verification, validation and credibility assessment
- Access: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/assessing-credibility-computational-modeling-and-simulation-medical-device-submissions
- Verification: applicability limited to intended guidance scope

### A16 — DICOM Standard
- Reading location: Image spatial geometry, DICOM SEG and referenced source images; locate exact part/modules for version
- Access: https://www.dicomstandard.org/current
- Verification: standard verified; section number pending

### A17 — MIT Computer Graphics OpenCourseWare
- Reading location: Transforms and 3D geometry; select exact lecture in course notes
- Access: https://ocw.mit.edu/courses/6-837-computer-graphics-fall-2012/pages/lecture-notes/
- Verification: exact lecture pending

### A18 — RECIST 1.1
- Reading location: Definitions of tumor measurement and formal response categories
- Access: https://recist.eortc.org/recist-1-1/
- Verification: verified topical reference

## Behavior-to-reference map

### DAT.01 — Source patient/study identity
- **Target behavior:** Preserve pseudonymous patient→study→series→acquisition linkage; distinct DCE phase vs repeat visit
- **Read first:** A16 (Image spatial geometry, DICOM SEG and referenced source images; locate exact part/modules for version), A03 (Lecture 17 — Medical image modalities; Lectures 9,12 image processing)
- **Inspect working implementation:** R07 (IDC Index)
- **Research/data support:** P05
- **Verify:** Patient/study/series manifest round-trip; no patient mixing
- **CancerOS specification:** COS-SPEC-003 · **Priority:** P0

### DAT.02 — Licensing and provenance
- **Target behavior:** Separate source licensing, original/derived/synthetic origin and immutable lineage
- **Read first:** A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration)
- **Inspect working implementation:** R07 (IDC Index)
- **Research/data support:** P05
- **Verify:** Provenance complete; unauthorized sources quarantined
- **CancerOS specification:** COS-SPEC-003 · **Priority:** P0

### DAT.03 — Data quality and missingness
- **Target behavior:** Do not impute absent labs or tumor labels without explicit derived/synthetic markers
- **Read first:** A11 (Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles), A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration)
- **Inspect working implementation:** R07 (IDC Index)
- **Research/data support:** P05
- **Verify:** Missingness and unit validation fixtures
- **CancerOS specification:** COS-SPEC-003 · **Priority:** P0

### DAT.04 — Patient-level split and duplicate detection
- **Target behavior:** Keep source patient and synthetic descendants in same evaluation partition
- **Read first:** A11 (Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles), A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration)
- **Inspect working implementation:** R07 (IDC Index)
- **Research/data support:** P05
- **Verify:** No split leakage or duplicated derivative patient
- **CancerOS specification:** COS-SPEC-003 · **Priority:** P0

### IMG.01 — DICOM/NIfTI volume construction
- **Target behavior:** Read slices using spatial metadata and preserve original image artifacts
- **Read first:** A05 (Volume 2 — Image reading/writing, filtering, registration, segmentation and analysis; find exact subchapter in chosen edition), A16 (Image spatial geometry, DICOM SEG and referenced source images; locate exact part/modules for version), A03 (Lecture 17 — Medical image modalities; Lectures 9,12 image processing)
- **Inspect working implementation:** R06 (SimpleITK), R07 (IDC Index)
- **Research/data support:** P05
- **Verify:** Round-trip known volume spacing/origin/orientation
- **CancerOS specification:** COS-SPEC-005 · **Priority:** P0

### IMG.02 — MRI channel and DCE-phase management
- **Target behavior:** Do not reinterpret contrast phases as longitudinal patient follow-up
- **Read first:** A03 (Lecture 17 — Medical image modalities; Lectures 9,12 image processing), A16 (Image spatial geometry, DICOM SEG and referenced source images; locate exact part/modules for version)
- **Inspect working implementation:** R01 (MAMA-MIA), R05 (MONAI)
- **Research/data support:** P01
- **Verify:** Correct channel order and study timestamps
- **CancerOS specification:** COS-SPEC-005 · **Priority:** P0

### IMG.03 — Intensity preprocessing
- **Target behavior:** Apply documented modality/model-specific clipping/normalization without changing physical metadata
- **Read first:** A03 (Lecture 17 — Medical image modalities; Lectures 9,12 image processing), A05 (Volume 2 — Image reading/writing, filtering, registration, segmentation and analysis; find exact subchapter in chosen edition), A06 (Segmentation, registration, shape analysis, validation; inspect edition table of contents for exact chapter)
- **Inspect working implementation:** R05 (MONAI), R01 (MAMA-MIA)
- **Research/data support:** P02
- **Verify:** Deterministic intensity transforms and mask alignment
- **CancerOS specification:** COS-SPEC-005 · **Priority:** P0

### IMG.04 — Physical-coordinate transformations
- **Target behavior:** Preserve voxel→patient LPS/RAS→viewer transforms; verify inverses
- **Read first:** A05 (Volume 2 — Image reading/writing, filtering, registration, segmentation and analysis; find exact subchapter in chosen edition), A16 (Image spatial geometry, DICOM SEG and referenced source images; locate exact part/modules for version), A17 (Transforms and 3D geometry; select exact lecture in course notes)
- **Inspect working implementation:** R03 (3D Slicer), R06 (SimpleITK)
- **Research/data support:** P04
- **Verify:** Known geometry test phantom; round trip
- **CancerOS specification:** COS-SPEC-005 · **Priority:** P0

### IMG.05 — Reference mask semantic validation
- **Target behavior:** Distinguish anatomical expert masks from FTV/enhancement ROI/bounding boxes
- **Read first:** A01 (Lecture 14 — Introduction to medical image segmentation), A06 (Segmentation, registration, shape analysis, validation; inspect edition table of contents for exact chapter), A08 (IBSI 1 reference manual — image preprocessing and biomarker feature definitions; select benchmark in documentation)
- **Inspect working implementation:** R01 (MAMA-MIA), R03 (3D Slicer)
- **Research/data support:** P01
- **Verify:** Annotation type labeled; reject unsupported mask meaning
- **CancerOS specification:** COS-SPEC-005 · **Priority:** P0

### IMG.06 — Segmentation inference
- **Target behavior:** Use evaluated model and matched preprocessing; reference-mask fallback
- **Read first:** A01 (Lecture 14 — Introduction to medical image segmentation), A06 (Segmentation, registration, shape analysis, validation; inspect edition table of contents for exact chapter)
- **Inspect working implementation:** R01 (MAMA-MIA), R02 (nnU-Net v2), R05 (MONAI)
- **Research/data support:** P01, P02
- **Verify:** Held-out Dice/HD95 and empty mask rate
- **CancerOS specification:** COS-SPEC-005 · **Priority:** P1

### IMG.07 — Segmentation postprocessing
- **Target behavior:** Connected components, label preserving resampling and mask QC
- **Read first:** A01 (Lecture 14 — Introduction to medical image segmentation), A05 (Volume 2 — Image reading/writing, filtering, registration, segmentation and analysis; find exact subchapter in chosen edition)
- **Inspect working implementation:** R05 (MONAI), R03 (3D Slicer)
- **Research/data support:** P02
- **Verify:** No unauthorized lesion deletion; dimensions align
- **CancerOS specification:** COS-SPEC-005 · **Priority:** P0

### IMG.08 — Lesion volume and diameter
- **Target behavior:** Compute volume from voxel geometry; do not treat box diameter as RECIST
- **Read first:** A05 (Volume 2 — Image reading/writing, filtering, registration, segmentation and analysis; find exact subchapter in chosen edition), A08 (IBSI 1 reference manual — image preprocessing and biomarker feature definitions; select benchmark in documentation), A18 (Definitions of tumor measurement and formal response categories)
- **Inspect working implementation:** R03 (3D Slicer), R11 (SlicerRT)
- **Research/data support:** P04
- **Verify:** Known 3D phantom volume and dimensional accuracy
- **CancerOS specification:** COS-SPEC-005 · **Priority:** P0

### IMG.09 — 3D surface reconstruction
- **Target behavior:** Extract, validate and optionally simplify mask-based surface; calculate authoritative volume on mask
- **Read first:** A07 (Isosurfaces, medical segmentation, deformable models, registration; inspect chapter headings in accessible edition), A17 (Transforms and 3D geometry; select exact lecture in course notes), A05 (Volume 2 — Image reading/writing, filtering, registration, segmentation and analysis; find exact subchapter in chosen edition)
- **Inspect working implementation:** R03 (3D Slicer)
- **Research/data support:** P04
- **Verify:** Mesh spatial/volume reconciliation
- **CancerOS specification:** COS-SPEC-005 · **Priority:** P0

### IMG.10 — Longitudinal registration
- **Target behavior:** Only align real exams if comparable; separate transform quality from volume measurement
- **Read first:** A02 (Lectures 15–16 — Image registration I and II), A04 (Lab 3 — Post-processing brain MRI images; Lab 4 — Registration of medical images), A05 (Volume 2 — Image reading/writing, filtering, registration, segmentation and analysis; find exact subchapter in chosen edition)
- **Inspect working implementation:** R03 (3D Slicer), R06 (SimpleITK)
- **Research/data support:** P05
- **Verify:** Known transform recovery; overlay disabled on failure
- **CancerOS specification:** COS-SPEC-005 · **Priority:** P0

### IMG.11 — Lesion correspondence
- **Target behavior:** Track lesion IDs only where evidence supports correspondence across visits
- **Read first:** A02 (Lectures 15–16 — Image registration I and II), A06 (Segmentation, registration, shape analysis, validation; inspect edition table of contents for exact chapter)
- **Inspect working implementation:** R04 (OHIF Viewer), R03 (3D Slicer)
- **Research/data support:** P05
- **Verify:** Uncertain lesion match abstains
- **CancerOS specification:** COS-SPEC-005 · **Priority:** P0

### IMG.12 — 2D/3D medical browser viewer
- **Target behavior:** Display actual scans and segmentations in correct orientation and coordinates
- **Read first:** A17 (Transforms and 3D geometry; select exact lecture in course notes), A16 (Image spatial geometry, DICOM SEG and referenced source images; locate exact part/modules for version)
- **Inspect working implementation:** R04 (OHIF Viewer), R03 (3D Slicer)
- **Research/data support:** P05
- **Verify:** Image/mask overlay matches 3D surface
- **CancerOS specification:** COS-SPEC-009 · **Priority:** P0

### IMG.13 — Synthetic shape generation
- **Target behavior:** Derive simulated mesh from original mask; label geometry simulated; constrain target volume
- **Read first:** A07 (Isosurfaces, medical segmentation, deformable models, registration; inspect chapter headings in accessible edition), A08 (IBSI 1 reference manual — image preprocessing and biomarker feature definitions; select benchmark in documentation), A17 (Transforms and 3D geometry; select exact lecture in course notes)
- **Inspect working implementation:** R03 (3D Slicer)
- **Research/data support:** P04
- **Verify:** Target-vs-produced mask volume tolerance
- **CancerOS specification:** COS-SPEC-004,005 · **Priority:** P0

### TWIN.01 — Observed and synthetic twin states
- **Target behavior:** Maintain immutable actual states and independent simulated branches
- **Read first:** A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration), A15 (Context of use; model verification, validation and credibility assessment)
- **Inspect working implementation:** R04 (OHIF Viewer)
- **Research/data support:** P05
- **Verify:** Branch isolation and history tests
- **CancerOS specification:** COS-SPEC-001,008 · **Priority:** P0

### TWIN.02 — Timeline synchronization
- **Target behavior:** Selecting visit synchronizes imagery, tumor metrics, labs, treatments and provenance
- **Read first:** A11 (Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles), A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration)
- **Inspect working implementation:** R04 (OHIF Viewer)
- **Research/data support:** P05
- **Verify:** E2E multi-date state consistency
- **CancerOS specification:** COS-SPEC-009 · **Priority:** P0

### TWIN.03 — New observation update
- **Target behavior:** Append new observation; recompute dependent measurements; retain old calculations
- **Read first:** A11 (Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles), A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration)
- **Inspect working implementation:** R04 (OHIF Viewer)
- **Research/data support:** P05
- **Verify:** No silent overwrite; stale interpretation invalidated
- **CancerOS specification:** COS-SPEC-008 · **Priority:** P0

### SIM.01 — Five trajectory scenario patterns
- **Target behavior:** Strong response, partial/stable, growth, regrowth, toxicity/deterioration
- **Read first:** A11 (Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles), A09 (Posterior and Prior Predictive Checks), A12 (Stage-specific treatment, receptor status and neoadjuvant therapy sections)
- **Inspect working implementation:** R10 (Stan)
- **Research/data support:** P05
- **Verify:** Shape constraints on all five families
- **CancerOS specification:** COS-SPEC-004 · **Priority:** P0

### SIM.02 — Within/between patient heterogeneity
- **Target behavior:** Separate individual latent state, scenario trajectory, observation noise and patient variability
- **Read first:** A11 (Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles), A10 (Hierarchical models and mixed replication; navigate from current official guide), A09 (Posterior and Prior Predictive Checks)
- **Inspect working implementation:** R10 (Stan)
- **Research/data support:** P05
- **Verify:** Between/within variance diagnostics
- **CancerOS specification:** COS-SPEC-004 · **Priority:** P0

### SIM.03 — Clinical treatment compatibility
- **Target behavior:** Guard endocrine/HER2/immunotherapy cases by documented subtype and setting
- **Read first:** A12 (Stage-specific treatment, receptor status and neoadjuvant therapy sections)
- **Inspect working implementation:** No direct full implementation verified; use source principles
- **Research/data support:** No direct research link assigned; validate assumption
- **Verify:** Invalid eligibility blocked; unknown not invented
- **CancerOS specification:** COS-SPEC-004 · **Priority:** P0

### SIM.04 — Discrete surgery and radiotherapy events
- **Target behavior:** Model intervention as dated event not generic geometric shrinkage
- **Read first:** A12 (Stage-specific treatment, receptor status and neoadjuvant therapy sections), A11 (Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles)
- **Inspect working implementation:** No direct full implementation verified; use source principles
- **Research/data support:** No direct research link assigned; validate assumption
- **Verify:** Surgical transition has explicit status and rationale
- **CancerOS specification:** COS-SPEC-004 · **Priority:** P0

### SIM.05 — Laboratory and symptom generation
- **Target behavior:** Generate observed variables by timestamp, unit, dependency, missingness and patient state
- **Read first:** A11 (Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles), A09 (Posterior and Prior Predictive Checks), A13 (Adverse-event definitions, laboratory abnormalities and grading criteria)
- **Inspect working implementation:** R10 (Stan)
- **Research/data support:** No direct research link assigned; validate assumption
- **Verify:** Cross-modal range, covariance and timing checks
- **CancerOS specification:** COS-SPEC-004 · **Priority:** P0

### SIM.06 — Toxicity/event grading
- **Target behavior:** Record abnormal observations and assign CTCAE grade only with defined evidence
- **Read first:** A13 (Adverse-event definitions, laboratory abnormalities and grading criteria), A12 (Stage-specific treatment, receptor status and neoadjuvant therapy sections)
- **Inspect working implementation:** No direct full implementation verified; use source principles
- **Research/data support:** No direct research link assigned; validate assumption
- **Verify:** Without required evidence no formal grade
- **CancerOS specification:** COS-SPEC-004 · **Priority:** P0

### SIM.07 — Reproducibility and parameter versioning
- **Target behavior:** Use seed, config hash, simulator version and independent lineage
- **Read first:** A09 (Posterior and Prior Predictive Checks), A15 (Context of use; model verification, validation and credibility assessment)
- **Inspect working implementation:** R10 (Stan)
- **Research/data support:** No direct research link assigned; validate assumption
- **Verify:** Byte/semantic reproducibility with controlled tolerance
- **CancerOS specification:** COS-SPEC-004 · **Priority:** P0

### SIM.08 — Simulation credibility tests
- **Target behavior:** Distinguish program verification, fit/calibration, external validation and context of use
- **Read first:** A09 (Posterior and Prior Predictive Checks), A15 (Context of use; model verification, validation and credibility assessment)
- **Inspect working implementation:** R10 (Stan)
- **Research/data support:** P05
- **Verify:** Report independent synthetic and real-case metrics
- **CancerOS specification:** COS-SPEC-011 · **Priority:** P0

### SIM.09 — Missing-data mechanisms
- **Target behavior:** Represent absent, censored and scheduled-not-collected differently if source supports
- **Read first:** A11 (Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles), A09 (Posterior and Prior Predictive Checks)
- **Inspect working implementation:** R10 (Stan)
- **Research/data support:** No direct research link assigned; validate assumption
- **Verify:** No missing=normal leaks
- **CancerOS specification:** COS-SPEC-004 · **Priority:** P0

### AI.01 — Clinical note extraction
- **Target behavior:** Extract typed mentions with spans, uncertainty, negation and dates
- **Read first:** A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration), A12 (Stage-specific treatment, receptor status and neoadjuvant therapy sections)
- **Inspect working implementation:** No direct full implementation verified; use source principles
- **Research/data support:** P03
- **Verify:** Curated entity and negation tests
- **CancerOS specification:** COS-SPEC-006 · **Priority:** P0

### AI.02 — Deterministic medical arithmetic
- **Target behavior:** Compute numeric trends outside LLM; units and dates source-grounded
- **Read first:** A08 (IBSI 1 reference manual — image preprocessing and biomarker feature definitions; select benchmark in documentation), A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration)
- **Inspect working implementation:** R03 (3D Slicer)
- **Research/data support:** P03
- **Verify:** Exact numeric claims match records
- **CancerOS specification:** COS-SPEC-006 · **Priority:** P0

### AI.03 — Evidence retrieval and citation checking
- **Target behavior:** Curate clinical sources, link exact evidence, avoid unverified generated links
- **Read first:** A12 (Stage-specific treatment, receptor status and neoadjuvant therapy sections), A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration)
- **Inspect working implementation:** No direct full implementation verified; use source principles
- **Research/data support:** P03
- **Verify:** Every cited claim resolves to supporting source
- **CancerOS specification:** COS-SPEC-006 · **Priority:** P0

### AI.04 — Multimodal fusion
- **Target behavior:** Combine observed imaging, labs, notes, symptoms and treatments with conflict/provenance markers
- **Read first:** A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration), A11 (Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles)
- **Inspect working implementation:** No direct full implementation verified; use source principles
- **Research/data support:** P03
- **Verify:** Cross-source conflicts surfaced
- **CancerOS specification:** COS-SPEC-006 · **Priority:** P0

### AI.05 — Temporal forecasting eligibility
- **Target behavior:** Use simple comparator first; abstain on insufficient real follow-up; synthetic not real proof
- **Read first:** A11 (Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles), A09 (Posterior and Prior Predictive Checks), A15 (Context of use; model verification, validation and credibility assessment)
- **Inspect working implementation:** R10 (Stan)
- **Research/data support:** P05
- **Verify:** Held-out simple baselines; no fabricated confidence
- **CancerOS specification:** COS-SPEC-006,011 · **Priority:** P0

### AI.06 — Interpretation output guard
- **Target behavior:** Evidence-constrained summaries, validation, provenance and no individualized prescriptions
- **Read first:** A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration), A12 (Stage-specific treatment, receptor status and neoadjuvant therapy sections)
- **Inspect working implementation:** No direct full implementation verified; use source principles
- **Research/data support:** P03
- **Verify:** Unsupported numeric and medical claims rejected
- **CancerOS specification:** COS-SPEC-006 · **Priority:** P0

### EVAL.01 — Segmentation quality reporting
- **Target behavior:** Report Dice, surface distance, volume error per real source cohort
- **Read first:** A01 (Lecture 14 — Introduction to medical image segmentation), A08 (IBSI 1 reference manual — image preprocessing and biomarker feature definitions; select benchmark in documentation)
- **Inspect working implementation:** R11 (SlicerRT), R05 (MONAI)
- **Research/data support:** P02
- **Verify:** Independent metric tests and cohort boundaries
- **CancerOS specification:** COS-SPEC-011 · **Priority:** P0

### EVAL.02 — Statistical diagnostics of synthetic cohorts
- **Target behavior:** Compare real available distributions against replicated synthetic summaries
- **Read first:** A09 (Posterior and Prior Predictive Checks), A10 (Hierarchical models and mixed replication; navigate from current official guide), A11 (Mixed-effects models, repeated-measure correlation and missing longitudinal observations; confirm edition-specific chapter titles)
- **Inspect working implementation:** R10 (Stan)
- **Research/data support:** No direct research link assigned; validate assumption
- **Verify:** Plots/tests for correlation, time spacing, missingness
- **CancerOS specification:** COS-SPEC-011 · **Priority:** P0

### EVAL.03 — Scientific model documentation
- **Target behavior:** Document context, assumption, version, calibration, applicability and failure
- **Read first:** A15 (Context of use; model verification, validation and credibility assessment), A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration)
- **Inspect working implementation:** No direct full implementation verified; use source principles
- **Research/data support:** P03
- **Verify:** Limitations report per model
- **CancerOS specification:** COS-SPEC-010,011 · **Priority:** P0

### UX.01 — Provenance-labeled scenario comparison
- **Target behavior:** Real observed / real derived / synthetic / interpolation / forecast never conflated
- **Read first:** A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration), A15 (Context of use; model verification, validation and credibility assessment)
- **Inspect working implementation:** R04 (OHIF Viewer)
- **Research/data support:** No direct research link assigned; validate assumption
- **Verify:** Visible labels in screenshots and E2E tests
- **CancerOS specification:** COS-SPEC-009 · **Priority:** P0

### OPS.01 — Reproducible image model deployment
- **Target behavior:** Pinned upstream version, licenses, model weights and scalable inference fallback
- **Read first:** A05 (Volume 2 — Image reading/writing, filtering, registration, segmentation and analysis; find exact subchapter in chosen edition), A14 (Model/data/evaluation reporting checklist; consult full checklist and elaboration)
- **Inspect working implementation:** R02 (nnU-Net v2), R05 (MONAI), R01 (MAMA-MIA)
- **Research/data support:** P02
- **Verify:** Fresh install, no-cloud fallback and logs
- **CancerOS specification:** COS-SPEC-007 · **Priority:** P0
