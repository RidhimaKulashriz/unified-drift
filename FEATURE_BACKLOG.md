# DRIFT Advanced Feature Backlog

This backlog captures the requested advanced intelligence capabilities. It is intentionally treated as a phased roadmap: features that need only the existing video pipeline come first, while multi-drone coordination, autonomous flight, external maps, and safety-critical decisions require separate services, telemetry, or human approval.

## Phase 1 — Evidence and detection foundation

Video ingestion, multi-camera fusion, person/vehicle/animal counting, cross-camera tracking, keyframe extraction, evidence clips, annotated video, event bookmarking, confidence maps, detection-density maps, image-quality scoring, thermal hotspot clustering, night-time detection, low-visibility detection, pixel-to-ground projection, GPS confidence, automatic FOV estimation, camera calibration, evidence provenance, model ensemble voting, model fallback, uncertainty display, automatic GIS/evidence packages, and natural-language mission queries.

## Phase 2 — Search, rescue, safety, and incident intelligence

Victim ranking, posture classification, heat-signature ranking, fall detection, fight/incident detection, loitering, running-person detection, restricted-area intrusion, perimeter breach, left-behind object detection, pickup and handover detection, crowd flow, abnormal behavior, threat scoring, alert prioritization, dynamic risk/search/survivor maps, evidence deduplication, temporal/spatial evidence weighting, mission confidence/readiness scores, SAR reports, executive summaries, mission briefings, and mission debriefs.

## Phase 3 — Infrastructure and disaster assessment

Traffic flow and anomalies, road blockage, accident and collision detection, wrong-way movement, stopped-vehicle detection, speed/direction estimation, lane occupancy, road-condition scoring, pothole and crack detection, bridge inspection, structural crack mapping, building damage grading, roof damage, collapse and debris classification, fire progression, smoke density, flood depth/boundary, water-level change, landslide and rockfall boundaries, terrain instability, and infrastructure inspection reports.

## Phase 4 — Geospatial and archaeology intelligence

Archaeology probability maps, site clustering, ancient-road/wall detection, geometric and buried-structure candidates, surface/vegetation/soil/shadow anomalies, historical imagery comparison, satellite + drone fusion, SAR + drone fusion, RGB + thermal + satellite fusion, DEM/elevation fusion, terrain-aware geolocation, archaeology survey reports, and automatic GIS packages. These require ALS/LiDAR, GeoTIFF, satellite, SAR, DEM, or historical imagery inputs; an ordinary RGB video is not sufficient.

## Phase 5 — Mission planning and autonomous operations

Automatic and dynamic geofencing, no-fly-zone awareness, safe-route generation, emergency and rescue route planning, search-path and area-coverage optimization, next-best-view and next-best-drone-position recommendations, autonomous inspection planning, revisit recommendations, multi-drone fusion, flight-path anomaly detection, drone drift detection, GPS spoofing detection, telemetry anomaly detection, and autonomous mission state management. These features require live telemetry, airspace data, vehicle control authority, and explicit human-safety gates.

## Phase 6 — Learning, reasoning, and mission memory

Long-term object memory, cross-mission re-identification, active learning from corrections, hard-example collection, continuous model evaluation, model comparison, confidence calibration, model/data/input drift detection, detection-distribution drift, explainable model disagreement, evidence-weighted decisions, causal event chains, impact propagation, root-cause candidates, hypothesis generation/ranking, contradiction analysis, source/sensor reliability ranking, immutable audit trails, mission snapshots, historical replay, time-travel intelligence, T-1/T-7/T-30 comparisons, event/asset/mission relationship graphs, cross-mission knowledge graphs, graph anomaly/impact analysis, information-gap detection, missing-sensor/telemetry/coverage detection, evidence completeness, search effectiveness scoring, and voice-free command-console queries.

## Delivery rule

The dashboard may expose these as capability flags, but a feature is only marked **live** after its adapter has a runnable implementation, test fixture, required model weights or data source, normalized output contract, and a safe failure state.

## Full requested feature list

- Real-time multi-camera fusion
- Multi-drone fusion
- Cross-camera person tracking
- Cross-camera vehicle tracking
- Cross-mission re-identification
- Long-term object memory
- Person behavior analysis
- Vehicle behavior analysis
- Crowd flow analysis
- Abnormal behavior detection
- Loitering detection
- Running-person detection
- Fall detection
- Fight/incident detection
- Restricted-area intrusion
- Perimeter breach detection
- Object left-behind detection
- Object pickup detection
- Object handover detection
- Convoy detection
- Vehicle counting
- Person counting
- Animal counting
- Crowd density estimation
- Queue detection
- Traffic flow analysis
- Traffic anomaly detection
- Road blockage detection
- Accident detection
- Wrong-way movement detection
- Near-collision detection
- Collision detection
- Stopped-vehicle detection
- Speed estimation
- Direction estimation
- Lane occupancy
- Road condition scoring
- Pothole severity estimation
- Crack detection
- Bridge inspection
- Structural crack mapping
- Building damage grading
- Roof damage detection
- Collapse detection
- Debris classification
- Fire progression tracking
- Smoke density estimation
- Flood depth estimation
- Flood boundary extraction
- Water-level change detection
- Landslide boundary detection
- Terrain instability detection
- Rockfall detection
- Search-and-rescue victim ranking
- Victim posture classification
- Heat-signature ranking
- Thermal hotspot clustering
- Night-time person detection
- Low-visibility detection
- Fog-aware detection
- Rain-aware detection
- Image-quality scoring
- Automatic enhancement
- Super-resolution preprocessing
- Blur-aware frame selection
- Best-evidence frame extraction
- Automatic keyframe generation
- Video summarization
- Incident video summarization
- Evidence clip extraction
- Automatic highlight reel
- Event bookmarking
- Event severity escalation
- Alert prioritization
- Multi-level threat scoring
- Dynamic risk map
- Dynamic confidence map
- Dynamic uncertainty map
- Detection density map
- Object movement heatmap
- Search probability map
- Survivor probability map
- Archaeology probability map
- Archaeological site clustering
- Ancient-road detection
- Ancient-wall detection
- Geometric structure detection
- Buried-structure candidate detection
- Surface anomaly detection
- Vegetation anomaly detection
- Soil anomaly detection
- Shadow anomaly detection
- Historical imagery comparison
- Satellite + drone fusion
- SAR + drone fusion
- RGB + thermal + satellite fusion
- DEM/elevation fusion
- Terrain-aware geolocation
- GPS confidence estimation
- GPS anomaly detection
- GPS spoofing detection
- Telemetry anomaly detection
- Flight-path anomaly detection
- Drone drift detection
- Camera calibration
- Automatic FOV estimation
- Pixel-to-ground projection
- Ground footprint estimation
- Object-to-coordinate projection
- Coordinate uncertainty radius
- Automatic geofencing
- Dynamic geofencing
- No-fly-zone awareness
- Safe-route generation
- Emergency-route planning
- Rescue route optimization
- Search-path optimization
- Area coverage optimization
- Next-best-view recommendation
- Next-best-drone-position recommendation
- Autonomous inspection planning
- Revisit recommendation
- Active learning from operator corrections
- Automatic hard-example collection
- Continuous model evaluation
- Model performance comparison
- Model ensemble voting
- Model fallback
- Model confidence calibration
- Drift detection between models
- Data-drift detection
- Input-quality drift
- Detection-distribution drift
- Explainable model disagreement
- Evidence-weighted decisions
- Causal event chains
- Impact propagation
- Root-cause candidate detection
- Hypothesis generation
- Hypothesis ranking
- Evidence contradiction analysis
- Evidence reliability scoring
- Source reliability ranking
- Sensor reliability ranking
- Temporal evidence weighting
- Spatial evidence weighting
- Automatic evidence deduplication
- Evidence provenance tracking
- Immutable mission audit trail
- Full mission state snapshots
- Historical state replay
- Time-travel intelligence
- T−1/T−7/T−30 comparisons
- Event dependency graph
- Asset relationship graph
- Mission relationship graph
- Cross-mission knowledge graph
- Graph centrality analysis
- Graph anomaly detection
- Graph impact analysis
- Information-gap detection
- Missing-sensor detection
- Missing-telemetry detection
- Missing-coverage detection
- Evidence completeness score
- Mission confidence score
- Mission readiness score
- Search effectiveness score
- Automatic executive summary
- Automatic incident report
- Automatic SAR report
- Automatic archaeology survey report
- Automatic infrastructure inspection report
- Automatic GIS package
- Automatic evidence package
- Automatic annotated video
- Automatic evidence clips
- Automatic map snapshots
- Automatic mission briefing
- Automatic mission debrief
- Voice-free command console
- Natural-language mission queries
- “Show every person”
- “Show highest-risk area”
- “Show what changed”
- “Show uncertain detections”
- “Show evidence for Track 17”
- “Where should the drone search next?”
- “Which detection has strongest evidence?”
- “Which models disagree?”
- “What was missed?”
- “What changed since last flight?”
