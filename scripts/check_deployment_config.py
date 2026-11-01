"""COS-088 config gate: typed missing-config diagnostics for staging topology.

Reads a private env file (never committed), checks the staging variables the
compose topology needs, and fails with exact variable names and owning
decisions. A local pass is configuration validation, not cloud deployment.
"""

import argparse
import re
import sys
from pathlib import Path

REQUIRED = {
    "MODE": "must be 'staging' for the staging topology",
    "POSTGRES_USER": "staging database identity; owner: platform",
    "POSTGRES_DB": "isolated staging database; owner: platform",
    "POSTGRES_PASSWORD": "staging database secret; owner: platform",
    "STORAGE_ACCESS_KEY": "staging object key; owner: platform",
    "STORAGE_SECRET_KEY": "staging object secret; owner: platform",
    "CORS_ORIGINS": "staging origin allowlist JSON; owner: platform",
    "EXTERNAL_INFERENCE_ENABLED": "must be explicit; false unless verified export policy exists",
}

UUID_LIKE = re.compile(r"^[0-9a-fA-F-]{8,}$")


def parse_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("\"'")
    return values


def main():
    parser = argparse.ArgumentParser(description="Validate staging deployment config")
    parser.add_argument("--env-file", default=".env.staging")
    parser.add_argument("--topology", default="staging")
    args = parser.parse_args()
    path = Path(args.env_file)
    if not path.exists():
        print(f"MISSING {args.env_file}: create a private staging env file; never commit it")
        print("Owning decision: authorized account/target/spending authority")
        raise SystemExit(2)
    if args.topology != "staging":
        print(f"Unsupported topology: {args.topology}; only 'staging' is supported")
        raise SystemExit(2)
    values = parse_env(path)
    gaps = []
    for key, reason in REQUIRED.items():
        if not values.get(key):
            gaps.append(f"MISSING {key}: {reason}")
    if values.get("MODE") not in (None, "", "staging") and values.get("MODE") != "staging":
        gaps.append("INVALID MODE: must be 'staging' for the staging topology")
    if gaps:
        print("Staging configuration incomplete; no cost-bearing apply is authorized.")
        for gap in gaps:
            print(f" - {gap}")
        print("Record digests, resources and deployment status only after a real apply.")
        raise SystemExit(2)
    print("PASS staging configuration present (validation only; not cloud-deployed evidence)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
