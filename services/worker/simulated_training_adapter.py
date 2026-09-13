"""Adapter for the upstream simulated archaeology training-data workflow."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_SRC = Path(__file__).resolve().parents[2] / "vendor" / "simulated-training-data"


def execute_training_data_generation(
    output_dir: Path,
    raster_path: Path,
    streams_path: Path,
    num_samples: int = 10,
    method: str = "simple",
) -> dict[str, Any]:
    """Call the real upstream generator and persist its geospatial outputs."""
    if not REPO_SRC.exists():
        raise FileNotFoundError(f"Repository missing: {REPO_SRC}")
    if not raster_path.exists():
        raise FileNotFoundError(f"Input DEM missing: {raster_path}")
    if not streams_path.exists():
        raise FileNotFoundError(f"Stream vector missing: {streams_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(REPO_SRC / "utils"))
    try:
        import generate_unknown_objects as gen
    except Exception as exc:
        raise RuntimeError(f"Could not import upstream generator: {exc}") from exc

    if method == "tar-kiln":
        result = gen.create_tar_kiln_like_objects(str(raster_path), num_samples, str(streams_path), 5, 5, 0.25)
        method_name = "create_tar_kiln_like_objects"
    else:
        result = gen.create_simple_objects(str(raster_path), num_samples, 2, 5, str(streams_path), 5, 0.25)
        method_name = "create_simple_objects"

    # The upstream functions return [binary_mask, instance_mask, modified_raster, GeoDataFrame].
    if not isinstance(result, list) or len(result) != 4:
        raise RuntimeError("Unexpected output from upstream simulated-data generator")

    import rasterio
    import geopandas as gpd

    with rasterio.open(raster_path) as src:
        profile = src.profile.copy()
        profile.update(count=1, dtype="uint8")
        with rasterio.open(output_dir / "annotation_mask.tif", "w", **profile) as dst:
            dst.write(result[0].astype("uint8"), 1)
        profile.update(dtype="float32")
        with rasterio.open(output_dir / "modified_dem.tif", "w", **profile) as dst:
            dst.write(result[2].astype("float32"), 1)

    gdf = result[3]
    if isinstance(gdf, gpd.GeoDataFrame) and not gdf.empty:
        gdf.to_file(output_dir / "annotations.gpkg", driver="GPKG")

    report: dict[str, Any] = {
        "adapterId": "simulated-training-data",
        "repository": "vendor/simulated-training-data",
        "model": "upstream procedural archaeological-object generator",
        "executionStatus": "FULLY RUNNING",
        "ran": True,
        "method": method_name,
        "inputRaster": str(raster_path),
        "streams": str(streams_path),
        "requestedSamples": num_samples,
        "returnTypes": [type(x).__name__ for x in result],
        "artifacts": [
            str(output_dir / "annotation_mask.tif"),
            str(output_dir / "modified_dem.tif"),
            str(output_dir / "annotations.gpkg"),
        ],
    }
    report_path = output_dir / "generation_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    report["artifact"] = str(report_path)
    return report
