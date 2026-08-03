import { EvidenceBadge } from "./EvidenceBadge";

type Assessment = {
  candidateId: string;
  eligible: boolean;
  reasons: string[];
};

export function EligibilityPanel({
  assessments,
  selectionStatus,
  chosenCandidateId,
  blockReasons,
}: {
  assessments?: Assessment[];
  selectionStatus?: string;
  chosenCandidateId?: string | null;
  blockReasons?: string[];
}) {
  if (!assessments?.length) return null;

  return (
    <div className="panel">
      <h2>Eligibility gate</h2>
      <p className="lede">
        Approve/export requires validation pass, no unresolved critical findings, and
        non-blocked review. No fallback to an ineligible candidate.
      </p>
      <p className="mono">
        selection={selectionStatus ?? "n/a"} · chosen={chosenCandidateId ?? "none"}
      </p>
      <table className="table">
        <thead>
          <tr>
            <th>Candidate</th>
            <th>Eligible</th>
            <th>Reasons</th>
          </tr>
        </thead>
        <tbody>
          {assessments.map((a) => (
            <tr key={a.candidateId}>
              <td className="mono">{a.candidateId}</td>
              <td>
                <span className={`badge ${a.eligible ? "PASS" : "BLOCKED"}`}>
                  {a.eligible ? "eligible" : "ineligible"}
                </span>
              </td>
              <td>
                {a.eligible ? (
                  <EvidenceBadge status="recommendation" />
                ) : (
                  <ul>
                    {a.reasons.slice(0, 8).map((r) => (
                      <li key={r} className="mono">
                        {r}
                      </li>
                    ))}
                  </ul>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {selectionStatus === "BLOCKED_NO_ELIGIBLE_CANDIDATE" &&
        (blockReasons?.length ?? 0) > 0 && (
          <details>
            <summary className="mono">All block reasons</summary>
            <ul>
              {blockReasons!.slice(0, 20).map((r) => (
                <li key={r} className="mono">
                  {r}
                </li>
              ))}
            </ul>
          </details>
        )}
    </div>
  );
}
