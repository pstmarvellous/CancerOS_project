"""Download pinned local-only development service binaries into ignored storage."""

import hashlib
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {
    "seaweedfs": (
        "4.51",
        "https://github.com/seaweedfs/seaweedfs/releases/download/4.51/windows_amd64.zip",
    ),
    "redis": (
        "8.10.3",
        "https://github.com/redis-windows/redis-windows/releases/download/8.10.3/Redis-8.10.3-Windows-x64-msys2.zip",
    ),
}


def download(item):
    name, (version, url) = item
    target = ROOT / ".local/tools" / name
    target.mkdir(parents=True, exist_ok=True)
    archive = target / "download.zip"
    if not archive.exists():
        partial = target / "download.partial"
        with (
            urlopen(
                Request(url, headers={"User-Agent": "CancerOS-local-development"}), timeout=120
            ) as source,
            partial.open("wb") as output,
        ):
            while chunk := source.read(1024 * 1024):
                output.write(chunk)
        partial.replace(archive)
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            destination = (target / member.filename).resolve()
            assert destination.is_relative_to(target.resolve()), "Unsafe archive path"
        package.extractall(target)
    record = {
        "name": name,
        "version": version,
        "url": url,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "scope": "Local-only development tool; not vendored/redistributed or clinical validation",
    }
    (target / "download-record.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Downloaded pinned {name} {version}; hash recorded privately", flush=True)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(download, TOOLS.items()))
