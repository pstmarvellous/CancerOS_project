# ADR-034: independent SC-05 clinical-condition descriptor

COS-047. `sc05-explicit/1` composes the existing SC-01/02/03 numerical tumor plugin
with a separate explicit `clinical-condition/1` profile. Selected laboratory/vital
concepts declare their direction; symptom courses use the named internal0–10 scale
with coherent presence. Onset/recovery, affected concepts and internal severity are
supplied assumptions. Required course points and dictionary entries cannot be inferred.

The profile must demonstrate configured worsening, with an explicit reversal if
recovery is configured. It does not produce diagnoses, emergency triage, treatment
changes or an overall health score. Tumor and clinical dimensions remain separately
configurable; a stable or shrinking lesion does not imply stable patient condition.

Output events use local configured-condition-change terminology, ungraded status,
parameter/slot references and hypothetical noncausal attribution. Internal severity
is not a CTCAE grade; no CTCAE thresholds, MedDRA codes or dosage recommendations
are implemented. Specific exposure compatibility remains unreviewed and unavailable.

Clinical descriptors are not yet source observations or materialized visit records;
COS-048 owns that step. Unknown clinical baseline values remain missing. All output
descendants remain synthetic and cannot satisfy observed eligibility. Geometry
validation returns the independent descriptor beside realized tumor quantities;
neither dimension alone grants complete-run publication.

Use exact unrounded mask volume for simulation arithmetic, and plain decimal wire
strings for very small quantities; display rounding is not a biological zero or a
computation input. Original source and immutable snapshot values are preserved.
