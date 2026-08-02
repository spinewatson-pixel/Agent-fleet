import { useState } from "react";
import { Navigate } from "react-router-dom";
import { api } from "../api";
import { useWorkspace } from "../App";
import { EvidenceBadge } from "../components/EvidenceBadge";

export function ReviewScreen() {
  const { snap, setSnap, workspaceId } = useWorkspace();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!snap) return null;
  if (!snap.reviewResults || !snap.recommendation) {
    return <Navigate to="/gaps" replace />;
  }

  async function decide(decision: "approved" | "rejected") {
    if (!workspaceId) return;
    setBusy(true);
    setError(null);
    try {
      const next = await api.decide(workspaceId, decision);
      setSnap(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const rec = snap.recommendation;
  const latestExport = snap.exports[snap.exports.length - 1];

  return (
    <div>
      <h1>Architecture Review & Decision</h1>
      <p className="lede">
        Independent review scores candidates across dimensions. Critical blockers are
        non-averaging: any blocker yields BLOCKED regardless of score. Approval is
        advisory only — no deployment path exists.
      </p>

      <div className="panel">
        <p className="mono">trace: {rec.traceChain.join(" → ")}</p>
        <p>
          <EvidenceBadge status="recommendation" /> {rec.rationale}
        </p>
        <p className="mono">
          chosen={rec.chosenCandidateId ?? "none"} · rejected=
          {rec.rejectedCandidateIds.join(", ") || "none"} · approval=
          {rec.approvalState}
        </p>
      </div>

      {snap.reviewResults.map((r) => (
        <div className="panel" key={r.candidateId}>
          <h2>
            {r.candidateId}{" "}
            <span className={`badge ${r.status}`}>{r.status}</span>
          </h2>
          <p>{r.summary}</p>
          {r.blockers.length > 0 && (
            <ul>
              {r.blockers.map((b) => (
                <li key={b} className="error">
                  BLOCKER: {b}
                </li>
              ))}
            </ul>
          )}
          <table className="table">
            <thead>
              <tr>
                <th>Dimension</th>
                <th>Score</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {r.dimensions.map((d) => (
                <tr key={d.dimension}>
                  <td className="mono">{d.dimension}</td>
                  <td className="mono">
                    {d.score.toFixed(2)}
                    {d.blocker ? " · BLOCKER" : ""}
                  </td>
                  <td>{d.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      <h2>Uncertainty</h2>
      <ul>
        {rec.uncertainty.map((u) => (
          <li key={u}>{u}</li>
        ))}
      </ul>

      <div className="row">
        <button disabled={busy} onClick={() => void decide("approved")}>
          Approve & export plan
        </button>
        <button
          disabled={busy}
          className="danger"
          onClick={() => void decide("rejected")}
        >
          Reject
        </button>
        <span className="mono">human review required · no approval = no deployment</span>
      </div>
      {error && <p className="error">{error}</p>}

      {latestExport && (
        <div className="panel">
          <h2>Exported artifact</h2>
          <p className="mono">
            {latestExport.id} · {latestExport.createdAt}
          </p>
          <pre className="export">{latestExport.markdown}</pre>
        </div>
      )}
    </div>
  );
}
