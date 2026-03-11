import { CONSTRAINTS } from '../lib/classifier';

export default function ConstraintFramework() {
  return (
    <div style={{ marginTop: 32 }}>
      <div style={{ background: "#080E14", border: "1px solid #132030", borderRadius: 4, padding: 28, marginBottom: 28 }}>
        <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.15em", marginBottom: 12 }}>CENTRAL THESIS</div>
        <blockquote style={{ fontFamily: "'IBM Plex Serif', serif", fontSize: 16, color: "#7A9AAA", lineHeight: 1.8, fontStyle: "italic", borderLeft: "2px solid #5DB8C8", paddingLeft: 20, margin: 0 }}>
          "Language does not emerge in spite of constraint — it emerges because of it. The acoustic signaling systems of marine mammals are not approximations of human language; they are optimal solutions to the coordination problems imposed by a dark, three-dimensional, high-pressure medium. Cadence, not lexicon, is the primary encoding channel."
        </blockquote>
        <div style={{ fontSize: 9, color: "#2A4050", marginTop: 12 }}>CetaSignal Research Framework, 2025</div>
      </div>

      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 10, color: "#3A5A6A", letterSpacing: "0.15em", marginBottom: 16, textTransform: "uppercase" }}>Physical Constraints</div>
        <div className="grid-2">
          {CONSTRAINTS.physical.map(c => (
            <div key={c.id} style={{ border: "1px solid #0F1E2A", borderRadius: 3, padding: 18 }}>
              <div style={{ fontSize: 12, color: "#8AAABB", marginBottom: 8 }}>{c.label}</div>
              <p style={{ fontSize: 11, color: "#4A6A7A", lineHeight: 1.8, marginBottom: 10 }}>{c.description}</p>
              <div style={{ fontSize: 9, color: "#2A4050", letterSpacing: "0.08em" }}>RELEVANT: {c.relevantSpecies.join(", ")}</div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div style={{ fontSize: 10, color: "#3A5A6A", letterSpacing: "0.15em", marginBottom: 16, textTransform: "uppercase" }}>Biological Constraints</div>
        <div className="grid-3">
          {CONSTRAINTS.biological.map(c => (
            <div key={c.id} style={{ border: "1px solid #0F1E2A", borderRadius: 3, padding: 18 }}>
              <div style={{ fontSize: 12, color: "#8AAABB", marginBottom: 8 }}>{c.label}</div>
              <p style={{ fontSize: 11, color: "#4A6A7A", lineHeight: 1.8, marginBottom: 10 }}>{c.description}</p>
              <div style={{ fontSize: 9, color: "#2A4050", letterSpacing: "0.08em" }}>RELEVANT: {c.relevantSpecies.join(", ")}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginTop: 28, border: "1px solid #0F1E2A", borderRadius: 4, padding: 20 }}>
        <div style={{ fontSize: 10, color: "#3A5A6A", letterSpacing: "0.15em", marginBottom: 14 }}>ACQUISITION HYPOTHESIS</div>
        <p style={{ fontSize: 12, color: "#4A6A7A", lineHeight: 1.9, fontFamily: "'IBM Plex Serif', serif" }}>
          The key to decoding cetacean language is not adult vocalizations — it is juvenile learning sequences. Adult signals are compressed, optimized, and context-dependent. Juvenile signals reveal the mapping process: a young whale producing an approximate upcall and observing which behaviors it triggers is, functionally, a biological experiment in signal-behavior grounding. By instrumenting the gap between juvenile acoustic output and behavioral consequence across development, we can reconstruct the protocol layer that adult whales execute fluently.
        </p>
        <div style={{ marginTop: 18, padding: "12px 16px", background: "#050A10", borderRadius: 3 }}>
          <div style={{ fontSize: 9, color: "#3A5A6A", letterSpacing: "0.12em", marginBottom: 8 }}>RESEARCH PRIORITY</div>
          <p style={{ fontSize: 11, color: "#4A6A7A", lineHeight: 1.7 }}>
            Acoustic tagging of whale calves (&lt;6 months) with synchronized behavioral logging represents the highest-value research direction for language acquisition. No published study has systematically tracked call-attempt → behavior-consequence → call-modification cycles in cetacean calves. This is the critical empirical gap.
          </p>
        </div>
      </div>
    </div>
  );
}
