#!/usr/bin/env node
/**
 * Sync config/watchfloor_registry.json from ui/watchfloor.html baseDivisions().
 */
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const htmlPath = path.join(root, "ui", "watchfloor.html");
const outPath = path.join(root, "config", "watchfloor_registry.json");
const html = fs.readFileSync(htmlPath, "utf8");

const start = html.indexOf("var TICKERS=");
const end = html.indexOf("/* ============ STATE + STORAGE ============ */");
if (start < 0 || end < 0) throw new Error("Could not locate baseDivisions block");

const code =
  html.slice(start, end) +
  `
var __DIVISIONS = baseDivisions();
var __agents = [];
__DIVISIONS.forEach(function(div){
  div.depts.forEach(function(dep){
    (dep.agents||[]).forEach(function(a){
      __agents.push(Object.assign({}, a, {
        division: div.key,
        department: dep.name,
        division_name: div.name
      }));
    });
  });
});
({
  divisions: __DIVISIONS.map(function(d){
    return {
      key: d.key,
      name: d.name,
      depts: d.depts.length,
      agents: d.depts.reduce(function(s,x){return s+x.agents.length},0)
    };
  }),
  agents: __agents
});
`;

const payload = eval(code);
const agents = payload.agents;
const ids = agents.map((a) => a.id);
const dupes = [...new Set(ids.filter((id, i) => ids.indexOf(id) !== i))];
if (dupes.length) {
  console.error("Duplicate agent ids:", dupes);
  process.exit(1);
}

function isProposer(a) {
  const tags = (a.tags || []).map(String);
  if (a.id === "EXEC-1" || a.id === "CAP-1") return false;
  if (["RT-FORGE-1", "RT-CULL-1", "RT-GROW-1"].includes(a.id)) return false;
  if (tags.includes("PAPER TRADER") || tags.includes("FUND TRADER")) return true;
  if (tags.includes("RENTEC") && a.id.startsWith("RT-")) return true;
  if (["BRK-TRD1", "BRK-TRD2", "PNY-TRD1", "PNY-TRD2", "LIV-TRD", "REN-BASK", "REN-EXEC", "CIT-POD3"].includes(a.id))
    return true;
  if (a.kind === "trader" && (a.division === "trade" || a.division === "funds" || a.division === "quant")) {
    // fund/quant traders only when explicitly trader kind and not support
    if (a.division === "trade") return tags.includes("PAPER TRADER");
    return true;
  }
  return false;
}

function enrich(a) {
  const tags = (a.tags || []).map(String);
  const upper = tags.map((t) => t.toUpperCase());
  const proposer = isProposer(a);
  const out = {
    id: a.id,
    nick: a.nick,
    role: a.role,
    tags: a.tags || [],
    status: a.status || "RUNNING",
    kind: a.kind || "trader",
    division: a.division,
    department: a.department,
    may_propose_trades: proposer,
    may_place_orders: a.id === "EXEC-1",
    execution_role: a.id === "EXEC-1",
    can_self_approve: false,
    paper_only: true,
  };

  if (proposer) {
    if (upper.includes("LONG ONLY") || upper.includes("LONG SCOUT")) out.side_restriction = "LONG ONLY";
    if (upper.includes("SHORT ONLY") || upper.includes("SHORT SCOUT")) out.side_restriction = "SHORT ONLY";
    const m = a.id.match(/^([A-Z0-9]+)-(L|S)$/);
    if (m) out.assets_permitted = [m[1]];
    if (upper.some((t) => t.includes("SWING"))) {
      out.holding_period = "1_to_5_days";
      out.holding_cap_days = 7;
    } else if (upper.includes("PAPER TRADER") || a.division === "trade") {
      out.holding_period = "intraday";
    }
    if (upper.includes("VAR $") || upper.includes("SIZING LAB")) out.sizing = "experimental_variable";
    else if (a.division === "funds" || a.id.startsWith("RT-ENS")) out.sizing = "desk_set";
    else if (a.division === "quant") out.sizing = null;
    else out.sizing = "fixed_1_2_usd";
    out.thesis_required = !(a.division === "quant" || upper.includes("RENTEC"));
    out.supervisor_id =
      a.division === "quant"
        ? a.id.includes("MICRO")
          ? "MICRO-Q"
          : a.id.includes("REG")
            ? "REG-1"
            : a.id.includes("STAT")
              ? "CORR-Q"
              : "ENS-1"
        : a.division === "funds"
          ? a.id.startsWith("BRK")
            ? "BRK-SAFE"
            : a.id.startsWith("CIT")
              ? "CIT-ALLOC"
              : a.id.startsWith("PNY")
                ? "PNY-SCAN"
                : a.id.startsWith("LIV")
                  ? "LIV-TAPE"
                  : a.id.startsWith("REN")
                    ? "REN-MINE"
                    : "HEAD-TRADE"
          : upper.includes("NOVEL")
            ? "HEAD-LAB"
            : "HEAD-TRADE";
  } else {
    const map = {
      ctrl: "GOV-CHAIR",
      intel: "HEAD-INTEL",
      pred: "FORE-1",
      lab: "HEAD-LAB",
      learn: "HEAD-LEARN",
      data: "MEM-1",
      sec: "SEC-HALT",
      contr: "GOV-CHAIR",
      quant: "ENS-1",
      funds: "HEAD-TRADE",
      trade: "HEAD-TRADE",
      minds: "MIND-FORGE",
    };
    out.supervisor_id = map[a.division] || "GOV-CHAIR";
    if (a.id === "RECON-1") out.supervisor_id = "COMP-1";
  }
  return out;
}

const enriched = agents.map(enrich);
const proposers = enriched.filter((a) => a.may_propose_trades);
const executors = enriched.filter((a) => a.may_place_orders || a.execution_role);

let prior = {};
if (fs.existsSync(outPath)) prior = JSON.parse(fs.readFileSync(outPath, "utf8"));

function nextVersion(counts) {
  const priorCounts = (prior && prior.counts) || {};
  const same =
    priorCounts.total_agents === counts.total_agents &&
    priorCounts.proposers === counts.proposers &&
    priorCounts.executors === counts.executors &&
    priorCounts.divisions === counts.divisions;
  if (same && prior.version) return prior.version;
  const base = String((prior && prior.version) || "0.5.1");
  const parts = base.split(".").map((n) => parseInt(n, 10) || 0);
  while (parts.length < 3) parts.push(0);
  parts[2] += 1;
  return parts.join(".");
}

const counts = {
  total_agents: enriched.length,
  proposers: proposers.length,
  executors: executors.length,
  divisions: new Set(enriched.map((a) => a.division)).size,
};

const registry = {
  source: "ui/watchfloor.html baseDivisions()",
  organization: "watchfloor quant lab",
  version: nextVersion(counts),
  rebuilt_at: new Date().toISOString(),
  hard_rules: Object.assign(
    {},
    prior.hard_rules || {},
    {
      paper_only: true,
      live_execution_enabled: false,
      agent_ceiling: 300,
      default_sizing_usd: [1, 2],
      swing_hard_cap_days: 7,
      thesis_required_for_discretionary: true,
      quant_exempt_from_thesis: true,
      strategies_cannot_self_approve: true,
      strategies_cannot_self_execute: true,
      learning_cannot_auto_mutate_production: true,
      compute_ceiling: { max_autonomous_jobs: 4, require_gov_above: true },
      dual_source_macro: true,
      max_orders_per_symbol_per_day: 20,
    }
  ),
  institutional_council_map: prior.institutional_council_map || {},
  approval_chain: prior.approval_chain || [
    "FIT-1",
    "RISK-1",
    "COMP-1",
    "CAP-1",
    "GOV-CHAIR",
    "HUMAN-1",
  ],
  veto_agents: prior.veto_agents || [
    "RISK-1",
    "COMP-1",
    "GOV-CHAIR",
    "SEC-HALT",
    "HUMAN-1",
    "FIT-1",
    "CIT-RISK",
    "BRK-SAFE",
  ],
  counts,
  division_summary: payload.divisions,
  proposer_ids: proposers.map((a) => a.id),
  executor_ids: executors.map((a) => a.id),
  agents: enriched,
};

const jpm = registry.institutional_council_map["JPMorgan Governance Operations"];
if (Array.isArray(jpm) && !jpm.includes("RECON-1")) jpm.push("RECON-1");

fs.writeFileSync(outPath, JSON.stringify(registry, null, 2) + "\n");
console.log(
  JSON.stringify(
    {
      wrote: outPath,
      counts: registry.counts,
      has_recon: enriched.some((a) => a.id === "RECON-1"),
      swing_ids: enriched.filter((a) => a.id.startsWith("SWING-")).map((a) => a.id),
    },
    null,
    2
  )
);
