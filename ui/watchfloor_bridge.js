/**
 * Watchfloor registry bridge — loads config/watchfloor_registry.json and
 * exposes agent counts / authority helpers for future UI wiring.
 *
 * Usage (from ui/watchfloor.html):
 *   const reg = await WatchfloorBridge.loadRegistry();
 *   WatchfloorBridge.summary(reg);
 */
(function (global) {
  "use strict";

  const DEFAULT_REGISTRY_URL = new URL(
    "../config/watchfloor_registry.json",
    global.location ? global.location.href : "file:///workspace/ui/"
  ).href;

  let _cache = null;

  async function loadRegistry(url = DEFAULT_REGISTRY_URL) {
    if (_cache && (!url || url === DEFAULT_REGISTRY_URL)) {
      return _cache;
    }
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`Failed to load watchfloor registry (${res.status})`);
    }
    const data = await res.json();
    if (!data || !Array.isArray(data.agents)) {
      throw new Error("Invalid watchfloor registry: missing agents[]");
    }
    if (!url || url === DEFAULT_REGISTRY_URL) {
      _cache = data;
    }
    return data;
  }

  function clearCache() {
    _cache = null;
  }

  function agents(registry) {
    return Array.isArray(registry?.agents) ? registry.agents : [];
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
    if (Array.isArray(registry?.proposer_ids) && registry.proposer_ids.length) {
      const set = new Set(registry.proposer_ids);
      return agents(registry).filter((a) => set.has(a.id));
    }
    return agents(registry).filter((a) => a.may_propose_trades);
  }

  function executors(registry) {
    if (Array.isArray(registry?.executor_ids) && registry.executor_ids.length) {
      return registry.executor_ids.slice();
    }
    return agents(registry)
      .filter((a) => a.may_place_orders)
      .map((a) => a.id);
  }

  function authorityFor(registry, agentId) {
    const a = agentById(registry, agentId);
    if (!a) {
      return null;
    }
    const veto = new Set(registry.veto_agents || []);
    const chain = registry.approval_chain || [];
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
    return { ...(registry?.hard_rules || {}) };
  }

  function institutionalCouncilMap(registry) {
    return { ...(registry?.institutional_council_map || {}) };
  }

  function summary(registry) {
    const counts = registry?.counts || {};
    const list = agents(registry);
    return {
      organization: registry?.organization || null,
      version: registry?.version || null,
      source: registry?.source || null,
      totalAgents: counts.total_agents ?? list.length,
      proposers: counts.proposers ?? proposers(registry).length,
      executors: executors(registry),
      divisions: counts.divisions ?? Object.keys(countByDivision(registry)).length,
      byDivision: countByDivision(registry),
      paperOnly: !!(registry?.hard_rules?.paper_only),
      liveExecutionEnabled: !!(registry?.hard_rules?.live_execution_enabled),
      agentCeiling: registry?.hard_rules?.agent_ceiling ?? null,
      vetoAgents: [...(registry?.veto_agents || [])],
      approvalChain: [...(registry?.approval_chain || [])],
    };
  }

  const api = {
    DEFAULT_REGISTRY_URL,
    loadRegistry,
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
    summary,
  };

  global.WatchfloorBridge = api;

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
