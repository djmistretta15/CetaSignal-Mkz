# 🐋 CetaSignal

> *Can you decode what whales are saying before AI does?*

CetaSignal is an open-source platform that challenges humans to interpret whale acoustic signals — then reveals what the AI model predicted, and finally shows the **ground truth**: what the whale actually did next.

It's a game. It's a science experiment. It's a proof of concept for non-human language decoding.

---

## 🧠 The Hypothesis

Whale calls are not random noise. They encode **coordination signals** — spatial, temporal, behavioral instructions that let pods synchronize across hundreds of miles of dark ocean. 

By mapping **cadence → behavior** (not "words" → meaning), we can build a proto-grammar for whale communication — the same way you'd reverse-engineer any distributed protocol.

CetaSignal is the public validation layer for that hypothesis.

---

## 🎮 How It Works

```
[Hear Call] → [Make Your Guess] → [See AI Prediction] → [Ground Truth Revealed] → [Score]
```

1. **Play** — A real whale call plays with an animated spectrogram
2. **Guess** — You pick what you think the call means (Contact / Dive / Forage / Danger / Regroup)
3. **Predict** — The ML model makes its prediction in parallel (hidden until you guess)
4. **Reveal** — Animated whale behavior shows what actually happened after the call
5. **Score** — You vs. model vs. ground truth. Leaderboard tracks accuracy over time.

Every guess is logged anonymously — building a crowdsourced validation dataset that compares human intuition to model accuracy against behavioral ground truth.

---

## 📡 Data Sources

All data is from open public archives:

| Source | What We Use | URL |
|--------|-------------|-----|
| NOAA NEFSC | Annotated baleen whale calls (humpback, right whale, fin, blue, sei) | [fisheries.noaa.gov](https://www.fisheries.noaa.gov/resource/data/noaa-nefsc-north-atlantic-right-whale-acoustic-data-and-annotations) |
| NOAA NCEI Passive Acoustic Archive | Raw WAV hydrophone recordings | [ncei.noaa.gov](https://www.ncei.noaa.gov/products/passive-acoustic-data) |
| DCLDE Oahu 2022 | 47 days towed array + synchronized visual sightings | [soest.hawaii.edu](https://www.soest.hawaii.edu/ore/dclde/dataset/) |
| Watkins Marine Mammal Sound DB | Species-labeled call library (WHOI) | [cis.whoi.edu](https://cis.whoi.edu/science/B/whalesounds/) |

---

## 🏗️ Architecture

```
cetasignal/
├── frontend/          # React + Tailwind + Wavesurfer.js
│   └── src/
│       ├── components/    # AudioPlayer, Spectrogram, GuessUI, RevealScreen, Leaderboard
│       ├── pages/         # Game, About, Data, Results
│       ├── hooks/         # useAudioAnalysis, useGameState, useLeaderboard
│       └── utils/         # featureExtractor, scoreCalculator
│
├── backend/           # FastAPI + Python
│   ├── routes/        # /calls, /predict, /submit-guess, /leaderboard
│   ├── models/        # CadenceClassifier (librosa + sklearn)
│   └── utils/         # audio_features, behavior_mapper
│
├── scripts/           # Data pipeline scripts
│   ├── download_noaa.py       # Pull from NOAA GCP bucket
│   ├── extract_features.py    # WAV → cadence features JSON
│   ├── build_manifest.py      # Curated call manifest with behavioral outcomes
│   └── train_model.py         # Train classifier on annotated calls
│
└── data/
    ├── calls/         # WAV files (gitignored, downloaded via script)
    └── manifest.json  # Call metadata + behavioral outcomes
```

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- Git

### 1. Clone
```bash
git clone https://github.com/YOUR_USERNAME/cetasignal.git
cd cetasignal
```

### 2. Download Data
```bash
cd scripts
pip install -r requirements.txt
python download_noaa.py        # Downloads sample calls from NOAA GCP
python extract_features.py     # Extracts cadence features
python build_manifest.py       # Builds the call manifest
```

### 3. Train Model
```bash
python train_model.py
# Outputs: backend/models/cadence_classifier.pkl
```

### 4. Run Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 5. Run Frontend
```bash
cd frontend
npm install
npm run dev
# Opens http://localhost:5173
```

---

## 🧬 The Model

The cadence classifier extracts these features from each WAV file:

| Feature | Extraction | Meaning |
|---------|-----------|---------|
| Peak frequency (Hz) | librosa.yin | Signal class (low = long range, high = local) |
| Inter-pulse interval (ms) | scipy peak detection | Urgency / rhythm |
| Call duration (s) | onset/offset detection | Sustained vs. burst |
| Frequency contour | librosa.piptrack | Rising sweep vs. descending |
| Amplitude envelope | RMS over time | Confidence / intensity |
| Repetition rate | autocorrelation | Coordination vs. single broadcast |

These 6 features map to 5 behavioral classes:

| Class | Description | Key Signal Patterns |
|-------|-------------|-------------------|
| CONTACT | "I'm here / where are you?" | Low freq, long gap, sustained |
| DIVE | Descent coordination | Descending sweep, cluster burst |
| FORAGE | Food detection / spread out | Rapid repetition, rising pitch |
| DANGER | Predator / threat | High amplitude, rapid bursts |
| REGROUP | Pod consolidation | Pulsed hum, medium freq, regular interval |

---

## 📊 The Validation Loop

```
Human Guess Accuracy    Model Prediction Accuracy    Ground Truth Match Rate
       ↓                          ↓                           ↓
   ~40-60%                    ~65-80%                      100% (by definition)
   (baseline)               (target V1)                   (behavioral records)
```

As more humans play → more validation data → model improves → closes the gap.

When model accuracy consistently exceeds human accuracy on the same calls, the hypothesis is validated: **cadence encodes coordination signal.**

---

## 🔬 The 5 Starter Calls

| # | Species | Call Type | Behavioral Outcome | Duration |
|---|---------|-----------|-------------------|----------|
| 1 | North Atlantic Right Whale | Upcall | Pod approached / converged | 1.2s |
| 2 | Fin Whale | 20Hz pulse train | Directional heading change | 3.4s |
| 3 | Humpback | Song phrase | Stationary broadcast, no movement | 8.1s |
| 4 | Orca | Burst pulse cluster | Pod spread into foraging arc | 2.7s |
| 5 | Sei Whale | Downsweep | Dive initiation (depth -40m in 30s) | 0.9s |

---

## 🤝 Contributing

We need:
- Marine biologists to validate call classifications
- ML engineers to improve the cadence classifier
- Frontend devs to build richer behavioral animations
- Citizen scientists to play the game and generate validation data

Open an issue or PR. Everything is welcome.

---

## 📄 License

MIT — use this freely. Cite us if you publish findings.

---

## 🧭 Roadmap

- [ ] V1 — 5 call types, rule-based classifier, basic animation
- [ ] V2 — ML classifier trained on DCLDE dataset, 20+ calls
- [ ] V3 — Juvenile vs adult call comparison layer
- [ ] V4 — Playback experiment design tool (ethical protocol templates)
- [ ] V5 — Multi-species comparison (orca, dolphin, humpback dialects)
- [ ] V∞ — Species-agnostic cadence protocol decoder

---

*Built on the hypothesis that language is not words — it's constraint navigation between agents.*
