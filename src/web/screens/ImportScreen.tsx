import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useWorkspace } from "../App";
import { EvidenceLegend } from "../components/EvidenceBadge";
import { JourneyNav } from "../components/JourneyNav";

export function ImportScreen() {
  const { setWorkspaceId, setSnap, snap } = useWorkspace();
  const nav = useNavigate();
  const [content, setContent] = useState("");
  const [format, setFormat] = useState<"yaml" | "json">("yaml");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [seeded, setSeeded] = useState<Array<{ organizationId: string; name: string }>>(
    [],
  );

  useEffect(() => {
    void api
      .list()
      .then((rows) => setSeeded(rows))
      .catch(() => setSeeded([]));
  }, [snap?.organizationId]);

  async function loadFixture(name: "demo-org.yaml" | "eligible-org.yaml") {
    setBusy(true);
    setError(null);
    try {
      const next =
        name === "demo-org.yaml"
          ? await api.importDemo()
          : await api.importFixture(name);
      setSnap(next);
      setWorkspaceId(next.organizationId);
      nav("/map");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function loadUpload() {
    setBusy(true);
    setError(null);
    try {
      const next = await api.importContent(content, format);
      setSnap(next);
      setWorkspaceId(next.organizationId);
      nav("/map");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Workspace / Import</h1>
      <p className="lede">
        Import a local JSON/YAML organization description. The builder validates and
        normalizes into a canonical registry. Nothing is deployed; discovery is read-only.
      </p>
      <EvidenceLegend />
      <JourneyNav current="/" nextDisabled={!snap} nextHint="Import an organization first" />

      <div className="panel">
        <h2>Fixture paths</h2>
        <p className="lede">
          <strong>Demo</strong> includes seeded defects and is expected to end{" "}
          <span className="mono">BLOCKED_NO_ELIGIBLE_CANDIDATE</span>.{" "}
          <strong>Eligible</strong> is a clean org you can approve and export.
        </p>
        <div className="row">
          <button disabled={busy} onClick={() => void loadFixture("demo-org.yaml")}>
            Load demo organization
          </button>
          <button
            className="secondary"
            disabled={busy}
            onClick={() => void loadFixture("eligible-org.yaml")}
          >
            Load eligible organization
          </button>
        </div>
        <p className="mono" style={{ marginTop: "0.75rem" }}>
          fixtures/demo-org.yaml · fixtures/eligible-org.yaml · or CLI: pnpm seed
        </p>
        {seeded.length > 0 && (
          <ul>
            {seeded.map((w) => (
              <li key={w.organizationId}>
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() => {
                    setWorkspaceId(w.organizationId);
                    nav("/map");
                  }}
                >
                  Open {w.name}
                </button>{" "}
                <span className="mono">{w.organizationId}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="panel">
        <h2>Upload organization</h2>
        <div className="field">
          <label htmlFor="format">Format</label>
          <select
            id="format"
            value={format}
            onChange={(e) => setFormat(e.target.value as "yaml" | "json")}
          >
            <option value="yaml">YAML</option>
            <option value="json">JSON</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="content">Organization description</label>
          <textarea
            id="content"
            rows={14}
            placeholder="Paste JSON or YAML…"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </div>
        <button disabled={busy || !content.trim()} onClick={() => void loadUpload()}>
          Import & validate
        </button>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
