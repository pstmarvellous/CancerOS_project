"""Five-family scenario discovery and branch listing over owned twin state."""

from uuid import UUID

from sqlalchemy import text

from canceros.contracts import Contract
from canceros.patient_linkage import authorize_patient
from canceros.simulation_contracts import Family

FAMILY_DESCRIPTIONS: dict[str, str] = {
    "SC-01": "Modest reduction trajectory under a bounded explicit schedule.",
    "SC-02": "Near-stable trajectory with explicit noise and missingness.",
    "SC-03": "Increasing trajectory with explicit target escalation.",
    "SC-04": "Decline then regrowth with an explicit control minimum.",
    "SC-05": "Symptom-conditioned course with explicit documented conditions.",
}
FAMILY_VERSIONS: dict[str, str] = {
    "SC-01": "sc01/1",
    "SC-02": "sc02/1",
    "SC-03": "sc03/1",
    "SC-04": "sc04/1",
    "SC-05": "sc05/1",
}


class ScenarioDiscovery(Contract):
    family: Family
    definition_version: str
    description: str
    synthetic_only: bool = True
    next_action: str = "check_eligibility_then_create_draft_branch"


class DiscoveryPage(Contract):
    items: tuple[ScenarioDiscovery, ...]


class BranchSummary(Contract):
    branch_id: UUID
    baseline_hash: str
    mode: str
    observed_baseline_verified: bool
    next_action: str = "inspect_branch_before_running"


class BranchPage(Contract):
    items: tuple[BranchSummary, ...]


def discovery_families() -> DiscoveryPage:
    families: list[ScenarioDiscovery] = []
    for family in ("SC-01", "SC-02", "SC-03", "SC-04", "SC-05"):
        families.append(
            ScenarioDiscovery(
                family=family,  # type: ignore[arg-type]
                definition_version=FAMILY_VERSIONS[family],
                description=FAMILY_DESCRIPTIONS[family],
            )
        )
    return DiscoveryPage(items=tuple(families))


def list_branches(c, i, p: UUID, u: UUID) -> BranchPage:
    authorize_patient(c, i, p, u)
    rows = (
        c.execute(
            text(
                "SELECT id,report->>'baseline_hash' AS baseline,report->>'mode' AS mode,"
                "COALESCE((report->>'observed_baseline_verified')::boolean,false) AS verified "
                "FROM imaging.twin_branches WHERE project_id=:p AND patient_id=:u ORDER BY id"
            ),
            {"p": p, "u": u},
        )
        .mappings()
        .all()
    )
    return BranchPage(
        items=tuple(
            BranchSummary(
                branch_id=r["id"],
                baseline_hash=r["baseline"] or "unknown",
                mode=r["mode"] or "unknown",
                observed_baseline_verified=bool(r["verified"]),
            )
            for r in rows
        )
    )
