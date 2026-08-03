/**
 * Seed local workspace with demo (intentionally blocked) and eligible (exportable) fixtures.
 * Safe to re-run: writes fresh imports into data/workspaces.
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

  const demo = await pipeline.importFixture("demo-org.yaml");
  const eligible = await pipeline.importFixture("eligible-org.yaml");

  console.log("Seeded workspaces");
  console.log(`  dataDir: ${dataDir}`);
  console.log(
    `  demo (blocked path): ${demo.canonical.organization.name} · ${demo.organizationId}`,
  );
  console.log(
    `  eligible (exportable path): ${eligible.canonical.organization.name} · ${eligible.organizationId}`,
  );
  console.log(
    `  tip: demo is expected to end BLOCKED_NO_ELIGIBLE_CANDIDATE; use eligible for approve/export.`,
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
