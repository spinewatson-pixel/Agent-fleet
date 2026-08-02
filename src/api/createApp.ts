import express, { type Express } from "express";
import cors from "cors";
import path from "node:path";
import fs from "node:fs";
import { BuilderPipeline } from "../core/pipeline.js";
import { rejectMutation } from "../core/adapters/mutationGuard.js";
import { KNOWLEDGE_OBJECTS } from "../core/knowledge/knowledgeObjects.js";
import { MVP_CONFIG } from "../core/schemas/common.js";
import {
  JsonFileWorkspaceStore,
  defaultDataDir,
} from "../core/services/workspaceStore.js";

export interface AppBundle {
  app: Express;
  pipeline: BuilderPipeline;
  dataDir: string;
}

export function createApp(options?: { dataDir?: string }): AppBundle {
  const dataDir = options?.dataDir ?? defaultDataDir();
  const pipeline = new BuilderPipeline(new JsonFileWorkspaceStore(dataDir));
  const app = express();

  app.use(cors());
  app.use(express.json({ limit: "2mb" }));
  app.use(
    express.text({
      type: ["text/*", "application/yaml", "application/x-yaml"],
      limit: "2mb",
    }),
  );

  app.get("/api/health", (_req, res) => {
    res.json({
      ok: true,
      mode: MVP_CONFIG.operatingMode,
      llmEnabled: MVP_CONFIG.llmEnabled,
      mutationAllowed: false,
      dataDir,
    });
  });

  app.get("/api/config", (_req, res) => {
    res.json({ ...MVP_CONFIG, knowledgeObjectCount: KNOWLEDGE_OBJECTS.length });
  });

  app.get("/api/knowledge", (_req, res) => {
    res.json(KNOWLEDGE_OBJECTS);
  });

  app.get("/api/workspaces", async (_req, res) => {
    res.json(await pipeline.getStore().list());
  });

  app.post("/api/workspaces/import/demo", async (_req, res) => {
    try {
      const snap = await pipeline.importDemo();
      res.status(201).json(snap);
    } catch (err) {
      res.status(400).json({ error: errorMessage(err) });
    }
  });

  app.post("/api/workspaces/import", async (req, res) => {
    try {
      const body = req.body as
        | { content?: string; format?: "json" | "yaml"; label?: string }
        | string;
      if (typeof body === "string") {
        const snap = await pipeline.importRaw(body, {
          format: req.header("content-type")?.includes("yaml") ? "yaml" : undefined,
        });
        res.status(201).json(snap);
        return;
      }
      if (!body.content) {
        res.status(400).json({ error: "content required" });
        return;
      }
      const snap = await pipeline.importRaw(body.content, {
        format: body.format,
        label: body.label,
      });
      res.status(201).json(snap);
    } catch (err) {
      res.status(400).json({ error: errorMessage(err) });
    }
  });

  app.get("/api/workspaces/:id", async (req, res) => {
    const snap = await pipeline.getStore().get(req.params.id);
    if (!snap) {
      res.status(404).json({ error: "not found" });
      return;
    }
    res.json(snap);
  });

  app.put("/api/workspaces/:id/intent", async (req, res) => {
    try {
      const snap = await pipeline.updateIntent(req.params.id, req.body);
      res.json(snap);
    } catch (err) {
      res.status(400).json({ error: errorMessage(err) });
    }
  });

  app.post("/api/workspaces/:id/analyze", async (req, res) => {
    try {
      const snap = await pipeline.runAnalysis(req.params.id);
      res.json(snap);
    } catch (err) {
      res.status(400).json({ error: errorMessage(err) });
    }
  });

  app.post("/api/workspaces/:id/decision", async (req, res) => {
    try {
      const decision = req.body?.decision as "approved" | "rejected";
      if (decision !== "approved" && decision !== "rejected") {
        res.status(400).json({ error: "decision must be approved|rejected" });
        return;
      }
      const snap = await pipeline.approveAndExport(req.params.id, decision);
      res.json(snap);
    } catch (err) {
      res.status(400).json({ error: errorMessage(err) });
    }
  });

  app.get("/api/workspaces/:id/exports/:exportId", async (req, res) => {
    const snap = await pipeline.getStore().get(req.params.id);
    const artifact = snap?.exports.find((e) => e.id === req.params.exportId);
    if (!artifact) {
      res.status(404).json({ error: "export not found" });
      return;
    }
    if (req.query.format === "md") {
      res.type("text/markdown").send(artifact.markdown);
      return;
    }
    res.json(artifact);
  });

  app.post("/api/apply", (_req, res) => {
    try {
      rejectMutation(_req.body);
    } catch (err) {
      res.status(405).json({
        error: errorMessage(err),
        code: "MUTATION_REJECTED",
        mutationAllowed: false,
      });
    }
  });

  const webDist = path.resolve(process.cwd(), "dist/web");
  if (fs.existsSync(webDist)) {
    app.use(express.static(webDist));
    app.get("*", (req, res, next) => {
      if (req.path.startsWith("/api")) return next();
      res.sendFile(path.join(webDist, "index.html"));
    });
  }

  return { app, pipeline, dataDir };
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
