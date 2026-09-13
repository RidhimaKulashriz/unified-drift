import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Archive,
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleDot,
  Database,
  Download,
  FileVideo,
  Flame,
  Layers3,
  Play,
  Radar,
  ScanSearch,
  Settings2,
  ShieldCheck,
  Sparkles,
  Upload,
  Video,
  Waves,
  X,
} from "lucide-react";

const modules = [
  { id: "mustatil", label: "GIS AI workspace", repo: "Mustatil", icon: ScanSearch, detail: "images / GeoTIFF / satellite" },
  { id: "foundation-models-archaeology", label: "Zero-shot archaeology", repo: "Foundation Models Archaeology", icon: ScanSearch, detail: "satellite / LiDAR / notebooks" },
  { id: "adaf", label: "Archaeological features", repo: "ADAF", icon: ScanSearch, detail: "ALS / LiDAR / GeoTIFF" },
  { id: "arran", label: "Archaeology benchmark", repo: "Arran", icon: Activity, detail: "dataset evaluation" },
  { id: "simulated-training-data", label: "Synthetic training data", repo: "Simulated Training Data", icon: Layers3, detail: "DEM + stream vectors" },
  { id: "uav-thermal-person-geolocation", label: "Thermal GPS geolocation", repo: "UAV Thermal Person Geolocation", icon: Flame, detail: "thermal video + SRT" },
  { id: "drone-tracker", label: "Drone object tracking", repo: "Drone Tracker", icon: Radar, detail: "RGB video + tracking model" },
  { id: "aerial-thermal-detection", label: "Thermal aerial detection", repo: "Aerial Thermal Detection", icon: Flame, detail: "YOLOv12 + RT-DETRv2" },
  { id: "aerial-thermal-sar-detection-demo", label: "Thermal SAR comparison", repo: "Aerial Thermal SAR Demo", icon: Radar, detail: "dual thermal models" },
  { id: "rgbt-fusion-drone-sar", label: "RGB-T fusion", repo: "RGB-T Fusion Drone SAR", icon: Layers3, detail: "synchronized RGB + thermal" },
  { id: "ros2-disaster-robot-sim", label: "Disaster robot simulation", repo: "ROS2 Disaster Robot Simulator", icon: Activity, detail: "ROS2 + Gazebo" },
  { id: "drone-control-monitoring-system", label: "Drone ground station", repo: "Drone Control Monitoring", icon: Waves, detail: "MAVLink / telemetry" },
];

const demoSpecs: Record<string, { input: string; detects: string; mode: string; ready: boolean; source: string; preview?: string }> = {
  mustatil: { input: "GeoTIFF / satellite image", detects: "GIS workspace review; not video ML", mode: "Input-gated", ready: false, source: "https://github.com/tarekwasfy01/Mustatil-YOLO-AI-Model-Trainer-" },
  "foundation-models-archaeology": { input: "Satellite / LiDAR / notebook input", detects: "Archaeological feature analysis", mode: "Input-gated", ready: false, source: "https://github.com/juergenlandauer/FoundationModelsArchaeology" },
  adaf: { input: "ALS / LiDAR GeoTIFF", detects: "Archaeological features in terrain", mode: "Input-gated", ready: false, source: "https://github.com/EarthObservation/adaf" },
  arran: { input: "Arran benchmark dataset", detects: "Benchmark scoring, not video detection", mode: "Dataset", ready: false, source: "https://github.com/ickramer/Arran" },
  "simulated-training-data": { input: "DEM + stream vectors", detects: "Synthetic terrain/training outputs", mode: "Input-gated", ready: false, source: "https://github.com/NMC-CRS/simulated-training-data-for-archaeological-site-detection" },
  "uav-thermal-person-geolocation": { input: "Thermal video + DJI SRT", detects: "People in thermal imagery + GPS projection", mode: "Needs thermal/SRT", ready: false, source: "https://github.com/Gruzver/uav-thermal-person-geolocation" },
  "drone-tracker": { input: "RGB drone video + checkpoint", detects: "Objects / people tracking", mode: "Needs checkpoint", ready: false, source: "https://github.com/Gruzver/drone-tracker" },
  "aerial-thermal-detection": { input: "Thermal video", detects: "Thermal people/objects with YOLO/RT-DETR", mode: "Needs thermal", ready: false, source: "https://huggingface.co/collections/Kiuyha/aerial-thermal-sar-detection", preview: "https://raw.githubusercontent.com/kiuyha/Aerial-Thermal-Detection-RT-DETRv2-and-YOLOv12/HEAD/RT-DETRv2/val_batch0_pred.jpg" },
  "aerial-thermal-sar-detection-demo": { input: "Thermal image/video", detects: "Thermal SAR person detection", mode: "Needs thermal", ready: false, source: "https://huggingface.co/collections/Kiuyha/aerial-thermal-sar-detection", preview: "https://raw.githubusercontent.com/kiuyha/Aerial-Thermal-Detection-RT-DETRv2-and-YOLOv12/HEAD/YOLOv12/val_batch0_pred.jpg" },
  "rgbt-fusion-drone-sar": { input: "Synchronized RGB + thermal", detects: "RGB-T fused objects", mode: "Needs paired inputs", ready: false, source: "https://github.com/hiungn/RGBT-Fusion-Drone-SAR", preview: "https://raw.githubusercontent.com/hiungn/RGBT-Fusion-Drone-SAR/HEAD/docs/figures/Mid_Stage.png" },
  "ros2-disaster-robot-sim": { input: "ROS2 disaster-world simulation", detects: "Robot simulation state; not video ML", mode: "Simulator", ready: false, source: "https://github.com/newton-adhikari/ros2-disaster-robot-sim", preview: "https://raw.githubusercontent.com/newton-adhikari/ros2-disaster-robot-sim/HEAD/SystemArchitectureDisasterRobotics.jpg" },
  "drone-control-monitoring-system": { input: "MAVLink / telemetry log", detects: "Flight/telemetry events; not video ML", mode: "Telemetry", ready: false, source: "https://github.com/thuyminh2112/Drone-control-monitoring-system", preview: "https://raw.githubusercontent.com/thuyminh2112/Drone-control-monitoring-system/HEAD/docs/images/dashboard.png" },
};

const tdmAssets = [
  ["thermalVideoUri", "Thermal video", "thermal-video.mp4"],
  ["srtUri", "DJI SRT telemetry", "thermal-video.SRT"],
  ["rgbImageUri", "Synchronized RGB frame", "rgb-frame.jpg"],
  ["geotiffUri", "ALS/LiDAR GeoTIFF fixture", "terrain.tif"],
  ["demUri", "DEM fixture", "dem.tif"],
  ["streamsUri", "Stream vectors", "streams.geojson"],
  ["arranDataUri", "Arran benchmark fixture", "arran-data.json"],
  ["foundationInputUri", "Foundation archaeology input", "foundation-input.json"],
  ["telemetryUri", "Ground-station telemetry", "telemetry.json"],
] as const;

type Adapter = { adapterId: string; repository: string; model: string; executionStatus: string; reason: string; contribution: string; ran: boolean; artifact?: string; visualArtifactUri?: string; statistics?: Record<string, unknown>; findingRecords?: Array<Record<string, unknown>> };
type Finding = { label: string; confidence: number; source: { repository: string; model: string }; [key: string]: unknown };
type MissionResult = { runId: string; findings: Finding[]; adapters: Adapter[]; executions?: Array<Record<string, unknown>>; fusion: { outputFindingCount: number } };
type Tab = "overview" | "pipeline" | "evidence";
type Stage = "idle" | "uploading" | "queued" | "processing" | "complete" | "error";

async function uploadMedia(file: Blob, name: string) {
  const apiBase = (import.meta.env.VITE_DRIFT_API_URL || "https://drift-orchestrator.onrender.com").replace(/\/$/, "");
  const form = new FormData();
  form.append("file", file, name);
  const response = await fetch(`${apiBase}/v1/storage/upload-file`, { method: "POST", body: form });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Media upload failed (${response.status})`);
  return body.uri as string;
}

function storageUrl(uri?: string) {
  if (!uri) return "";
  const apiBase = (import.meta.env.VITE_DRIFT_API_URL || "https://drift-orchestrator.onrender.com").replace(/\/$/, "");
  if (!uri.startsWith("s3://")) return uri;
  const [, rest] = uri.split("s3://");
  const [, ...parts] = rest.split("/");
  return `${apiBase}/v1/storage/objects/${parts.map(encodeURIComponent).join("/")}`;
}

async function waitForWorker(runId: string, onProgress: (value: number, stage: Stage) => void) {
  const apiBase = (import.meta.env.VITE_DRIFT_API_URL || "https://drift-orchestrator.onrender.com").replace(/\/$/, "");
  const deadline = Date.now() + 15 * 60 * 1000;
  while (Date.now() < deadline) {
    const response = await fetch(`${apiBase}/v1/runs/${encodeURIComponent(runId)}`);
    const job = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(job.detail || `Worker status failed (${response.status})`);
    if (job.status === "completed") return { runId, ...job.results } as MissionResult;
    if (job.status === "failed") throw new Error(job.error || "Worker failed this mission");
    const progress = Math.max(0, Math.min(100, Math.round((Number(job.progress) || 0) * 100)));
    onProgress(progress, progress >= 70 ? "processing" : "queued");
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  throw new Error("The worker did not finish within 15 minutes");
}

async function queueMission(input: Record<string, unknown>) {
  const apiBase = (import.meta.env.VITE_DRIFT_API_URL || "https://drift-orchestrator.onrender.com").replace(/\/$/, "");
  const response = await fetch(`${apiBase}/api/trpc/mission.run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ json: input }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.error?.json?.message || payload?.detail || `Mission queue failed (${response.status})`);
  const queued = payload?.result?.data?.json;
  if (!queued?.runId) throw new Error("Mission queue returned no run ID");
  return queued as { runId: string };
}

const navItems: Array<{ id: Tab; icon: typeof Activity; text: string }> = [
  { id: "overview", icon: Activity, text: "Mission overview" },
  { id: "pipeline", icon: Waves, text: "Pipeline progress" },
  { id: "evidence", icon: Archive, text: "Evidence & findings" },
];

export default function Home() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<Stage>("idle");
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [thermalMode, setThermalMode] = useState(false);
  const [tdmMode, setTdmMode] = useState(false);
  const [demoVideoMode, setDemoVideoMode] = useState(false);
  const [executionMode, setExecutionMode] = useState<"real-upstream" | "rgb12" | "synthetic-demo">("real-upstream");
  const [tdmPipelineId, setTdmPipelineId] = useState("all");
  const [tdmAssetKey, setTdmAssetKey] = useState("all");
  const [enabled, setEnabled] = useState<Record<string, boolean>>(() => Object.fromEntries(modules.map((module) => [module.id, true])));
  const [result, setResult] = useState<MissionResult | null>(null);
  const [error, setError] = useState("");
  const [selectedAdapterId, setSelectedAdapterId] = useState<string | null>(null);
  const activeCount = useMemo(() => Object.values(enabled).filter(Boolean).length, [enabled]);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  useEffect(() => {
    const apiBase = (import.meta.env.VITE_DRIFT_API_URL || "https://drift-orchestrator.onrender.com").replace(/\/$/, "");
    fetch(`${apiBase}/v1/runs/latest`).then((response) => response.ok ? response.json() : null).then((job) => {
      if (!job?.results) return;
      const stored = { runId: job.run_id, ...job.results } as MissionResult;
      setResult(stored); setSelectedAdapterId(stored.adapters[0]?.adapterId ?? null); setProgress(100); setStage("complete"); setActiveTab("evidence");
    }).catch(() => undefined);
  }, []);

  const handleFile = (next: File | undefined) => {
    if (!next) return;
    if (preview) URL.revokeObjectURL(preview);
    setFile(next); setPreview(URL.createObjectURL(next)); setProgress(0); setStage("idle"); setResult(null); setError("");
  };

  const runMission = async () => {
    if ((!file && !tdmMode) || running) return;
    const selectedFile = file;
    setRunning(true); setError(""); setStage("uploading"); setProgress(8);
    try {
      let videoUri: string;
      const tdmInput: Record<string, string> = {};
      if (tdmMode) {
        const rgbResponse = await fetch(demoVideoMode ? "/tdm/delhi-collapse-demo.mp4" : "/tdm/rgb-video.mp4");
        videoUri = await uploadMedia(await rgbResponse.blob(), demoVideoMode ? "delhi-collapse-demo.mp4" : "tdm-rgb-video.mp4");
        for (const [field, _label, filename] of tdmAssets) {
          const response = await fetch(`/tdm/${filename}`);
          tdmInput[field] = await uploadMedia(await response.blob(), `tdm-${filename}`);
        }
      } else {
        if (!selectedFile) throw new Error("Choose a video or select the TDM test pack");
        videoUri = await uploadMedia(selectedFile, selectedFile.name);
      }
      setStage("queued"); setProgress(22);
      const enabledModules = tdmPipelineId === "all" ? modules.filter((module) => enabled[module.id]).map((module) => module.id) : [tdmPipelineId];
      const queued = await queueMission({ executionMode, tdmPipelineId, tdmAssetKey, videoUri, fileName: tdmMode ? (demoVideoMode ? "delhi-collapse-demo.mp4" : "tdm-rgb-video.mp4") : selectedFile!.name, thermalVideoUri: tdmMode ? tdmInput.thermalVideoUri : thermalMode ? videoUri : undefined, ...tdmInput, enabledModules });
      const output = await waitForWorker(queued.runId, (value, nextStage) => { setProgress(value); setStage(nextStage); });
      setResult(output); setSelectedAdapterId(output.adapters[0]?.adapterId ?? null); setStage("complete"); setProgress(100); setActiveTab("evidence");
    } catch (cause) {
      setStage("error"); setProgress(0); setError(cause instanceof Error ? cause.message : "The worker could not complete this mission.");
    } finally { setRunning(false); }
  };

  const executed = result?.adapters.filter((adapter) => adapter.ran) ?? [];
  const visibleFindings = result?.findings ?? [];
  const selectedAdapter = result?.adapters.find((adapter) => adapter.adapterId === selectedAdapterId) ?? result?.adapters[0];
  const selectedFindings = selectedAdapter ? visibleFindings.filter((finding) => {
    const source = finding.source?.repository?.toLowerCase() ?? "";
    return source.includes(selectedAdapter.repository.toLowerCase()) || selectedAdapter.repository.toLowerCase().includes(source);
  }) : visibleFindings;
  const detectionBoxes = selectedFindings.filter((finding) => Array.isArray(finding.bboxPixels)).slice(0, 40);
  const annotatedImageUrl = storageUrl(selectedAdapter?.visualArtifactUri);
  const visualAdapters = result?.adapters ?? [];
  const stageLabel = { idle: "Ready for input", uploading: "Preparing media", queued: "Queued for worker", processing: "Executing upstream code", complete: "Verified worker output", error: "Run needs attention" }[stage];
  const statusFor = (moduleId: string) => {
    if (!result) return running ? "QUEUED" : "STAGED";
    const match = result.adapters.find((item) => item.adapterId.toLowerCase().includes(moduleId.toLowerCase()));
    return match?.executionStatus ?? (enabled[moduleId] ? "NOT REPORTED" : "DISABLED");
  };
  const topicFor = (adapterId: string) => modules.find((module) => adapterId.toLowerCase().includes(module.id.toLowerCase()))?.label ?? adapterId;

  return (
    <main className="drift-shell">
      <header className="topbar"><div className="brand-lockup"><div className="brand-mark"><span /></div><div><p className="eyebrow">DRIFT / FIELD INTELLIGENCE</p><h1>Drone Reconnaissance &amp; Inference Fusion Terminal</h1></div></div><div className="top-actions"><span className="status-dot"><CircleDot size={13} /> REAL WORKER PIPELINE</span><button className="icon-button" aria-label="Settings"><Settings2 size={18} /></button></div></header>
      <div className="workspace-grid">
        <aside className="side-rail">
          <div className="rail-section"><p className="eyebrow">MISSION</p><p className="mission-name">UNNAMED / 001</p><span className="rail-meta">single video orchestration</span></div>
          <nav className="rail-nav" aria-label="Mission sections">{navItems.map((item) => <button key={item.id} className={activeTab === item.id ? "rail-link active" : "rail-link"} onClick={() => setActiveTab(item.id)}><item.icon size={16} />{item.text}<ChevronRight size={14} className="rail-chevron" /></button>)}</nav>
          <div className="adapter-sidebar"><p className="eyebrow">12 PIPELINES / VISUAL OUTPUTS</p>{modules.map((module) => { const adapter = result?.adapters.find((item) => item.adapterId.toLowerCase().includes(module.id.toLowerCase())); const status = adapter?.executionStatus ?? (running ? "QUEUED" : "READY"); const count = adapter?.findingRecords?.length ?? (adapter ? visibleFindings.filter((finding) => finding.source?.repository?.toLowerCase().includes(adapter.repository.toLowerCase())).length : 0); return <button key={module.id} className={selectedAdapter?.adapterId === adapter?.adapterId || (!result && selectedAdapterId === module.id) ? "adapter-link active" : "adapter-link"} onClick={() => { setSelectedAdapterId(adapter?.adapterId ?? module.id); setActiveTab("evidence"); }}><span><strong>{module.label}</strong><small>{status}</small></span><b>{count}</b></button>; })}</div>
          <div className="progress-sidebar"><div className="progress-title"><span>RUN PROGRESS</span><strong>{progress}%</strong></div><div className="progress-track"><div style={{ width: `${progress}%` }} /></div><ol>{["Input received", "Worker queued", "Repositories evaluated", "Findings normalized"].map((label, index) => { const done = progress >= [8, 22, 70, 100][index]; return <li key={label} className={done ? "done" : ""}><span>{done ? <Check size={10} /> : index + 1}</span>{label}</li>; })}</ol></div>
          <div className="rail-bottom"><div className="mini-stat"><span>FINDINGS</span><strong>{result?.findings.length ?? 0}</strong></div><div className="mini-stat"><span>EXECUTED</span><strong>{executed.length}/12</strong></div><div className="license-note"><ShieldCheck size={14} />Open-source runners<br /><span>ROS2 · ONNX · PyTorch</span></div></div>
        </aside>
        <section className="main-stage">
          <div className="stage-heading"><div><p className="eyebrow">MISSION CONTROL / {activeTab.toUpperCase()}</p><h2>{activeTab === "evidence" ? "Evidence, without the guesswork." : activeTab === "pipeline" ? "See every stage move." : "One video. Every lens."}</h2><p className="lede">{activeTab === "pipeline" ? "A live execution ledger for the worker, adapters, and input requirements." : "Every result below comes from the worker output. No simulated detections are rendered."}</p></div><div className="heading-id"><span>RUN ID</span><strong>{result?.runId?.slice(0, 12) ?? "PENDING"}</strong></div></div>
          <section className="ingest-card"><div className="ingest-copy"><div className="number-stamp">01</div><div><p className="eyebrow">INGEST</p><h3>{tdmMode ? (demoVideoMode ? "Delhi collapse demo video + TDM assets" : "TDM synthetic mission pack") : file ? file.name : "Drop drone footage here"}</h3><p>{tdmMode ? (demoVideoMode ? "60-second supplied demo clip · 10 companion test assets" : "10 packaged test assets · synthetic fixtures, not field evidence") : file ? `${(file.size / (1024 * 1024)).toFixed(1)} MB · ready to upload to secure object storage` : "MP4, MOV, AVI · choose footage, then upload and run the real pipeline"}</p></div></div><div className="ingest-actions"><select id="tdm-pipeline" name="tdmPipeline" className="outline-button" value={tdmPipelineId} onChange={(event) => setTdmPipelineId(event.target.value)} aria-label="TDM pipeline"><option value="all">TDM: all pipelines</option>{modules.map((module) => <option key={module.id} value={module.id}>{module.label}</option>)}</select><select id="tdm-asset" name="tdmAsset" className="outline-button" value={tdmAssetKey} onChange={(event) => setTdmAssetKey(event.target.value)} aria-label="TDM test asset"><option value="all">Asset: complete TDM pack</option>{tdmAssets.map(([field, label]) => <option key={field} value={field}>{label}</option>)}</select><select id="execution-mode" name="executionMode" className="outline-button" value={executionMode} onChange={(event) => setExecutionMode(event.target.value as typeof executionMode)} aria-label="Execution mode"><option value="real-upstream">Real upstream outputs</option><option value="rgb12">12 real RGB detectors</option><option value="synthetic-demo">Synthetic demo (labeled)</option></select><input id="video-file" name="videoFile" ref={inputRef} type="file" accept="video/*" hidden onChange={(event) => handleFile(event.target.files?.[0])} /><button className={tdmMode ? "outline-button active" : "outline-button"} onClick={() => setTdmMode((value) => !value)}><Database size={16} />{tdmMode ? "TDM pack selected" : "Use TDM test pack"}</button><button className={demoVideoMode ? "outline-button active" : "outline-button"} onClick={() => { setTdmMode(true); setDemoVideoMode((value) => !value); }}><Video size={16} />{demoVideoMode ? "Delhi demo selected" : "Use Delhi demo"}</button><button className="outline-button" onClick={() => inputRef.current?.click()} disabled={tdmMode}><Upload size={16} />{file ? "Replace footage" : "Choose footage"}</button><button className={thermalMode ? "outline-button active" : "outline-button"} onClick={() => setThermalMode((value) => !value)}><Flame size={15} />{thermalMode ? "Thermal input on" : "Mark as thermal"}</button><button className="primary-button" disabled={(!file && !tdmMode) || running} onClick={runMission}><Play size={15} fill="currentColor" />{running ? "Uploading & running" : "Upload & run pipeline"}</button></div></section>
          <section className="module-strip"><div className="strip-label"><p className="eyebrow">02 / MODULES</p><span>{activeCount} enabled</span></div>{modules.map((module) => { const Icon = module.icon; const isOn = enabled[module.id]; return <button key={module.id} className={isOn ? "module-card on" : "module-card"} onClick={() => setEnabled((current) => ({ ...current, [module.id]: !current[module.id] }))}><div className="module-top"><Icon size={17} /><span className={isOn ? "toggle on" : "toggle"}>{isOn ? <Check size={10} /> : <X size={10} />}</span></div><strong>{module.label}</strong><small>{module.detail}</small><code>{statusFor(module.id)}</code></button>; })}</section>
          <section className="demo-lab"><div className="gallery-heading"><div><p className="eyebrow">DEMO LAB / 12 PIPELINES</p><h3>What each repository can actually detect</h3></div><span>REAL INPUT CONTRACTS · NO FABRICATED FINDINGS</span></div><div className="demo-grid">{modules.map((module) => { const spec = demoSpecs[module.id]; return <article className="demo-card" key={module.id}>{spec.preview && <img className="demo-preview" src={spec.preview} alt={`${module.label} official sample output`} />}<div className="demo-card-top"><strong>{module.label}</strong><span className={spec.ready ? "demo-ready" : "demo-gated"}>{spec.mode}</span></div><p><b>Input:</b> {spec.input}</p><p><b>Output:</b> {spec.detects}</p>{spec.preview && <small className="demo-caption">Official upstream sample output; not this run</small>}<div className="demo-card-actions"><button className="outline-button" onClick={() => { setTdmPipelineId(module.id); setTdmMode(true); setActiveTab("pipeline"); }}>Select pipeline</button><a className="demo-source" href={spec.source} target="_blank" rel="noreferrer">official source ↗</a></div></article>; })}</div></section>
          {result && <section className="visual-gallery"><div className="gallery-heading"><div><p className="eyebrow">VISUAL OUTPUTS / ALL 12 REPOSITORIES</p><h3>Judge-ready evidence gallery</h3></div><span>{visualAdapters.filter((adapter) => adapter.visualArtifactUri).length}/12 annotated artifacts</span></div><div className="gallery-grid">{visualAdapters.map((adapter) => { const imageUrl = storageUrl(adapter.visualArtifactUri); const findingsForAdapter = visibleFindings.filter((finding) => finding.source?.repository?.toLowerCase().includes(adapter.repository.toLowerCase())); return <button key={adapter.adapterId} className={selectedAdapter?.adapterId === adapter.adapterId ? "visual-card active" : "visual-card"} onClick={() => { setSelectedAdapterId(adapter.adapterId); setActiveTab("evidence"); }}>{imageUrl ? <img src={imageUrl} alt={`${topicFor(adapter.adapterId)} annotated output`} /> : <div className="visual-empty"><Database size={20} /><span>No visual artifact</span><small>{adapter.reason || "Adapter returned no image output"}</small></div>}<div className="visual-card-meta"><strong>{topicFor(adapter.adapterId)}</strong><small>{adapter.executionStatus} · {findingsForAdapter.length} detections</small></div></button>; })}</div></section>}
          <section className="analysis-grid"><div className="viewer-panel"><div className="panel-head"><div><p className="eyebrow">03 / LIVE EVIDENCE</p><h3>{selectedAdapter ? `${topicFor(selectedAdapter.adapterId)} detection frame` : "Frame analysis"}</h3></div><span className="frame-counter"><Video size={13} /> {result ? `${selectedFindings.length} selected detections` : "awaiting worker"}</span></div><div className="video-stage">{preview ? <video src={preview} controls muted className="uploaded-video" /> : <div className="empty-video"><FileVideo size={30} /><span>Preview appears here after upload</span><small>Real annotated output is written by the worker</small></div>}{detectionBoxes.map((finding, index) => { const box = finding.bboxPixels as number[]; const [x1, y1, x2, y2] = box; return <div key={`${finding.label}-${index}`} className="detection-box" style={{ left: `${(x1 / 640) * 100}%`, top: `${(y1 / 360) * 100}%`, width: `${((x2 - x1) / 640) * 100}%`, height: `${((y2 - y1) / 360) * 100}%`, borderColor: "#d8f59c" }}><span>{finding.label} {Number(finding.confidence).toFixed(2)}</span></div>; })}{annotatedImageUrl && <img src={annotatedImageUrl} className="uploaded-video annotated-frame" alt={`${selectedAdapter ? topicFor(selectedAdapter.adapterId) : "ML"} annotated detection frame`} />}</div><div className="scrub"><span>0%</span><div className="scrub-line"><div style={{ width: `${progress}%` }} /></div><span>{progress}%</span></div></div>
            <div className="signal-panel"><div className="panel-head"><div><p className="eyebrow">04 / EXECUTION LEDGER</p><h3>{activeTab === "evidence" ? `${selectedAdapter ? topicFor(selectedAdapter.adapterId) : "Findings"} detections` : "Topic execution status"}</h3></div><span className="live-pill">{running ? "PROCESSING" : result ? "VERIFIED" : "STAGED"}</span></div><div className="signal-list">{activeTab === "evidence" && selectedFindings.length ? selectedFindings.map((finding, index) => <div className="signal-item" key={`${finding.label}-${index}`}><span className="signal-icon"><Radar size={15} /></span><div><strong>{finding.label}</strong><small>{finding.source.model} · {String(finding.source.repository)} · provenance preserved</small></div><b>{Number(finding.confidence).toFixed(2)}</b></div>) : result && selectedAdapter ? <div className="signal-item"><span className="signal-icon"><Database size={15} /></span><div><strong>{selectedAdapter.executionStatus}</strong><small>{selectedAdapter.reason || "No detection records returned by this adapter."}</small></div><b className={selectedAdapter.ran ? "good" : "muted"}>{selectedAdapter.findingRecords?.length ?? 0}</b></div> : result ? result.adapters.map((adapter) => <div className="signal-item" key={adapter.adapterId}><span className="signal-icon"><Database size={15} /></span><div><strong>{topicFor(adapter.adapterId)}</strong><small>{adapter.model} · {adapter.reason}</small></div><b className={adapter.ran ? "good" : "muted"}>{adapter.executionStatus}</b></div>) : <div className="signal-item"><span className="signal-icon"><Database size={15} /></span><div><strong>No worker result yet</strong><small>Upload input and run the actual pipeline</small></div><b>—</b></div>}</div><div className="signal-footer"><span><Database size={13} /> {selectedFindings.length} detections / provenance-preserved JSON</span><button className="download-button"><Download size={13} /> export bundle</button></div></div></section>
          {error && <div className="error-banner"><X size={15} /><span>{error}</span></div>}
          <section className="footer-run"><div className="run-status"><span className={running ? "pulse active" : stage === "error" ? "pulse error" : "pulse"} /><div><strong>{stageLabel}</strong><small>{result ? `${result.fusion.outputFindingCount} outputs fused; ${executed.length} repository execution records` : "The worker records exact repository, model, status, output, and contribution."}</small></div></div><div className="run-meter"><span>{progress}%</span><div><div style={{ width: `${progress}%` }} /></div></div></section>
        </section>
      </div><footer className="site-footer"><span>DRIFT v0.2 / execution-first pipeline</span><span><Sparkles size={13} /> no fabricated findings</span><a href="https://github.com/RidhimaKulashriz/unified-drift" target="_blank" rel="noreferrer">repository <ArrowUpRight size={13} /></a></footer>
    </main>
  );
}
