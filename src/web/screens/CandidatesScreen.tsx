import { Navigate } from "react-router-dom";
import { useWorkspace } from "../App";
import { EvidenceBadge } from "../components/EvidenceBadge";

export function CandidatesScreen() {
  const { snap } = useWorkspace();
  if (!snap) return null;
  if (!snap.candidates || !snap.validationResults) {
    return <Navigate to="/gaps" replace />;
  }

  const { candidates, notes } = snap.candidates;

  return (
    <div>
      <h1>Candidates & Validation</h1>
      <p className="lede">
        At least two template-backed architectures with trade-offs. Validation is
        declared-fidelity static/scenario checking — not full behavioral prediction.
      </p>
      <p className="mono">{notes}</p>

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
                          {ch.pass ? "pass" : "fail"}
                        </span>
                        <div className="mono">{ch.observations[0]}</div>
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
