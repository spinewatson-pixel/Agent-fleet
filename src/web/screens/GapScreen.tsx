import { useState } from "react";
import { api } from "../api";
import { useWorkspace } from "../App";
import { EvidenceBadge } from "../components/EvidenceBadge";

export function GapScreen() {
  const { snap, setSnap, workspaceId } = useWorkspace();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!snap || !workspaceId) return null;

  async function run() {
    if (!workspaceId) return;
    setBusy(true);
    setError(null);
    try {
      const next = await api.analyze(workspaceId);
      setSnap(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const gaps = snap.gapAnalysis;

  return (
    <div>
      <h1>Gap Analysis</h1>
      <p className="lede">
        Deterministic comparison of the canonical model against stated intent/constraints
        for reliability / capability coverage. Cost and latency are recorded as trade-offs only.
      </p>

      <div className="row">
        <button disabled={busy} onClick={() => void run()}>
          {gaps ? "Re-run gap + candidate + validation + review" : "Run analysis engines"}
        </button>
        <span className="mono">objective=reliability_capability_coverage</span>
      </div>
      {error && <p className="error">{error}</p>}

      {!gaps && (
        <div className="panel">
          <p className="lede">No analysis yet. Run engines to produce prioritized findings.</p>
        </div>
      )}

      {gaps && (
        <>
          <div className="panel">
            <p>{gaps.summary}</p>
            <h2>Preserve list</h2>
            <ul>
              {gaps.preserveList.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>

          <h2>Findings</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Category</th>
                <th>Finding</th>
                <th>Evidence</th>
                <th>Knowledge</th>
              </tr>
            </thead>
            <tbody>
              {gaps.findings.map((f) => (
                <tr key={f.id}>
                  <td>
                    <span className={`badge ${f.severity}`}>{f.severity}</span>
                  </td>
                  <td className="mono">{f.category}</td>
                  <td>
                    <strong>{f.title}</strong>
                    <div>{f.rationale}</div>
                    <div>
                      <EvidenceBadge status="inference" />{" "}
                      <span className="mono">conf={f.evidenceConfidence}</span>
                    </div>
                  </td>
                  <td className="mono">{f.evidenceIds.join(", ") || "—"}</td>
                  <td className="mono">{f.knowledgeIds.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
