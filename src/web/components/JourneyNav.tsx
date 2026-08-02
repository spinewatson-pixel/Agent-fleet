import { Link } from "react-router-dom";

const STEPS = [
  { path: "/", label: "Import" },
  { path: "/map", label: "Org map" },
  { path: "/intent", label: "Intent" },
  { path: "/gaps", label: "Gaps" },
  { path: "/candidates", label: "Candidates" },
  { path: "/review", label: "Review" },
  { path: "/history", label: "History" },
] as const;

export function JourneyNav({
  current,
  nextDisabled,
  nextHint,
}: {
  current: (typeof STEPS)[number]["path"];
  nextDisabled?: boolean;
  nextHint?: string;
}) {
  const idx = STEPS.findIndex((s) => s.path === current);
  const prev = idx > 0 ? STEPS[idx - 1] : null;
  const next = idx >= 0 && idx < STEPS.length - 1 ? STEPS[idx + 1] : null;

  return (
    <div className="panel journey-nav">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          {prev ? (
            <Link className="button secondary" to={prev.path}>
              ← {prev.label}
            </Link>
          ) : (
            <span />
          )}
        </div>
        <div className="mono journey-steps">
          {STEPS.map((s, i) => (
            <span key={s.path} className={s.path === current ? "current" : undefined}>
              {i + 1}.{s.label}
              {i < STEPS.length - 1 ? " · " : ""}
            </span>
          ))}
        </div>
        <div>
          {next && !nextDisabled ? (
            <Link className="button" to={next.path}>
              {next.label} →
            </Link>
          ) : next ? (
            <span className="mono" title={nextHint}>
              {nextHint ?? "Complete this step to continue"}
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}
