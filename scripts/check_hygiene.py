"""Check Git-visible files and known local secrets without printing secret values."""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
result = subprocess.run(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
    cwd=ROOT,
    capture_output=True,
    check=True,
)
files = [ROOT / p.decode("utf-8") for p in result.stdout.split(b"\0") if p]
known = []
private = ROOT / ".local/development.json"
if private.exists():
    known = [
        v.encode()
        for v in json.loads(private.read_text()).values()
        if isinstance(v, str) and len(v) > 15
    ]
for path in files:
    relative = path.relative_to(ROOT).as_posix()
    assert not relative.startswith(("Data_folder/", ".local/", ".venv/", "node_modules/")), (
        f"Private runtime/source path: {relative}"
    )
    assert not (path.name.startswith(".env") and path.name != ".env.example"), (
        f"Private environment file: {relative}"
    )
    assert not re.search(r"\.(dcm|nii|nii\.gz|pth|ckpt|pem|key)$", relative, re.I), (
        f"Restricted asset: {relative}"
    )
    if not path.is_file() or path.suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg"):
        continue
    content = path.read_bytes()
    assert not any(value in content for value in known), f"Known local secret in {relative}"
    assert not re.search(
        rb"-----BEGIN (?:RSA )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]+\s+-----END (?:RSA )?PRIVATE KEY-----",
        content,
    ), f"Private key in {relative}"
for target in (".env", ".local/development.json", "Data_folder/example.dcm"):
    check = subprocess.run(["git", "check-ignore", "-q", target], cwd=ROOT)
    assert check.returncode == 0, f"Missing ignore for {target}"
print(
    f"PASS {len(files)} Git-visible file paths, private-source ignores and known local secret scan; source/asset license review remains a release gate"
)
