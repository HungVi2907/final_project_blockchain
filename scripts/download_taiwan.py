"""Download the official UCI archive and record its checksum."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile
import json

URL = "https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    archive = OUT / "taiwan_uci350.zip"
    if not archive.exists():
        with urlopen(URL, timeout=60) as response:
            archive.write_bytes(response.read())
    with ZipFile(archive) as bundle:
        members = [n for n in bundle.namelist() if n.lower().endswith(".xls")]
        if len(members) != 1:
            raise ValueError(f"Expected one XLS file, found {members}")
        destination = OUT / "default of credit card clients.xls"
        if not destination.exists():
            destination.write_bytes(bundle.read(members[0]))
    manifest = {
        "source_url": URL,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "archive_sha256": sha256(archive.read_bytes()).hexdigest(),
        "source_file": destination.name,
        "source_sha256": sha256(destination.read_bytes()).hexdigest(),
    }
    (OUT / "taiwan_source_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
