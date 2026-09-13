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
import { trpc } from "@/lib/trpc";

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

type Adapter = { adapterId: string; repository: string; model: string; executionStatus: string; reason: string; contribution: string; ran: boolean };
type MissionResult = { runId: string; findings: Array<{ label: string; confidence: number; source: { repository: string; model: string } }>; adapters: Adapter[]; fusion: { outputFindingCount: number } };
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
  const [enabled, setEnabled] = useState<Record<string, boolean>>(() => Object.fromEntries(modules.map((module) => [module.id, true])));
  const [result, setResult] = useState<MissionResult | null>(null);
  const [error, setError] = useState("");
  const activeCount = useMemo(() => Object.values(enabled).filter(Boolean).length, [enabled]);
  const runMutation = trpc.mission.run.useMutation();

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

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
        const rgbResponse = await fetch("/tdm/rgb-video.mp4");
        videoUri = await uploadMedia(await rgbResponse.blob(), "tdm-rgb-video.mp4");
        for (const [field, _label, filename] of tdmAssets) {
          const response = await fetch(`/tdm/${filename}`);
          tdmInput[field] = await uploadMedia(await response.blob(), `tdm-${filename}`);
        }
      } else {
        if (!selectedFile) throw new Error("Choose a video or select the TDM test pack");
        videoUri = await uploadMedia(selectedFile, selectedFile.name);
      }
      setStage("queued"); setProgress(22);
      const output = await runMutation.mutateAsync({ videoUri, fileName: tdmMode ? "tdm-rgb-video.mp4" : selectedFile!.name, thermalVideoUri: tdmMode ? tdmInput.thermalVideoUri : thermalMode ? videoUri : undefined, ...tdmInput, enabledModules: modules.filter((module) => enabled[module.id]).map((module) => module.id) }) as MissionResult;
      setResult(output); setStage("complete"); setProgress(100); setActiveTab("evidence");
    } catch (cause) {
      setStage("error"); setError(cause instanceof Error ? cause.message : "The worker could not complete this mission.");
    } finally { setRunning(false); }
  };

  const executed = result?.adapters.filter((adapter) => adapter.ran) ?? [];
  const visibleFindings = result?.findings ?? [];
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
          <div className="progress-sidebar"><div className="progress-title"><span>RUN PROGRESS</span><strong>{progress}%</strong></div><div className="progress-track"><div style={{ width: `${progress}%` }} /></div><ol>{["Input received", "Worker queued", "Repositories evaluated", "Findings normalized"].map((label, index) => { const done = progress >= [8, 22, 70, 100][index]; return <li key={label} className={done ? "done" : ""}><span>{done ? <Check size={10} /> : index + 1}</span>{label}</li>; })}</ol></div>
          <div className="rail-bottom"><div className="mini-stat"><span>FINDINGS</span><strong>{result?.findings.length ?? 0}</strong></div><div className="mini-stat"><span>EXECUTED</span><strong>{executed.length}/12</strong></div><div className="license-note"><ShieldCheck size={14} />Open-source runners<br /><span>ROS2 · ONNX · PyTorch</span></div></div>
        </aside>
        <section className="main-stage">
          <div className="stage-heading"><div><p className="eyebrow">MISSION CONTROL / {activeTab.toUpperCase()}</p><h2>{activeTab === "evidence" ? "Evidence, without the guesswork." : activeTab === "pipeline" ? "See every stage move." : "One video. Every lens."}</h2><p className="lede">{activeTab === "pipeline" ? "A live execution ledger for the worker, adapters, and input requirements." : "Every result below comes from the worker output. No simulated detections are rendered."}</p></div><div className="heading-id"><span>RUN ID</span><strong>{result?.runId?.slice(0, 12) ?? "PENDING"}</strong></div></div>
          <section className="ingest-card"><div className="ingest-copy"><div className="number-stamp">01</div><div><p className="eyebrow">INGEST</p><h3>{tdmMode ? "TDM synthetic mission pack" : file ? file.name : "Drop drone footage here"}</h3><p>{tdmMode ? "10 packaged test assets · synthetic fixtures, not field evidence" : file ? `${(file.size / (1024 * 1024)).toFixed(1)} MB · ready to upload to secure object storage` : "MP4, MOV, AVI · choose footage, then upload and run the real pipeline"}</p></div></div><div className="ingest-actions"><input ref={inputRef} type="file" accept="video/*" hidden onChange={(event) => handleFile(event.target.files?.[0])} /><button className={tdmMode ? "outline-button active" : "outline-button"} onClick={() => setTdmMode((value) => !value)}><Database size={16} />{tdmMode ? "TDM pack selected" : "Use TDM test pack"}</button><button className="outline-button" onClick={() => inputRef.current?.click()} disabled={tdmMode}><Upload size={16} />{file ? "Replace footage" : "Choose footage"}</button><button className={thermalMode ? "outline-button active" : "outline-button"} onClick={() => setThermalMode((value) => !value)}><Flame size={15} />{thermalMode ? "Thermal input on" : "Mark as thermal"}</button><button className="primary-button" disabled={(!file && !tdmMode) || running} onClick={runMission}><Play size={15} fill="currentColor" />{running ? "Uploading & running" : "Upload & run pipeline"}</button></div></section>
          <section className="module-strip"><div className="strip-label"><p className="eyebrow">02 / MODULES</p><span>{activeCount} enabled</span></div>{modules.map((module) => { const Icon = module.icon; const isOn = enabled[module.id]; return <button key={module.id} className={isOn ? "module-card on" : "module-card"} onClick={() => setEnabled((current) => ({ ...current, [module.id]: !current[module.id] }))}><div className="module-top"><Icon size={17} /><span className={isOn ? "toggle on" : "toggle"}>{isOn ? <Check size={10} /> : <X size={10} />}</span></div><strong>{module.label}</strong><small>{module.detail}</small><code>{statusFor(module.id)}</code></button>; })}</section>
          <section className="analysis-grid"><div className="viewer-panel"><div className="panel-head"><div><p className="eyebrow">03 / LIVE EVIDENCE</p><h3>Frame analysis</h3></div><span className="frame-counter"><Video size={13} /> {result ? `${result.findings.length} normalized findings` : "awaiting worker"}</span></div><div className="video-stage">{preview ? <video src={preview} controls muted className="uploaded-video" /> : <div className="empty-video"><FileVideo size={30} /><span>Preview appears here after upload</span><small>Real annotated output is written by the worker</small></div>}</div><div className="scrub"><span>0%</span><div className="scrub-line"><div style={{ width: `${progress}%` }} /></div><span>{progress}%</span></div></div>
            <div className="signal-panel"><div className="panel-head"><div><p className="eyebrow">04 / EXECUTION LEDGER</p><h3>{activeTab === "evidence" ? "Findings & provenance" : "Topic execution status"}</h3></div><span className="live-pill">{running ? "PROCESSING" : result ? "VERIFIED" : "STAGED"}</span></div><div className="signal-list">{activeTab === "evidence" && visibleFindings.length ? visibleFindings.map((finding, index) => <div className="signal-item" key={`${finding.label}-${index}`}><span className="signal-icon"><Radar size={15} /></span><div><strong>{finding.label}</strong><small>{finding.source.model} · provenance preserved</small></div><b>{finding.confidence.toFixed(2)}</b></div>) : result ? result.adapters.map((adapter) => <div className="signal-item" key={adapter.adapterId}><span className="signal-icon"><Database size={15} /></span><div><strong>{topicFor(adapter.adapterId)}</strong><small>{adapter.model} · {adapter.reason}</small></div><b className={adapter.ran ? "good" : "muted"}>{adapter.executionStatus}</b></div>) : <div className="signal-item"><span className="signal-icon"><Database size={15} /></span><div><strong>No worker result yet</strong><small>Upload input and run the actual pipeline</small></div><b>—</b></div>}</div><div className="signal-footer"><span><Database size={13} /> findings / provenance-preserved JSON</span><button className="download-button"><Download size={13} /> export bundle</button></div></div></section>
          {error && <div className="error-banner"><X size={15} /><span>{error}</span></div>}
          <section className="footer-run"><div className="run-status"><span className={running ? "pulse active" : stage === "error" ? "pulse error" : "pulse"} /><div><strong>{stageLabel}</strong><small>{result ? `${result.fusion.outputFindingCount} outputs fused; ${executed.length} repository execution records` : "The worker records exact repository, model, status, output, and contribution."}</small></div></div><div className="run-meter"><span>{progress}%</span><div><div style={{ width: `${progress}%` }} /></div></div></section>
        </section>
      </div><footer className="site-footer"><span>DRIFT v0.2 / execution-first pipeline</span><span><Sparkles size={13} /> no fabricated findings</span><a href="https://github.com/RidhimaKulashriz/unified-drift" target="_blank" rel="noreferrer">repository <ArrowUpRight size={13} /></a></footer>
    </main>
  );
}
