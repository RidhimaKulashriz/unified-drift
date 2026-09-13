"""DRIFT adapter preflight. This runs before queue dispatch and prevents invalid jobs."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "services" / "worker" / "adapter-manifest.json"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def inspect() -> list[dict]:
    results = []
    for adapter in load_manifest()["adapters"]:
        repo = ROOT / adapter["repo"]
        results.append({
            "id": adapter["id"],
            "repo": adapter["repo"],
            "vendored": repo.exists(),
            "videoCompatible": adapter["videoCompatible"],
            "executionStatus": "DEPENDENCY BLOCKED" if not repo.exists() else "PARTIALLY INTEGRATED",
            "requiredRuntime": adapter.get("requiredRuntime", []),
            "checkpointPresent": adapter.get("checkpointPresent", False),
        })
    return results


if __name__ == "__main__":
    rows = inspect()
    missing = [row for row in rows if not row["vendored"]]
    print(json.dumps({"adapters": rows, "missing": missing}, indent=2))
    raise SystemExit(1 if missing else 0)
