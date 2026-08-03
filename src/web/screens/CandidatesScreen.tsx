import { Navigate } from "react-router-dom";
import { useWorkspace } from "../App";
import { EvidenceBadge } from "../components/EvidenceBadge";
import { EligibilityPanel } from "../components/EligibilityPanel";
import { JourneyNav } from "../components/JourneyNav";

export function CandidatesScreen() {
  const { snap } = useWorkspace();
  if (!snap) return null;
  if (!snap.candidates || !snap.validationResults) {
    return <Navigate to="/gaps" replace />;
  }

  const { candidates, notes } = snap.candidates;
  const comparison = snap.baselineComparison;
  const eligibility = snap.recommendation?.eligibility ?? snap.eligibility;

  return (
    <div>
      <h1>Candidates & Validation</h1>
      <p className="lede">
        Compare the current baseline to at least two template-backed proposals. Validation is
        declared-fidelity static/scenario checking — not full behavioral prediction.
      </p>
      <JourneyNav current="/candidates" />
      <p className="mono">{notes}</p>

      <EligibilityPanel
        assessments={eligibility?.assessments}
        selectionStatus={
          snap.recommendation?.selectionStatus ?? eligibility?.selectionStatus
        }
        chosenCandidateId={snap.recommendation?.chosenCandidateId}
        blockReasons={eligibility?.blockReasons}
      />

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
                    <EvidenceBadge status="inference" /> {p.name}
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
        </div>
      )}

      <div className="compare">
        {candidates.map((c) => {
          const val = snap.validationResults!.find((v) => v.candidateId === c.id);
          const elig = eligibility?.assessments.find((a) => a.candidateId === c.id);
          return (
            <div className="panel" key={c.id}>
              <h2>{c.name}</h2>
              <p>{c.summary}</p>
              <p>
                <EvidenceBadge status="inference" />{" "}
                <span className="mono">{c.template}</span>{" "}
                <span className={`badge ${elig?.eligible ? "PASS" : "BLOCKED"}`}>
                  {elig?.eligible ? "eligible" : "ineligible"}
                </span>
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
              <h3>Do not use when</h3>
              <ul>
                {c.doNotUseWhen.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
              <h3>
                Validation{" "}
                <span className={`badge ${val?.overallPass ? "PASS" : "BLOCKED"}`}>
                  {val?.overallPass ? "projected-ok" : "projected-fail"}
                </span>
              </h3>
              <p>
                <EvidenceBadge status="simulation" /> {val?.declaredFidelity}
              </p>
              <table className="table">
                <thead>
                  <tr>
                    <th>Check</th>
                    <th>Current state</th>
                    <th>Projected</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {(val?.checks ?? []).map((ch) => (
                    <tr key={ch.id}>
                      <td>
                        {ch.name}
                        <div className="mono">{ch.kind}</div>
                      </td>
                      <td>
                        <EvidenceBadge status="observation" />{" "}
                        <span className={`badge ${ch.currentStatePass ? "ok" : "critical"}`}>
                          {ch.currentStatePass ? "pass" : "fail"}
                        </span>
                      </td>
                      <td>
                        <EvidenceBadge status="simulation" />{" "}
                        <span className={`badge ${ch.pass ? "ok" : "critical"}`}>
                          {ch.pass ? "pass" : "fail"}
                        </span>
                      </td>
                      <td>
                        <div className="mono">{ch.observations[0]}</div>
                        {(ch.assumptions?.length ?? 0) > 0 && (
                          <div className="mono">
                            <EvidenceBadge status="assertion" /> {ch.assumptions[0]}
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
            </div>
          );
        })}
      </div>
    </div>
  );
}
