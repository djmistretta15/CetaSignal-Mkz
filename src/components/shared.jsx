export function Label({ children }) {
  return <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.15em", textTransform: "uppercase" }}>{children}</div>;
}

export function SourceField({ label, value, mono }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 9, color: "#2A4050", letterSpacing: "0.1em", marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: 10, color: "#5A7A8A", lineHeight: 1.6, fontFamily: mono ? "'IBM Plex Mono', monospace" : "inherit" }}>{value}</div>
    </div>
  );
}

export function SectionHeader({ label, sub, badge, sourceCount, specimenCount }) {
  return (
    <div style={{ borderBottom: "1px solid #0F1E2A", paddingBottom: 20, marginBottom: 4 }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 24 }}>
        <div>
          <div style={{ fontSize: 10, color: "#3A5A6A", letterSpacing: "0.2em", marginBottom: 8, textTransform: "uppercase" }}>
            {badge || "CETASIGNAL RESEARCH PLATFORM"}
          </div>
          <h1 style={{ fontSize: 18, fontWeight: 500, letterSpacing: "0.05em", color: "#8AAABB", marginBottom: 10 }}>{label}</h1>
          <p style={{ fontSize: 12, color: "#4A6A7A", lineHeight: 1.8, maxWidth: 680, fontFamily: "'IBM Plex Serif', serif", fontStyle: "italic" }}>{sub}</p>
        </div>
        {(sourceCount || specimenCount) && (
          <div style={{ display: "flex", gap: 12, flexShrink: 0 }}>
            {specimenCount && <div className="metric-box" style={{ textAlign: "center", minWidth: 80 }}><div style={{ fontSize: 22, fontWeight: 300, color: "#5DB8C8" }}>{specimenCount}</div><div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.1em", marginTop: 3 }}>SPECIMENS</div></div>}
            {sourceCount && <div className="metric-box" style={{ textAlign: "center", minWidth: 80 }}><div style={{ fontSize: 22, fontWeight: 300, color: "#5DB8C8" }}>{sourceCount}</div><div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.1em", marginTop: 3 }}>DATA SOURCES</div></div>}
          </div>
        )}
      </div>
    </div>
  );
}
