import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";
import { z } from "zod";

const ORCHESTRATOR_URL = process.env.DRIFT_ORCHESTRATOR_URL ?? "https://drift-orchestrator.onrender.com";

async function submitToOrchestrator(input: { videoBase64: string; fileName: string; thermalVideoBase64?: string }) {
  const response = await fetch(`${ORCHESTRATOR_URL}/v1/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_base64: input.videoBase64,
      video_file_name: input.fileName,
      thermal_video_base64: input.thermalVideoBase64,
      thermal_video_file_name: input.thermalVideoBase64 ? `thermal-${input.fileName}` : undefined,
    }),
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`Orchestrator ${response.status}: ${text}`);
  return JSON.parse(text) as { run_id: string; status: string };
}

async function waitForRun(runId: string) {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    const response = await fetch(`${ORCHESTRATOR_URL}/v1/runs/${encodeURIComponent(runId)}`);
    if (!response.ok) throw new Error(`Run status ${response.status}: ${await response.text()}`);
    const job = await response.json() as any;
    if (job.status === "completed") return job.results ?? job;
    if (job.status === "failed") throw new Error(job.error ?? "Remote worker failed");
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  return { runId, status: "queued", findings: [], adapters: [], fusion: { outputFindingCount: 0 } };
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
      videoBase64: z.string().min(10),
      fileName: z.string().min(1).max(160),
      thermalVideoBase64: z.string().optional(),
    })).mutation(async ({ input }) => {
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
