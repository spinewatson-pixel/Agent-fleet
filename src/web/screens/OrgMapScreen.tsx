import { useWorkspace } from "../App";
import { EvidenceBadge, EvidenceLegend } from "../components/EvidenceBadge";

export function OrgMapScreen() {
  const { snap } = useWorkspace();
  if (!snap) return null;
  const org = snap.canonical.organization;
  const topo = snap.canonical.topologies[0];
  const gaps = snap.importValidation?.gaps ?? [];

  return (
    <div>
      <h1>Organization Map</h1>
      <p className="lede">
        Canonical inventory for <strong>{org.name}</strong> (v{org.version}, {org.environment}).
        Missing fields and mapping gaps are listed without inventing values.
      </p>
      <EvidenceLegend />

      <div className="panel">
        <table className="table">
          <tbody>
            <tr>
              <th>Mission</th>
              <td>{org.mission ?? <em>unknown</em>}</td>
            </tr>
            <tr>
              <th>Scope</th>
              <td>{org.scope ?? <em>unknown</em>}</td>
            </tr>
            <tr>
              <th>Criticality</th>
              <td>{org.criticality ?? <em>unknown</em>}</td>
            </tr>
            <tr>
              <th>Owners</th>
              <td className="mono">{org.owners.join(", ") || "—"}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2>Topology — {topo?.name ?? "none"}</h2>
      <div className="topo">
        {(topo?.nodes ?? []).map((n) => (
          <div className="topo-node" key={n.id}>
            <div>{n.label}</div>
            <small>
              {n.kind} · {n.refId}
            </small>
          </div>
        ))}
      </div>
      <div className="panel edge-list">
        {(topo?.edges ?? []).map((e) => (
          <div key={e.id}>
            {e.from} —{e.kind}→ {e.to}
            {e.label ? ` (${e.label})` : ""}
          </div>
        ))}
      </div>

      <h2>Inventory</h2>
      <InventoryTable title="Capabilities" rows={snap.canonical.capabilities} />
      <InventoryTable title="Workers" rows={snap.canonical.workers} />
      <InventoryTable title="Interfaces" rows={snap.canonical.interfaces} />
      <InventoryTable title="Governance" rows={snap.canonical.governancePolicies} />

      <h2>Evidence inventory</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Status</th>
            <th>Source</th>
            <th>Summary</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {snap.canonical.evidence.map((e) => (
            <tr key={e.id}>
              <td>
                <EvidenceBadge status={e.status} />
              </td>
              <td className="mono">{e.sourceType}</td>
              <td>{e.summary}</td>
              <td className="mono">{e.confidence}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Mapping gaps / warnings</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Severity</th>
            <th>Path</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {gaps.map((g, i) => (
            <tr key={`${g.path}-${i}`}>
              <td>
                <span className={`badge ${g.severity}`}>{g.severity}</span>
              </td>
              <td className="mono">{g.path}</td>
              <td>{g.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {(snap.importValidation?.warnings ?? []).map((w) => (
        <p key={w} className="mono">
          warning: {w}
        </p>
      ))}
    </div>
  );
}

function InventoryTable({
  title,
  rows,
}: {
  title: string;
  rows: Array<Record<string, unknown>>;
}) {
  return (
    <div className="panel">
      <h3>{title}</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Id</th>
            <th>Name</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={String(r.id)}>
              <td className="mono">{String(r.id)}</td>
              <td>{String(r.name ?? "")}</td>
              <td className="mono">
                {r.kind ? `kind=${String(r.kind)} ` : ""}
                {r.contractSchema === undefined && title === "Interfaces"
                  ? "contract=MISSING "
                  : ""}
                {r.requiresHumanApprovalGate === false
                  ? "approvalGate=false "
                  : ""}
                {Array.isArray(r.ownerIds) && (r.ownerIds as unknown[]).length === 0
                  ? "owners=none"
                  : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
