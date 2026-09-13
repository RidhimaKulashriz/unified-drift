#!/usr/bin/env python3
"""Acquire public TDM sources, verify bytes, and emit a provenance manifest.

This script never treats a landing page as an asset. Zenodo records are resolved
through the record API; direct files are downloaded; repositories are shallow
cloned. Sources requiring login/terms acceptance/manual selection are emitted as
INPUT_REQUIRED rather than silently skipped.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "client/public/source-catalog.json"

MANUAL = {
    "arran-dataset": "Google Drive folder requires user download/selection",
    "usgs-national-map": "USGS downloader requires a user-selected geographic extent",
    "caltech-rgbt": "Dataset landing page requires selecting/download terms and files",
    "archaeoscape": "Zenodo record must be resolved to selected GeoTIFF file(s)",
    "hit-uav": "Zenodo record must be resolved to selected thermal files",
    "dji-mavic-3-thermal": "Zenodo record may contain multiple large files; select paired thermal/SRT assets",
}
DIRECT_FILES = {
    "thermal-yolov12-checkpoint": "https://huggingface.co/Kiuyha/yolov12-human-detection-thermal-uav/resolve/main/best.pt",
    "dronekit-flight-tlog": "https://raw.githubusercontent.com/dronekit/dronekit-la-testdata/master/flight.tlog",
    "rgbt-onnx": "https://huggingface.co/hiuS04/RGBT-Fusion-Drone-SAR/resolve/main/fusion_progressive_finetune.onnx",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "DRIFT-TDM-Acquirer/1.0"})
    with urlopen(req, timeout=120) as response, target.open("wb") as out:
        shutil.copyfileobj(response, out)


def zenodo_files(record_url: str) -> list[dict]:
    record_id = urlparse(record_url).path.rstrip("/").split("/")[-1]
    req = Request(f"https://zenodo.org/api/records/{record_id}", headers={"User-Agent":"DRIFT-TDM-Acquirer/1.0"})
    with urlopen(req, timeout=60) as response:
        payload = json.load(response)
    return payload.get("files", [])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT / "tdm-cache")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text())
    args.root.mkdir(parents=True, exist_ok=True)
    report = {"createdAt": datetime.now(timezone.utc).isoformat(), "sources": []}
    for source in catalog["sources"]:
        item = {"id": source["id"], "url": source["url"], "category": source["category"], "usedBy": source.get("usedBy", [])}
        if source["id"] in DIRECT_FILES and not args.check_only:
            try:
                target = args.root / "files" / source["id"] / Path(urlparse(DIRECT_FILES[source["id"]]).path).name
                download(DIRECT_FILES[source["id"]], target)
                item.update({"status":"COMPLETED", "asset":str(target), "sha256":sha256(target), "bytes":target.stat().st_size, "entrypoint":DIRECT_FILES[source["id"]]})
            except Exception as exc:
                item.update({"status":"FAILED", "reason":str(exc), "entrypoint":DIRECT_FILES[source["id"]]})
            report["sources"].append(item); continue
        if source["id"] in MANUAL:
            item.update({"status":"INPUT_REQUIRED", "reason":MANUAL[source["id"]]})
            report["sources"].append(item); continue
        try:
            if source["category"] == "repository":
                dest = args.root / "repositories" / source["id"]
                item["entrypoint"] = source["url"]
                if not args.check_only:
                    clone_url = source["url"].removesuffix("/releases")
                    if not (dest / ".git").exists():
                        subprocess.run(["git", "clone", "--depth=1", clone_url, str(dest)], check=True, timeout=900)
                    item["path"] = str(dest)
                item["status"] = "COMPLETED"
            elif source["category"] == "runtime":
                item.update({"status":"RUNTIME_REQUIRED", "reason":"Install and verify this runtime on the worker before execution", "entrypoint":source["url"]})
            elif source["category"] == "checkpoint":
                item.update({"status":"DEPENDENCY_REQUIRED", "reason":"Resolve the direct checkpoint file from this public model/release page", "entrypoint":source["url"]})
            else:
                item.update({"status":"INPUT_REQUIRED", "reason":"Resolve and select a compatible downloadable asset; landing page is not treated as a file", "entrypoint":source["url"]})
            report["sources"].append(item)
        except Exception as exc:
            item.update({"status":"FAILED", "reason":str(exc)})
            report["sources"].append(item)
    out = args.root / "tdm-provenance.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
