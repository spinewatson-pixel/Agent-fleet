import { Navigate } from "react-router-dom";
import { useWorkspace } from "../App";
import { EvidenceBadge } from "../components/EvidenceBadge";
import { JourneyNav } from "../components/JourneyNav";

export function CandidatesScreen() {
  const { snap } = useWorkspace();
  if (!snap) return null;
  if (!snap.candidates || !snap.validationResults) {
    return <Navigate to="/gaps" replace />;
  }

  const { candidates, notes } = snap.candidates;
  const comparison = snap.baselineComparison;

  return (
    <div>
      <h1>Candidates & Validation</h1>
      <p className="lede">
        Compare the current baseline to at least two template-backed proposals. Validation is
        declared-fidelity static/scenario checking — not full behavioral prediction.
      </p>
      <JourneyNav current="/candidates" />
      <p className="mono">{notes}</p>

      {comparison && (
        <div className="panel">
          <h2>Baseline vs proposals</h2>
          <p>{comparison.notes}</p>
          <table className="table">
            <thead>
              <tr>
                <th>View</th>
                <th>Critical gaps</th>
                <th>Missing contracts</th>
                <th>Approval gate</th>
                <th>Orphans / cycle</th>
                <th>Review</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <EvidenceBadge status="observation" /> current baseline
                </td>
                <td className="mono">{comparison.baseline.criticalGapCount}</td>
                <td className="mono">{comparison.baseline.missingContracts}</td>
                <td className="mono">
                  {comparison.baseline.hasApprovalGate ? "yes" : "no"}
                </td>
                <td className="mono">
                  orphans={comparison.baseline.orphanWorkerNodes} cycle=
                  {comparison.baseline.circularDependency ? "yes" : "no"}
                </td>
                <td className="mono">n/a (as-is)</td>
              </tr>
              {comparison.proposals.map((p) => (
                <tr key={p.candidateId}>
                  <td>
                    <EvidenceBadge status="recommendation" /> {p.name}
                  </td>
                  <td className="mono" colSpan={3}>
                    remediates: {p.remediates.join("; ") || "—"}
                  </td>
                  <td className="mono">
                    rel={p.tradeOffs.reliability} cost={p.tradeOffs.cost} lat=
                    {p.tradeOffs.latency}
                  </td>
                  <td>
                    <span className={`badge ${p.reviewStatus}`}>{p.reviewStatus}</span>{" "}
                    <span className="mono">{p.weightedScore.toFixed(2)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="mono">
            {comparison.proposals.map((p) => (
              <li key={`${p.candidateId}-vs`}>{p.vsBaseline}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="compare">
        {candidates.map((c) => {
          const val = snap.validationResults!.find((v) => v.candidateId === c.id);
          return (
            <div className="panel" key={c.id}>
              <h2>{c.name}</h2>
              <p>{c.summary}</p>
              <p>
                <EvidenceBadge status="recommendation" />{" "}
                <span className="mono">{c.template}</span>
              </p>
              <h3>Trade-offs</h3>
              <ul className="mono">
                {Object.entries(c.tradeOffs).map(([k, v]) => (
                  <li key={k}>
                    {k}: {v}
                  </li>
                ))}
              </ul>
              <h3>Benefits</h3>
              <ul>
                {c.benefits.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <h3>Costs / risks</h3>
              <ul>
                {[...c.costs, ...c.risks].map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
              <h3>Do not use when</h3>
              <ul>
                {c.doNotUseWhen.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
              <h3>
                Validation{" "}
                <span className={`badge ${val?.overallPass ? "PASS" : "BLOCKED"}`}>
                  {val?.overallPass ? "structural-ok" : "issues"}
                </span>
              </h3>
              <p>
                <EvidenceBadge status="simulation" /> {val?.declaredFidelity}
              </p>
              <table className="table">
                <thead>
                  <tr>
                    <th>Check</th>
                    <th>Kind</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {(val?.checks ?? []).map((ch) => (
                    <tr key={ch.id}>
                      <td>{ch.name}</td>
                      <td className="mono">{ch.kind}</td>
                      <td>
                        <span className={`badge ${ch.pass ? "ok" : "critical"}`}>
                          projected={ch.pass ? "pass" : "fail"}
                        </span>{" "}
                        <EvidenceBadge status="observation" />{" "}
                        <span className="mono">
                          current=
                          {"currentStatePass" in ch
                            ? String((ch as { currentStatePass?: boolean }).currentStatePass)
                            : "n/a"}
                        </span>
                        <div className="mono">{ch.observations[0]}</div>
                        {(ch.assumptions?.length ?? 0) > 0 && (
                          <div className="mono">
                            assumption: {ch.assumptions[0]}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <h3>Limitations</h3>
              <ul>
                {(val?.limitations ?? []).map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
              <p className="mono">
                modeled: {(val?.modeled ?? []).join(", ")}
                <br />
                not modeled: {(val?.notModeled ?? []).join(", ")}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
