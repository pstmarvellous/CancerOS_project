# AGENT ACADEMIC REFERENCE PROTOCOL

Before implementing any CancerOS behavior:

1. Query `knowledge-map.json` or `python query_academic_map.py <behavior-or-keyword>`.
2. Open every `READ_TO_DESIGN` academic source for that behavior. Read the specified chapter/lecture/section. Where the location is pending, identify it in the edition you can access and record exact edition/chapter/pages in your task notes. Never invent page numbers or assert that the book supports an algorithm without checking it.
3. Write a compact **Source Learning Record**: source ID, title, edition/version, actual section reviewed, principle, assumptions, failure modes, direct relevance to CancerOS, and link. Distinguish confirmed source statements from agent inference.
4. Open `INSPECT_IMPLEMENTATION` repositories at a pinned commit. Locate actual files, interfaces, demos and tests. Record code license and model/dataset licenses separately. Run the smallest documented compatible example.
5. Open `CHECK_EVIDENCE` papers/datasets; verify population, modality, annotations, restrictions and which claimed behaviors were demonstrated.
6. Create a **Three-Source Decision Note**: academic principle → working repository implementation → empirical research support → chosen CancerOS integration or own adaptation → test. One source category may be absent; explicitly record gaps rather than inventing an equivalent.
7. Prefer supported dependency APIs; copy source only if license permits, with provenance and minimal diff. Do not redistribute textbook chapters. Never assume study dataset phases equal longitudinal visits or FTV masks equal anatomical tumor masks.
8. Implement behind CancerOS-owned typed contracts. Keep real/synthetic/model-predicted provenance and source identity.
9. Execute listed validation, negative-case and clinical-boundary tests. Store pass/fail evidence; mark as implemented only after completion.
10. Update implementation links in a separate `implementation-state.json`; do not change the academic source mapping without documenting new evidence.

**Precedence:** CancerOS PRD/specifications define intended product requirements. Academic/clinical standards govern correctness of established definitions. Repositories inform implementation, papers establish scoped evidence; conflicts are logged and escalated for review. An unsafe or unsupported requirement cannot be justified by a repository alone.

**Task handoff template:** Behavior ID; academic source IDs and precise read excerpts summarized in your own words; repo IDs and pinned commits; paper IDs; decision; alternative rejected; artifacts touched; validation command/result; limitations; outstanding questions.
