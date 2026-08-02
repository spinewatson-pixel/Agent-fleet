/**
 * Seed local workspace with the demo organization fixture.
 * Safe to re-run: writes a fresh import into data/workspaces.
 */
import path from "node:path";
import { BuilderPipeline } from "../src/core/pipeline.js";
import { JsonFileWorkspaceStore } from "../src/core/services/workspaceStore.js";

async function main() {
  const dataDir =
    process.env.AGENT_FLEET_DATA_DIR ??
    path.resolve(process.cwd(), "data", "workspaces");
  const store = new JsonFileWorkspaceStore(dataDir);
  const pipeline = new BuilderPipeline(store);
  const snap = await pipeline.importDemo();
  console.log("Seeded demo organization");
  console.log(`  organizationId: ${snap.organizationId}`);
  console.log(`  name: ${snap.canonical.organization.name}`);
  console.log(`  dataDir: ${dataDir}`);
  console.log(
    `  unresolvedIntentQuestions: ${snap.intent?.unresolvedQuestions.length ?? 0}`,
  );
  console.log(
    `  importGaps: ${(snap.importValidation as { gaps: unknown[] } | undefined)?.gaps.length ?? 0}`,
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
