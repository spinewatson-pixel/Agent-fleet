/**
 * Watchfloor registry + blueprint bridge.
 * Loads rebuilt artifacts published under ui/data/ (from scripts/rebuild_from_watchfloor.sh).
 *
 * Usage:
 *   await WatchfloorBridge.bootstrap();
 *   WatchfloorBridge.blueprintFor("AAPL-L");
 *   WatchfloorBridge.summary(WatchfloorBridge.registry);
 */
(function (global) {
  "use strict";

  function resolve(rel) {
    if (global.location && global.location.href) {
      return new URL(rel, global.location.href).href;
    }
    return rel;
  }

  const DEFAULT_REGISTRY_URL = resolve("./data/watchfloor_registry.json");
  const DEFAULT_BLUEPRINTS_URL = resolve("./data/blueprints.json");
  const DEFAULT_META_URL = resolve("./data/rebuild_meta.json");

  let _registry = null;
  let _blueprints = null;
  let _meta = null;
  let _bootstrapped = false;

  async function fetchJson(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`Failed to load ${url} (${res.status})`);
    }
    return res.json();
  }

  async function loadRegistry(url = DEFAULT_REGISTRY_URL) {
    const data = await fetchJson(url);
    if (!data || !Array.isArray(data.agents)) {
      throw new Error("Invalid watchfloor registry: missing agents[]");
    }
    _registry = data;
    return data;
  }

  async function loadBlueprints(url = DEFAULT_BLUEPRINTS_URL) {
    const data = await fetchJson(url);
    if (!data || typeof data !== "object") {
      throw new Error("Invalid blueprints payload");
    }
    _blueprints = data;
    return data;
  }

  async function loadMeta(url = DEFAULT_META_URL) {
    try {
      _meta = await fetchJson(url);
    } catch (_e) {
      _meta = null;
    }
    return _meta;
  }

  async function bootstrap(opts) {
    const o = opts || {};
    const [reg, bp] = await Promise.all([
      loadRegistry(o.registryUrl || DEFAULT_REGISTRY_URL),
      loadBlueprints(o.blueprintsUrl || DEFAULT_BLUEPRINTS_URL),
    ]);
    await loadMeta(o.metaUrl || DEFAULT_META_URL);
    _bootstrapped = true;
    return { registry: reg, blueprints: bp, meta: _meta };
  }

  function clearCache() {
    _registry = null;
    _blueprints = null;
    _meta = null;
    _bootstrapped = false;
  }

  function agents(registry) {
    const r = registry || _registry;
    return Array.isArray(r?.agents) ? r.agents : [];
  }

  function agentById(registry, id) {
    return agents(registry).find((a) => a.id === id) || null;
  }

  function agentsByDivision(registry, divisionId) {
    return agents(registry).filter((a) => a.division === divisionId);
  }

  function countByDivision(registry) {
    const out = Object.create(null);
    for (const a of agents(registry)) {
      const key = a.division || "unknown";
      out[key] = (out[key] || 0) + 1;
    }
    return out;
  }

  function proposers(registry) {
    const r = registry || _registry;
    if (Array.isArray(r?.proposer_ids) && r.proposer_ids.length) {
      const set = new Set(r.proposer_ids);
      return agents(r).filter((a) => set.has(a.id));
    }
    return agents(r).filter((a) => a.may_propose_trades);
  }

  function executors(registry) {
    const r = registry || _registry;
    if (Array.isArray(r?.executor_ids) && r.executor_ids.length) {
      return r.executor_ids.slice();
    }
    return agents(r)
      .filter((a) => a.may_place_orders)
      .map((a) => a.id);
  }

  function authorityFor(registry, agentId) {
    const r = registry || _registry;
    const a = agentById(r, agentId);
    if (!a) return null;
    const veto = new Set(r.veto_agents || []);
    const chain = r.approval_chain || [];
    return {
      id: a.id,
      division: a.division,
      department: a.department,
      kind: a.kind,
      status: a.status,
      mayProposeTrades: !!a.may_propose_trades,
      mayPlaceOrders: !!a.may_place_orders,
      canSelfApprove: !!a.can_self_approve,
      paperOnly: a.paper_only !== false,
      isVeto: veto.has(a.id),
      inApprovalChain: chain.includes(a.id),
      supervisorId: a.supervisor_id || null,
    };
  }

  function hardRules(registry) {
    return { ...((registry || _registry)?.hard_rules || {}) };
  }

  function institutionalCouncilMap(registry) {
    return { ...((registry || _registry)?.institutional_council_map || {}) };
  }

  function blueprintFor(agentId) {
    if (!_blueprints) return null;
    return _blueprints[agentId] || null;
  }

  const LAYER_KEYS = [
    ["Identity", "identity"],
    ["Goal", "goal"],
    ["Responsibilities", "responsibilities"],
    ["Functions", "functions"],
    ["Tools", "tools"],
    ["Capabilities", "capabilities"],
    ["Memory", "memory"],
    ["Knowledge Base", "knowledge_base"],
    ["Skills", "skills"],
    ["Workflows", "workflows"],
    ["Decision Rules", "decision_rules"],
    ["Communication", "communication"],
    ["Inputs", "inputs"],
    ["Outputs", "outputs"],
    ["Learning", "learning"],
    ["Evaluation", "evaluation"],
    ["Permissions", "permissions"],
    ["Constraints", "constraints"],
    ["Triggers", "triggers"],
    ["Scheduling", "scheduling"],
    ["Logging", "logging"],
    ["Self-Reflection", "self_reflection"],
    ["Escalation", "escalation"],
    ["Versioning", "versioning"],
    ["Health Monitoring", "health_monitoring"],
  ];

  function formatLayerValue(key, value) {
    if (value == null) return [];
    if (key === "tools" && Array.isArray(value)) {
      return value.map(function (t) {
        if (typeof t === "string") return t;
        var label = t.name || "tool";
        if (t.access) label += " [" + t.access + "]";
        if (t.purpose) label += " — " + t.purpose;
        return label;
      });
    }
    if (Array.isArray(value)) return value.map(String);
    return [String(value)];
  }

  function layersFromBlueprint(bp) {
    if (!bp) return null;
    return LAYER_KEYS.map(function (pair) {
      return [pair[0], formatLayerValue(pair[1], bp[pair[1]])];
    });
  }

  function summary(registry) {
    const r = registry || _registry;
    const counts = r?.counts || {};
    const list = agents(r);
    return {
      organization: r?.organization || null,
      version: r?.version || null,
      source: r?.source || null,
      rebuiltAt: r?.rebuilt_at || (_meta && _meta.rebuilt_at) || null,
      totalAgents: counts.total_agents ?? list.length,
      proposers: counts.proposers ?? proposers(r).length,
      executors: executors(r),
      divisions: counts.divisions ?? Object.keys(countByDivision(r)).length,
      byDivision: countByDivision(r),
      paperOnly: !!(r?.hard_rules?.paper_only),
      liveExecutionEnabled: !!(r?.hard_rules?.live_execution_enabled),
      agentCeiling: r?.hard_rules?.agent_ceiling ?? null,
      vetoAgents: [...(r?.veto_agents || [])],
      approvalChain: [...(r?.approval_chain || [])],
      blueprintsLoaded: !!_blueprints,
      blueprintCount: _blueprints ? Object.keys(_blueprints).length : 0,
      meta: _meta,
    };
  }

  const api = {
    DEFAULT_REGISTRY_URL,
    DEFAULT_BLUEPRINTS_URL,
    DEFAULT_META_URL,
    LAYER_KEYS,
    get registry() {
      return _registry;
    },
    get blueprints() {
      return _blueprints;
    },
    get meta() {
      return _meta;
    },
    get bootstrapped() {
      return _bootstrapped;
    },
    loadRegistry,
    loadBlueprints,
    loadMeta,
    bootstrap,
    clearCache,
    agents,
    agentById,
    agentsByDivision,
    countByDivision,
    proposers,
    executors,
    authorityFor,
    hardRules,
    institutionalCouncilMap,
    blueprintFor,
    layersFromBlueprint,
    summary,
  };

  global.WatchfloorBridge = api;

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
