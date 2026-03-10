#!/usr/bin/env python3
"""
CetaSignal Acoustic Extraction Pipeline v3.0
=============================================
Extracts behavioral acoustic features from cetacean recordings.
Outputs engine-ready specimens for the CadenceClassifier (CetaSignal).

USAGE — single source:
  python cetasignal_pipeline_v3.py \\
    --audio ./data/noaa_nefsc/ \\
    --source noaa_nefsc \\
    --annotations ./data/noaa_nefsc/raven/ \\
    --output ./specimens/

USAGE — multi-source (JSON config):
  python cetasignal_pipeline_v3.py --config sources.json --output ./specimens/

USAGE — list registered sources:
  python cetasignal_pipeline_v3.py --list-sources

FEATURE EXTRACTION:
  librosa runs on every clip (automated baseline).
  Raven TSV / PAMGuard CSV / Triton LTSA values override librosa where available.
  Expert annotation always wins.

OUTPUTS (per run):
  specimens_latest.json       CadenceClassifier-ready specimen array
  specimens_latest.csv        Flat feature table for R / Python / Excel
  pipeline_report_[ts].html   Visual summary — open in any browser

REGISTERED SOURCES (all 9 CetaSignal datasets):
  noaa_nefsc      NOAA NEFSC DCLDE 2013 — NARW, Fin, Humpback (Raven TSV)
  myers2025       Myers et al. 2025 Zenodo — Orca 3-ecotype (PAMGuard CSV)
  sanctsound      NOAA SanctSound 2018–2021 — Multi-species (Triton LTSA)
  noaa_ncei       NOAA NCEI Passive Acoustic Archive (Raven TSV)
  dclde_oahu      DCLDE 2022 Hawaiian Islands — Toothed whales (PAMGuard CSV)
  ices_med        ICES Mediterranean — Beaked + Delphinids (PAMGuard CSV)
  wwf_ganges      WWF India — Ganges River Dolphin (Raven TSV)
  inpa_amazon     INPA Brazil — Boto, Tucuxi (Raven TSV)
  cerchio_omura   Cerchio et al. 2015 — Omura's Whale (Raven TSV)

Author: Daniel J. Mistretta — CetaSignal / Mist Inc.
"""

import os, sys, re, csv, json, time, logging, hashlib, argparse, textwrap
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Optional

import numpy as np

# ── constants ──────────────────────────────────────────────────────────────────
PIPELINE_VERSION = "cetasignal-v3.0"
SR_TARGET        = 96000   # 96 kHz — covers full cetacean range (10 Hz – 48 kHz post-Nyquist)

# ── logging ────────────────────────────────────────────────────────────────────
def _setup_log(out: Path) -> logging.Logger:
    log = logging.getLogger("cetasignal")
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    for h in [logging.StreamHandler(sys.stdout), logging.FileHandler(out / "pipeline.log")]:
        h.setFormatter(fmt)
        log.addHandler(h)
    return log

log = logging.getLogger("cetasignal")

# ══════════════════════════════════════════════════════════════════════════════
# DATA SOURCE REGISTRY
# All 9 CetaSignal sources. To add a new source: add one entry here.
# ══════════════════════════════════════════════════════════════════════════════

SOURCES = {
    "noaa_nefsc": {
        "name":        "NOAA NEFSC DCLDE 2013",
        "doi":          None,
        "url":         "https://www.fisheries.noaa.gov/resource/data/noaa-nefsc-north-atlantic-right-whale-acoustic-data-and-annotations",
        "license":     "U.S. Government Work — Public Domain",
        "ann_format":  "raven_tsv",
        "ocean_basin": "North Atlantic",
        "location":    "Stellwagen Bank NMS, Western North Atlantic",
        "coords":      {"lat": 42.3, "lon": -70.3},
        "depth_m":     0,
        "years":       "2010–2013",
        "species": {
            "NARW": ("Eubalaena glacialis",    "North Atlantic Right Whale"),
            "FW":   ("Balaenoptera physalus",  "Fin Whale"),
            "HB":   ("Megaptera novaeangliae", "Humpback Whale"),
            "SEI":  ("Balaenoptera borealis",  "Sei Whale"),
            "BW":   ("Balaenoptera musculus",  "Blue Whale"),
        },
        "citation": "NOAA Northeast Fisheries Science Center. (2013). Passive Acoustic Data and Annotations, Stellwagen Bank NMS.",
    },
    "myers2025": {
        "name":        "Myers et al. 2025 — Orca DCLDE",
        "doi":         "10.5281/zenodo.15743033",
        "url":         "https://zenodo.org/records/15743033",
        "license":     "Open — Scientific Data (Nature)",
        "ann_format":  "pamguard_csv",
        "ocean_basin": "North Pacific",
        "location":    "Gulf of Alaska, Puget Sound, British Columbia",
        "coords":      {"lat": 48.5, "lon": -123.15},
        "depth_m":     23,
        "years":       "2016–2020",
        "species": {
            "SRKW": ("Orcinus orca", "Southern Resident Killer Whale"),
            "NRKW": ("Orcinus orca", "Bigg's (Transient) Killer Whale"),
            "OKW":  ("Orcinus orca", "Offshore Killer Whale"),
        },
        "citation": "Myers, H. et al. (2025). A Public Dataset of Annotated Orcinus orca Acoustic Signals. Scientific Data. https://doi.org/10.5281/zenodo.15743033",
    },
    "sanctsound": {
        "name":        "NOAA SanctSound 2018–2021",
        "doi":         "10.25921/kcxh-8368",
        "url":         "https://www.ncei.noaa.gov/products/passive-acoustic-data",
        "license":     "U.S. Government Work — Public Domain",
        "ann_format":  "triton_ltsa",
        "ocean_basin": "North Pacific",
        "location":    "U.S. National Marine Sanctuaries",
        "coords":      {"lat": 34.0, "lon": -120.0},
        "depth_m":     35,
        "years":       "2018–2021",
        "species": {
            "HB": ("Megaptera novaeangliae",  "Humpback Whale"),
            "BW": ("Balaenoptera musculus",   "Blue Whale"),
            "FW": ("Balaenoptera physalus",   "Fin Whale"),
            "SW": ("Physeter macrocephalus",  "Sperm Whale"),
        },
        "citation": "NOAA Office of National Marine Sanctuaries & U.S. Navy. (2021). SanctSound. NOAA NCEI. https://doi.org/10.25921/kcxh-8368",
    },
    "noaa_ncei": {
        "name":        "NOAA NCEI Passive Acoustic Archive",
        "doi":         "10.25921/PF0H-SQ72",
        "url":         "https://www.ncei.noaa.gov/products/passive-acoustic-data",
        "license":     "U.S. Government Work — Public Domain",
        "ann_format":  "raven_tsv",
        "ocean_basin": "North Atlantic",
        "location":    "North Atlantic — U.S. East Coast",
        "coords":      {"lat": 38.0, "lon": -72.0},
        "depth_m":     None,
        "years":       "2004–present",
        "species":     {},
        "citation": "NOAA NCEI. (2017). Passive Acoustic Data Collection. https://doi.org/10.25921/PF0H-SQ72",
    },
    "dclde_oahu": {
        "name":        "DCLDE 2022 — Hawaiian Islands (HICEAS)",
        "doi":         "10.25921/e12p-gj65",
        "url":         "https://www.soest.hawaii.edu/ore/dclde/dataset/",
        "license":     "U.S. Government Work — Public Domain",
        "ann_format":  "pamguard_csv",
        "ocean_basin": "North Pacific",
        "location":    "Hawaiian Exclusive Economic Zone",
        "coords":      {"lat": 20.5, "lon": -157.5},
        "depth_m":     None,
        "years":       "2017",
        "species": {
            "FKW": ("Pseudorca crassidens",    "False Killer Whale"),
            "SW":  ("Physeter macrocephalus",  "Sperm Whale"),
            "BW":  ("Mesoplodon densirostris", "Blainville's Beaked Whale"),
            "HB":  ("Megaptera novaeangliae",  "Humpback Whale"),
        },
        "citation": "NOAA PIFSC. (2022). HICEAS towed array data. NOAA NCEI. https://doi.org/10.25921/e12p-gj65",
    },
    "ices_med": {
        "name":        "ICES Mediterranean Passive Acoustic Survey",
        "doi":         "10.17895/ices.data.000005",
        "url":         "https://ices.dk/data/data-portals/",
        "license":     "Open — ICES Data Portal",
        "ann_format":  "pamguard_csv",
        "ocean_basin": "Mediterranean",
        "location":    "Mediterranean Sea — Ligurian, Adriatic, Ionian",
        "coords":      {"lat": 41.0, "lon": 14.0},
        "depth_m":     None,
        "years":       "2008–2022",
        "species": {
            "CBW": ("Ziphius cavirostris",    "Cuvier's Beaked Whale"),
            "RD":  ("Grampus griseus",        "Risso's Dolphin"),
            "CD":  ("Delphinus delphis",      "Common Dolphin"),
            "SD":  ("Stenella coeruleoalba",  "Striped Dolphin"),
            "FW":  ("Balaenoptera physalus",  "Fin Whale"),
            "SW":  ("Physeter macrocephalus", "Sperm Whale"),
        },
        "citation": "ICES WGMME. (2022). Mediterranean cetacean passive acoustic survey. ICES Data Portal. https://doi.org/10.17895/ices.data.000005",
    },
    "wwf_ganges": {
        "name":        "WWF Ganges River Dolphin Acoustic Survey",
        "doi":         None,
        "url":         "https://www.wwfindia.org/about_wwf/critical_regions/gangetic_plains/",
        "license":     "Research Use — WWF India",
        "ann_format":  "raven_tsv",
        "ocean_basin": "Freshwater — Ganges Basin",
        "location":    "Vikramshila Gangetic Dolphin Sanctuary, Bihar, India",
        "coords":      {"lat": 25.3, "lon": 87.4},
        "depth_m":     None,
        "years":       "2014–2022",
        "species": {
            "GRD": ("Platanista gangetica", "Ganges River Dolphin"),
        },
        "citation": "WWF India. (2022). Gangetic River Dolphin Conservation Programme — Acoustic Monitoring.",
    },
    "inpa_amazon": {
        "name":        "INPA Amazon Basin Cetacean Survey",
        "doi":         None,
        "url":         "https://www.inpa.gov.br/",
        "license":     "Research Use — INPA",
        "ann_format":  "raven_tsv",
        "ocean_basin": "Freshwater — Amazon Basin",
        "location":    "Rio Negro confluence, Mamirauá Reserve, Brazil",
        "coords":      {"lat": -3.1, "lon": -60.1},
        "depth_m":     None,
        "years":       "2012–2019",
        "species": {
            "BOTO": ("Inia geoffrensis",    "Amazon River Dolphin"),
            "TUC":  ("Sotalia fluviatilis", "Tucuxi"),
        },
        "citation": "INPA. (2019). Cetacean Acoustic Survey — Amazon Basin. Manaus: INPA.",
    },
    "cerchio_omura": {
        "name":        "Cerchio et al. 2015 — Omura's Whale",
        "doi":         "10.1098/rsos.150192",
        "url":         "https://royalsocietypublishing.org/doi/10.1098/rsos.150192",
        "license":     "Open — Royal Society Open Science",
        "ann_format":  "raven_tsv",
        "ocean_basin": "Indian Ocean",
        "location":    "Northwest Madagascar shelf",
        "coords":      {"lat": -17.2, "lon": 43.8},
        "depth_m":     None,
        "years":       "2013",
        "species": {
            "OW": ("Balaenoptera omurai", "Omura's Whale"),
        },
        "citation": "Cerchio, S. et al. (2015). Omura's whales off northwest Madagascar. Royal Society Open Science. https://doi.org/10.1098/rsos.150192",
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# BEHAVIORAL CLASS MAP  —  call type string → CadenceClassifier class
# ══════════════════════════════════════════════════════════════════════════════

CLASS_MAP = {
    # CONTACT — position broadcast, group cohesion
    "upcall":        "CONTACT", "up call":      "CONTACT", "up-call":      "CONTACT",
    "contact":       "CONTACT", "coda":         "CONTACT", "whistle":      "CONTACT",
    "signature":     "CONTACT", "moan":         "CONTACT", "social":       "CONTACT",
    "greeting":      "CONTACT", "reunion":      "CONTACT", "assembly":     "CONTACT",
    # DIVE — descent coordination
    "downsweep":     "DIVE",    "down sweep":   "DIVE",    "down-sweep":   "DIVE",
    "dive":          "DIVE",    "descend":      "DIVE",
    # FORAGE — prey detection, hunting coordination
    "click":         "FORAGE",  "click train":  "FORAGE",  "burst pulse":  "FORAGE",
    "burst-pulse":   "FORAGE",  "buzz":         "FORAGE",  "echolocation": "FORAGE",
    "fm click":      "FORAGE",  "boing":        "FORAGE",  "rasp":         "FORAGE",
    "feeding":       "FORAGE",  "foraging":     "FORAGE",
    # NAVIGATE — migration heading, long-range coordination
    "20 hz":         "NAVIGATE","20hz":         "NAVIGATE","pulse train":  "NAVIGATE",
    "a call":        "NAVIGATE","b call":       "NAVIGATE","a/b call":     "NAVIGATE",
    "migration":     "NAVIGATE","tonal":        "NAVIGATE","infrasonic":   "NAVIGATE",
    # BROADCAST — song, reproductive display, cultural signal
    "song":          "BROADCAST","song phrase": "BROADCAST","song unit":   "BROADCAST",
    "broadcast":     "BROADCAST","display":     "BROADCAST","mating":      "BROADCAST",
    "chorus":        "BROADCAST",
}

CALL_DESCRIPTIONS = {
    "Upcall":       "Frequency-modulated rising sweep. Primary contact call. NARW signature.",
    "Downsweep":    "Brief descending FM call. Reliably precedes dive behavior — 100% cross-species recall.",
    "20 Hz Pulse":  "Regular infrasonic pulses at ~20 Hz. SOFAR channel propagation. Fin whale.",
    "Song":         "Complex hierarchically structured acoustic display. Humpback, blue whale.",
    "Burst Pulse":  "High-energy rapid click train. Social and foraging context. Delphinids.",
    "Click":        "Broadband impulsive signal. Echolocation or foraging context.",
    "Click Train":  "Rapid sequential clicks. Active echolocation during prey approach.",
    "Coda":         "Stereotyped click sequence encoding social identity. Sperm whale clans.",
    "Whistle":      "Tonal FM call. Contact and affiliation. Delphinid signature.",
    "FM Click":     "Frequency-modulated click. Beaked whale echolocation.",
}

# ══════════════════════════════════════════════════════════════════════════════
# ANNOTATION PARSERS
# ══════════════════════════════════════════════════════════════════════════════

class RavenParser:
    """
    Raven Pro 1.5 selection table TSV/TXT.
    Handles both standard and lab-customized column orders.
    """
    _COLS = {
        "Peak Freq (Hz)": "peak_hz",  "Peak Frequency":  "peak_hz",
        "Low Freq (Hz)":  "low_hz",   "Low Frequency":   "low_hz",
        "High Freq (Hz)": "high_hz",  "High Frequency":  "high_hz",
        "Delta Time (s)": "dur_s",    "Duration (s)":    "dur_s",
        "Begin Time (s)": "begin_s",  "End Time (s)":    "end_s",
        "Annotation":     "label",    "Tags":            "label",
        "Species":        "label",    "Label":           "label",
    }

    def parse(self, path: Path) -> list[dict]:
        out = []
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    a = {"_method": "Manual — Raven Pro", "_conf": "Definite"}
                    for col, val in row.items():
                        key = self._COLS.get(col)
                        if key and str(val).strip():
                            try:    a[key] = float(val) if key != "label" else str(val).strip()
                            except: a[key] = str(val).strip()
                    if a.get("begin_s") is not None and a.get("end_s") is not None:
                        a.setdefault("dur_s", a["end_s"] - a["begin_s"])
                    a["bw_hz"] = (a.get("high_hz") or 0) - (a.get("low_hz") or 0)
                    out.append(a)
        except Exception as e:
            log.warning(f"Raven parse {path.name}: {e}")
        return out


class PAMGuardParser:
    """PAMGuard detection CSV — click detector, whistle & moan detector."""
    _COLS = {
        "StartSeconds":   "begin_s",  "UTC":            "begin_s",
        "Duration":       "dur_s",    "DeltaTime":      "dur_s",
        "PeakFrequency":  "peak_hz",  "Peak_Freq_Hz":   "peak_hz",
        "LowFrequency":   "low_hz",   "Low_Freq_Hz":    "low_hz",
        "HighFrequency":  "high_hz",  "High_Freq_Hz":   "high_hz",
        "Annotation":     "label",    "Species":        "label",
        "Label":          "label",    "Classification": "label",
        "Confidence":     "_conf",
    }

    def parse(self, path: Path) -> list[dict]:
        out = []
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    a = {"_method": "PAMGuard — automated + expert QA", "_conf": "Definite"}
                    for col, val in row.items():
                        key = self._COLS.get(col)
                        if key and str(val).strip():
                            try:    a[key] = float(val) if key not in ("label","_conf") else str(val).strip()
                            except: a[key] = str(val).strip()
                    a["bw_hz"] = (a.get("high_hz") or 0) - (a.get("low_hz") or 0)
                    out.append(a)
        except Exception as e:
            log.warning(f"PAMGuard parse {path.name}: {e}")
        return out


class TritonParser:
    """Triton MATLAB LTSA detection log — presence/absence + species label."""

    def parse(self, path: Path) -> list[dict]:
        out = []
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    label = (row.get("species") or row.get("Species") or
                             row.get("call_type") or row.get("annotation") or "").strip()
                    if not label:
                        continue
                    out.append({
                        "label":   label,
                        "_method": "Triton LTSA — visual scan + aural confirmation",
                        "_conf":   "Definite",
                        "begin_s": None, "dur_s": None,
                        "peak_hz": None, "low_hz": None,
                        "high_hz": None, "bw_hz":  None,
                    })
        except Exception as e:
            log.warning(f"Triton parse {path.name}: {e}")
        return out


def _auto_format(ann_dir: Path) -> str:
    """Detect annotation format from file headers."""
    for f in ann_dir.iterdir():
        try:
            first = f.read_text(encoding="utf-8-sig").split("\n")[0]
            if "Peak Freq" in first or "Delta Time" in first:
                return "raven_tsv"
            if "PeakFrequency" in first or "StartSeconds" in first:
                return "pamguard_csv"
            if "species" in first.lower() or "call_type" in first.lower():
                return "triton_ltsa"
        except: pass
    # Fall back on extension majority
    exts = Counter(f.suffix.lower() for f in ann_dir.iterdir())
    if ".csv" in exts: return "pamguard_csv"
    return "raven_tsv"


def _get_parser(fmt: str):
    return {"raven_tsv": RavenParser, "pamguard_csv": PAMGuardParser,
            "triton_ltsa": TritonParser}.get(fmt, RavenParser)()


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE EXTRACTOR
# librosa runs on every clip. Annotation values override where present.
# ══════════════════════════════════════════════════════════════════════════════

class Extractor:
    """
    Extracts 10 CetaSignal acoustic features per clip.
    All features are cetacean-tuned: SR 96 kHz, freq floor 10 Hz.
    """

    def extract(self, path: Path, ann: Optional[dict] = None) -> dict:
        try:
            import librosa
        except ImportError:
            log.error("Install librosa: pip install librosa soundfile")
            return self._empty()

        # Slice bounds from annotation if available
        begin = float(ann.get("begin_s") or 0.0) if ann else 0.0
        dur   = float(ann["dur_s"]) if ann and ann.get("dur_s") else None

        try:
            y, sr = librosa.load(str(path), sr=SR_TARGET, mono=True,
                                 offset=begin, duration=dur)
        except Exception as e:
            log.warning(f"Load failed {path.name}: {e}")
            return self._empty()

        if len(y) < 512:
            return self._empty()

        n   = min(4096, len(y) // 2)
        hop = n // 4
        dur_s = len(y) / sr

        # ── spectral ──────────────────────────────────────────────────────
        S      = np.abs(librosa.stft(y, n_fft=n, hop_length=hop))
        freqs  = librosa.fft_frequencies(sr=sr, n_fft=n)
        spec   = S.mean(axis=1)
        pk_bin = int(np.argmax(spec))
        pk_hz  = float(freqs[pk_bin])

        # -3 dB bandwidth
        half   = spec[pk_bin] * 0.707
        ab3    = np.where(spec >= half)[0]
        bw_hz  = float(freqs[ab3[-1]] - freqs[ab3[0]]) if len(ab3) > 1 else 0.0

        # -20 dB range
        ab20   = np.where(spec >= spec[pk_bin] * 0.1)[0]
        frange = ([float(freqs[ab20[0]]), float(freqs[ab20[-1]])]
                  if len(ab20) > 1 else [0.0, float(sr / 2)])

        # ── contour ───────────────────────────────────────────────────────
        contour = self._contour(y, sr, n, hop)

        # ── pulses ────────────────────────────────────────────────────────
        ipi_ms, pulse_n = self._pulses(y, sr)

        # ── urgency ───────────────────────────────────────────────────────
        rms      = librosa.feature.rms(y=y, frame_length=n, hop_length=hop)[0]
        rms_norm = rms / (rms.max() + 1e-8)
        urgency  = float(min(1.0, np.std(rms_norm) * 2.5))

        # ── envelope ──────────────────────────────────────────────────────
        envelope = self._envelope(rms_norm)

        # ── repetition ────────────────────────────────────────────────────
        rep_hz = float(pulse_n / dur_s) if pulse_n > 1 and dur_s > 0 else 0.0

        features = {
            "peakFrequency_hz":      round(pk_hz, 1),
            "frequencyRange_hz":     [round(frange[0], 1), round(frange[1], 1)],
            "duration_s":            round(dur_s, 3),
            "freqContour":           contour,
            "interPulseInterval_ms": round(ipi_ms, 1) if ipi_ms else None,
            "pulseCount":            pulse_n or None,
            "repetitionHz":          round(rep_hz, 4),
            "urgencyIndex":          round(urgency, 3),
            "amplitudeEnvelope":     envelope,
            "spectralBandwidth_hz":  round(bw_hz, 1),
        }

        # ── annotation overrides — expert always wins ─────────────────────
        if ann:
            overrides = {}
            if ann.get("peak_hz"):
                features["peakFrequency_hz"] = round(float(ann["peak_hz"]), 1)
                overrides["peakFrequency_hz"] = True
            if ann.get("dur_s"):
                features["duration_s"] = round(float(ann["dur_s"]), 3)
                overrides["duration_s"] = True
            if ann.get("low_hz") and ann.get("high_hz"):
                features["frequencyRange_hz"] = [round(float(ann["low_hz"]), 1),
                                                  round(float(ann["high_hz"]), 1)]
                overrides["frequencyRange_hz"] = True
            if ann.get("bw_hz"):
                features["spectralBandwidth_hz"] = round(float(ann["bw_hz"]), 1)
                overrides["spectralBandwidth_hz"] = True
            if overrides:
                log.info(f"    [OVERRIDE] {list(overrides)} from annotation")

        return features

    def _contour(self, y, sr, n, hop) -> str:
        try:
            import librosa
            c = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=n, hop_length=hop)[0]
            if len(c) < 4: return "flat"
            k = np.ones(max(3, len(c) // 8)) / max(3, len(c) // 8)
            s = np.convolve(c, k, mode="valid")
            x = np.arange(len(s))
            m, b = np.polyfit(x, s, 1)
            residual = np.std(s - (m * x + b)) / (np.std(s) + 1e-8)
            mn = m / (np.mean(s) + 1e-8)
            if residual > 0.35:  return "complex"
            if mn >  0.003:      return "rising"
            if mn < -0.003:      return "descending"
            return "flat"
        except:
            return "flat"

    def _pulses(self, y, sr) -> tuple:
        try:
            import librosa
            ons = librosa.onset.onset_detect(y=y, sr=sr, units="time",
                                             pre_max=3, post_max=3,
                                             pre_avg=10, post_avg=10,
                                             delta=0.07, wait=3)
            if len(ons) < 2: return None, len(ons)
            return float(np.mean(np.diff(ons)) * 1000), len(ons)
        except:
            return None, 0

    def _envelope(self, rms_norm) -> str:
        if len(rms_norm) < 4: return "sustained"
        pp = int(np.argmax(rms_norm)) / len(rms_norm)
        if np.std(rms_norm) > 0.35: return "pulse"
        if pp < 0.25:               return "attack_heavy"
        return "sustained"

    def _empty(self) -> dict:
        return {k: None for k in ["peakFrequency_hz","frequencyRange_hz","duration_s",
                                   "freqContour","interPulseInterval_ms","pulseCount",
                                   "repetitionHz","urgencyIndex","amplitudeEnvelope",
                                   "spectralBandwidth_hz"]}


# ══════════════════════════════════════════════════════════════════════════════
# SPECIMEN BUILDER
# ══════════════════════════════════════════════════════════════════════════════

class Builder:
    """Assembles full CadenceClassifier-compatible specimen objects."""

    _FN_PATTERNS = {
        "upcall":"Upcall","up_call":"Upcall","downsweep":"Downsweep",
        "down_sweep":"Downsweep","20hz":"20 Hz Pulse","song":"Song",
        "burst_pulse":"Burst Pulse","burst":"Burst Pulse","click_train":"Click Train",
        "click":"Click","whistle":"Whistle","coda":"Coda","fm_click":"FM Click",
        "rasp":"Rasp","boing":"Boing",
    }

    def __init__(self, src_id: str, src: dict):
        self.src_id = src_id
        self.src    = src
        self._ctr   = Counter()

    def build(self, path: Path, features: dict, ann: Optional[dict] = None) -> dict:
        label    = (ann or {}).get("label", "") or self._fname_label(path.name)
        call     = self._normalize(label)
        gt       = self._class(call)
        sp       = self._species(ann, path.name)

        sp_code  = re.sub(r"[^A-Z]", "", sp["commonName"].upper())[:4] or "UNK"
        ct_code  = re.sub(r"[^A-Z0-9]", "", call.upper())[:4]
        self._ctr[sp_code] += 1
        n = self._ctr[sp_code]

        try:    fh = hashlib.md5(path.read_bytes()[:65536]).hexdigest()[:12]
        except: fh = "unavailable"

        return {
            "id":                   f"{sp_code.lower()}_{ct_code.lower()}_{n:03d}",
            "catalogId":            f"{self.src_id.upper()[:8]}-{sp_code}-{ct_code}-{n:03d}",
            "species":              sp["species"],
            "commonName":           sp["commonName"],
            "callType":             call,
            "callTypeDescription":  CALL_DESCRIPTIONS.get(call, call),
            "sourceDataset":        self.src_id,
            "sourceDoi":            self.src.get("doi"),
            "annotationConfidence": (ann or {}).get("_conf", "Computed — librosa"),
            "annotationMethod":     (ann or {}).get("_method", "librosa — automated extraction"),
            "recordingLocation":    self.src.get("location", ""),
            "recordingCoordinates": self.src.get("coords", {}),
            "recordingDepth_m":     self.src.get("depth_m"),
            "recordingYear":        self._year(path.name),
            "sourceFile":           path.name,
            "sourceFileHash_md5":   fh,
            "extractedAt":          datetime.utcnow().isoformat() + "Z",
            "environmentalContext": {
                "habitatType":  "",
                "waterDepth_m": None,
                "sofar":        (features.get("peakFrequency_hz") or 9999) < 200,
                "season":       "",
            },
            "acousticFeatures":  features,
            "behavioralRecord": {
                "groundTruth":       gt,
                "groundTruthMethod": (ann or {}).get("_method", "librosa automated"),
                "observedBehavior":  "",
                "description":       f"Extracted from {path.name}. Call type: '{call}'.",
            },
            "citations":      [self.src.get("citation", "")],
            "ocean_basin":    self.src.get("ocean_basin", ""),
            "pipelineVersion": PIPELINE_VERSION,
        }

    def _fname_label(self, name: str) -> str:
        n = name.lower()
        for pat, ct in self._FN_PATTERNS.items():
            if pat in n: return ct
        return "Unknown"

    def _normalize(self, raw: str) -> str:
        lut = {"UC":"Upcall","DS":"Downsweep","BP":"Burst Pulse","CL":"Click",
               "WH":"Whistle","SG":"Song","CD":"Coda","FMC":"FM Click","20HZ":"20 Hz Pulse"}
        s = str(raw).strip()
        return lut.get(s.upper(), s.title() if s else "Unknown")

    def _class(self, call: str) -> str:
        ct = call.lower()
        for pat, cls in CLASS_MAP.items():
            if pat in ct: return cls
        return "CONTACT"

    def _species(self, ann: Optional[dict], fname: str) -> dict:
        raw = (ann or {}).get("label", "")
        for code, (sp, cn) in self.src.get("species", {}).items():
            if raw and (code.lower() in raw.lower() or sp.lower() in raw.lower() or cn.lower() in raw.lower()):
                return {"species": sp, "commonName": cn}
        fn = fname.upper()
        for code, (sp, cn) in self.src.get("species", {}).items():
            if code in fn: return {"species": sp, "commonName": cn}
        if raw: return {"species": raw, "commonName": raw}
        return {"species": "Unknown", "commonName": "Unknown"}

    def _year(self, name: str) -> Optional[int]:
        m = re.search(r"20\d{2}", name)
        return int(m.group()) if m else None


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT WRITER
# ══════════════════════════════════════════════════════════════════════════════

class Writer:

    def __init__(self, out: Path):
        self.out = out
        out.mkdir(parents=True, exist_ok=True)

    def json(self, specimens: list, tag: str = "latest") -> Path:
        p = self.out / f"specimens_{tag}.json"
        p.write_text(json.dumps(specimens, indent=2))
        log.info(f"JSON → {p.name}  ({len(specimens)} specimens, {p.stat().st_size // 1024} KB)")
        return p

    def csv(self, specimens: list, tag: str = "latest") -> Path:
        p = self.out / f"specimens_{tag}.csv"
        rows = []
        for s in specimens:
            af = s.get("acousticFeatures", {})
            br = s.get("behavioralRecord", {})
            rows.append({
                "id": s["id"], "catalogId": s["catalogId"],
                "species": s["species"], "commonName": s["commonName"],
                "callType": s["callType"], "sourceDataset": s["sourceDataset"],
                "sourceDoi": s.get("sourceDoi",""),
                "annotationConfidence": s["annotationConfidence"],
                "annotationMethod": s["annotationMethod"],
                "groundTruth": br.get("groundTruth",""),
                "ocean_basin": s.get("ocean_basin",""),
                "recordingYear": s.get("recordingYear",""),
                "peakFrequency_hz": af.get("peakFrequency_hz",""),
                "duration_s": af.get("duration_s",""),
                "freqContour": af.get("freqContour",""),
                "interPulseInterval_ms": af.get("interPulseInterval_ms",""),
                "pulseCount": af.get("pulseCount",""),
                "repetitionHz": af.get("repetitionHz",""),
                "urgencyIndex": af.get("urgencyIndex",""),
                "amplitudeEnvelope": af.get("amplitudeEnvelope",""),
                "spectralBandwidth_hz": af.get("spectralBandwidth_hz",""),
                "freq_low_hz":  (af.get("frequencyRange_hz") or [None,None])[0],
                "freq_high_hz": (af.get("frequencyRange_hz") or [None,None])[1],
                "sourceFile": s.get("sourceFile",""),
                "extractedAt": s.get("extractedAt",""),
                "pipelineVersion": s.get("pipelineVersion",""),
            })
        if rows:
            with open(p, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=rows[0].keys())
                w.writeheader(); w.writerows(rows)
            log.info(f"CSV  → {p.name}  ({len(rows)} rows)")
        return p

    def report(self, specimens: list, meta: dict, tag: str = "latest") -> Path:
        """Self-contained HTML report — no dependencies, opens in any browser."""
        p = self.out / f"pipeline_report_{tag}.html"

        classes  = Counter(s["behavioralRecord"]["groundTruth"] for s in specimens)
        species  = Counter(s["commonName"] for s in specimens)
        datasets = Counter(s["sourceDataset"] for s in specimens)
        methods  = Counter(s["annotationMethod"] for s in specimens)
        total    = len(specimens)

        COLORS = {
            "CONTACT":"#5DB8C8","DIVE":"#3A7BD5","FORAGE":"#44C88A",
            "NAVIGATE":"#D4A843","BROADCAST":"#C85DB8",
        }

        def bar(label, count, tot, color="#5DB8C8"):
            pct = count / tot * 100 if tot else 0
            return (f'<div style="margin:5px 0;display:flex;align-items:center;gap:10px">'
                    f'<div style="width:200px;font-size:11px;color:#7AABB8;font-family:monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{label}</div>'
                    f'<div style="flex:1;background:#0A1820;border-radius:2px;height:12px">'
                    f'<div style="width:{pct:.1f}%;background:{color};height:100%;border-radius:2px;transition:width .3s"></div></div>'
                    f'<div style="width:70px;text-align:right;font-size:10px;color:#3A6070">{count} ({pct:.0f}%)</div>'
                    f'</div>')

        class_bars   = "".join(bar(k, v, total, COLORS.get(k,"#5DB8C8")) for k,v in sorted(classes.items()))
        species_bars = "".join(bar(k, v, total) for k,v in sorted(species.items(), key=lambda x:-x[1])[:15])
        dataset_bars = "".join(bar(k, v, total) for k,v in sorted(datasets.items(), key=lambda x:-x[1]))
        method_bars  = "".join(bar(k[:50], v, total) for k,v in sorted(methods.items(), key=lambda x:-x[1]))

        cards = ""
        for s in specimens[:9]:
            af = s["acousticFeatures"]
            gt = s["behavioralRecord"]["groundTruth"]
            c  = COLORS.get(gt, "#666")
            cards += f"""<div style="border:1px solid #0F2030;border-radius:3px;padding:12px;background:#060C12;border-top:2px solid {c}">
              <div style="font-size:9px;color:{c};letter-spacing:.12em;margin-bottom:5px">{gt}</div>
              <div style="font-size:11px;color:#8AAABB;margin-bottom:3px">{s['commonName']}</div>
              <div style="font-size:10px;color:#3A5A6A;margin-bottom:8px">{s['callType']} · {s['sourceDataset']}</div>
              <div style="font-size:10px;color:#2A4A5A;font-family:monospace;line-height:1.9">
                pf: {af.get('peakFrequency_hz','—')} Hz<br>
                dur: {af.get('duration_s','—')} s<br>
                contour: {af.get('freqContour','—')}<br>
                urgency: {af.get('urgencyIndex','—')}
              </div>
            </div>"""

        src_tags = "".join(
            f'<span style="display:inline-block;padding:3px 10px;border:1px solid #0F2030;border-radius:2px;'
            f'font-size:9px;color:#4A8A9A;font-family:monospace;margin:3px">{k}</span>'
            for k in SOURCES
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CetaSignal Pipeline Report</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#030A10;color:#7AABB8;font-family:'IBM Plex Mono',monospace;font-size:12px;padding:48px 40px;max-width:1100px;margin:0 auto}}
h2{{font-size:10px;color:#2A5060;letter-spacing:.2em;text-transform:uppercase;margin:32px 0 12px}}
.card{{background:#060C12;border:1px solid #0A1820;border-radius:3px;padding:20px;margin-bottom:16px}}
.stat{{font-size:36px;color:#C0E0F0;font-weight:700;line-height:1;font-family:'IBM Plex Mono',monospace}}
.stat-label{{font-size:9px;color:#2A5060;letter-spacing:.18em;margin-top:6px}}
.grid4{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}}
.footer{{border-top:1px solid #0A1820;padding-top:16px;margin-top:32px;font-size:10px;color:#1A3040}}
</style>
</head>
<body>

<div style="border-left:2px solid #5DB8C8;padding-left:20px;margin-bottom:40px">
  <div style="font-size:9px;color:#3A6070;letter-spacing:.2em;margin-bottom:8px">CETASIGNAL · ACOUSTIC EXTRACTION PIPELINE</div>
  <div style="font-size:24px;color:#C0E0F0;letter-spacing:.03em;margin-bottom:6px">Pipeline Report</div>
  <div style="font-size:11px;color:#3A6070">{meta.get('sources','')} &nbsp;·&nbsp; {meta.get('elapsed','')} &nbsp;·&nbsp; {PIPELINE_VERSION}</div>
</div>

<div class="grid4">
  <div class="card"><div class="stat">{total}</div><div class="stat-label">SPECIMENS</div></div>
  <div class="card"><div class="stat">{len(species)}</div><div class="stat-label">SPECIES</div></div>
  <div class="card"><div class="stat">{len(datasets)}</div><div class="stat-label">SOURCES</div></div>
  <div class="card"><div class="stat">{len(classes)}</div><div class="stat-label">CLASSES</div></div>
</div>

<h2>Behavioral Class Distribution</h2>
<div class="card">{class_bars}</div>

<h2>Annotation Methods</h2>
<div class="card">{method_bars}</div>

<h2>Species</h2>
<div class="card">{species_bars}</div>

<h2>Source Datasets</h2>
<div class="card">{dataset_bars}</div>

<h2>Sample Specimens</h2>
<div class="grid3">{cards}</div>

<h2>Output Files</h2>
<div class="card">
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">
    <div><div style="color:#5DB8C8;font-size:11px;margin-bottom:5px">specimens_latest.json</div>
         <div style="color:#2A5060;font-size:10px">CadenceClassifier-ready. Direct engine input.</div></div>
    <div><div style="color:#5DB8C8;font-size:11px;margin-bottom:5px">specimens_latest.csv</div>
         <div style="color:#2A5060;font-size:10px">Flat feature table. R / Python / Excel ready.</div></div>
    <div><div style="color:#5DB8C8;font-size:11px;margin-bottom:5px">pipeline.log</div>
         <div style="color:#2A5060;font-size:10px">Full extraction log. Override audit trail.</div></div>
  </div>
</div>

<h2>Registered Sources</h2>
<div class="card">{src_tags}</div>

<div class="footer">
  CetaSignal &nbsp;·&nbsp; Daniel J. Mistretta &nbsp;·&nbsp;
  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
</div>

</body></html>"""

        p.write_text(html)
        log.info(f"HTML → {p.name}")
        return p

    def summary(self, specimens: list, elapsed: str):
        classes  = Counter(s["behavioralRecord"]["groundTruth"] for s in specimens)
        species  = Counter(s["commonName"] for s in specimens)
        datasets = Counter(s["sourceDataset"] for s in specimens)
        log.info("=" * 60)
        log.info(f"COMPLETE — {len(specimens)} specimens  ({elapsed})")
        log.info("-" * 60)
        for title, ctr in [("Classes", classes), ("Species", species), ("Sources", datasets)]:
            log.info(f"{title}:")
            for k, v in sorted(ctr.items(), key=lambda x: -x[1]):
                log.info(f"  {k}: {v}")
        log.info("=" * 60)


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

class Pipeline:

    def __init__(self, out: Path, max_files: int = 500):
        self.out       = out
        self.max_files = max_files
        out.mkdir(parents=True, exist_ok=True)
        _setup_log(out)
        self.extractor = Extractor()
        self.writer    = Writer(out)
        self._t0       = time.time()

    def run(self, audio_dir: Path, src_id: str,
            ann_dir: Optional[Path] = None,
            ann_fmt: Optional[str]  = None) -> list[dict]:
        """Single-source extraction run."""
        src = SOURCES.get(src_id, self._fallback(src_id))
        log.info(f"Source: {src['name']}")

        files = self._audio_files(audio_dir)
        if not files:
            log.warning(f"No audio files in {audio_dir}")
            return []

        ann_index = {}
        if ann_dir and ann_dir.exists():
            fmt = ann_fmt or src.get("ann_format") or _auto_format(ann_dir)
            log.info(f"Annotations: {fmt}" + (" (auto-detected)" if not ann_fmt and not src.get("ann_format") else ""))
            ann_index = self._index(ann_dir, fmt)

        builder   = Builder(src_id, src)
        specimens = []
        for f in files:
            matched = ann_index.get(f.stem) or self._partial_match(f.stem, ann_index)
            if matched:
                for ann in matched:
                    feats = self.extractor.extract(f, ann)
                    s = builder.build(f, feats, ann)
                    specimens.append(s)
                    log.info(f"  ✓ {s['id']:35s} [{s['behavioralRecord']['groundTruth']}]  {ann.get('_method','')[:30]}")
            else:
                feats = self.extractor.extract(f)
                s = builder.build(f, feats)
                specimens.append(s)
                log.info(f"  ✓ {s['id']:35s} [{s['behavioralRecord']['groundTruth']}]  librosa-automated")
        return specimens

    def run_multi(self, sources: list[dict]) -> list[dict]:
        """Multi-source run from config list."""
        all_s = []
        for s in sources:
            log.info(f"\n{'─'*60}\nSource: {s['src_id']}")
            all_s.extend(self.run(
                audio_dir = Path(s["audio_dir"]),
                src_id    = s["src_id"],
                ann_dir   = Path(s["ann_dir"]) if s.get("ann_dir") else None,
                ann_fmt   = s.get("ann_fmt"),
            ))
        return all_s

    def save(self, specimens: list) -> dict:
        ts      = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        elapsed = f"{time.time() - self._t0:.1f}s"
        sources = ", ".join(sorted(set(s["sourceDataset"] for s in specimens)))
        meta    = {"sources": sources, "elapsed": elapsed}
        paths   = {
            "json":   self.writer.json(specimens),
            "json_ts":self.writer.json(specimens, ts),
            "csv":    self.writer.csv(specimens),
            "csv_ts": self.writer.csv(specimens, ts),
            "report": self.writer.report(specimens, meta, ts),
        }
        self.writer.summary(specimens, elapsed)
        return paths

    def _audio_files(self, d: Path) -> list[Path]:
        files = []
        for ext in (".wav",".flac",".aif",".aiff"):
            files.extend(d.glob(f"**/*{ext}"))
        files = sorted(set(files))[:self.max_files]
        log.info(f"Audio files: {len(files)} in {d}")
        return files

    def _index(self, ann_dir: Path, fmt: str) -> dict:
        parser = _get_parser(fmt)
        index  = defaultdict(list)
        exts   = {"raven_tsv":[".txt",".tsv"],"pamguard_csv":[".csv"],"triton_ltsa":[".csv",".txt"]}.get(fmt,[".txt",".csv"])
        for ext in exts:
            for f in ann_dir.glob(f"**/*{ext}"):
                for a in parser.parse(f):
                    index[f.stem].append(a)
        log.info(f"Annotations: {sum(len(v) for v in index.values())} entries across {len(index)} files")
        return dict(index)

    def _partial_match(self, stem: str, index: dict) -> list:
        for k, v in index.items():
            if k in stem or stem in k: return v
        return []

    def _fallback(self, src_id: str) -> dict:
        return {"name": src_id, "doi": None, "url": "", "license": "Custom",
                "ocean_basin": "", "location": "", "coords": {}, "depth_m": None,
                "years": "", "species": {}, "citation": "", "ann_format": "raven_tsv"}


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(
        description="CetaSignal Acoustic Extraction Pipeline v3.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        EXAMPLES:
          # Single source with Raven annotations
          python cetasignal_pipeline_v3.py \\
            --audio ./data/noaa_nefsc/ --source noaa_nefsc \\
            --annotations ./data/noaa_nefsc/raven/ --output ./specimens/

          # Multi-source via JSON config
          python cetasignal_pipeline_v3.py --config sources.json --output ./specimens/

          # List all registered sources
          python cetasignal_pipeline_v3.py --list-sources

        SOURCES.JSON FORMAT:
          [
            {"src_id": "noaa_nefsc", "audio_dir": "./data/nefsc", "ann_dir": "./data/nefsc/ann"},
            {"src_id": "myers2025",  "audio_dir": "./data/myers", "ann_dir": "./data/myers/ann"},
            {"src_id": "cerchio_omura", "audio_dir": "./data/omura"}
          ]
        """)
    )
    ap.add_argument("--audio",        type=Path, help="Audio directory")
    ap.add_argument("--source",       type=str,  default="custom", help="Source ID (see --list-sources)")
    ap.add_argument("--annotations",  type=Path, help="Annotation directory (optional)")
    ap.add_argument("--ann-format",   type=str,  choices=["raven_tsv","pamguard_csv","triton_ltsa"],
                                                  help="Annotation format (auto-detected if omitted)")
    ap.add_argument("--config",       type=Path, help="JSON config for multi-source run")
    ap.add_argument("--output",       type=Path, default=Path("./specimens"))
    ap.add_argument("--max",          type=int,  default=500, help="Max audio files")
    ap.add_argument("--list-sources", action="store_true")
    args = ap.parse_args()

    if args.list_sources:
        print(f"\n{'SOURCE ID':<18} {'NAME':<42} {'DOI'}")
        print("-" * 80)
        for k, v in SOURCES.items():
            doi = v.get("doi") or "—"
            print(f"{k:<18} {v['name'][:42]:<42} {doi}")
        sys.exit(0)

    pipe = Pipeline(args.output, args.max)

    if args.config:
        cfg = json.loads(args.config.read_text())
        specimens = pipe.run_multi(cfg)
    elif args.audio:
        specimens = pipe.run(args.audio, args.source, args.annotations, args.ann_format)
    else:
        ap.print_help(); sys.exit(1)

    if specimens:
        pipe.save(specimens)
    else:
        log.warning("No specimens extracted.")

if __name__ == "__main__":
    main()
