# ADR-053: imaging/geometry closure with discovery reads and honest grants

COS-067 implements SPEC-008 study/segmentation/imaging-job/artifact routes
and SPEC-005/010 over the existing Phase 2 ingestion, QC, job, storage and
viewer services. No new upload path, no remote ingestion, no public links
and no P1 model routes are introduced. Three discovery reads compose owned
stores: study enumeration from associations, acquisition detail from import
reports plus study/series identity, and segmentation discovery from
annotations with live QC state. All re-authorize the patient; cross-patient
and unknown IDs fail closed.

Upload, preview, confirmation and publication keep existing admin services
with size/format/hash/object-version and source-rights enforcement; browsers
never select bucket keys and no anonymous endpoint exists. Read grants stay
short-lived, intended-use checked and audit-logged without storing URLs;
the response warns that an issued URL can survive to expiry after
withdrawal, with renewal guidance instead of revocation claims. Segmentation
discovery exposes mask type, label and QC state with blocked/unavailable
semantics; job 202 remains acceptance, never completion. Geometry and
orientation metadata serialize from verified reports so the viewer cannot
receive a scale-stripped mesh; failed QC geometry never publishes.
Fixture denominators cover discovery stability, QC visibility, grant
honesty, ownership isolation and HTTP boundaries — not clinical accuracy.
