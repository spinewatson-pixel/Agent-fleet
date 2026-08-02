export function EvidenceBadge({ status }: { status: string }) {
  const key = status === "observation" ? "fact" : status;
  return <span className={`badge ${status} ${key}`}>{status}</span>;
}

export function EvidenceLegend() {
  return (
    <div className="legend" aria-label="Evidence type legend">
      <EvidenceBadge status="observation" />
      <EvidenceBadge status="assertion" />
      <EvidenceBadge status="inference" />
      <EvidenceBadge status="simulation" />
      <EvidenceBadge status="recommendation" />
      <span className="mono" style={{ color: "var(--muted)" }}>
        observation = fact
      </span>
    </div>
  );
}
