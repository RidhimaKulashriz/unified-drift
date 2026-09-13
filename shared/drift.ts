export type DriftModuleId = "thermal" | "fusion" | "detection" | "archaeology";

export type DriftModule = {
  id: DriftModuleId;
  label: string;
  runner: string;
  input: "video" | "rgb-thermal" | "als";
  output: string[];
};

export const DRIFT_MODULES: DriftModule[] = [
  { id: "thermal", label: "Thermal SAR", runner: "uav-thermal-person-geolocation", input: "video", output: ["person", "track", "gps"] },
  { id: "fusion", label: "RGB + Thermal", runner: "RGBT-Fusion-Drone-SAR", input: "rgb-thermal", output: ["person", "track", "gps"] },
  { id: "detection", label: "Aerial Detection", runner: "Aerial-Thermal-Detection-RT-DETRv2-and-YOLOv12", input: "video", output: ["detection", "annotated-video"] },
  { id: "archaeology", label: "Archaeology", runner: "ADAF + FoundationModelsArchaeology", input: "als", output: ["site-candidate", "geojson"] },
];

export const clampProgress = (value: number) => Math.max(0, Math.min(100, Math.round(value)));

export const enabledModuleCount = (selection: Partial<Record<DriftModuleId, boolean>>) =>
  DRIFT_MODULES.reduce((count, module) => count + (selection[module.id] !== false ? 1 : 0), 0);
