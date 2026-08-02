/**
 * Build verification CLI.
 *
 *   pnpm verify                              every registered project
 *   pnpm verify --project nursing-ecosystem  one project
 *   pnpm verify --only build.types,deps.lockfile
 *   pnpm verify --update-baseline            record a successful run as the baseline
 *
 * Exit code is 1 when any project is BLOCKED, so a deployment step chained
 * after this command stops on its own.
 */
import fs from "node:fs";
import path from "node:path";
import {
  JsonBaselineStore,
  baselineFromRun,
  defaultBaselineDir,
  defaultHistoryDir,
  renderConsole,
  renderMarkdown,
  runVerification,
  writeRunHistory,
} from "../src/verification/index.js";
import { MANIFESTS, getManifest } from "../src/verification/manifests/index.js";
import type { ProjectManifest, VerificationRun } from "../src/verification/index.js";

interface Args {
  projects: ProjectManifest[];
  only: string[];
  updateBaseline: boolean;
  reportDir: string;
}

function parseArgs(argv: string[]): Args {
  const only: string[] = [];
  const projectIds: string[] = [];
  let updateBaseline = false;

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--project" || arg === "-p") {
      projectIds.push(...(argv[++i] ?? "").split(",").filter(Boolean));
    } else if (arg === "--only") {
      only.push(...(argv[++i] ?? "").split(",").filter(Boolean));
    } else if (arg === "--update-baseline") {
      updateBaseline = true;
    } else if (arg === "--help" || arg === "-h") {
      console.log(
        [
          "usage: pnpm verify [--project <id[,id]>] [--only <gateId[,gateId]>] [--update-baseline]",
          "",
          "projects:",
          ...MANIFESTS.map((m) => `  ${m.id.padEnd(20)} ${m.name}`),
        ].join("\n"),
      );
      process.exit(0);
    }
  }

  const projects = projectIds.length
    ? projectIds.map((id) => {
        const manifest = getManifest(id);
        if (!manifest) {
          console.error(
            `unknown project '${id}'. known: ${MANIFESTS.map((m) => m.id).join(", ")}`,
          );
          process.exit(2);
        }
        return manifest;
      })
    : MANIFESTS;

  return {
    projects,
    only,
    updateBaseline,
    reportDir: path.resolve(process.cwd(), ".verification", "reports"),
  };
}

async function verifyProject(manifest: ProjectManifest, args: Args): Promise<VerificationRun> {
  const baselineStore = new JsonBaselineStore(defaultBaselineDir(manifest.rootDir));

  process.stdout.write(`\n▸ ${manifest.name}\n`);
  const run = await runVerification({
    manifest,
    baselineStore,
    only: args.only,
    onGateStart: (spec) => {
      process.stdout.write(`  … ${spec.id} (${spec.category})\n`);
    },
    onGateFinish: (result) => {
      process.stdout.write(
        `  ${result.status.toUpperCase().padEnd(4)} ${result.gateId} ${result.durationMs}ms\n`,
      );
    },
  });

  fs.mkdirSync(args.reportDir, { recursive: true });
  const stem = path.join(args.reportDir, `${manifest.id}-${run.runId}`);
  fs.writeFileSync(`${stem}.md`, renderMarkdown(run), "utf8");
  fs.writeFileSync(`${stem}.json`, `${JSON.stringify(run, null, 2)}\n`, "utf8");
  writeRunHistory(defaultHistoryDir(manifest.rootDir), run);

  console.log(`\n${renderConsole(run)}`);
  console.log(`report: ${path.relative(process.cwd(), stem)}.md`);

  if (args.updateBaseline) {
    // A partial run is not a description of the build, so it must never become
    // the thing future builds are compared against.
    if (args.only.length > 0) {
      console.log("baseline not updated: --only makes this a partial run");
    } else {
      const baseline = baselineFromRun(run);
      if (baseline) {
        baselineStore.write(baseline);
        console.log(`baseline updated: verification/baselines/${manifest.id}.json`);
      } else {
        console.log("baseline not updated: the build is BLOCKED");
      }
    }
  }

  return run;
}

async function main(): Promise<number> {
  const args = parseArgs(process.argv.slice(2));
  const runs: VerificationRun[] = [];

  for (const manifest of args.projects) {
    runs.push(await verifyProject(manifest, args));
  }

  console.log("\n═══ deployment readiness ═══");
  for (const run of runs) {
    console.log(
      `  ${run.verdict.padEnd(20)} ${run.projectId.padEnd(20)} ${run.readiness.score}/100`,
    );
  }

  const blocked = runs.filter((r) => r.verdict === "BLOCKED");
  if (blocked.length > 0) {
    console.log("\nDEPLOYMENT BLOCKED");
    for (const run of blocked) {
      console.log(`\n  ${run.projectName}`);
      for (const reason of run.blockReasons) {
        console.log(`    [${reason.code}] ${reason.detail}`);
      }
    }
    return 1;
  }

  console.log("\nAll projects cleared for deployment.");
  return 0;
}

main()
  .then((code) => process.exit(code))
  .catch((err: unknown) => {
    // The harness itself failing is a blocked build, not a passing one.
    console.error("VERIFICATION HARNESS FAILED");
    console.error(err instanceof Error ? err.stack : String(err));
    process.exit(1);
  });
