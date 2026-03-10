#!/usr/bin/env python3
"""
CetaSignal Acoustic Extraction Pipeline v2.0
=============================================
A universal behavioral acoustic feature extraction system.
Designed for cetaceans — extensible to any vocally active organism.

PLUG-AND-PLAY USAGE:
  1. Download audio from any of the 9 registered sources (or your own)
  2. Run: python cetasignal_pipeline_v2.py --audio ./wav/ --source noaa_nefsc
  3. Collect: specimens_latest.json + specimens_latest.csv + pipeline_report.html

ADDING A NEW ORGANISM or DATASET:
  - Edit DATA_SOURCES to add a new source entry
  - Edit BEHAVIORAL_CLASS_MAP to add call-type → class mappings
  - Edit ORGANISM_PROFILES to define default acoustic ranges
  - No other code changes needed.

FEATURE EXTRACTION:
  - librosa: automated spectral + temporal analysis (always runs)
  - Raven TSV: expert annotation override (if available)
  - PAMGuard CSV: automated detection override (if available)
  - Triton LTSA: presence/absence with species label (if available)
  Rule: expert annotation ALWAYS overrides computed values.

SUPPORTED SOURCES (all 9 CetaSignal datasets):
  noaa_nefsc      NOAA NEFSC DCLDE 2013 — NARW, Fin, Humpback
  myers2025       Myers et al. 2025 Zenodo — Orca 3-ecotype
  sanctsound      NOAA SanctSound 2018-2021 — Multi-species
  noaa_ncei       NOAA NCEI Passive Acoustic Archive
  dclde_oahu      DCLDE 2022 Hawaiian Islands — Toothed whales
  ices_med        ICES Mediterranean — Beaked, Delphinids
  wwf_ganges      WWF India — Ganges River Dolphin
  inpa_amazon     INPA Brazil — Boto, Tucuxi
  cerchio_omura   Cerchio et al. 2015 — Omura's Whale

OUTPUT SCHEMA (CadenceClassifier-compatible):
  Each specimen object contains:
    id, catalogId, species, commonName, callType
    sourceDataset, annotationConfidence, annotationMethod
    recordingLocation, recordingCoordinates, recordingDepth_m
    recordingYear, sourceFile, sourceFileHash, extractedAt
    acousticFeatures: { peakFrequency_hz, frequencyRange_hz,
      duration_s, freqContour, interPulseInterval_ms, pulseCount,
      repetitionHz, urgencyIndex, amplitudeEnvelope, spectralBandwidth_hz }
    behavioralRecord: { groundTruth, groundTruthMethod, description }
    citations, ocean_basin, organism, pipelineVersion
"""

import os, sys, re, csv, json, time, logging, hashlib, argparse, shutil
import tempfile, textwrap
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Optional, Any

import numpy as np

# ── Logging ─────────────────────────────────────────────────────────────────
def setup_logging(output_dir: Path) -> logging.Logger:
    log = logging.getLogger("cetasignal")
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    fh = logging.FileHandler(output_dir / "pipeline.log")
    fh.setFormatter(fmt)
    log.addHandler(sh)
    log.addHandler(fh)
    return log

log = logging.getLogger("cetasignal")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA SOURCE REGISTRY — All 9 CetaSignal sources + extensible
# Add new sources here. No other code changes needed.
# ═══════════════════════════════════════════════════════════════════════════════

DATA_SOURCES = {

    "noaa_nefsc": {
        "shortName": "NOAA NEFSC DCLDE 2013",
        "fullName": "NOAA Northeast Fisheries Science Center — North Atlantic Right Whale Acoustic Data",
        "organism": "cetacean",
        "doi": None,
        "access_url": "https://www.fisheries.noaa.gov/resource/data/noaa-nefsc-north-atlantic-right-whale-acoustic-data-and-annotations",
        "gcp_bucket": None,
        "zenodo_id": None,
        "license": "U.S. Government Work — Public Domain",
        "default_annotation_format": "raven_tsv",
        "ocean_basin": "North Atlantic",
        "location": "Stellwagen Bank NMS, Western North Atlantic",
        "coordinates": {"lat": 42.3, "lon": -70.3},
        "recording_depth_m": 0,
        "years": "2010–2013",
        "species_codes": {
            "NARW": {"species": "Eubalaena glacialis",      "commonName": "North Atlantic Right Whale"},
            "FW":   {"species": "Balaenoptera physalus",    "commonName": "Fin Whale"},
            "HB":   {"species": "Megaptera novaeangliae",   "commonName": "Humpback Whale"},
            "SEI":  {"species": "Balaenoptera borealis",    "commonName": "Sei Whale"},
            "BW":   {"species": "Balaenoptera musculus",    "commonName": "Blue Whale"},
        },
        "citation": "NOAA Northeast Fisheries Science Center. (2013). Passive Acoustic Data and Annotations, Stellwagen Bank NMS. NOAA Fisheries.",
    },

    "myers2025": {
        "shortName": "Myers et al. 2025 — Orca DCLDE",
        "fullName": "Public Dataset of Annotated Orcinus orca Acoustic Signals",
        "organism": "cetacean",
        "doi": "10.5281/zenodo.15743033",
        "access_url": "https://www.nature.com/articles/s41597-025-05281-5",
        "gcp_bucket": None,
        "zenodo_id": "15743033",
        "license": "Open — Scientific Data (Nature)",
        "default_annotation_format": "pamguard_csv",
        "ocean_basin": "North Pacific",
        "location": "Gulf of Alaska, Puget Sound, British Columbia",
        "coordinates": {"lat": 48.5, "lon": -123.15},
        "recording_depth_m": 23,
        "years": "2016–2020",
        "species_codes": {
            "SRKW": {"species": "Orcinus orca", "commonName": "Southern Resident Killer Whale"},
            "NRKW": {"species": "Orcinus orca", "commonName": "Bigg's (Transient) Killer Whale"},
            "OKW":  {"species": "Orcinus orca", "commonName": "Offshore Killer Whale"},
        },
        "citation": "Myers, H. et al. (2025). A Public Dataset of Annotated Orcinus orca Acoustic Signals. Scientific Data. https://doi.org/10.5281/zenodo.15743033",
    },

    "sanctsound": {
        "shortName": "NOAA SanctSound 2018–2021",
        "fullName": "NOAA-Navy Sanctuary Soundscape Monitoring Project",
        "organism": "cetacean",
        "doi": "10.25921/kcxh-8368",
        "access_url": "https://www.ncei.noaa.gov/products/passive-acoustic-data",
        "gcp_bucket": None,
        "zenodo_id": None,
        "license": "U.S. Government Work — Public Domain",
        "default_annotation_format": "triton_ltsa",
        "ocean_basin": "North Pacific",
        "location": "U.S. National Marine Sanctuaries",
        "coordinates": {"lat": 34.0, "lon": -120.0},
        "recording_depth_m": 35,
        "years": "2018–2021",
        "species_codes": {
            "HB": {"species": "Megaptera novaeangliae",  "commonName": "Humpback Whale"},
            "BW": {"species": "Balaenoptera musculus",   "commonName": "Blue Whale"},
            "FW": {"species": "Balaenoptera physalus",   "commonName": "Fin Whale"},
            "SW": {"species": "Physeter macrocephalus",  "commonName": "Sperm Whale"},
        },
        "citation": "NOAA Office of National Marine Sanctuaries and U.S. Navy. (2021). SanctSound. NOAA NCEI. https://doi.org/10.25921/kcxh-8368",
    },

    "noaa_ncei": {
        "shortName": "NOAA NCEI Passive Acoustic Archive",
        "fullName": "NOAA National Centers for Environmental Information — Passive Acoustic Data Archive",
        "organism": "cetacean",
        "doi": "10.25921/PF0H-SQ72",
        "access_url": "https://www.ncei.noaa.gov/products/passive-acoustic-data",
        "gcp_bucket": "noaa-passive-bioacoustic",
        "zenodo_id": None,
        "license": "U.S. Government Work — Public Domain",
        "default_annotation_format": "raven_tsv",
        "ocean_basin": "North Atlantic",
        "location": "North Atlantic Ocean — U.S. East Coast",
        "coordinates": {"lat": 38.0, "lon": -72.0},
        "recording_depth_m": None,
        "years": "2004–present",
        "species_codes": {},  # all species — infer from annotations
        "citation": "NOAA NCEI. (2017). Passive Acoustic Data Collection. https://doi.org/10.25921/PF0H-SQ72",
    },

    "dclde_oahu": {
        "shortName": "DCLDE 2022 — Hawaiian Islands",
        "fullName": "Hawaiian Islands Cetacean and Ecosystem Assessment Survey — DCLDE 2022",
        "organism": "cetacean",
        "doi": "10.25921/e12p-gj65",
        "access_url": "https://www.soest.hawaii.edu/ore/dclde/dataset/",
        "gcp_bucket": None,
        "zenodo_id": None,
        "license": "U.S. Government Work — Public Domain",
        "default_annotation_format": "pamguard_csv",
        "ocean_basin": "North Pacific",
        "location": "Hawaiian Exclusive Economic Zone",
        "coordinates": {"lat": 20.5, "lon": -157.5},
        "recording_depth_m": None,
        "years": "2017",
        "species_codes": {
            "FKW": {"species": "Pseudorca crassidens",     "commonName": "False Killer Whale"},
            "SW":  {"species": "Physeter macrocephalus",   "commonName": "Sperm Whale"},
            "BW":  {"species": "Mesoplodon densirostris",  "commonName": "Blainville's Beaked Whale"},
            "HB":  {"species": "Megaptera novaeangliae",   "commonName": "Humpback Whale"},
        },
        "citation": "NOAA PIFSC. (2022). HICEAS towed array data. NOAA NCEI. https://doi.org/10.25921/e12p-gj65",
    },

    "ices_med": {
        "shortName": "ICES Mediterranean Passive Acoustic Survey",
        "fullName": "ICES Working Group on Marine Mammal Ecology — Mediterranean Survey",
        "organism": "cetacean",
        "doi": "10.17895/ices.data.000005",
        "access_url": "https://ices.dk/data/data-portals/",
        "gcp_bucket": None,
        "zenodo_id": None,
        "license": "Open — ICES Data Portal",
        "default_annotation_format": "pamguard_csv",
        "ocean_basin": "Mediterranean",
        "location": "Mediterranean Sea — Ligurian, Adriatic, Ionian",
        "coordinates": {"lat": 41.0, "lon": 14.0},
        "recording_depth_m": None,
        "years": "2008–2022",
        "species_codes": {
            "CBW": {"species": "Ziphius cavirostris",      "commonName": "Cuvier's Beaked Whale"},
            "RD":  {"species": "Grampus griseus",          "commonName": "Risso's Dolphin"},
            "CD":  {"species": "Delphinus delphis",        "commonName": "Common Dolphin"},
            "SD":  {"species": "Stenella coeruleoalba",    "commonName": "Striped Dolphin"},
            "FW":  {"species": "Balaenoptera physalus",    "commonName": "Fin Whale"},
            "SW":  {"species": "Physeter macrocephalus",   "commonName": "Sperm Whale"},
        },
        "citation": "ICES WGMME. (2022). Mediterranean cetacean passive acoustic survey. ICES Data Portal.",
    },

    "wwf_ganges": {
        "shortName": "WWF Ganges River Dolphin Acoustic Survey",
        "fullName": "WWF India — Vikramshila Gangetic Dolphin Sanctuary PAM",
        "organism": "cetacean",
        "doi": None,
        "access_url": "https://www.wwfindia.org/about_wwf/critical_regions/gangetic_plains/",
        "gcp_bucket": None,
        "zenodo_id": None,
        "license": "Research Use — WWF India",
        "default_annotation_format": "raven_tsv",
        "ocean_basin": "Freshwater — Ganges Basin",
        "location": "Vikramshila Gangetic Dolphin Sanctuary, Bihar, India",
        "coordinates": {"lat": 25.3, "lon": 87.4},
        "recording_depth_m": None,
        "years": "2014–2022",
        "species_codes": {
            "GRD": {"species": "Platanista gangetica", "commonName": "Ganges River Dolphin"},
        },
        "citation": "WWF India. (2022). Gangetic River Dolphin Conservation Programme — Acoustic Monitoring.",
    },

    "inpa_amazon": {
        "shortName": "INPA Amazon Basin Cetacean Survey",
        "fullName": "Instituto Nacional de Pesquisas da Amazônia — Boto Acoustic Survey",
        "organism": "cetacean",
        "doi": None,
        "access_url": "https://www.inpa.gov.br/",
        "gcp_bucket": None,
        "zenodo_id": None,
        "license": "Research Use — INPA",
        "default_annotation_format": "raven_tsv",
        "ocean_basin": "Freshwater — Amazon Basin",
        "location": "Rio Negro confluence, Mamirauá Reserve, Brazil",
        "coordinates": {"lat": -3.1, "lon": -60.1},
        "recording_depth_m": None,
        "years": "2012–2019",
        "species_codes": {
            "BOTO": {"species": "Inia geoffrensis",   "commonName": "Amazon River Dolphin"},
            "TUC":  {"species": "Sotalia fluviatilis", "commonName": "Tucuxi"},
        },
        "citation": "INPA. (2019). Cetacean Acoustic Survey — Amazon Basin. Manaus: INPA.",
    },

    "cerchio_omura": {
        "shortName": "Cerchio et al. 2015 — Omura's Whale",
        "fullName": "Behavioral and acoustic records of Omura's whale off northwest Madagascar",
        "organism": "cetacean",
        "doi": "10.1098/rsos.150192",
        "access_url": "https://royalsocietypublishing.org/doi/10.1098/rsos.150192",
        "gcp_bucket": None,
        "zenodo_id": None,
        "license": "Open — Royal Society Open Science",
        "default_annotation_format": "raven_tsv",
        "ocean_basin": "Indian Ocean",
        "location": "Northwest Madagascar shelf",
        "coordinates": {"lat": -17.2, "lon": 43.8},
        "recording_depth_m": None,
        "years": "2013",
        "species_codes": {
            "OW": {"species": "Balaenoptera omurai", "commonName": "Omura's Whale"},
        },
        "citation": "Cerchio, S. et al. (2015). Omura's whales off northwest Madagascar. Royal Society Open Science. https://doi.org/10.1098/rsos.150192",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# ORGANISM PROFILES — Acoustic ranges per organism type
# Extend here to add fish, birds, bats, elephants, etc.
# ═══════════════════════════════════════════════════════════════════════════════

ORGANISM_PROFILES = {
    "cetacean": {
        "freq_range_hz": [10, 160000],
        "sr_target": 96000,
        "typical_call_duration_s": [0.1, 30.0],
        "behavioral_classes": ["CONTACT", "DIVE", "FORAGE", "NAVIGATE", "BROADCAST"],
        "notes": "Mysticetes: 10–8000 Hz. Odontocetes: 200–160000 Hz.",
    },
    "bat": {
        "freq_range_hz": [10000, 200000],
        "sr_target": 250000,
        "typical_call_duration_s": [0.002, 0.05],
        "behavioral_classes": ["FORAGE", "NAVIGATE", "CONTACT", "BROADCAST"],
        "notes": "Ultrasonic FM sweeps. Echolocation-dominant.",
    },
    "bird": {
        "freq_range_hz": [200, 20000],
        "sr_target": 44100,
        "typical_call_duration_s": [0.05, 10.0],
        "behavioral_classes": ["CONTACT", "BROADCAST", "NAVIGATE", "FORAGE"],
        "notes": "Song, alarm, contact calls. Seasonal migration signals.",
    },
    "elephant": {
        "freq_range_hz": [1, 10000],
        "sr_target": 48000,
        "typical_call_duration_s": [0.5, 20.0],
        "behavioral_classes": ["CONTACT", "BROADCAST", "NAVIGATE", "FORAGE"],
        "notes": "Infrasonic rumbles (<20 Hz) for long-range contact and coordination.",
    },
    # Add more: fish, frog, primate, insect...
    "custom": {
        "freq_range_hz": [1, 200000],
        "sr_target": 96000,
        "typical_call_duration_s": [0.001, 60.0],
        "behavioral_classes": ["CONTACT", "DIVE", "FORAGE", "NAVIGATE", "BROADCAST"],
        "notes": "Generic profile. Override with --organism custom and adjust as needed.",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# BEHAVIORAL CLASS MAP — Call type string → behavioral class
# Organism-agnostic by design. Extend for new organisms/call types.
# ═══════════════════════════════════════════════════════════════════════════════

BEHAVIORAL_CLASS_MAP = {
    # CONTACT — position broadcast, group cohesion
    "upcall":           "CONTACT", "up call":        "CONTACT", "up-call":       "CONTACT",
    "contact":          "CONTACT", "coda":           "CONTACT", "whistle":       "CONTACT",
    "signature":        "CONTACT", "moan":           "CONTACT", "grunt":         "CONTACT",
    "reunion":          "CONTACT", "assembly":       "CONTACT", "social":        "CONTACT",
    "alarm":            "CONTACT", "greeting":       "CONTACT",
    # DIVE — descent coordination
    "downsweep":        "DIVE",    "down sweep":     "DIVE",    "down-sweep":    "DIVE",
    "dive":             "DIVE",    "descend":        "DIVE",    "submergence":   "DIVE",
    # FORAGE — prey detection, hunting coordination
    "click":            "FORAGE",  "click train":    "FORAGE",  "burst pulse":   "FORAGE",
    "burst-pulse":      "FORAGE",  "buzz":           "FORAGE",  "echolocation":  "FORAGE",
    "fm click":         "FORAGE",  "boing":          "FORAGE",  "rasp":          "FORAGE",
    "feeding":          "FORAGE",  "foraging":       "FORAGE",  "prey":          "FORAGE",
    # NAVIGATE — migration heading, long-range coordination
    "20 hz":            "NAVIGATE","20hz":           "NAVIGATE","pulse train":   "NAVIGATE",
    "a call":           "NAVIGATE","b call":         "NAVIGATE","a/b call":      "NAVIGATE",
    "migration":        "NAVIGATE","tonal":          "NAVIGATE","infrasonic":    "NAVIGATE",
    "navigation":       "NAVIGATE","heading":        "NAVIGATE",
    # BROADCAST — reproductive, cultural, long-range display
    "song":             "BROADCAST","song phrase":   "BROADCAST","song unit":    "BROADCAST",
    "broadcast":        "BROADCAST","display":       "BROADCAST","advertising":  "BROADCAST",
    "reproductive":     "BROADCAST","mating":        "BROADCAST","chorus":       "BROADCAST",
}

# ═══════════════════════════════════════════════════════════════════════════════
# ANNOTATION PARSERS
# ═══════════════════════════════════════════════════════════════════════════════

class RavenParser:
    """
    Parses Raven Pro selection table TSV/TXT files.
    Handles both standard and custom column orders.
    """
    # Maps Raven column name variants → canonical field
    COL_MAP = {
        "Peak Freq (Hz)":   "peak_freq_hz",
        "Peak Frequency":   "peak_freq_hz",
        "Low Freq (Hz)":    "low_freq_hz",
        "Low Frequency":    "low_freq_hz",
        "High Freq (Hz)":   "high_freq_hz",
        "High Frequency":   "high_freq_hz",
        "Delta Time (s)":   "duration_s",
        "Duration (s)":     "duration_s",
        "Begin Time (s)":   "begin_s",
        "End Time (s)":     "end_s",
        "Annotation":       "annotation",
        "Tags":             "annotation",
        "Species":          "annotation",
        "Label":            "annotation",
    }

    def parse(self, path: Path) -> list[dict]:
        anns = []
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    ann = {"source_file": path.name,
                           "annotation_method": "Manual — Raven Pro"}
                    for col, val in row.items():
                        canonical = self.COL_MAP.get(col)
                        if canonical and val.strip():
                            try:    ann[canonical] = float(val) if canonical != "annotation" else val.strip()
                            except: ann[canonical] = val.strip()
                    ann["confidence"] = "Definite" if ann.get("annotation") else "Possibly Detected"
                    ann["bandwidth_hz"] = (ann.get("high_freq_hz", 0) or 0) - (ann.get("low_freq_hz", 0) or 0)
                    if ann.get("begin_s") is not None and ann.get("end_s") is not None:
                        ann["duration_s"] = ann.get("duration_s") or (ann["end_s"] - ann["begin_s"])
                    anns.append(ann)
        except Exception as e:
            log.warning(f"Raven parse error {path.name}: {e}")
        return anns


class PAMGuardParser:
    """Parses PAMGuard detection CSV exports (click detector, whistle detector)."""

    COL_MAP = {
        "StartSeconds":     "begin_s",    "UTC":            "begin_s",
        "Duration":         "duration_s", "DeltaTime":      "duration_s",
        "PeakFrequency":    "peak_freq_hz","Peak_Freq_Hz":  "peak_freq_hz",
        "LowFrequency":     "low_freq_hz","Low_Freq_Hz":    "low_freq_hz",
        "HighFrequency":    "high_freq_hz","High_Freq_Hz":  "high_freq_hz",
        "Annotation":       "annotation", "Species":        "annotation",
        "Label":            "annotation", "Classification": "annotation",
        "Confidence":       "confidence",
    }

    def parse(self, path: Path) -> list[dict]:
        anns = []
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ann = {"source_file": path.name,
                           "annotation_method": "PAMGuard — automated + expert QA"}
                    for col, val in row.items():
                        canonical = self.COL_MAP.get(col)
                        if canonical and val.strip():
                            try:    ann[canonical] = float(val) if canonical not in ("annotation","confidence") else val.strip()
                            except: ann[canonical] = val.strip()
                    ann.setdefault("confidence", "Definite")
                    ann["bandwidth_hz"] = (ann.get("high_freq_hz", 0) or 0) - (ann.get("low_freq_hz", 0) or 0)
                    anns.append(ann)
        except Exception as e:
            log.warning(f"PAMGuard parse error {path.name}: {e}")
        return anns


class TritonParser:
    """
    Parses Triton LTSA log files (MATLAB-generated).
    Triton logs are typically CSV with: UTC, species, detection_type
    """

    def parse(self, path: Path) -> list[dict]:
        anns = []
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    annotation = (row.get("species") or row.get("Species") or
                                  row.get("call_type") or row.get("annotation") or "").strip()
                    if not annotation:
                        continue
                    ann = {
                        "source_file": path.name,
                        "annotation_method": "Triton LTSA — visual scan + aural confirmation",
                        "annotation": annotation,
                        "confidence": "Definite",
                        "begin_s": None, "duration_s": None,
                        "peak_freq_hz": None, "low_freq_hz": None,
                        "high_freq_hz": None, "bandwidth_hz": None,
                    }
                    anns.append(ann)
        except Exception as e:
            log.warning(f"Triton parse error {path.name}: {e}")
        return anns


def get_parser(fmt: str):
    return {"raven_tsv": RavenParser,
            "pamguard_csv": PAMGuardParser,
            "triton_ltsa": TritonParser}.get(fmt, RavenParser)()


def detect_annotation_format(ann_dir: Path) -> str:
    """Auto-detect annotation format from file extensions and content."""
    files = list(ann_dir.iterdir())
    exts = Counter(f.suffix.lower() for f in files)
    if ".txt" in exts or ".tsv" in exts:
        # Check if it's Raven by looking for Raven header
        for f in files:
            if f.suffix in (".txt", ".tsv"):
                try:
                    first = f.read_text(encoding="utf-8-sig").split("\n")[0]
                    if "Peak Freq" in first or "Delta Time" in first:
                        return "raven_tsv"
                except: pass
    if ".csv" in exts:
        for f in files:
            if f.suffix == ".csv":
                try:
                    first = f.read_text(encoding="utf-8-sig").split("\n")[0]
                    if "PeakFrequency" in first or "StartSeconds" in first:
                        return "pamguard_csv"
                    if "species" in first.lower() or "call_type" in first.lower():
                        return "triton_ltsa"
                except: pass
        return "pamguard_csv"
    return "raven_tsv"


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE EXTRACTOR — librosa core, organism-aware
# ═══════════════════════════════════════════════════════════════════════════════

class AcousticFeatureExtractor:
    """
    Extracts 10 CetaSignal acoustic features from any audio file.
    Organism profile sets the sample rate and expected frequency range.
    Expert annotation values override computed values if provided.
    """

    def __init__(self, organism: str = "cetacean"):
        profile = ORGANISM_PROFILES.get(organism, ORGANISM_PROFILES["custom"])
        self.sr = profile["sr_target"]
        self.freq_range = profile["freq_range_hz"]

    def extract(self, audio_path: Path, annotation: Optional[dict] = None,
                begin_s: float = 0.0, end_s: Optional[float] = None) -> dict:
        try:
            import librosa
        except ImportError:
            log.error("librosa not installed. Run: pip install librosa")
            return self._empty()

        try:
            y, sr = librosa.load(str(audio_path), sr=self.sr, mono=True,
                                 offset=begin_s,
                                 duration=(end_s - begin_s) if end_s else None)
        except Exception as e:
            log.warning(f"Load failed {audio_path.name}: {e}")
            return self._empty()

        if len(y) < 512:
            return self._empty()

        duration_s = len(y) / sr
        n_fft = min(4096, len(y) // 2)
        hop   = n_fft // 4

        # ── Spectral ──────────────────────────────────────────────────────
        stft         = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
        freqs        = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
        mean_spec    = stft.mean(axis=1)
        peak_bin     = int(np.argmax(mean_spec))
        peak_freq_hz = float(freqs[peak_bin])

        # -3 dB bandwidth
        half_pwr  = mean_spec[peak_bin] * 0.707
        above_3db = np.where(mean_spec >= half_pwr)[0]
        bw_hz     = float(freqs[above_3db[-1]] - freqs[above_3db[0]]) if len(above_3db) > 1 else 0.0

        # -20 dB frequency range
        thresh       = mean_spec[peak_bin] * 0.1
        above_20db   = np.where(mean_spec >= thresh)[0]
        freq_range   = ([float(freqs[above_20db[0]]), float(freqs[above_20db[-1]])]
                        if len(above_20db) > 1 else [0.0, float(sr / 2)])

        # ── Contour ───────────────────────────────────────────────────────
        freq_contour = self._contour(y, sr, n_fft, hop)

        # ── Pulses ────────────────────────────────────────────────────────
        ipi_ms, pulse_count = self._pulses(y, sr)

        # ── Urgency ───────────────────────────────────────────────────────
        rms       = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=hop)[0]
        rms_norm  = rms / (rms.max() + 1e-8)
        urgency   = float(min(1.0, np.std(rms_norm) * 2.5))

        # ── Envelope ──────────────────────────────────────────────────────
        amp_env = self._envelope(rms_norm)

        # ── Repetition ────────────────────────────────────────────────────
        rep_hz = float(pulse_count / duration_s) if pulse_count > 1 and duration_s > 0 else 0.0

        features = {
            "peakFrequency_hz":     round(peak_freq_hz, 1),
            "frequencyRange_hz":    [round(freq_range[0], 1), round(freq_range[1], 1)],
            "duration_s":           round(duration_s, 3),
            "freqContour":          freq_contour,
            "interPulseInterval_ms": round(ipi_ms, 1) if ipi_ms else None,
            "pulseCount":           pulse_count if pulse_count > 0 else None,
            "repetitionHz":         round(rep_hz, 4),
            "urgencyIndex":         round(urgency, 3),
            "amplitudeEnvelope":    amp_env,
            "spectralBandwidth_hz": round(bw_hz, 1),
            "_extraction_method":   "librosa-automated",
        }

        # ── Annotation override — expert always wins ───────────────────────
        overrides = {}
        if annotation:
            if annotation.get("peak_freq_hz"):
                features["peakFrequency_hz"] = round(float(annotation["peak_freq_hz"]), 1)
                overrides["peakFrequency_hz"] = "annotation"
            if annotation.get("duration_s"):
                features["duration_s"] = round(float(annotation["duration_s"]), 3)
                overrides["duration_s"] = "annotation"
            if annotation.get("low_freq_hz") and annotation.get("high_freq_hz"):
                features["frequencyRange_hz"] = [round(float(annotation["low_freq_hz"]), 1),
                                                  round(float(annotation["high_freq_hz"]), 1)]
                overrides["frequencyRange_hz"] = "annotation"
            if annotation.get("bandwidth_hz"):
                features["spectralBandwidth_hz"] = round(float(annotation["bandwidth_hz"]), 1)
                overrides["spectralBandwidth_hz"] = "annotation"

        if overrides:
            features["_overrides"] = overrides
            log.info(f"    [OVERRIDE] {list(overrides.keys())} from expert annotation")

        return features

    def _contour(self, y, sr, n_fft, hop) -> str:
        try:
            import librosa
            c = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=n_fft, hop_length=hop)[0]
            if len(c) < 4: return "flat"
            k = np.ones(max(3, len(c)//8)) / max(3, len(c)//8)
            s = np.convolve(c, k, mode="valid")
            if len(s) < 3: return "flat"
            x = np.arange(len(s))
            slope, intercept = np.polyfit(x, s, 1)
            residual = np.std(s - (slope * x + intercept)) / (np.std(s) + 1e-8)
            slope_norm = slope / (np.mean(s) + 1e-8)
            if residual > 0.35: return "complex"
            if slope_norm >  0.003: return "rising"
            if slope_norm < -0.003: return "descending"
            return "flat"
        except:
            return "flat"

    def _pulses(self, y, sr) -> tuple:
        try:
            import librosa
            onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time",
                                                pre_max=3, post_max=3,
                                                pre_avg=10, post_avg=10,
                                                delta=0.07, wait=3)
            if len(onsets) < 2: return None, len(onsets)
            return float(np.mean(np.diff(onsets)) * 1000), len(onsets)
        except:
            return None, 0

    def _envelope(self, rms_norm) -> str:
        if len(rms_norm) < 4: return "sustained"
        peak_pos  = int(np.argmax(rms_norm)) / len(rms_norm)
        variance  = float(np.std(rms_norm))
        if variance > 0.35:   return "pulse"
        if peak_pos < 0.25:   return "attack_heavy"
        return "sustained"

    def _empty(self) -> dict:
        return {k: None for k in ["peakFrequency_hz","frequencyRange_hz","duration_s",
                                   "freqContour","interPulseInterval_ms","pulseCount",
                                   "repetitionHz","urgencyIndex","amplitudeEnvelope",
                                   "spectralBandwidth_hz"]}


# ═══════════════════════════════════════════════════════════════════════════════
# SPECIMEN BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class SpecimenBuilder:
    """Assembles full CadenceClassifier-compatible specimen objects."""

    FILENAME_CALL_PATTERNS = {
        "upcall":"Upcall","up_call":"Upcall","downsweep":"Downsweep",
        "down_sweep":"Downsweep","20hz":"20 Hz Pulse","20_hz":"20 Hz Pulse",
        "song":"Song","burst":"Burst Pulse","burst_pulse":"Burst Pulse",
        "click":"Click","click_train":"Click Train","whistle":"Whistle",
        "coda":"Coda","fm_click":"FM Click","rasp":"Rasp","boing":"Boing",
    }

    def __init__(self, source_id: str, source_info: dict, organism: str = "cetacean"):
        self.source_id   = source_id
        self.source_info = source_info
        self.organism    = organism
        self._counters   = Counter()

    def build(self, audio_path: Path, features: dict,
              annotation: Optional[dict] = None) -> dict:

        # Resolve call type
        call_type_raw = (annotation or {}).get("annotation", "") or \
                         self._infer_from_filename(audio_path.name)
        call_type  = self._normalize(call_type_raw)
        ground_truth = self._to_class(call_type)

        # Resolve species
        species_info = self._resolve_species(annotation, audio_path.name)

        # IDs
        sp_code = species_info["commonName"].split()[0][:4].upper()
        ct_code = re.sub(r"[^A-Z0-9]", "", call_type.upper())[:4]
        self._counters[sp_code] += 1
        n = self._counters[sp_code]

        specimen_id = f"{sp_code.lower()}_{ct_code.lower()}_{n:03d}"
        catalog_id  = f"{self.source_id.upper()[:8]}-{sp_code}-{ct_code}-{n:03d}"

        # File hash (first 64KB for speed)
        try:
            fh = hashlib.md5(audio_path.read_bytes()[:65536]).hexdigest()[:12]
        except:
            fh = "unavailable"

        # Annotation method
        ann_method = (annotation or {}).get("annotation_method", "librosa — automated extraction")
        ann_conf   = (annotation or {}).get("confidence", "Computed — librosa")

        # Strip internal pipeline keys from features before storing
        clean_features = {k: v for k, v in features.items() if not k.startswith("_")}

        return {
            "id":                  specimen_id,
            "catalogId":           catalog_id,
            "species":             species_info["species"],
            "commonName":          species_info["commonName"],
            "organism":            self.organism,
            "callType":            call_type,
            "callTypeDescription": self._describe(call_type),
            "sourceDataset":       self.source_id,
            "sourceDoi":           self.source_info.get("doi"),
            "sourceUrl":           self.source_info.get("access_url"),
            "annotationConfidence":ann_conf,
            "annotationMethod":    ann_method,
            "recordingLocation":   self.source_info.get("location", ""),
            "recordingCoordinates":self.source_info.get("coordinates", {}),
            "recordingDepth_m":    self.source_info.get("recording_depth_m"),
            "recordingYear":       self._year(audio_path.name),
            "sourceFile":          audio_path.name,
            "sourceFileHash_md5":  fh,
            "extractedAt":         datetime.utcnow().isoformat() + "Z",
            "acousticFeatures":    clean_features,
            "behavioralRecord": {
                "groundTruth":       ground_truth,
                "groundTruthMethod": ann_method,
                "observedBehavior":  "",
                "description":       f"Extracted from {audio_path.name}. "
                                     f"Ground truth from call type: '{call_type}'.",
            },
            "citations":      [self.source_info.get("citation", "")],
            "ocean_basin":    self.source_info.get("ocean_basin", ""),
            "pipelineVersion":"cetasignal-pipeline-v2.0",
        }

    def _infer_from_filename(self, name: str) -> str:
        n = name.lower()
        for pat, ct in self.FILENAME_CALL_PATTERNS.items():
            if pat in n: return ct
        return "Unknown"

    def _normalize(self, raw: str) -> str:
        lut = {"UC":"Upcall","DS":"Downsweep","BP":"Burst Pulse",
               "CL":"Click","WH":"Whistle","SG":"Song","CD":"Coda",
               "FMC":"FM Click","20HZ":"20 Hz Pulse"}
        return lut.get(raw.strip().upper(), raw.strip().title() or "Unknown")

    def _to_class(self, call_type: str) -> str:
        ct = call_type.lower()
        for pattern, cls in BEHAVIORAL_CLASS_MAP.items():
            if pattern in ct: return cls
        return "CONTACT"

    def _resolve_species(self, annotation: Optional[dict], filename: str) -> dict:
        if annotation and annotation.get("annotation"):
            raw = annotation["annotation"]
            for code, info in self.source_info.get("species_codes", {}).items():
                if code.lower() in raw.lower() or \
                   info["species"].lower() in raw.lower() or \
                   info["commonName"].lower() in raw.lower():
                    return info
            # Return annotation text as species if no match
            return {"species": raw, "commonName": raw}

        fn = filename.upper()
        for code, info in self.source_info.get("species_codes", {}).items():
            if code in fn:
                return info
        return {"species": "Unknown", "commonName": "Unknown"}

    def _describe(self, call_type: str) -> str:
        lut = {
            "Upcall":       "Frequency-modulated rising sweep. Primary contact call.",
            "Downsweep":    "Brief descending FM call. Reliably precedes dive behavior.",
            "20 Hz Pulse":  "Regular infrasonic pulses. SOFAR channel propagation.",
            "Song":         "Complex hierarchically structured acoustic display.",
            "Burst Pulse":  "High-energy rapid click train. Social and foraging context.",
            "Click":        "Broadband impulsive signal. Echolocation or foraging.",
            "Click Train":  "Rapid click sequence. Foraging echolocation.",
            "Coda":         "Stereotyped click sequence. Social identity signal.",
            "Whistle":      "Tonal FM call. Contact and affiliation.",
            "FM Click":     "Frequency-modulated click. Beaked whale echolocation.",
            "Rasp":         "Short broadband click series. Social/foraging context.",
        }
        for key, desc in lut.items():
            if key.lower() in call_type.lower(): return desc
        return call_type

    def _year(self, filename: str) -> Optional[int]:
        m = re.search(r"20\d{2}", filename)
        return int(m.group()) if m else None


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT WRITER — JSON, CSV, HTML Report
# ═══════════════════════════════════════════════════════════════════════════════

class OutputWriter:

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

    def write_json(self, specimens: list, tag: str = "latest") -> Path:
        p = self.output_dir / f"specimens_{tag}.json"
        p.write_text(json.dumps(specimens, indent=2))
        log.info(f"JSON  → {p}  ({len(specimens)} specimens, {p.stat().st_size//1024} KB)")
        return p

    def write_csv(self, specimens: list, tag: str = "latest") -> Path:
        p = self.output_dir / f"specimens_{tag}.csv"
        rows = []
        for s in specimens:
            af = s.get("acousticFeatures", {})
            br = s.get("behavioralRecord", {})
            rows.append({
                "id": s["id"], "catalogId": s["catalogId"],
                "species": s["species"], "commonName": s["commonName"],
                "organism": s.get("organism", ""), "callType": s["callType"],
                "sourceDataset": s["sourceDataset"], "sourceDoi": s.get("sourceDoi", ""),
                "annotationConfidence": s["annotationConfidence"],
                "annotationMethod": s["annotationMethod"],
                "groundTruth": br.get("groundTruth", ""),
                "ocean_basin": s.get("ocean_basin", ""),
                "recordingYear": s.get("recordingYear", ""),
                "peakFrequency_hz": af.get("peakFrequency_hz", ""),
                "duration_s": af.get("duration_s", ""),
                "freqContour": af.get("freqContour", ""),
                "interPulseInterval_ms": af.get("interPulseInterval_ms", ""),
                "pulseCount": af.get("pulseCount", ""),
                "repetitionHz": af.get("repetitionHz", ""),
                "urgencyIndex": af.get("urgencyIndex", ""),
                "amplitudeEnvelope": af.get("amplitudeEnvelope", ""),
                "spectralBandwidth_hz": af.get("spectralBandwidth_hz", ""),
                "freq_low_hz": (af.get("frequencyRange_hz") or [None, None])[0],
                "freq_high_hz": (af.get("frequencyRange_hz") or [None, None])[1],
                "sourceFile": s.get("sourceFile", ""),
                "extractedAt": s.get("extractedAt", ""),
                "pipelineVersion": s.get("pipelineVersion", ""),
            })
        if rows:
            with open(p, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=rows[0].keys())
                w.writeheader(); w.writerows(rows)
            log.info(f"CSV   → {p}  ({len(rows)} rows)")
        return p

    def write_report(self, specimens: list, run_meta: dict, tag: str = "latest") -> Path:
        """Generate a self-contained HTML pipeline report for scientists."""
        p = self.output_dir / f"pipeline_report_{tag}.html"

        classes   = Counter(s["behavioralRecord"]["groundTruth"] for s in specimens)
        species   = Counter(s["commonName"] for s in specimens)
        datasets  = Counter(s["sourceDataset"] for s in specimens)
        methods   = Counter(s["annotationMethod"] for s in specimens)
        organisms = Counter(s.get("organism", "?") for s in specimens)

        CLASS_COLORS = {
            "CONTACT":"#5DB8C8","DIVE":"#3A7BD5","FORAGE":"#44C88A",
            "NAVIGATE":"#D4A843","BROADCAST":"#C85DB8","Unknown":"#666",
        }

        def bar(label, count, total, color="#5DB8C8"):
            pct = count / total * 100 if total else 0
            return (f'<div style="margin:6px 0">'
                    f'<div style="display:flex;align-items:center;gap:10px">'
                    f'<div style="width:160px;font-size:11px;color:#8AAABB;font-family:monospace">{label}</div>'
                    f'<div style="flex:1;background:#0F1E28;border-radius:2px;height:14px">'
                    f'<div style="width:{pct:.1f}%;background:{color};height:100%;border-radius:2px"></div></div>'
                    f'<div style="width:60px;text-align:right;font-size:11px;color:#5A7A8A">{count} ({pct:.0f}%)</div>'
                    f'</div></div>')

        total = len(specimens)
        class_bars  = "".join(bar(k, v, total, CLASS_COLORS.get(k,"#5DB8C8")) for k,v in sorted(classes.items()))
        species_bars = "".join(bar(k[:28], v, total) for k,v in sorted(species.items(), key=lambda x:-x[1])[:12])
        dataset_bars = "".join(bar(k, v, total) for k,v in sorted(datasets.items(), key=lambda x:-x[1]))
        method_bars  = "".join(bar(k[:40], v, total) for k,v in sorted(methods.items(), key=lambda x:-x[1]))

        # Sample specimen cards
        sample_cards = ""
        for s in specimens[:6]:
            af = s["acousticFeatures"]
            gt = s["behavioralRecord"]["groundTruth"]
            color = CLASS_COLORS.get(gt, "#666")
            sample_cards += f"""
            <div style="border:1px solid #132030;border-radius:4px;padding:14px;background:#080E14;border-top:2px solid {color}">
              <div style="font-size:9px;color:{color};letter-spacing:.15em;margin-bottom:6px">{gt}</div>
              <div style="font-size:11px;color:#8AAABB;margin-bottom:4px">{s['commonName']}</div>
              <div style="font-size:10px;color:#4A6A7A;margin-bottom:8px">{s['callType']} · {s['sourceDataset']}</div>
              <div style="font-size:10px;color:#3A5A6A;font-family:monospace;line-height:1.8">
                pf: {af.get('peakFrequency_hz','—')} Hz<br>
                dur: {af.get('duration_s','—')} s<br>
                contour: {af.get('freqContour','—')}<br>
                urgency: {af.get('urgencyIndex','—')}
              </div>
            </div>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CetaSignal Pipeline Report</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#040C14;color:#8AAABB;font-family:'IBM Plex Mono',monospace;font-size:12px;padding:40px}}
  h1{{font-size:22px;color:#C8E8F0;letter-spacing:.05em;margin-bottom:4px}}
  h2{{font-size:11px;color:#3A5A6A;letter-spacing:.2em;text-transform:uppercase;margin:28px 0 14px}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:28px}}
  .card{{background:#080E14;border:1px solid #0F2030;border-radius:4px;padding:20px}}
  .stat{{font-size:32px;color:#C8E8F0;font-weight:700;line-height:1}}
  .stat-label{{font-size:9px;color:#3A5A6A;letter-spacing:.2em;margin-top:6px}}
  .tag{{display:inline-block;padding:2px 8px;border-radius:2px;font-size:9px;letter-spacing:.1em;margin:2px}}
  .sample-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:28px}}
  .footer{{border-top:1px solid #0F2030;padding-top:16px;margin-top:28px;font-size:10px;color:#2A4A5A}}
</style>
</head>
<body>

<div style="border-left:3px solid #5DB8C8;padding-left:20px;margin-bottom:32px">
  <h1>CetaSignal Pipeline Report</h1>
  <div style="color:#4A6A7A;font-size:11px;margin-top:6px">
    {run_meta.get('sources_used','')}&nbsp;·&nbsp;
    {run_meta.get('run_time','')}&nbsp;·&nbsp;
    v2.0
  </div>
</div>

<div class="grid">
  <div class="card">
    <div class="stat">{total}</div>
    <div class="stat-label">SPECIMENS EXTRACTED</div>
  </div>
  <div class="card">
    <div class="stat">{len(species)}</div>
    <div class="stat-label">SPECIES</div>
  </div>
  <div class="card">
    <div class="stat">{len(datasets)}</div>
    <div class="stat-label">SOURCE DATASETS</div>
  </div>
  <div class="card">
    <div class="stat">{len(organisms)}</div>
    <div class="stat-label">ORGANISM TYPES</div>
  </div>
</div>

<h2>Behavioral Class Distribution</h2>
<div class="card" style="margin-bottom:20px">{class_bars}</div>

<h2>Annotation Methods</h2>
<div class="card" style="margin-bottom:20px">{method_bars}</div>

<h2>Species</h2>
<div class="card" style="margin-bottom:20px">{species_bars}</div>

<h2>Source Datasets</h2>
<div class="card" style="margin-bottom:20px">{dataset_bars}</div>

<h2>Sample Specimens</h2>
<div class="sample-grid">{sample_cards}</div>

<h2>Output Files</h2>
<div class="card">
  <div style="color:#5DB8C8;font-size:11px;margin-bottom:10px">specimens_latest.json</div>
  <div style="color:#3A5A6A;font-size:10px;margin-bottom:16px">CadenceClassifier-ready. Load directly into CetaSignal engine.</div>
  <div style="color:#5DB8C8;font-size:11px;margin-bottom:10px">specimens_latest.csv</div>
  <div style="color:#3A5A6A;font-size:10px;margin-bottom:16px">Flat feature table. Import to R, Python, Excel for analysis.</div>
  <div style="color:#5DB8C8;font-size:11px;margin-bottom:10px">pipeline.log</div>
  <div style="color:#3A5A6A;font-size:10px">Full extraction log with override audit trail.</div>
</div>

<h2>Registered Sources</h2>
<div class="card">
  {''.join(f'<span class="tag" style="background:#0F2030;color:#5DB8C8">{k}</span>' for k in DATA_SOURCES.keys())}
</div>

<div class="footer">
  CetaSignal Acoustic Extraction Pipeline v2.0 &nbsp;·&nbsp;
  Daniel J. Mistretta &nbsp;·&nbsp;
  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} &nbsp;·&nbsp;
  Organism profiles: {', '.join(ORGANISM_PROFILES.keys())}
</div>

</body></html>"""

        p.write_text(html)
        log.info(f"HTML  → {p}")
        return p


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class CetaSignalPipeline:

    def __init__(self, output_dir: Path, organism: str = "cetacean", max_files: int = 500):
        self.output_dir = output_dir
        self.organism   = organism
        self.max_files  = max_files
        output_dir.mkdir(parents=True, exist_ok=True)
        setup_logging(output_dir)
        self.extractor  = AcousticFeatureExtractor(organism)
        self.writer     = OutputWriter(output_dir)
        self._start     = time.time()

    def run(self, audio_dir: Path, source_id: str,
            annotation_dir: Optional[Path] = None,
            annotation_fmt: Optional[str] = None) -> list[dict]:
        """
        Main entry point.
        audio_dir:      directory of WAV/FLAC files
        source_id:      key in DATA_SOURCES (or 'custom')
        annotation_dir: optional directory of annotation files
        annotation_fmt: 'raven_tsv' | 'pamguard_csv' | 'triton_ltsa' | None (auto-detect)
        """
        source_info = DATA_SOURCES.get(source_id, self._custom_source(source_id))
        log.info(f"Source: {source_info['shortName']}")
        log.info(f"Organism: {self.organism}")

        # Collect audio files
        audio_files = self._collect_audio(audio_dir)
        if not audio_files:
            log.warning(f"No audio files in {audio_dir}")
            return []

        # Build annotation index
        ann_index = {}
        if annotation_dir and annotation_dir.exists():
            fmt = annotation_fmt or detect_annotation_format(annotation_dir)
            log.info(f"Annotation format: {fmt} (auto-detected)" if not annotation_fmt else f"Annotation format: {fmt}")
            ann_index = self._index_annotations(annotation_dir, fmt, source_info.get("default_annotation_format","raven_tsv"))

        builder   = SpecimenBuilder(source_id, source_info, self.organism)
        specimens = []

        for audio_path in audio_files:
            matched_anns = self._match(audio_path, ann_index)

            if matched_anns:
                # One specimen per annotation selection
                for ann in matched_anns:
                    begin = ann.get("begin_s") or 0.0
                    end   = ann.get("end_s")
                    features = self.extractor.extract(audio_path, ann, begin_s=begin, end_s=end)
                    specimen = builder.build(audio_path, features, ann)
                    specimens.append(specimen)
                    log.info(f"  ✓ {specimen['id']:32s}  [{specimen['behavioralRecord']['groundTruth']}]  {ann.get('annotation_method','')[:30]}")
            else:
                # No annotation — full clip, automated only
                features = self.extractor.extract(audio_path)
                specimen = builder.build(audio_path, features)
                specimens.append(specimen)
                log.info(f"  ✓ {specimen['id']:32s}  [{specimen['behavioralRecord']['groundTruth']}]  librosa-automated")

        return specimens

    def run_multi_source(self, sources: list[dict]) -> list[dict]:
        """
        Run across multiple sources in one pass.
        sources: list of dicts with keys: audio_dir, source_id, annotation_dir (optional)
        """
        all_specimens = []
        for s in sources:
            log.info(f"\n{'='*60}")
            log.info(f"Processing source: {s['source_id']}")
            specimens = self.run(
                audio_dir=Path(s["audio_dir"]),
                source_id=s["source_id"],
                annotation_dir=Path(s["annotation_dir"]) if s.get("annotation_dir") else None,
                annotation_fmt=s.get("annotation_fmt"),
            )
            all_specimens.extend(specimens)
        return all_specimens

    def save(self, specimens: list[dict]) -> dict:
        """Write all outputs. Returns dict of output paths."""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        elapsed = f"{time.time() - self._start:.1f}s"
        sources = ", ".join(sorted(set(s["sourceDataset"] for s in specimens)))
        run_meta = {"sources_used": sources, "run_time": elapsed}

        paths = {
            "json_latest":  self.writer.write_json(specimens, "latest"),
            "json_ts":      self.writer.write_json(specimens, ts),
            "csv_latest":   self.writer.write_csv(specimens, "latest"),
            "csv_ts":       self.writer.write_csv(specimens, ts),
            "report":       self.writer.write_report(specimens, run_meta, ts),
        }
        self._log_summary(specimens, elapsed)
        return paths

    def _collect_audio(self, audio_dir: Path) -> list[Path]:
        exts = (".wav", ".flac", ".aif", ".aiff", ".mp3", ".ogg")
        files = []
        for ext in exts:
            files.extend(audio_dir.glob(f"**/*{ext}"))
        files = sorted(set(files))[:self.max_files]
        log.info(f"Audio files found: {len(files)} in {audio_dir}")
        return files

    def _index_annotations(self, ann_dir: Path, fmt: str, fallback_fmt: str) -> dict:
        parser = get_parser(fmt)
        index  = defaultdict(list)
        extensions = {
            "raven_tsv":    [".txt", ".tsv"],
            "pamguard_csv": [".csv"],
            "triton_ltsa":  [".csv", ".txt"],
        }.get(fmt, [".txt", ".csv"])

        for ext in extensions:
            for f in ann_dir.glob(f"**/*{ext}"):
                anns = parser.parse(f)
                index[f.stem].extend(anns)

        total = sum(len(v) for v in index.values())
        log.info(f"Annotations indexed: {total} across {len(index)} files")
        return dict(index)

    def _match(self, audio_path: Path, index: dict) -> list:
        # Exact stem match
        if audio_path.stem in index:
            return index[audio_path.stem]
        # Partial match
        for stem, anns in index.items():
            if stem in audio_path.stem or audio_path.stem in stem:
                return anns
        return []

    def _custom_source(self, source_id: str) -> dict:
        return {
            "shortName": source_id, "fullName": source_id,
            "organism": self.organism, "doi": None,
            "access_url": "", "license": "Custom",
            "ocean_basin": "Unknown", "location": "Unknown",
            "coordinates": {}, "recording_depth_m": None,
            "years": "", "species_codes": {}, "citation": "",
        }

    def _log_summary(self, specimens: list, elapsed: str):
        classes  = Counter(s["behavioralRecord"]["groundTruth"] for s in specimens)
        species  = Counter(s["commonName"] for s in specimens)
        datasets = Counter(s["sourceDataset"] for s in specimens)
        methods  = Counter(s["annotationMethod"] for s in specimens)

        log.info("\n" + "="*60)
        log.info(f"COMPLETE — {len(specimens)} specimens in {elapsed}")
        log.info("-"*60)
        for section, ctr in [("Classes", classes), ("Species", species),
                               ("Datasets", datasets), ("Methods", methods)]:
            log.info(f"{section}:")
            for k, v in sorted(ctr.items(), key=lambda x: -x[1]):
                log.info(f"  {k}: {v}")
        log.info("="*60)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(
        description="CetaSignal Universal Acoustic Extraction Pipeline v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(f"""
        SINGLE SOURCE:
          python cetasignal_pipeline_v2.py \\
            --audio ./data/myers2025/ \\
            --source myers2025 \\
            --annotations ./data/myers2025/annotations/ \\
            --output ./specimens/

        MULTIPLE SOURCES (JSON config):
          python cetasignal_pipeline_v2.py \\
            --config sources.json \\
            --output ./specimens/

        CUSTOM / NON-CETACEAN:
          python cetasignal_pipeline_v2.py \\
            --audio ./bat_recordings/ \\
            --source custom \\
            --organism bat \\
            --output ./specimens/

        REGISTERED SOURCES: {', '.join(DATA_SOURCES.keys())}
        ORGANISM PROFILES:  {', '.join(ORGANISM_PROFILES.keys())}

        sources.json format:
          [{{"source_id": "myers2025", "audio_dir": "./data/myers2025",
             "annotation_dir": "./data/myers2025/ann"}},
           {{"source_id": "noaa_nefsc", "audio_dir": "./data/nefsc",
             "annotation_dir": "./data/nefsc/raven"}}]
        """)
    )
    ap.add_argument("--audio",       type=Path,  help="Audio directory (single source)")
    ap.add_argument("--source",      type=str,   default="custom", help="Source dataset ID")
    ap.add_argument("--annotations", type=Path,  help="Annotation directory (optional)")
    ap.add_argument("--ann-format",  type=str,   help="raven_tsv | pamguard_csv | triton_ltsa (auto-detected if omitted)")
    ap.add_argument("--config",      type=Path,  help="JSON config for multi-source run")
    ap.add_argument("--organism",    type=str,   default="cetacean",
                    choices=list(ORGANISM_PROFILES.keys()), help="Organism profile")
    ap.add_argument("--output",      type=Path,  default=Path("./specimens"))
    ap.add_argument("--max",         type=int,   default=500, help="Max audio files to process")
    ap.add_argument("--list-sources",action="store_true", help="List registered sources and exit")

    args = ap.parse_args()

    if args.list_sources:
        print("\nRegistered Data Sources:")
        for k, v in DATA_SOURCES.items():
            doi = f"  DOI: {v['doi']}" if v.get("doi") else ""
            print(f"  {k:20s}  {v['shortName']}{doi}")
        print("\nOrganism Profiles:", ", ".join(ORGANISM_PROFILES.keys()))
        sys.exit(0)

    pipeline = CetaSignalPipeline(args.output, args.organism, args.max)

    if args.config:
        sources = json.loads(args.config.read_text())
        specimens = pipeline.run_multi_source(sources)
    elif args.audio:
        specimens = pipeline.run(args.audio, args.source,
                                 args.annotations, args.ann_format)
    else:
        ap.print_help(); sys.exit(1)

    if specimens:
        pipeline.save(specimens)
    else:
        log.warning("No specimens extracted.")

if __name__ == "__main__":
    main()
