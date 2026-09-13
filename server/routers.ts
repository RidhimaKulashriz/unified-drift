import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";
import { z } from "zod";

const ORCHESTRATOR_URL = process.env.DRIFT_ORCHESTRATOR_URL ?? "https://drift-orchestrator.onrender.com";

async function submitToOrchestrator(input: Record<string, unknown> & { fileName: string }) {
  const response = await fetch(`${ORCHESTRATOR_URL}/v1/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_base64: input.videoBase64,
      video_uri: input.videoUri,
      execution_mode: input.executionMode,
      video_file_name: input.fileName,
      thermal_video_base64: input.thermalVideoBase64,
      thermal_video_uri: input.thermalVideoUri,
      rgb_image_uri: input.rgbImageUri,
      image_uri: input.imageUri,
      srt_uri: input.srtUri,
      telemetry_uri: input.telemetryUri,
      mavlink_uri: input.mavlinkUri,
      geotiff_uri: input.geotiffUri,
      als_uri: input.alsUri,
      dem_uri: input.demUri,
      streams_uri: input.streamsUri,
      arran_data_uri: input.arranDataUri,
      foundation_input_uri: input.foundationInputUri,
      robot_simulation_uri: input.robotSimulationUri,
      thermal_video_file_name: input.thermalVideoBase64 ? `thermal-${input.fileName}` : undefined,
      enabled_modules: input.enabledModules ?? [],
    }),
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`Orchestrator ${response.status}: ${text}`);
  return JSON.parse(text) as { run_id: string; status: string };
}

async function waitForRun(runId: string) {
  const deadline = Date.now() + 10 * 60 * 1000;
  while (Date.now() < deadline) {
    const response = await fetch(`${ORCHESTRATOR_URL}/v1/runs/${encodeURIComponent(runId)}`);
    if (!response.ok) throw new Error(`Run status ${response.status}: ${await response.text()}`);
    const job = await response.json() as any;
    if (job.status === "completed") return job.results ?? job;
    if (job.status === "failed") throw new Error(job.error ?? "Remote worker failed");
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  throw new Error("The worker is still processing this mission after 10 minutes. Check the run in the orchestrator before retrying.");
}

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return { success: true } as const;
    }),
  }),
  mission: router({
    run: publicProcedure.input(z.object({
      videoBase64: z.string().min(10).optional(),
      videoUri: z.string().min(1).optional(),
      executionMode: z.enum(["real-upstream", "rgb12", "synthetic-demo"]).optional(),
      fileName: z.string().min(1).max(160),
      thermalVideoBase64: z.string().optional(),
      thermalVideoUri: z.string().min(1).optional(),
      rgbImageUri: z.string().min(1).optional(),
      imageUri: z.string().min(1).optional(),
      srtUri: z.string().min(1).optional(),
      telemetryUri: z.string().min(1).optional(),
      mavlinkUri: z.string().min(1).optional(),
      geotiffUri: z.string().min(1).optional(),
      alsUri: z.string().min(1).optional(),
      demUri: z.string().min(1).optional(),
      streamsUri: z.string().min(1).optional(),
      arranDataUri: z.string().min(1).optional(),
      foundationInputUri: z.string().min(1).optional(),
      robotSimulationUri: z.string().min(1).optional(),
      enabledModules: z.array(z.string()).optional(),
    }).refine(input => Boolean(input.videoBase64 || input.videoUri), { message: "videoUri or videoBase64 is required" })).mutation(async ({ input }) => {
      const queued = await submitToOrchestrator(input);
      const results = await waitForRun(queued.run_id);
      return {
        runId: queued.run_id,
        ...results,
      };
    }),
  }),
});

export type AppRouter = typeof appRouter;
