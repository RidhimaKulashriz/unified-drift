import { describe, expect, it } from "vitest";
import { DRIFT_MODULES, clampProgress, enabledModuleCount } from "../shared/drift";

describe("DRIFT orchestration contract", () => {
  it("declares the four requested analysis modules", () => {
    expect(DRIFT_MODULES.map((module) => module.id)).toEqual(["thermal", "fusion", "detection", "archaeology"]);
  });

  it("counts enabled modules by default and respects explicit disablement", () => {
    expect(enabledModuleCount({})).toBe(4);
    expect(enabledModuleCount({ archaeology: false, fusion: false })).toBe(2);
  });

  it("keeps progress inside the UI's 0–100 range", () => {
    expect(clampProgress(-10)).toBe(0);
    expect(clampProgress(42.6)).toBe(43);
    expect(clampProgress(140)).toBe(100);
  });
});
