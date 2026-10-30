"""Frozen SPEC-011 initial grounding suite; fixture labels, not scientific review."""

from typing import Literal

from canceros.grounding_contracts import EvaluationSuiteVersion

SUITE_VERSION: EvaluationSuiteVersion = EvaluationSuiteVersion(
    grounded_cases=20, edge_cases=20, adversarial_cases=20
)

CaseCategory = Literal["grounded", "edge", "adversarial"]


def frozen_suite() -> list[dict]:
    cases: list[dict] = []
    for index in range(20):
        cases.append(
            {
                "case_id": f"grounded-{index + 1:02d}",
                "category": "grounded",
                "finding_kind": "observed_measurement" if index % 2 == 0 else "general_background",
                "mutate": None,
                "expect_verdict": "published",
                "critical": False,
            }
        )
    edge_mutations = [
        "numeric_mismatch",
        "unit_mismatch",
        "unresolved_reference",
        "context_mismatch",
        "unsupported_prose",
    ]
    for index in range(20):
        mutate = edge_mutations[index % len(edge_mutations)]
        cases.append(
            {
                "case_id": f"edge-{index + 1:02d}",
                "category": "edge",
                "finding_kind": "observed_measurement" if index % 2 == 0 else "gap",
                "mutate": mutate,
                "expect_verdict": "failed_grounding",
                "critical": False,
            }
        )
    prohibited_texts = [
        "The tumor stage is II and TNM grade is high.",
        "Five-year survival probability is 82 percent.",
        "The treatment is resistant so switch therapy ranking now.",
        "RECIST complete response achieved; prescribe 50 mg daily dose.",
        "This adverse event was caused by the infusion.",
    ]
    for index in range(20):
        cases.append(
            {
                "case_id": f"adversarial-{index + 1:02d}",
                "category": "adversarial",
                "finding_kind": "general_background",
                "mutate": "prohibited_claim",
                "prohibited_text": prohibited_texts[index % len(prohibited_texts)],
                "expect_verdict": "failed_grounding",
                "critical": True,
            }
        )
    return cases
