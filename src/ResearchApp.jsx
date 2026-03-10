import { useState, useCallback } from 'react';
import { SPECIMENS } from './data/specimens';
import { runCadenceModel } from './lib/classifier';
import SpecimenLibrary from './components/SpecimenLibrary';
import SandboxPanel from './components/SandboxPanel';
import ConstraintFramework from './components/ConstraintFramework';
import TheoryPanel from './components/TheoryPanel';
import ValidationPanel from './components/ValidationPanel';
import DataSources from './components/DataSources';

const TABS = [
  ["observatory", "SPECIMEN LIBRARY"],
  ["sandbox",     "ANALYSIS SANDBOX"],
  ["framework",   "CONSTRAINT FRAMEWORK"],
  ["theory",      "THEORY & FINDINGS"],
  ["validation",  "VALIDATION"],
  ["sources",     "DATA SOURCES"],
];

export default function ResearchApp({ onPlayGame }) {
  const [activeTab, setActiveTab] = useState("observatory");
  const [sandboxSpecimen, setSandboxSpecimen] = useState(null);
  const [sandboxResult, setSandboxResult] = useState(null);
  const [sandboxRunning, setSandboxRunning] = useState(false);
  const [userSpecimens, setUserSpecimens] = useState([]);

  const runSandbox = useCallback((specimen) => {
    setSandboxSpecimen(specimen);
    setSandboxResult(null);
    setSandboxRunning(true);
    setTimeout(() => {
      setSandboxResult(runCadenceModel(specimen.acousticFeatures));
      setSandboxRunning(false);
    }, 1400);
  }, []);

  const handleAnalyse = useCallback((specimen) => {
    runSandbox(specimen);
    setActiveTab("sandbox");
  }, [runSandbox]);

  const handleAddToLibrary = useCallback((specimen) => {
    setUserSpecimens(prev => prev.find(s => s.id === specimen.id) ? prev : [...prev, specimen]);
  }, []);

  const allSpecimens = [...SPECIMENS, ...userSpecimens];

  return (
    <div style={{ fontFamily: "'IBM Plex Mono', monospace", background: "#07090F", color: "#C8D8E8", minHeight: "100vh" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Serif:ital,wght@0,300;0,400;1,300&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; } ::-webkit-scrollbar-track { background: #0D1117; } ::-webkit-scrollbar-thumb { background: #1E3A4A; }
        .nav-item { cursor: pointer; padding: 8px 16px; font-size: 11px; letter-spacing: 0.12em; color: #5A7A8A; border-bottom: 1px solid transparent; transition: all 0.2s; text-transform: uppercase; }
        .nav-item:hover { color: #8AAABB; }
        .nav-item.active { color: #5DB8C8; border-bottom-color: #5DB8C8; }
        .specimen-row { cursor: pointer; padding: 14px 20px; border-bottom: 1px solid #0F1E2A; transition: background 0.15s; display: grid; grid-template-columns: 140px 1fr 80px 80px; align-items: center; gap: 16px; }
        .specimen-row:hover { background: rgba(93,184,200,0.04); }
        .specimen-row.selected { background: rgba(93,184,200,0.07); border-left: 2px solid #5DB8C8; }
        .feature-bar { height: 3px; background: #0F1E2A; border-radius: 2px; overflow: hidden; }
        .feature-bar-fill { height: 100%; border-radius: 2px; transition: width 0.6s ease; }
        .source-card { border: 1px solid #132030; border-radius: 4px; overflow: hidden; }
        .source-header { padding: 14px 18px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background 0.15s; }
        .source-header:hover { background: rgba(93,184,200,0.04); }
        .source-body { padding: 18px; border-top: 1px solid #132030; background: #080E14; }
        .tag { display: inline-block; padding: 2px 8px; border-radius: 2px; font-size: 9px; letter-spacing: 0.1em; font-weight: 600; text-transform: uppercase; }
        .btn-primary { background: transparent; border: 1px solid #5DB8C8; color: #5DB8C8; padding: 8px 18px; font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.1em; cursor: pointer; border-radius: 2px; transition: all 0.2s; text-transform: uppercase; }
        .btn-primary:hover { background: rgba(93,184,200,0.1); }
        .btn-primary:disabled { opacity: 0.35; cursor: not-allowed; }
        .evidence-row { padding: 10px 12px; border-left: 2px solid #132030; margin-bottom: 8px; }
        .metric-box { border: 1px solid #132030; border-radius: 3px; padding: 14px 16px; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
        @media (max-width: 768px) { .grid-2, .grid-3 { grid-template-columns: 1fr; } .specimen-row { grid-template-columns: 1fr 1fr; } }
        .fade-in { animation: fadeIn 0.4s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
        .pulse-dot { width: 6px; height: 6px; border-radius: 50%; background: #5DB8C8; animation: pulse 1.6s ease-in-out infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.7); } }
        canvas { display: block; }
      `}</style>

      <header style={{ borderBottom: "1px solid #0F1E2A", position: "sticky", top: 0, background: "#07090F", zIndex: 100 }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 24, padding: "14px 0" }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: "0.15em", color: "#8AAABB" }}>CETASIGNAL</div>
              <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.2em", marginTop: 1 }}>MARINE ACOUSTIC LANGUAGE RESEARCH PLATFORM</div>
            </div>
            <div style={{ width: 1, height: 28, background: "#0F1E2A" }} />
            <nav style={{ display: "flex", gap: 2 }}>
              {TABS.map(([id, label]) => (
                <div key={id} className={`nav-item ${activeTab === id ? "active" : ""}`} onClick={() => setActiveTab(id)}>{label}</div>
              ))}
            </nav>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ fontSize: 9, color: "#2A4050", letterSpacing: "0.12em" }}>v3.0 · 99.2% VALIDATED</div>
            {onPlayGame && (
              <button
                onClick={onPlayGame}
                style={{ background: "transparent", border: "1px solid #44C88A", color: "#44C88A", padding: "6px 14px", fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, letterSpacing: "0.1em", cursor: "pointer", borderRadius: 2, transition: "all 0.2s", textTransform: "uppercase" }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(68,200,138,0.1)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
              >
                PLAY GAME →
              </button>
            )}
          </div>
        </div>
      </header>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>
        {activeTab === "observatory" && (
          <SpecimenLibrary onAnalyse={handleAnalyse} userSpecimens={userSpecimens} />
        )}
        {activeTab === "sandbox" && (
          sandboxSpecimen ? (
            <SandboxPanel
              specimen={sandboxSpecimen}
              result={sandboxResult}
              running={sandboxRunning}
              onSelectNew={runSandbox}
              allSpecimens={allSpecimens}
              onAddToLibrary={handleAddToLibrary}
            />
          ) : (
            <div className="fade-in" style={{ paddingTop: 48, textAlign: "center" }}>
              <div style={{ fontSize: 11, color: "#3A5A6A", letterSpacing: "0.15em", marginBottom: 20 }}>NO SPECIMEN LOADED</div>
              <div style={{ fontSize: 11, color: "#2A4050", marginBottom: 24 }}>Select a specimen to analyse:</div>
              <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
                {SPECIMENS.slice(0, 4).map(s => (
                  <button key={s.id} className="btn-primary" style={{ fontSize: 10 }} onClick={() => handleAnalyse(s)}>
                    {s.callType}
                  </button>
                ))}
              </div>
            </div>
          )
        )}
        {activeTab === "framework" && <ConstraintFramework />}
        {activeTab === "theory"    && <TheoryPanel />}
        {activeTab === "validation" && <ValidationPanel />}
        {activeTab === "sources"   && <DataSources />}
      </div>
    </div>
  );
}
