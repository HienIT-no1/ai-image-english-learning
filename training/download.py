"""Download official data with size checks, retries and safe ZIP extraction."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))


def download(url: str, target: Path, *, attempts: int = 4) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and target.stat().st_size:
        return target
    temporary = target.with_suffix(target.suffix + ".part")
    last_error = None
    for attempt in range(attempts):
        try:
            offset = temporary.stat().st_size if temporary.exists() else 0
            headers = {"User-Agent": "LensLearn-Training/1.0"}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
                resume = response.status == 206 and response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")
                if response.status == 206 and not resume:
                    raise ValueError("Server returned an unexpected byte range")
                received = offset if resume else 0
                remaining = response.headers.get("Content-Length")
                expected = received + int(remaining) if remaining else None
                if expected and shutil.disk_usage(target.parent).free < expected - received + 2 * 2**30:
                    raise OSError("Insufficient disk space; keep at least 2 GiB free")
                with temporary.open("ab" if resume else "wb") as output:
                    while block := response.read(1024 * 1024):
                        output.write(block)
                        received += len(block)
                if expected is not None and received != expected:
                    raise IOError(f"Incomplete download: {received} != {expected}")
            temporary.replace(target)
            return target
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_error = exc
            time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"Download failed for {url}: {last_error}") from last_error


def extract_json(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as package:
        members = [member for member in package.infolist() if member.filename.endswith(".json")]
        if len(members) != 1:
            raise ValueError("Expected exactly one annotation JSON")
        member = members[0]
        target = destination / Path(member.filename).name
        if not target.exists():
            partial = target.with_suffix(".json.part")
            with package.open(member) as source, partial.open("wb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
            partial.replace(target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", action="store_true", required=True)
    args = parser.parse_args()
    from concurrent.futures import ThreadPoolExecutor

    def fetch(split: str) -> dict:
        url = SOURCES[f"lvis_{split}"]
        print(f"Downloading LVIS {split} metadata", flush=True)
        archive = download(url, ROOT / "data/raw" / f"lvis_v1_{split}.json.zip")
        annotation = extract_json(archive, ROOT / "data/raw")
        with archive.open("rb") as source:
            checksum = hashlib.file_digest(source, "sha256").hexdigest()
        return {"split": split, "source": url, "archive_sha256": checksum,
                "archive_bytes": archive.stat().st_size, "annotations": str(annotation)}

    with ThreadPoolExecutor(max_workers=2) as executor:
        records = list(executor.map(fetch, ("train", "val")))
    download(SOURCES["open_images_categories"], ROOT / "data/raw/open_images_boxable.csv")
    (ROOT / "data/raw/provenance.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(records, indent=2), flush=True)


if __name__ == "__main__":
    main()
