# CetaSignal
### Marine Acoustic Language Research Platform

> Open-source platform for cetacean vocalization analysis. Maps acoustic cadence features to behavioral outcomes using verified observational records from NOAA and DCLDE archives.

---

## What This Is

CetaSignal is a research instrument — not a game, not a visualizer.

It is built on one core hypothesis: **cetacean vocalizations encode behavioral coordination through cadence structure** (frequency contour, inter-pulse interval, duration, urgency) rather than lexical content. Signal meaning is not carried by what sound is made — it is carried by *how* it is timed, shaped, and patterned within a set of physical and biological constraints.

This platform provides:

1. **A specimen library** — catalogued vocalizations with full provenance, acoustic parameters, environmental context, and behavioral ground-truth records
2. **An analysis sandbox** — plug any specimen into the cadence model, receive a behavioral prediction, and backtest it against the verified observational record
3. **A constraint framework** — the theoretical basis: SOFAR exploitation, 3D coordination, pod cohesion under low-visibility conditions, prey distribution signaling
4. **A full data provenance chain** — every specimen traces to a public archive with DOI, citation, annotation methodology, and direct access URL

---

## The Sandbox (Core Feature)

Select any specimen from the library → click ANALYSE → the `CadenceClassifier-v1.0` generates a behavioral class prediction from acoustic features alone → compare against ground truth.

**What the model uses:**
- Peak frequency (Hz)
- Frequency contour (rising / descending / flat / complex)
- Duration (s)
- Inter-pulse interval (ms)
- Urgency index (composite)
- Repetition rate (Hz)

**What it predicts:**
`CONTACT` · `DIVE` · `FORAGE` · `NAVIGATE` · `BROADCAST`

**The evidence trail** shows every rule that fired, the score contribution, and the rationale from bioacoustics literature — fully transparent, no black box.

---

## Data Sources

All data is sourced from publicly archived, peer-reviewed or government-curated datasets.

| Source | Institution | DOI | Specimens |
|--------|------------|-----|-----------|
| NOAA NEFSC / DCLDE 2013 | NOAA Northeast Fisheries Science Center | — | NARW, Fin, Sei, Blue, Humpback, Minke |
| DCLDE Oahu 2022 | NOAA Pacific Islands Fisheries Science Center | [10.25921/e12p-gj65](https://doi.org/10.25921/e12p-gj65) | False killer whale, Sperm whale, Delphinids |
| NOAA NCEI Passive Acoustic Archive | NOAA NCEI | [10.25921/PF0H-SQ72](https://doi.org/10.25921/PF0H-SQ72) | All North Atlantic cetaceans |
| Orca DCLDE — Myers et al. 2025 | Multiple institutions | [10.5281/zenodo.15743033](https://doi.org/10.5281/zenodo.15743033) | Southern Resident KW, Bigg's KW, Offshore KW |
| NOAA SanctSound | NOAA ONMS + U.S. Navy | [10.25921/kcxh-8368](https://doi.org/10.25921/kcxh-8368) | Humpback, Blue, Fin, Sperm |

All specimen records in the platform include: catalog ID, institution, annotator, annotation method (software + protocol), recording location + coordinates, license, citation, and direct dataset URL.

---

## The Acquisition Hypothesis

The key to decoding cetacean communication is not adult vocalizations — it is **juvenile learning sequences**.

Adult signals are optimized, compressed, and context-dependent. Juvenile signals reveal the acquisition process: a calf producing an approximate upcall and observing behavioral consequences is running a natural experiment in signal-behavior grounding. Tracking this across development — call approximation → behavioral response → call refinement — reconstructs the protocol layer that adults execute automatically.

No published study has systematically tracked this cycle in cetacean calves. This is the primary empirical gap CetaSignal is designed to surface and support.

---

## Running Locally

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

No backend required. The cadence model runs entirely in the browser. All specimen data is embedded in the application.

---

## Architecture

```
cetasignal/
├── frontend/
│   └── src/
│       └── App.jsx          # Complete single-file React application
│           ├── DATA_REGISTRY    # 5 source datasets with full provenance
│           ├── SPECIMENS        # 6 catalogued specimens with behavioral records
│           ├── CONSTRAINTS      # Physical + biological constraint framework
│           ├── runCadenceModel  # Transparent rule-based classifier
│           └── Components:
│               ├── Observatory  # Specimen library with detail panel
│               ├── SandboxPanel # Plug-and-play backtesting engine
│               ├── ConstraintFramework
│               └── SourcesRegistry
```

The entire application is a single self-contained React file. No external API dependencies. No authentication. Designed to be deployed anywhere static files are served.

---

## Extending the Platform

### Adding a specimen
Add an entry to the `SPECIMENS` array in `App.jsx`. Required fields:
- `catalogId` — unique identifier with source prefix
- `species` — binomial nomenclature
- `sourceDataset` — must match an entry in `DATA_REGISTRY`
- `acousticFeatures` — peak frequency, contour, duration, IPI, urgency, repetition
- `behavioralRecord` — observed behavior, description, ground truth method
- `acquisitionRelevance` — constraint mapping + juvenile response data if available
- `citations` — formatted academic citations

### Adding a data source
Add an entry to `DATA_REGISTRY`. Required fields: institution, annotation method, DOI (if available), citation, access URL, license.

### Improving the model
`runCadenceModel()` in `App.jsx` is the classifier. It is rule-based (V1) and fully transparent. Replace with a trained Random Forest or neural network by swapping the function — the evidence trail interface expects the same output schema.

---

## Grant Context

This platform is designed to support research proposals to:
- NSF Division of Biological Infrastructure (DBI)
- NOAA Ocean Exploration and Research Program
- National Geographic Society Science & Exploration
- Wellcome Trust Open Research Fund
- Schmidt Ocean Institute

The platform itself constitutes a methodology — the sandbox backtesting engine is a repeatable experimental protocol for testing cadence-behavior correlation hypotheses across species.

---

## License

MIT. All specimen data sourced from U.S. Government Public Domain archives or open-licensed research publications. Citations required for academic use — see individual specimen records.

---

## Citation

```
CetaSignal Research Platform (2025). Marine Acoustic Language Research Platform v1.0.
Open-source. https://github.com/cetasignal/platform
```
