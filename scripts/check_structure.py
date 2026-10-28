from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for name in (
    "apps/web",
    "services/api",
    "packages/contracts",
    "packages/clinical",
    "packages/imaging",
    "packages/simulation",
    "packages/intelligence",
    "workers",
    "infrastructure",
    "migrations",
    "tests",
    "fixtures",
    "docs",
    "src/canceros",
):
    assert (ROOT / name).is_dir(), name
assert (ROOT / ".gitignore").is_file()
assert "/Data_folder/" in (ROOT / ".gitignore").read_text()
print(
    "PASS module structure and private source ignore; runtime imports verified separately after installation"
)
