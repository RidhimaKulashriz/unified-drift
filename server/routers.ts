import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";
import { z } from "zod";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

async function runWorker(input: { videoBase64: string; fileName: string; thermalVideoBase64?: string }) {
  const root = path.resolve(process.cwd());
  const jobDir = await fs.mkdtemp(path.join(os.tmpdir(), "drift-mission-"));
  const videoPath = path.join(jobDir, input.fileName.replace(/[^a-zA-Z0-9._-]/g, "_"));
  const outputDir = path.join(jobDir, "output");
  await fs.writeFile(videoPath, Buffer.from(input.videoBase64, "base64"));
  const args = [path.join(root, "services/worker/run_pipeline.py"), videoPath, outputDir];
  if (input.thermalVideoBase64) {
    const thermalPath = path.join(jobDir, "thermal-" + path.basename(videoPath));
    await fs.writeFile(thermalPath, Buffer.from(input.thermalVideoBase64, "base64"));
    args.push("--thermal-video", thermalPath);
  }
  await execFileAsync("python3", args, { cwd: root, maxBuffer: 10 * 1024 * 1024 });
  return JSON.parse(await fs.readFile(path.join(outputDir, "run.json"), "utf8"));
}

export const appRouter = router({
    // if you need to use socket.io, read and register route in server/_core/index.ts, all api should start with '/api/' so that the gateway can route correctly
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),
  mission: router({
    run: publicProcedure.input(z.object({
      videoBase64: z.string().min(10),
      fileName: z.string().min(1).max(160),
      thermalVideoBase64: z.string().optional(),
    })).mutation(({ input }) => runWorker(input)),
  }),

  // TODO: add feature routers here, e.g.
  // todo: router({
  //   list: protectedProcedure.query(({ ctx }) =>
  //     db.getUserTodos(ctx.user.id)
  //   ),
  // }),
});

export type AppRouter = typeof appRouter;
