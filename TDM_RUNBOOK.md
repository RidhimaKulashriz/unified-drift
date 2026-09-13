# Reproducible TDM execution runbook

The worker uses `client/public/source-catalog.json` as the source registry and `EXTERNAL_SOURCES.md` as the compatibility matrix. The acquisition command is:

```bash
python3 scripts/prepare_tdm_sources.py --root /var/lib/drift/tdm-cache
```

For a non-mutating provenance/status preview:

```bash
python3 scripts/prepare_tdm_sources.py --check-only
```

The command writes `tdm-provenance.json`. Every downloaded file records byte size and SHA-256. Git repositories are shallow-cloned into the cache and their exact source URL is retained. Landing pages, Google Drive folders, dataset portals requiring a geographic selection, and records with multiple large files are not misrepresented as downloaded assets; they remain `INPUT_REQUIRED` until a concrete file is selected.

Each pipeline must receive its compatible input: thermal video plus matching SRT for geolocation, ALS/LiDAR GeoTIFF for ADAF, DEM plus streams for procedural training data, RGB plus synchronized thermal for RGB-T fusion, `.tlog` for the ground station, and ROS2/Gazebo for the simulator. The executor invokes the original vendored repository entrypoint and stores both the raw upstream output and the normalized DRIFT record. A result is `COMPLETED` only when the upstream command exits successfully and its expected artifact exists.

The only permitted statuses are `COMPLETED`, `INPUT_REQUIRED`, `DEPENDENCY_REQUIRED`, `RUNTIME_REQUIRED`, and `FAILED`. No HTTP 200 response is treated as an acquired asset, and no generic detector is substituted for a missing upstream implementation. Secrets such as `GEMINI_API_KEY` are read only from the environment; they are never written to the catalog or provenance files.
