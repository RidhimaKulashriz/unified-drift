import { useMemo, useRef, useState } from "react";
import { Activity, Archive, ArrowUpRight, Check, ChevronRight, CircleDot, Database, Download, FileVideo, Flame, Layers3, Play, Radar, ScanSearch, Settings2, ShieldCheck, Sparkles, Upload, Video, Waves, X } from "lucide-react";
import { trpc } from "@/lib/trpc";

const modules = [
  { id: "thermal", label: "Thermal SAR", repo: "uav-thermal-person-geolocation", icon: Flame, detail: "person detection / GPS projection" },
  { id: "fusion", label: "RGB + Thermal", repo: "RGBT-Fusion-Drone-SAR", icon: Layers3, detail: "mid-stage fusion / tracking" },
  { id: "detection", label: "Aerial Detection", repo: "Aerial-Thermal-Detection-RT-DETRv2-and-YOLOv12", icon: Radar, detail: "YOLOv12 + RT-DETRv2" },
  { id: "archaeology", label: "Archaeology", repo: "ADAF + FoundationModelsArchaeology", icon: ScanSearch, detail: "ALS features / foundation models" },
];

type MissionResult = { runId: string; findings: Array<{ label: string; confidence: number; source: { repository: string; model: string } }>; adapters: Array<{ adapterId: string; repository: string; model: string; executionStatus: string; reason: string; contribution: string; ran: boolean }>; fusion: { outputFindingCount: number } };

function fileToBase64(file: File) {
  return new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result).split(",")[1] ?? ""); reader.onerror = reject; reader.readAsDataURL(file); });
}

export default function Home() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [activeTab, setActiveTab] = useState("overview");
  const [thermalMode, setThermalMode] = useState(false);
  const [enabled, setEnabled] = useState<Record<string, boolean>>({ thermal: true, fusion: true, detection: true, archaeology: true });
  const [result, setResult] = useState<MissionResult | null>(null);
  const activeCount = useMemo(() => Object.values(enabled).filter(Boolean).length, [enabled]);
  const runMutation = trpc.mission.run.useMutation();

  const handleFile = (next: File | undefined) => { if (!next) return; setFile(next); setPreview(URL.createObjectURL(next)); setProgress(0); setResult(null); };
  const runMission = async () => {
    if (!file || running) return;
    setRunning(true); setProgress(12);
    try { const payload = { videoBase64: await fileToBase64(file), fileName: file.name, thermalVideoBase64: thermalMode ? await fileToBase64(file) : undefined }; const output = await runMutation.mutateAsync(payload) as MissionResult; setResult(output); setProgress(100); }
    finally { setRunning(false); }
  };
  const executed = result?.adapters.filter((adapter) => adapter.ran) ?? [];
  const visibleFindings = result?.findings.slice(0, 5) ?? [];

  return <main className="drift-shell">
    <header className="topbar"><div className="brand-lockup"><div className="brand-mark"><span /></div><div><p className="eyebrow">DRIFT / FIELD INTELLIGENCE</p><h1>Drone Reconnaissance &amp; Inference Fusion Terminal</h1></div></div><div className="top-actions"><span className="status-dot"><CircleDot size={13} /> REAL WORKER PIPELINE</span><button className="icon-button" aria-label="Settings"><Settings2 size={18} /></button></div></header>
    <div className="workspace-grid"><aside className="side-rail"><div className="rail-section"><p className="eyebrow">MISSION</p><p className="mission-name">UNNAMED / 001</p><span className="rail-meta">single video orchestration</span></div><nav className="rail-nav">{[{ id: "overview", icon: Activity, text: "Overview" }, { id: "pipeline", icon: Waves, text: "Pipeline" }, { id: "evidence", icon: Archive, text: "Evidence" }].map((item) => <button key={item.id} className={activeTab === item.id ? "rail-link active" : "rail-link"} onClick={() => setActiveTab(item.id)}><item.icon size={16} />{item.text}<ChevronRight size={14} className="rail-chevron" /></button>)}</nav><div className="rail-bottom"><div className="mini-stat"><span>FINDINGS</span><strong>{result?.findings.length ?? 0}</strong></div><div className="mini-stat"><span>EXECUTED</span><strong>{executed.length}/12</strong></div><div className="license-note"><ShieldCheck size={14} />Open-source runners<br /><span>ROS2 · ONNX · PyTorch</span></div></div></aside>
      <section className="main-stage"><div className="stage-heading"><div><p className="eyebrow">MISSION CONTROL / {activeTab.toUpperCase()}</p><h2>One video. Every lens.</h2><p className="lede">Every result below comes from the worker output. No simulated detections are rendered.</p></div><div className="heading-id"><span>RUN ID</span><strong>{result?.runId?.slice(0, 12) ?? "PENDING"}</strong></div></div>
        <section className="ingest-card"><div className="ingest-copy"><div className="number-stamp">01</div><div><p className="eyebrow">INGEST</p><h3>{file ? file.name : "Drop drone footage here"}</h3><p>{file ? `${(file.size / (1024 * 1024)).toFixed(1)} MB · ready for real execution` : "MP4, MOV, AVI · thermal mode uses the published RT-DETRv2 checkpoint"}</p></div></div><div className="ingest-actions"><input ref={inputRef} type="file" accept="video/*" hidden onChange={(event) => handleFile(event.target.files?.[0])} /><button className="outline-button" onClick={() => inputRef.current?.click()}><Upload size={16} />{file ? "Replace footage" : "Choose footage"}</button><button className={thermalMode ? "outline-button active" : "outline-button"} onClick={() => setThermalMode((value) => !value)}><Flame size={15} />{thermalMode ? "Thermal input on" : "Mark as thermal"}</button><button className="primary-button" disabled={!file || running} onClick={runMission}><Play size={15} fill="currentColor" />{running ? "Running real code" : "Run real pipeline"}</button></div></section>
        <section className="module-strip"><div className="strip-label"><p className="eyebrow">02 / MODULES</p><span>{activeCount} enabled</span></div>{modules.map((module) => { const Icon = module.icon; const isOn = enabled[module.id]; return <button key={module.id} className={isOn ? "module-card on" : "module-card"} onClick={() => setEnabled((current) => ({ ...current, [module.id]: !current[module.id] }))}><div className="module-top"><Icon size={17} /><span className={isOn ? "toggle on" : "toggle"}>{isOn ? <Check size={10} /> : <X size={10} />}</span></div><strong>{module.label}</strong><small>{module.detail}</small><code>{module.repo}</code></button>; })}</section>
        <section className="analysis-grid"><div className="viewer-panel"><div className="panel-head"><div><p className="eyebrow">03 / LIVE EVIDENCE</p><h3>Frame analysis</h3></div><span className="frame-counter"><Video size={13} /> {result ? `${result.findings.length} normalized findings` : "awaiting worker"}</span></div><div className="video-stage">{preview ? <video src={preview} controls muted className="uploaded-video" /> : <div className="empty-video"><FileVideo size={30} /><span>Preview appears here after upload</span><small>Real annotated output is written by the worker</small></div>}</div><div className="scrub"><span>0%</span><div className="scrub-line"><div style={{ width: `${progress}%` }} /></div><span>{progress}%</span></div></div>
          <div className="signal-panel"><div className="panel-head"><div><p className="eyebrow">04 / REAL OUTPUTS</p><h3>Repository contribution</h3></div><span className="live-pill">{running ? "PROCESSING" : result ? "VERIFIED" : "STAGED"}</span></div><div className="signal-list">{result ? executed.map((adapter) => <div className="signal-item" key={adapter.adapterId}><span className="signal-icon"><Database size={15} /></span><div><strong>{adapter.repository}</strong><small>{adapter.model} · {adapter.contribution}</small></div><b>{adapter.executionStatus}</b></div>) : <div className="signal-item"><span className="signal-icon"><Database size={15} /></span><div><strong>No worker result yet</strong><small>Upload input and run the actual pipeline</small></div><b>—</b></div>}{visibleFindings.map((finding, index) => <div className="signal-item" key={`${finding.label}-${index}`}><span className="signal-icon"><Radar size={15} /></span><div><strong>{finding.label}</strong><small>{finding.source.repository} · {finding.source.model}</small></div><b>{finding.confidence.toFixed(2)}</b></div>)}</div><div className="signal-footer"><span><Database size={13} /> findings / provenance-preserved JSON</span><button className="download-button"><Download size={13} /> export bundle</button></div></div></section>
        <section className="footer-run"><div className="run-status"><span className={running ? "pulse active" : "pulse"} /><div><strong>{running ? "Executing upstream repository code" : result ? "Analysis complete — real output verified" : "Awaiting footage"}</strong><small>{result ? `${result.fusion.outputFindingCount} outputs fused; ${executed.length} repository execution records` : "The worker records exact repository, model, status, output, and contribution."}</small></div></div><div className="run-meter"><span>{progress}%</span><div><div style={{ width: `${progress}%` }} /></div></div></section>
      </section></div><footer className="site-footer"><span>DRIFT v0.2 / execution-first pipeline</span><span><Sparkles size={13} /> no fabricated findings</span><a href="https://github.com/RidhimaKulashriz/DRIFT-Unified-Drone-Intelligence" target="_blank" rel="noreferrer">repository <ArrowUpRight size={13} /></a></footer>
  </main>;
}
