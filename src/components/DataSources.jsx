import { useState } from 'react';
import { DATA_REGISTRY } from '../data/registry';
import { SourceField } from './shared';

export default function DataSources() {
  const [expandedSource, setExpandedSource] = useState(null);

  return (
    <div style={{ marginTop: 28 }}>
      <p style={{ fontSize: 12, color: "#4A6A7A", lineHeight: 1.8, fontFamily: "'IBM Plex Serif', serif", marginBottom: 28, maxWidth: 640 }}>
        All data used in CetaSignal is sourced from publicly archived, peer-reviewed or government-curated datasets. Each source record below contains the complete provenance chain including institution, methodology, annotation protocol, license, DOI where available, and direct access URL.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {DATA_REGISTRY.map(src => (
          <div key={src.id} className="source-card">
            <div className="source-header" onClick={() => setExpandedSource(expandedSource === src.id ? null : src.id)}>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <div>
                  <div style={{ fontSize: 12, color: "#8AAABB" }}>{src.shortName}</div>
                  <div style={{ fontSize: 10, color: "#4A6A7A", marginTop: 2 }}>{src.type} · {src.institution}</div>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <div style={{ display: "flex", gap: 6 }}>
                  {src.doi && <span className="tag" style={{ background: "rgba(93,184,200,0.1)", color: "#5DB8C8", border: "1px solid #5DB8C833" }}>DOI</span>}
                  <span className="tag" style={{ background: "rgba(68,200,138,0.08)", color: "#44C88A", border: "1px solid #44C88A33" }}>PUBLIC</span>
                </div>
                <div style={{ fontSize: 11, color: "#3A5A6A" }}>{expandedSource === src.id ? "▲" : "▼"}</div>
              </div>
            </div>

            {expandedSource === src.id && (
              <div className="source-body fade-in">
                <div className="grid-2" style={{ gap: 20, marginBottom: 20 }}>
                  <div>
                    <SourceField label="FULL NAME" value={src.fullName} />
                    <SourceField label="INSTITUTION" value={src.institution} />
                    <SourceField label="ANNOTATORS" value={src.annotators} />
                    <SourceField label="YEARS COVERED" value={src.years} />
                    <SourceField label="LICENSE" value={src.license} />
                    {src.doi && <SourceField label="DOI" value={src.doi} mono />}
                  </div>
                  <div>
                    <SourceField label="LOCATION" value={`${src.location} (${src.coordinates.lat}°N, ${Math.abs(src.coordinates.lon)}°W)`} />
                    <SourceField label="SPECIES COVERED" value={src.species.join("; ")} />
                    <SourceField label="CALL TYPES" value={src.callTypes.join("; ")} />
                    <SourceField label="ANNOTATION METHOD" value={src.method} />
                  </div>
                </div>

                <div style={{ padding: "12px 16px", background: "#07090F", borderRadius: 3, marginBottom: 16 }}>
                  <div style={{ fontSize: 9, color: "#2A4050", letterSpacing: "0.1em", marginBottom: 6 }}>CITATION</div>
                  <div style={{ fontSize: 10, color: "#4A6A7A", lineHeight: 1.7, fontFamily: "'IBM Plex Serif', serif", fontStyle: "italic" }}>{src.citation}</div>
                </div>

                {src.notes && (
                  <div style={{ fontSize: 10, color: "#3A5A6A", lineHeight: 1.7, marginBottom: 16 }}>{src.notes}</div>
                )}

                <a href={src.url} target="_blank" rel="noopener noreferrer" style={{ display: "inline-block", fontSize: 10, color: "#5DB8C8", textDecoration: "none", letterSpacing: "0.08em", borderBottom: "1px solid #5DB8C844", paddingBottom: 1 }}>
                  ↗ ACCESS DATASET: {src.url}
                </a>
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 28, padding: 20, border: "1px dashed #132030", borderRadius: 4 }}>
        <div style={{ fontSize: 10, color: "#3A5A6A", letterSpacing: "0.12em", marginBottom: 10 }}>CONTRIBUTING ADDITIONAL SOURCES</div>
        <p style={{ fontSize: 11, color: "#4A6A7A", lineHeight: 1.7 }}>
          CetaSignal is an open research platform. Researchers with access to additional cetacean acoustic datasets with behavioral ground-truth records are invited to contribute via the project GitHub repository. All contributions must include full provenance, methodology documentation, and license confirmation.
        </p>
        <a href="https://github.com/cetasignal/platform" target="_blank" rel="noopener noreferrer" style={{ display: "inline-block", marginTop: 12, fontSize: 10, color: "#5DB8C8", textDecoration: "none", letterSpacing: "0.08em", borderBottom: "1px solid #5DB8C844" }}>
          ↗ CONTRIBUTE TO CETASIGNAL
        </a>
      </div>
    </div>
  );
}
