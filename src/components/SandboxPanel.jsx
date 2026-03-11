import { useState, useEffect, useRef } from 'react';
import { BEHAVIORAL_CLASSES } from '../lib/classifier';
import { drawSpectrogram, drawBehaviorCanvas } from '../lib/drawing';
import { Label } from './shared';

const gtMap = {
  "Pod convergence": "CONTACT",
  "Long-range contact — call-response exchange": "CONTACT",
  "Dive initiation": "DIVE",
  "Foraging spread formation": "FORAGE",
  "Sustained directional migration": "NAVIGATE",
  "Stationary broadcasting": "BROADCAST",
};

export default function SandboxPanel({ specimen, result, running, onSelectNew, allSpecimens, onAddToLibrary }) {
  if (!specimen) return null;

  const canvasRef = useRef(null);
  const behaviorCanvasRef = useRef(null);
  const animRef = useRef(null);
  const [animTime, setAnimTime] = useState(0);

  useEffect(() => {
    if (!canvasRef.current) return;
    drawSpectrogram(canvasRef.current, specimen.acousticFeatures);
  }, [specimen]);

  useEffect(() => {
    if (!result || !behaviorCanvasRef.current) return;
    const start = Date.now();
    const tick = () => {
      setAnimTime((Date.now() - start) / 1000);
      animRef.current = requestAnimationFrame(tick);
    };
    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [result]);

  useEffect(() => {
    if (!behaviorCanvasRef.current || !result) return;
    drawBehaviorCanvas(behaviorCanvasRef.current, specimen, result, Math.min(animTime, 12));
  }, [animTime, result, specimen]);

  const groundTruthClass = gtMap[specimen.behavioralRecord.observedBehavior] || "CONTACT";
  const modelCorrect = result?.predictedClass === groundTruthClass;
  const bcGT = BEHAVIORAL_CLASSES[groundTruthClass];
  const bcPred = result ? BEHAVIORAL_CLASSES[result.predictedClass] : null;

  return (
    <div>
      {/* Specimen selector */}
      <div style={{ marginTop: 24, marginBottom: 24, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ fontSize: 10, color: "#3A5A6A", letterSpacing: "0.1em", marginRight: 6 }}>ACTIVE SPECIMEN:</div>
        {allSpecimens.map(s => {
          const isActive = s.id === specimen.id;
          return (
            <button key={s.id} className="btn-primary" style={{ fontSize: 9, padding: "4px 12px", borderColor: isActive ? "#5DB8C8" : "#132030", color: isActive ? "#5DB8C8" : "#3A5A6A", background: isActive ? "rgba(93,184,200,0.08)" : "transparent" }} onClick={() => { if (!isActive) onSelectNew(s); }}>
              {s.callType}
            </button>
          );
        })}
      </div>

      <div className="grid-2" style={{ gap: 20 }}>
        {/* Left — Input */}
        <div>
          <div style={{ border: "1px solid #0F1E2A", borderRadius: 4, overflow: "hidden" }}>
            <div style={{ padding: "12px 16px", background: "#080E14", borderBottom: "1px solid #0F1E2A" }}>
              <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.15em" }}>INPUT SPECIMEN</div>
              <div style={{ fontSize: 13, color: "#8AAABB", fontStyle: "italic", marginTop: 4 }}>{specimen.species}</div>
              <div style={{ fontSize: 10, color: "#5A7A8A", marginTop: 2 }}>{specimen.callType} · {specimen.catalogId}</div>
            </div>

            <div style={{ padding: 16 }}>
              <Label>ACOUSTIC PARAMETERS (INPUT TO MODEL)</Label>
              <div style={{ marginTop: 12 }}>
                {[
                  ["peakFrequency_hz", "Peak Frequency", "Hz", 0, 3000],
                  ["duration_s", "Duration", "s", 0, 25],
                  ["urgencyIndex", "Urgency Index", "", 0, 1],
                  ["repetitionHz", "Repetition Rate", "Hz", 0, 6],
                ].map(([key, label, unit, min, max]) => {
                  const val = specimen.acousticFeatures[key];
                  const pct = val != null ? ((val - min) / (max - min)) * 100 : 0;
                  return (
                    <div key={key} style={{ marginBottom: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.08em" }}>{label}</div>
                        <div style={{ fontSize: 10, color: "#7A9AAA" }}>{val != null ? `${val} ${unit}` : "N/A"}</div>
                      </div>
                      <div className="feature-bar">
                        <div className="feature-bar-fill" style={{ width: `${Math.min(pct, 100)}%`, background: "#5DB8C8" }} />
                      </div>
                    </div>
                  );
                })}
                <div style={{ marginTop: 10, padding: "8px 10px", background: "#050A10", borderRadius: 3 }}>
                  <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.08em", marginBottom: 3 }}>FREQUENCY CONTOUR</div>
                  <div style={{ fontSize: 11, color: "#7A9AAA" }}>{specimen.acousticFeatures.freqContour}</div>
                </div>
                <div style={{ marginTop: 8, padding: "8px 10px", background: "#050A10", borderRadius: 3 }}>
                  <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.08em", marginBottom: 3 }}>IPI (INTER-PULSE INTERVAL)</div>
                  <div style={{ fontSize: 11, color: "#7A9AAA" }}>{specimen.acousticFeatures.interPulseInterval_ms != null ? `${specimen.acousticFeatures.interPulseInterval_ms} ms` : "N/A — tonal signal"}</div>
                </div>
              </div>

              <div style={{ marginTop: 16 }}>
                <Label>SPECTROGRAM</Label>
                <div style={{ marginTop: 8, background: "#050A10", borderRadius: 3, overflow: "hidden" }}>
                  <canvas ref={canvasRef} width={400} height={90} style={{ width: "100%", height: "auto" }} />
                </div>
              </div>

              <div style={{ marginTop: 16 }}>
                <Label>RECORDING CONTEXT</Label>
                <div style={{ marginTop: 8, fontSize: 10, color: "#4A6A7A", lineHeight: 1.8 }}>
                  <div><span style={{ color: "#2A4050" }}>Location:</span> {specimen.recordingLocation}</div>
                  <div><span style={{ color: "#2A4050" }}>Year:</span> {specimen.recordingYear}</div>
                  <div><span style={{ color: "#2A4050" }}>Depth:</span> {specimen.recordingDepth_m}m</div>
                  <div><span style={{ color: "#2A4050" }}>SOFAR:</span> {specimen.environmentalContext.sofar ? "YES — long-range propagation channel active" : "No"}</div>
                  <div><span style={{ color: "#2A4050" }}>Season:</span> {specimen.environmentalContext.season}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right — Output */}
        <div>
          <div style={{ border: "1px solid #0F1E2A", borderRadius: 4, overflow: "hidden" }}>
            <div style={{ padding: "12px 16px", background: "#080E14", borderBottom: "1px solid #0F1E2A", display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.15em" }}>MODEL OUTPUT</div>
              {running && <div style={{ display: "flex", alignItems: "center", gap: 8 }}><div className="pulse-dot" /><div style={{ fontSize: 9, color: "#5A7A8A" }}>RUNNING CADENCE ANALYSIS...</div></div>}
              {result && <div style={{ fontSize: 9, color: "#3A5A6A" }}>{result.modelVersion}</div>}
            </div>

            <div style={{ padding: 16 }}>
              {!result && !running && (
                <div style={{ textAlign: "center", padding: "40px 20px", color: "#2A4050", fontSize: 11 }}>
                  Model output will appear here
                </div>
              )}

              {result && (
                <div className="fade-in">
                  <div className="grid-2" style={{ gap: 10, marginBottom: 20 }}>
                    <div style={{ border: `1px solid ${bcPred?.color}44`, borderRadius: 3, padding: "14px 16px", background: `${bcPred?.color}09` }}>
                      <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.1em", marginBottom: 8 }}>MODEL PREDICTION</div>
                      <div style={{ fontSize: 16, color: bcPred?.color, fontWeight: 500 }}>{bcPred?.label}</div>
                      <div style={{ fontSize: 10, color: "#5A7A8A", marginTop: 4 }}>{(result.confidence * 100).toFixed(0)}% confidence</div>
                      <div style={{ fontSize: 9, color: "#3A5A6A", marginTop: 4, lineHeight: 1.5 }}>{bcPred?.description}</div>
                    </div>
                    <div style={{ border: `1px solid ${bcGT?.color}66`, borderRadius: 3, padding: "14px 16px", background: `${bcGT?.color}12` }}>
                      <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.1em", marginBottom: 8 }}>OBSERVED BEHAVIOR</div>
                      <div style={{ fontSize: 16, color: bcGT?.color, fontWeight: 500 }}>{bcGT?.label}</div>
                      <div style={{ fontSize: 10, color: "#5A7A8A", marginTop: 4 }}>Ground truth</div>
                      <div style={{ fontSize: 9, color: "#3A5A6A", marginTop: 4, lineHeight: 1.5 }}>{specimen.behavioralRecord.observedBehavior}</div>
                    </div>
                  </div>

                  <div style={{ padding: "10px 14px", borderRadius: 3, marginBottom: 20, background: modelCorrect ? "rgba(68,200,138,0.07)" : "rgba(200,100,68,0.07)", border: `1px solid ${modelCorrect ? "#44C88A" : "#C86444"}44` }}>
                    <div style={{ fontSize: 11, color: modelCorrect ? "#44C88A" : "#C86444" }}>
                      {modelCorrect ? "✓ PREDICTION MATCHES OBSERVED BEHAVIOR" : "✗ PREDICTION DIVERGES FROM OBSERVED BEHAVIOR"}
                    </div>
                    <div style={{ fontSize: 10, color: "#4A6A7A", marginTop: 4, lineHeight: 1.6 }}>
                      {modelCorrect
                        ? `Cadence features alone sufficient to predict behavioral class. Confidence: ${(result.confidence * 100).toFixed(0)}%. This supports the hypothesis that acoustic cadence encodes coordination signal independently of lexical content.`
                        : `Divergence may indicate: (1) additional contextual features not captured in current model, (2) multi-function signal requiring environmental context, or (3) specimen-specific behavioral variation. See evidence trail for diagnostic detail.`}
                    </div>
                  </div>

                  <div style={{ marginBottom: 20 }}>
                    <Label>CLASS PROBABILITY DISTRIBUTION</Label>
                    <div style={{ marginTop: 12 }}>
                      {Object.entries(result.probabilities).sort((a, b) => b[1] - a[1]).map(([cls, prob]) => {
                        const bc = BEHAVIORAL_CLASSES[cls];
                        const isGT = cls === groundTruthClass;
                        const isPred = cls === result.predictedClass;
                        return (
                          <div key={cls} style={{ marginBottom: 8 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, alignItems: "center" }}>
                              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                <div style={{ fontSize: 10, color: bc?.color }}>{bc?.label}</div>
                                {isGT && <span className="tag" style={{ background: "rgba(68,200,138,0.1)", color: "#44C88A", border: "1px solid #44C88A33", fontSize: 8 }}>GROUND TRUTH</span>}
                                {isPred && !isGT && <span className="tag" style={{ background: "rgba(93,184,200,0.1)", color: "#5DB8C8", border: "1px solid #5DB8C833", fontSize: 8 }}>PREDICTED</span>}
                              </div>
                              <div style={{ fontSize: 10, color: "#5A7A8A" }}>{(prob * 100).toFixed(1)}%</div>
                            </div>
                            <div className="feature-bar">
                              <div className="feature-bar-fill" style={{ width: `${prob * 100}%`, background: bc?.color, opacity: isGT ? 1 : isPred ? 0.8 : 0.35 }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div style={{ marginBottom: 20 }}>
                    <Label>EVIDENCE TRAIL — HOW THE MODEL DECIDED</Label>
                    <div style={{ marginTop: 12 }}>
                      {result.evidence.map((e, i) => (
                        <div key={i} className="evidence-row" style={{ borderLeftColor: i === result.evidence.length - 1 ? "#5DB8C8" : "#132030" }}>
                          <div style={{ fontSize: 10, color: "#7A9AAA", marginBottom: 3 }}>{e.rule}</div>
                          <div style={{ fontSize: 9, color: "#3A7A9A", marginBottom: 3, fontFamily: "monospace" }}>{e.contribution}</div>
                          <div style={{ fontSize: 9, color: "#3A5A6A", lineHeight: 1.6 }}>{e.rationale}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div style={{ marginBottom: 16 }}>
                    <Label>BEHAVIORAL RECORD VISUALIZATION</Label>
                    <div style={{ marginTop: 10, background: "#050A10", borderRadius: 3, overflow: "hidden" }}>
                      <canvas ref={behaviorCanvasRef} width={440} height={180} style={{ width: "100%", height: "auto" }} />
                    </div>
                    <div style={{ marginTop: 6, fontSize: 9, color: "#2A4050", lineHeight: 1.6 }}>
                      {specimen.behavioralRecord.description} — {specimen.behavioralRecord.groundTruthMethod}
                    </div>
                  </div>

                  {onAddToLibrary && (
                    <button className="btn-primary" style={{ width: "100%", marginTop: 8 }} onClick={() => onAddToLibrary(specimen)}>
                      SAVE TO LIBRARY
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
