import { useState, useEffect, useRef } from 'react';
import { SPECIMENS } from '../data/specimens';
import { DATA_REGISTRY } from '../data/registry';
import { BEHAVIORAL_CLASSES } from '../lib/classifier';
import { drawSpectrogram } from '../lib/drawing';
import { Label, SectionHeader } from './shared';

const gtMap = {
  "Pod convergence": "CONTACT",
  "Long-range contact — call-response exchange": "CONTACT",
  "Dive initiation": "DIVE",
  "Foraging spread formation": "FORAGE",
  "Sustained directional migration": "NAVIGATE",
  "Stationary broadcasting": "BROADCAST",
};

function SpecimenDetail({ specimen: s, onAnalyse }) {
  const src = DATA_REGISTRY.find(d => d.id === s.sourceDataset);
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    drawSpectrogram(canvasRef.current, s.acousticFeatures);
  }, [s]);

  return (
    <div style={{ border: "1px solid #0F1E2A", borderRadius: 4, overflow: "hidden" }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid #0F1E2A", background: "#080E14" }}>
        <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.15em", marginBottom: 6 }}>{s.catalogId}</div>
        <div style={{ fontSize: 15, color: "#8AAABB", fontStyle: "italic", fontFamily: "'IBM Plex Serif', serif" }}>{s.species}</div>
        <div style={{ fontSize: 11, color: "#5A7A8A", marginTop: 3 }}>{s.commonName} · {s.callType}</div>
      </div>

      <div style={{ padding: 20 }}>
        <div style={{ marginBottom: 20 }}>
          <Label>SPECTROGRAM VISUALIZATION</Label>
          <div style={{ background: "#050A10", borderRadius: 3, overflow: "hidden", marginTop: 8 }}>
            <canvas ref={canvasRef} width={480} height={120} style={{ width: "100%", height: "auto" }} />
          </div>
          <div style={{ fontSize: 9, color: "#2A4050", marginTop: 4 }}>Synthetic representation — generated from documented acoustic parameters. Real WAV available from source dataset.</div>
        </div>

        <div style={{ marginBottom: 20 }}>
          <Label>ACOUSTIC PARAMETERS</Label>
          <div style={{ marginTop: 10 }} className="grid-2">
            {[
              ["Peak Frequency", `${s.acousticFeatures.peakFrequency_hz} Hz`, ""],
              ["Duration", `${s.acousticFeatures.duration_s} s`, ""],
              ["Frequency Range", `${s.acousticFeatures.frequencyRange_hz[0]}–${s.acousticFeatures.frequencyRange_hz[1]} Hz`, ""],
              ["Contour", s.acousticFeatures.freqContour, ""],
              ["Urgency Index", s.acousticFeatures.urgencyIndex.toFixed(2), `${s.acousticFeatures.urgencyIndex * 100}%`],
              ["IPI", s.acousticFeatures.interPulseInterval_ms ? `${s.acousticFeatures.interPulseInterval_ms} ms` : "N/A (tonal)", ""],
            ].map(([k, v]) => (
              <div key={k} style={{ borderBottom: "1px solid #0A1520", paddingBottom: 8, marginBottom: 8 }}>
                <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.1em", marginBottom: 3 }}>{k}</div>
                <div style={{ fontSize: 12, color: "#7A9AAA" }}>{v}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: 20 }}>
          <Label>BEHAVIORAL RECORD</Label>
          <div style={{ marginTop: 10, background: "#080E14", border: "1px solid #132030", borderRadius: 3, padding: 14 }}>
            <div style={{ fontSize: 11, color: "#5DB8C8", marginBottom: 8 }}>{s.behavioralRecord.observedBehavior}</div>
            <p style={{ fontSize: 11, color: "#5A7A8A", lineHeight: 1.7, marginBottom: 10 }}>{s.behavioralRecord.description}</p>
            <div style={{ fontSize: 9, color: "#2A4050", letterSpacing: "0.1em" }}>GROUND TRUTH METHOD: {s.behavioralRecord.groundTruthMethod}</div>
            {s.behavioralRecord.observerNotes && (
              <div style={{ marginTop: 8, fontSize: 10, color: "#3A5A6A", fontStyle: "italic", borderTop: "1px solid #0F1E2A", paddingTop: 8 }}>{s.behavioralRecord.observerNotes}</div>
            )}
          </div>
        </div>

        <div style={{ marginBottom: 20 }}>
          <Label>LANGUAGE ACQUISITION RELEVANCE</Label>
          <div style={{ marginTop: 10, background: "#080E14", border: "1px solid #132030", borderRadius: 3, padding: 14 }}>
            <p style={{ fontSize: 11, color: "#5A7A8A", lineHeight: 1.7, marginBottom: 8 }}>{s.acquisitionRelevance.constraintMapped}</p>
            {s.acquisitionRelevance.juvenileResponse && (
              <div style={{ borderTop: "1px solid #0F1E2A", paddingTop: 10, marginTop: 8 }}>
                <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.1em", marginBottom: 5 }}>JUVENILE RESPONSE DATA</div>
                <p style={{ fontSize: 11, color: "#5A7A8A", lineHeight: 1.7 }}>{s.acquisitionRelevance.juvenileResponse}</p>
              </div>
            )}
          </div>
        </div>

        <div style={{ marginBottom: 20, padding: 12, background: "#050A10", border: "1px solid #0A1520", borderRadius: 3 }}>
          <div style={{ fontSize: 9, color: "#2A4050", letterSpacing: "0.1em", marginBottom: 4 }}>SOURCE DATASET</div>
          <div style={{ fontSize: 11, color: "#5A7A8A", marginBottom: 4 }}>{src?.fullName}</div>
          <div style={{ fontSize: 9, color: "#2A4050", marginBottom: 2 }}>{src?.citation}</div>
          {src?.doi && <div style={{ fontSize: 9, color: "#3A5A6A" }}>DOI: {src.doi}</div>}
          <a href={src?.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 9, color: "#5DB8C8", textDecoration: "none", letterSpacing: "0.08em", display: "inline-block", marginTop: 6 }}>↗ ACCESS DATASET</a>
        </div>

        <div style={{ marginBottom: 20 }}>
          <Label>LITERATURE</Label>
          <div style={{ marginTop: 10 }}>
            {s.citations.map((c, i) => (
              <div key={i} style={{ fontSize: 10, color: "#3A5A6A", padding: "6px 0", borderBottom: "1px solid #0A1520", lineHeight: 1.6 }}>[{i + 1}] {c}</div>
            ))}
          </div>
        </div>

        <button className="btn-primary" style={{ width: "100%" }} onClick={onAnalyse}>
          RUN CADENCE ANALYSIS IN SANDBOX →
        </button>
      </div>
    </div>
  );
}

export default function SpecimenLibrary({ onAnalyse, userSpecimens = [] }) {
  const [selectedSpecimen, setSelectedSpecimen] = useState(null);
  const allSpecimens = [...SPECIMENS, ...userSpecimens];

  return (
    <div className="fade-in" style={{ paddingTop: 32 }}>
      <SectionHeader
        label="ACOUSTIC SPECIMEN LIBRARY"
        sub="Catalogued cetacean vocalizations with full provenance, environmental context, and behavioral ground-truth records"
        sourceCount={DATA_REGISTRY.length}
        specimenCount={allSpecimens.length}
      />

      <div style={{ display: "grid", gridTemplateColumns: selectedSpecimen ? "1fr 1.2fr" : "1fr", gap: 24, marginTop: 24 }}>
        <div>
          <div style={{ border: "1px solid #0F1E2A", borderRadius: 4, overflow: "hidden" }}>
            <div style={{ padding: "10px 20px", borderBottom: "1px solid #0F1E2A", display: "grid", gridTemplateColumns: "140px 1fr 80px 80px", gap: 16, fontSize: 9, color: "#3A5A6A", letterSpacing: "0.12em", textTransform: "uppercase" }}>
              <div>CATALOG ID</div><div>SPECIMEN</div><div>CLASS</div><div>ACTION</div>
            </div>
            {allSpecimens.map(s => {
              const bcKey = gtMap[s.behavioralRecord.observedBehavior] || "CONTACT";
              const bc = BEHAVIORAL_CLASSES[bcKey];
              const isSelected = selectedSpecimen?.id === s.id;
              return (
                <div
                  key={s.id}
                  className={`specimen-row ${isSelected ? "selected" : ""}`}
                  onClick={() => setSelectedSpecimen(isSelected ? null : s)}
                >
                  <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.08em" }}>{s.catalogId}</div>
                  <div>
                    <div style={{ fontSize: 11, color: "#8AAABB", fontStyle: "italic" }}>{s.species}</div>
                    <div style={{ fontSize: 9, color: "#4A6A7A", marginTop: 2 }}>{s.callType}</div>
                  </div>
                  <div style={{ fontSize: 9, color: bc?.color, letterSpacing: "0.06em" }}>{bcKey}</div>
                  <button className="btn-primary" style={{ fontSize: 9, padding: "4px 10px" }} onClick={(e) => { e.stopPropagation(); onAnalyse(s); }}>
                    ANALYSE
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {selectedSpecimen && (
          <SpecimenDetail
            specimen={selectedSpecimen}
            onAnalyse={() => onAnalyse(selectedSpecimen)}
          />
        )}
      </div>
    </div>
  );
}
