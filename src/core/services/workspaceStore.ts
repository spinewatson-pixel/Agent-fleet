import fs from "node:fs";
import path from "node:path";
import type {
  CanonicalOrganization,
  ChangeSet,
  IntentProfile,
} from "../schemas/entities.js";
import { nowIso } from "../util/ids.js";

export interface ExportArtifact {
  id: string;
  changeSetId: string;
  createdAt: string;
  markdown: string;
  json: unknown;
}

export interface WorkspaceSnapshot {
  organizationId: string;
  canonical: CanonicalOrganization;
  intent?: IntentProfile;
  importValidation?: unknown;
  gapAnalysis?: unknown;
  candidates?: unknown;
  validationResults?: unknown;
  reviewResults?: unknown;
  recommendation?: unknown;
  changeHistory: ChangeSet[];
  exports: ExportArtifact[];
  updatedAt: string;
}

export interface WorkspaceStore {
  list(): Promise<{ organizationId: string; name: string; updatedAt: string }[]>;
  get(organizationId: string): Promise<WorkspaceSnapshot | null>;
  save(snapshot: WorkspaceSnapshot): Promise<void>;
  appendChange(organizationId: string, change: ChangeSet): Promise<void>;
  appendExport(organizationId: string, artifact: ExportArtifact): Promise<void>;
  clearAll(): Promise<void>;
}

export class JsonFileWorkspaceStore implements WorkspaceStore {
  constructor(private readonly rootDir: string) {
    fs.mkdirSync(rootDir, { recursive: true });
  }

  private fileFor(id: string): string {
    return path.join(this.rootDir, `${id}.json`);
  }

  async list(): Promise<{ organizationId: string; name: string; updatedAt: string }[]> {
    const files = fs.readdirSync(this.rootDir).filter((f) => f.endsWith(".json"));
    const out: { organizationId: string; name: string; updatedAt: string }[] = [];
    for (const file of files) {
      const raw = JSON.parse(fs.readFileSync(path.join(this.rootDir, file), "utf8")) as WorkspaceSnapshot;
      out.push({
        organizationId: raw.organizationId,
        name: raw.canonical.organization.name,
        updatedAt: raw.updatedAt,
      });
    }
    return out.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }

  async get(organizationId: string): Promise<WorkspaceSnapshot | null> {
    const file = this.fileFor(organizationId);
    if (!fs.existsSync(file)) return null;
    return JSON.parse(fs.readFileSync(file, "utf8")) as WorkspaceSnapshot;
  }

  async save(snapshot: WorkspaceSnapshot): Promise<void> {
    const next = { ...snapshot, updatedAt: nowIso() };
    fs.writeFileSync(this.fileFor(snapshot.organizationId), JSON.stringify(next, null, 2));
  }

  async appendChange(organizationId: string, change: ChangeSet): Promise<void> {
    const snap = await this.get(organizationId);
    if (!snap) throw new Error(`Workspace not found: ${organizationId}`);
    snap.changeHistory = [...snap.changeHistory, change];
    snap.canonical.changeSets = [...snap.canonical.changeSets, change];
    await this.save(snap);
  }

  async appendExport(organizationId: string, artifact: ExportArtifact): Promise<void> {
    const snap = await this.get(organizationId);
    if (!snap) throw new Error(`Workspace not found: ${organizationId}`);
    snap.exports = [...snap.exports, artifact];
    await this.save(snap);
  }

  async clearAll(): Promise<void> {
    for (const file of fs.readdirSync(this.rootDir)) {
      if (file.endsWith(".json")) fs.unlinkSync(path.join(this.rootDir, file));
    }
  }
}

export function defaultDataDir(): string {
  return path.resolve(process.cwd(), "data", "workspaces");
}
