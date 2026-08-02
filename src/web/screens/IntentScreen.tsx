import { useState } from "react";
import { api } from "../api";
import { useWorkspace } from "../App";
import { EvidenceBadge, EvidenceLegend } from "../components/EvidenceBadge";
import { JourneyNav } from "../components/JourneyNav";

export function IntentScreen() {
  const { snap, setSnap, workspaceId } = useWorkspace();
  const intent = snap?.intent;
  const [mission, setMission] = useState(intent?.mission ?? "");
  const [success, setSuccess] = useState((intent?.successMeasures ?? []).join("\n"));
  const [constraints, setConstraints] = useState((intent?.constraints ?? []).join("\n"));
  const [risk, setRisk] = useState(intent?.riskTolerance ?? "unknown");
  const [preserve, setPreserve] = useState((intent?.preserveList ?? []).join("\n"));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!snap || !workspaceId) return null;

  async function save(confirm: boolean) {
    if (!workspaceId) return;
    setBusy(true);
    setError(null);
    try {
      const next = await api.updateIntent(workspaceId, {
        mission: mission.trim() || undefined,
        successMeasures: splitLines(success),
        constraints: splitLines(constraints),
        riskTolerance: risk,
        preserveList: splitLines(preserve),
        confirmed: confirm,
      });
      setSnap(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Intent & Evidence Review</h1>
      <p className="lede">
        Complete mission, constraints, and preserve list. Missing fields become explicit
        questions — the builder will not invent answers.
      </p>
      <JourneyNav current="/intent" />
      <EvidenceLegend />

      <div className="panel">
        <div className="field">
          <label htmlFor="mission">Mission</label>
          <input
            id="mission"
            value={mission}
            onChange={(e) => setMission(e.target.value)}
            placeholder="Unknown until owner states it"
          />
          <Confidence conf={snap.intent?.fieldConfidence?.mission} />
        </div>
        <div className="field">
          <label htmlFor="success">Success measures (one per line)</label>
          <textarea
            id="success"
            rows={3}
            value={success}
            onChange={(e) => setSuccess(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="constraints">Constraints (one per line)</label>
          <textarea
            id="constraints"
            rows={3}
            value={constraints}
            onChange={(e) => setConstraints(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="risk">Risk tolerance</label>
          <select id="risk" value={risk} onChange={(e) => setRisk(e.target.value)}>
            <option value="unknown">unknown</option>
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="preserve">Preserve list (one per line)</label>
          <textarea
            id="preserve"
            rows={3}
            value={preserve}
            onChange={(e) => setPreserve(e.target.value)}
          />
        </div>
        <div className="row">
          <button disabled={busy} onClick={() => void save(false)}>
            Save intent draft
          </button>
          <button disabled={busy} className="secondary" onClick={() => void save(true)}>
            Mark confirmed (if complete)
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>

      <h2>Unresolved questions</h2>
      <ul>
        {(snap.intent?.unresolvedQuestions ?? []).map((q) => (
          <li key={q}>{q}</li>
        ))}
        {(snap.intent?.unresolvedQuestions ?? []).length === 0 && (
          <li>No unresolved intent questions.</li>
        )}
      </ul>

      <h2>Evidence (typed)</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Status</th>
            <th>Summary</th>
            <th>Freshness</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {snap.canonical.evidence.map((e) => (
            <tr key={e.id}>
              <td>
                <EvidenceBadge status={e.status} />
              </td>
              <td>{e.summary}</td>
              <td className="mono">{e.freshness ?? "—"}</td>
              <td className="mono">{e.confidence}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function splitLines(text: string): string[] {
  return text
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

function Confidence({ conf }: { conf?: string }) {
  return (
    <span className="mono" style={{ color: "var(--muted)" }}>
      field confidence: {conf ?? "unknown"}
    </span>
  );
}
