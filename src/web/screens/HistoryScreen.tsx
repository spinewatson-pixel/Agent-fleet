import { useWorkspace } from "../App";
import { EvidenceBadge } from "../components/EvidenceBadge";

export function HistoryScreen() {
  const { snap } = useWorkspace();
  if (!snap) return null;

  return (
    <div>
      <h1>Change History</h1>
      <p className="lede">
        Immutable local record of decisions and exported plans. Outcomes do not mutate
        connected systems.
      </p>

      <h2>Change sets</h2>
      {snap.changeHistory.length === 0 && (
        <p className="mono">No decisions recorded yet.</p>
      )}
      <table className="table">
        <thead>
          <tr>
            <th>Id</th>
            <th>State</th>
            <th>Proposal</th>
            <th>Outcome</th>
          </tr>
        </thead>
        <tbody>
          {snap.changeHistory.map((c) => (
            <tr key={String(c.id)}>
              <td className="mono">{String(c.id)}</td>
              <td>
                <span className="badge recommendation">{String(c.approvalState)}</span>
              </td>
              <td>{String(c.proposal)}</td>
              <td>{String(c.outcome ?? "—")}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Exports</h2>
      {snap.exports.map((e) => (
        <div className="panel" key={e.id}>
          <p>
            <EvidenceBadge status="recommendation" />{" "}
            <span className="mono">
              {e.id} · changeset={e.changeSetId} · {e.createdAt}
            </span>
          </p>
          <details>
            <summary>Markdown</summary>
            <pre className="export">{e.markdown}</pre>
          </details>
        </div>
      ))}
    </div>
  );
}
