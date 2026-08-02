import type { ReactNode } from "react";
import { NavLink, Navigate, Route, Routes, useParams } from "react-router-dom";
import { createContext, useContext, useEffect, useState } from "react";
import { api, type WorkspaceSnapshot } from "./api";
import { ImportScreen } from "./screens/ImportScreen";
import { OrgMapScreen } from "./screens/OrgMapScreen";
import { IntentScreen } from "./screens/IntentScreen";
import { GapScreen } from "./screens/GapScreen";
import { CandidatesScreen } from "./screens/CandidatesScreen";
import { ReviewScreen } from "./screens/ReviewScreen";
import { HistoryScreen } from "./screens/HistoryScreen";

type Ctx = {
  workspaceId: string | null;
  snap: WorkspaceSnapshot | null;
  setWorkspaceId: (id: string | null) => void;
  refresh: () => Promise<void>;
  setSnap: (s: WorkspaceSnapshot | null) => void;
};

const WorkspaceCtx = createContext<Ctx | null>(null);

export function useWorkspace(): Ctx {
  const ctx = useContext(WorkspaceCtx);
  if (!ctx) throw new Error("WorkspaceCtx missing");
  return ctx;
}

export function App() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(
    () => localStorage.getItem("af_workspace") ?? null,
  );
  const [snap, setSnap] = useState<WorkspaceSnapshot | null>(null);

  const refresh = async () => {
    if (!workspaceId) {
      setSnap(null);
      return;
    }
    const s = await api.get(workspaceId);
    setSnap(s);
  };

  useEffect(() => {
    if (workspaceId) localStorage.setItem("af_workspace", workspaceId);
    else localStorage.removeItem("af_workspace");
    void refresh().catch(() => setSnap(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId]);

  const ready = Boolean(snap);
  const analyzed = Boolean(snap?.gapAnalysis);

  return (
    <WorkspaceCtx.Provider
      value={{ workspaceId, snap, setWorkspaceId, refresh, setSnap }}
    >
      <div className="app-shell">
        <aside className="sidebar">
          <p className="brand">Agent Fleet</p>
          <p className="brand-sub">Architecture Builder · advisory only</p>
          <nav className="nav">
            <NavLink to="/" end>
              Workspace / Import
            </NavLink>
            <NavLink className={ready ? undefined : "disabled"} to="/map">
              Organization Map
            </NavLink>
            <NavLink className={ready ? undefined : "disabled"} to="/intent">
              Intent & Evidence
            </NavLink>
            <NavLink className={ready ? undefined : "disabled"} to="/gaps">
              Gap Analysis
            </NavLink>
            <NavLink className={analyzed ? undefined : "disabled"} to="/candidates">
              Candidates & Validation
            </NavLink>
            <NavLink className={analyzed ? undefined : "disabled"} to="/review">
              Review & Decision
            </NavLink>
            <NavLink className={ready ? undefined : "disabled"} to="/history">
              Change History
            </NavLink>
          </nav>
          <div className="mode-pill">
            mode=advisory_export_only
            <br />
            mutation=rejected
            <br />
            llm=disabled
          </div>
        </aside>
        <main className="main">
          <Routes>
            <Route path="/" element={<ImportScreen />} />
            <Route path="/map" element={<Require snap={snap}><OrgMapScreen /></Require>} />
            <Route path="/intent" element={<Require snap={snap}><IntentScreen /></Require>} />
            <Route path="/gaps" element={<Require snap={snap}><GapScreen /></Require>} />
            <Route path="/candidates" element={<Require snap={snap}><CandidatesScreen /></Require>} />
            <Route path="/review" element={<Require snap={snap}><ReviewScreen /></Require>} />
            <Route path="/history" element={<Require snap={snap}><HistoryScreen /></Require>} />
            <Route path="/w/:id" element={<WorkspaceDeepLink setWorkspaceId={setWorkspaceId} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </WorkspaceCtx.Provider>
  );
}

function Require({
  snap,
  children,
}: {
  snap: WorkspaceSnapshot | null;
  children: ReactNode;
}) {
  if (!snap) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function WorkspaceDeepLink({
  setWorkspaceId,
}: {
  setWorkspaceId: (id: string) => void;
}) {
  const { id } = useParams();
  useEffect(() => {
    if (id) setWorkspaceId(id);
  }, [id, setWorkspaceId]);
  return <Navigate to="/map" replace />;
}
