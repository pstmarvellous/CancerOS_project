# COS-026 canonical geometry learning and fixture evidence

Scope: delegated pure geometry contract/functions and artificial tests. Parent
[COS-026 context](COS-026.md) records queries, original map IDs and relevant edges;
consulted its capability, academic and repository/scientific outputs. Relevant
behavior includes IMG.01 and geometry/measurement nodes; references A05 (ITK),
A08 (IBSI), R03 (Slicer) and associated guards are pointers, not completed reviews.
Read the exact COS-026 prompt, SPEC-005 P-01–04, SPEC-008 spatial-frame contract
and SPEC-011 section 5 before finalizing geometry decisions. Source documents/maps
remain unchanged. This is AI engineering self-review, not qualified imaging review.

## Actual source learning

- ITK project, online **ITK Software Guide, Book 1 chapter 4, Image physical-space
  representation**, [Data Representation](https://itk.org/ITKSoftwareGuide/html/Book1/ITKSoftwareGuide-Book1ch4.html):
  read origin, spacing, direction and the index-to-physical-point equations in the
  image metadata discussion. Exact edition is not printed in the inspected page;
  record this online chapter rather than invent an edition. Mapped A05 points to
  Book 2; Book 1 was deliberately consulted for the foundational geometry equations.
  Principle: a voxel index maps through a full spatial transform plus origin; units
  and common reference space need explicit handling. ITK's orthonormal-direction
  example does not cover arbitrary shear, so preserve the complete affine rather
  than force every source into its direction/spacing example.
- SimpleITK documentation labelled **2.4.0**, [Fundamental Concepts, Images](https://simpleitk.readthedocs.io/en/master/fundamentalConcepts.html):
  read physical grid extent, center-origin convention, direction columns and unit
  consistency. An image occupies half a voxel beyond its first/last centers. Same
  array size and spacing do not establish the same physical image. SimpleITK is a
  conceptual reference only here; no new dependency or execution claimed.
- NiBabel online [Coordinate systems and affines](https://nipy.org/nibabel/coordinate_systems.html),
  sections voxel coordinates, affine mapping and applying/inverting the affine:
  read that voxel coordinates require a reference transform and that the affine
  maps into RAS physical space. The live site is development-labelled; pinned
  implementation behavior was separately inspected in **NiBabel 5.4.2**
  [orientations.py](https://github.com/nipy/nibabel/blob/5.4.2/nibabel/orientations.py),
  `io_orientation` and `aff2axcodes`. Its polar/SVD-based nearest-cardinal labels
  describe dominant axes without resampling. CancerOS reports that meaning explicitly;
  these labels are not proof of orthogonality or longitudinal registration.
- DICOM PS3.3 **2026d** C.7.6.2 was read for COS-025 and remains the source for
  biped LPS/source voxel-center interpretation. RAS/LPS conversion flips world X/Y
  by left multiplication, preserving XYZ index order and spacing exactly once.
- Pinned NiBabel/NumPy software license inspection is recorded in
  [COS-025 parser learning](COS-025-parser.md). No upstream code copied, no model,
  dataset or annotation rights inferred. Slicer/IBSI experiments were not performed;
  no breast-MRI empirical validation or clinical thresholds are established.

## Three-source decision and precision

Physical-grid principle → pinned NiBabel orientation API plus explicit NumPy
float64 affine algebra → no approved authentic cohort/reference-tool evidence →
retain the exact full affine in an owned immutable contract and label its scope
as technical geometry only → verify independent cuboid arithmetic, known transforms
and negative fixtures. Geometry validity cannot establish study alignment.

Canonical matrix/coordinate metadata are finite JSON float64 values. This preserves
small rotations/shears without truncating every matrix coefficient to nine decimal
places. Scalar physical quantities use shared decimal-string syntax at nine decimal
places with half-even rounding; voxel volume uses the absolute spatial determinant,
never the product of column norms for shear. Column norms are reported as axis-step
spacing and handedness follows the determinant sign. Source frame, original numeric
affine, conversion matrix and conversion direction are retained; source headers and
patient-identifying metadata remain in the parent's private source artifacts.

Version `geometry/1` freezes a bounded coordinate round-trip check of 1e-5 mm from
SPEC-011 section 5, which explicitly identifies it as an engineering tolerance.
Additional resource/numerical policy: 0.001–1000 mm axis steps, condition number at
most 1e6, determinant magnitude at least 1e-9 mm3, origin magnitude at most 1e7 mm,
XYZ axes at most 1024, 2 million total voxels and at most 16 declared DCE phases.
These limits are support/numerical bounds, not clinical acceptability thresholds.
Unknown units/frames and missing fourth-axis meaning fail; no metadata are inferred.
Imported NIfTI q/s disagreements and irregular DICOM sampling remain quarantined
by COS-025; no reconstruction or evidence-based conflict resolution is fabricated.

## Critical review and actual checks

Self-review covered row/column swaps, reflection, voxel centers versus faces,
double spacing, obliquity, shear determinant, stale source transforms, nonfinite
coordinates, direct construction of inconsistent contracts and unknown phase units.
`geometry_for` cross-checks decoded canonical geometry against the original DICOM
LPS transform; public contracts contain numerical geometry, not raw identifiers.

Executed `uv run pytest tests/test_imaging_geometry.py -q`: **27 passed** on wholly
artificial fixtures, including translated/aniso cuboid support volume, independent
rotation/reflection/oblique/shear coordinates, LPS/RAS round trips, both COS-025
reader adapters, singular/ill-conditioned/nonfinite/unknown-unit cases, phase and
allocation bounds, inconsistent contract assertions and coordinate errors.
Executed Ruff check/format and focused mypy successfully after fixing a tuple type.
Parent task owns persistence, source rights, API ownership and generated-client checks.
Independent Slicer comparison, representative source geometry and qualified review
remain absent. Next action: run parent geometry integration checks while retaining
the real-source/scientific-review gates.

Hackathon compliance impact: deterministic local geometry only; no external model
request, source publication, clinical claims or competition eligibility asserted.
