"""Adapter for the upstream FoundationModelsArchaeology notebooks.

The upstream project publishes five executable Google Colab notebooks. This
adapter runs the selected notebook locally/inside the remote worker with
nbconvert. It never claims success merely because a notebook exists.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

REPO_SRC = Path(__file__).resolve().parents[2] / "vendor" / "foundation-models-archaeology"


def list_experiments() -> dict[str, Any]:
    if not REPO_SRC.exists():
        raise FileNotFoundError(f"Foundation Models Archaeology repository not found: {REPO_SRC}")
    experiments = []
    for exp_dir in sorted(REPO_SRC.glob("Experiment_*")):
        if not exp_dir.is_dir():
            continue
        notebooks = sorted(exp_dir.glob("*.ipynb"))
        if notebooks:
            experiments.append({"name": exp_dir.name, "path": str(exp_dir), "notebooks": [p.name for p in notebooks]})
    return {
        "adapterId": "foundation-models-archaeology",
        "repository": "vendor/foundation-models-archaeology",
        "executionStatus": "READY",
        "ran": False,
        "experiments": experiments,
    }


def run_experiment(experiment_name: str, input_data: Path, output_dir: Path) -> dict[str, Any]:
    """Execute one real upstream notebook and save the executed notebook."""
    exp_dir = REPO_SRC / experiment_name
    if not exp_dir.is_dir():
        raise ValueError(f"Unknown experiment: {experiment_name}")
    notebooks = sorted(exp_dir.glob("*.ipynb"))
    if not notebooks:
        raise FileNotFoundError(f"No notebook found in {exp_dir}")
    notebook = notebooks[0]
    output_dir.mkdir(parents=True, exist_ok=True)
    executed = output_dir / f"{notebook.stem}_executed.ipynb"
    try:
        check = subprocess.run(["jupyter", "nbconvert", "--version"], capture_output=True, text=True, timeout=60)
    except FileNotFoundError as exc:
        raise RuntimeError("jupyter/nbconvert is required on the execution worker") from exc
    if check.returncode != 0:
        raise RuntimeError(check.stderr or "nbconvert is unavailable")

    env = os.environ.copy()
    env["DRIFT_INPUT_DATA"] = str(input_data)
    result = subprocess.run(
        ["jupyter", "nbconvert", "--to", "notebook", "--execute", str(notebook), "--output", executed.name],
        cwd=str(exp_dir),
        capture_output=True,
        text=True,
        timeout=1800,
        env=env,
    )
    if result.returncode != 0 or not executed.exists():
        raise RuntimeError(result.stderr[-6000:] or result.stdout[-6000:] or "upstream notebook execution failed")
    return {
        "adapterId": "foundation-models-archaeology",
        "repository": "vendor/foundation-models-archaeology",
        "model": notebook.name,
        "executionStatus": "FULLY RUNNING",
        "ran": True,
        "experiment": experiment_name,
        "input": str(input_data),
        "artifact": str(executed),
        "command": "jupyter nbconvert --to notebook --execute",
        "stdout": result.stdout[-4000:],
    }
