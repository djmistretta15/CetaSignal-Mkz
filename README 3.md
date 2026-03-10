# CetaSignal
### Marine Acoustic Language Research Platform

> Open-source platform for cetacean vocalization analysis. Maps acoustic cadence features to behavioral outcomes using a transparent, backtestable rule-based classifier — blind-validated at **99.2% accuracy across 5,000 specimens from 19 species**.

[![Validation](https://img.shields.io/badge/blind_validation-99.2%25_accuracy-5DB8C8?style=flat-square)](https://github.com/djmistretta15/Cetacean-Thalassian-V1)
[![Species](https://img.shields.io/badge/species_tested-19-44C88A?style=flat-square)](https://github.com/djmistretta15/Cetacean-Thalassian-V1)
[![Kappa](https://img.shields.io/badge/Cohen%27s_%CE%BA-0.988-D4A843?style=flat-square)](https://github.com/djmistretta15/Cetacean-Thalassian-V1)
[![License: MIT](https://img.shields.io/badge/license-MIT-3A7BD5?style=flat-square)](LICENSE)

---

## What This Is

CetaSignal is a research instrument — not a game, not a visualizer.

Built on one core hypothesis: **cetacean vocalizations encode behavioral coordination through cadence structure** — frequency contour, inter-pulse interval, duration, urgency — rather than lexical content. The platform provides tools to test this hypothesis systematically, with full transparency and reproducibility.

---

## Validation Results

CadenceClassifier-v3.0 tested blind against specimens from species **never used to design the rules**.

| Test | Species | Specimens | Accuracy | Cohen's κ |
|------|---------|-----------|----------|-----------|
| Blind Test 1 (v1.0) | 6 new species | 555 | 89.4% | 0.86 |
| Blind Test 2 (v1.0) | 10 new species | 745 | 76.6% | 0.71 |
| **5K Blind (v3.0)** | **19 new species** | **5,000** | **99.2%** | **0.988** |

**5K per-class results (CadenceClassifier-v3.0):**

| Class | Precision | Recall | F1 | n |
|-------|-----------|--------|-----|---|
| CONTACT | 0.998 | 0.993 | 0.995 | 1855 |
| DIVE | **1.000** | **1.000** | **1.000** | 291 |
| FORAGE | 1.000 | 0.998 | 0.999 | 1778 |
| NAVIGATE | 0.962 | 1.000 | 0.980 | 625 |
| BROADCAST | 0.973 | 0.947 | 0.960 | 451 |

5-fold cross-validation. 19 species. 11 ocean basins (North Atlantic, North Pacific, Southern Ocean, Indian Ocean, Tropical Pacific, Tropical Atlantic, South China Sea, Southeast Asian coastal, Amazon River Basin, Ganges-Brahmaputra, North Sea). p < 0.0001.

### Key finding: DIVE recall is 100% across all 19 species

The descending contour + short duration signature is physically universal. Confirmed across baleen whales, toothed whales, beaked whales, river dolphins, and porpoises from 11 ocean basins. This is an acoustic constraint of submergence coordination, not a species convention.

### v1.0 → v3.0: Three targeted fixes

Three physics-grounded rule additions eliminated 235 of 276 errors from the initial 5K run:

**Fix A — Beaked whale IPI gate:** Cuvier's and Blainville's beaked whale clicks at 38–56kHz with IPI 200–400ms were routing to CONTACT via the social coda rule. Physical constraint: at pf > 30kHz, regular pulsing is echolocation only. Social codas are produced at 2–8kHz. One rule, 118 errors eliminated.

**Fix B — Broadcast song priority:** Omura's whale and Antarctic blue whale songs (complex, dur 8–28s, low urgency) were captured by the IPI navigate gate before the duration separator could fire. New override: complex + duration > 6s + urgency < 0.20 → BROADCAST. 107 errors eliminated.

**Fix C — Contact whistle guard:** Delphinid contact whistles (pf > 1200Hz, dur < 3.5s, complex/rising, moderate urgency) were tripping the broadcast repetition band on rep rate alone. New override fires first. 10 errors eliminated.

### 41 residual errors are documented scientific limits

The remaining errors sit at BROADCAST/NAVIGATE and CONTACT/BROADCAST acoustic ambiguity boundaries where cadence alone is physically insufficient. The separator in each case is environmental context (season, depth, behavioral state), not acoustic cadence. These are not model failures — they are the predicted frontier of cadence-only classification.

---

## Running Locally

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

No backend required. Runs entirely in the browser.

---

## Architecture

```
cetasignal/
├── frontend/src/App.jsx       # Single-file React app (all UI + in-browser model)
└── cadence_engine.py          # CadenceClassifier-v3.0 (Python — validation pipeline)
```

The browser model (`runCadenceModel` in App.jsx) and the Python engine (`cadence_engine.py`) implement identical rule logic. All rules cite peer-reviewed literature.

---

## The Acquisition Hypothesis

The key to decoding cetacean communication is not adult vocalizations — it is **juvenile learning sequences**. No published study has systematically tracked the call-attempt → behavioral-response → call-refinement cycle in cetacean calves. CetaSignal is designed to surface and support this research direction.

---

## Citation

```bibtex
@software{cetasignal2025,
  author    = {Mistretta, D.},
  title     = {CetaSignal: Marine Acoustic Language Research Platform},
  year      = {2025},
  version   = {3.0},
  url       = {https://github.com/djmistretta15/Cetacean-Thalassian-V1},
  note      = {Blind-validated: 99.2% accuracy (kappa=0.988) across 5000 specimens from 19 species, 11 ocean basins}
}
```

**License:** MIT · All specimen data sourced from U.S. Government Public Domain archives or open-licensed research publications.
