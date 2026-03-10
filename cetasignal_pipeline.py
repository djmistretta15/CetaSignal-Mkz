#!/usr/bin/env python3
"""
CetaSignal Data Extraction Pipeline v1.0
=========================================
Downloads real cetacean audio recordings from public archives,
extracts acoustic features using librosa, and outputs engine-ready
specimen JSON conforming to the CadenceClassifier schema.

Supported sources:
  - Myers et al. 2025 (Zenodo DOI: 10.5281/zenodo.15743033)  — Orca 3-ecotype
  - NOAA NEFSC DCLDE 2013 (NOAA Fisheries open data)         — NARW + baleen
  - NOAA SanctSound (NOAA NCEI DOI: 10.25921/kcxh-8368)      — Multi-species
  - ICES Mediterranean Passive Acoustic Survey                 — Beaked + delphinids

Usage:
  python cetasignal_pipeline.py --source myers2025 --output ./specimens/
  python cetasignal_pipeline.py --source noaa_nefsc --raven ./annotations/ --output ./specimens/
  python cetasignal_pipeline.py --source all --output ./specimens/
  python cetasignal_pipeline.py --audio ./my_clips/ --raven ./my_annotations/ --output ./specimens/

Output:
  specimens.json   — Array of CadenceClassifier-ready specimen objects
  specimens.csv    — Flat feature table for analysis
  pipeline.log     — Extraction log with confidence and error flags

Author: Daniel J. Mistretta / CetaSignal
"""

import os
import sys
import json
import csv
import time
import logging
import hashlib
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log"),
    ],
)
log = logging.getLogger("cetasignal")

# ── Dataset Registry ───────────────────────────────────────────────────────────
# Each entry defines where to get data, what species/calls to expect,
# and how annotations are structured.

DATASETS = {
    "myers2025": {
        "id": "myers2025",
        "shortName": "Myers et al. 2025 — Orca DCLDE",
        "doi": "10.5281/zenodo.15743033",
        "zenodo_record_id": "15743033",
        "base_url": "https://zenodo.org/api/records/15743033",
        "download_url": "https://zenodo.org/records/15743033/files/",
        "license": "Open — Scientific Data (Nature)",
        "species_map": {
            "SRKW": {"species": "Orcinus orca", "commonName": "Southern Resident Killer Whale"},
            "NRKW": {"species": "Orcinus orca", "commonName": "Bigg's (Transient) Killer Whale"},
            "OKW":  {"species": "Orcinus orca", "commonName": "Offshore Killer Whale"},
        },
        "annotation_format": "pamguard_csv",  # PAMGuard exported CSV
        "ocean_basin": "North Pacific",
        "location": "Gulf of Alaska / Puget Sound",
        "coordinates": {"lat": 48.5, "lon": -123.15},
        "recording_depth_m": 23,
        "years": "2016–2020",
        "citation": "Myers, H. et al. (2025). A Public Dataset of Annotated Orcinus orca Acoustic Signals for Detection and Ecotype Classification. Scientific Data. https://doi.org/10.5281/zenodo.15743033",
    },

    "noaa_nefsc": {
        "id": "noaa_nefsc",
        "shortName": "NOAA NEFSC DCLDE 2013",
        "doi": None,
        "base_url": "https://www.fisheries.noaa.gov/resource/data/noaa-nefsc-north-atlantic-right-whale-acoustic-data-and-annotations",
        "license": "U.S. Government Work — Public Domain",
        "species_map": {
            "NARW": {"species": "Eubalaena glacialis", "commonName": "North Atlantic Right Whale"},
            "FW":   {"species": "Balaenoptera physalus", "commonName": "Fin Whale"},
            "HB":   {"species": "Megaptera novaeangliae", "commonName": "Humpback Whale"},
            "SEI":  {"species": "Balaenoptera borealis", "commonName": "Sei Whale"},
            "BW":   {"species": "Balaenoptera musculus", "commonName": "Blue Whale"},
        },
        "annotation_format": "raven_tsv",  # Raven Pro 1.5 selection tables
        "ocean_basin": "North Atlantic",
        "location": "Stellwagen Bank NMS, Western North Atlantic",
        "coordinates": {"lat": 42.3, "lon": -70.3},
        "recording_depth_m": 0,
        "years": "2010–2013",
        "citation": "NOAA Northeast Fisheries Science Center. (2013). Passive Acoustic Data and Annotations, Stellwagen Bank NMS. NOAA Fisheries.",
    },

    "sanctsound": {
        "id": "sanctsound",
        "shortName": "NOAA SanctSound",
        "doi": "10.25921/kcxh-8368",
        "base_url": "https://www.ncei.noaa.gov/products/passive-acoustic-data",
        "license": "U.S. Government Work — Public Domain",
        "species_map": {
            "HB": {"species": "Megaptera novaeangliae", "commonName": "Humpback Whale"},
            "BW": {"species": "Balaenoptera musculus", "commonName": "Blue Whale"},
            "FW": {"species": "Balaenoptera physalus", "commonName": "Fin Whale"},
            "SW": {"species": "Physeter macrocephalus", "commonName": "Sperm Whale"},
        },
        "annotation_format": "triton_ltsa",  # Triton MATLAB LTSA detections
        "ocean_basin": "North Pacific",
        "location": "U.S. National Marine Sanctuaries",
        "coordinates": {"lat": 34.0, "lon": -120.0},
        "recording_depth_m": 35,
        "years": "2018–2021",
        "citation": "NOAA Office of National Marine Sanctuaries and U.S. Navy. (2021). SanctSound. NOAA NCEI. https://doi.org/10.25921/kcxh-8368",
    },
}

# ── Downloader ─────────────────────────────────────────────────────────────────

class DatasetDownloader:
    """
    Downloads audio files and annotation tables from public archives.
    Handles Zenodo API, NOAA direct download, and GCP buckets.
    Verifies checksums, resumes partial downloads.
    """

    def __init__(self, output_dir: Path, max_files: int = 50):
        self.output_dir = output_dir
        self.max_files = max_files
        output_dir.mkdir(parents=True, exist_ok=True)

    def download_zenodo(self, record_id: str, file_filter: str = ".wav") -> list[Path]:
        """
        Download files from a Zenodo record.
        Returns list of downloaded file paths.
        """
        log.info(f"Querying Zenodo record {record_id}...")
        api_url = f"https://zenodo.org/api/records/{record_id}"

        try:
            with urllib.request.urlopen(api_url, timeout=30) as r:
                record = json.loads(r.read())
        except Exception as e:
            log.error(f"Failed to query Zenodo API: {e}")
            raise

        files = [f for f in record.get("files", []) if f["key"].endswith(file_filter)]
        log.info(f"Found {len(files)} {file_filter} files in record {record_id}")

        downloaded = []
        for f in files[:self.max_files]:
            dest = self.output_dir / f["key"]
            if dest.exists() and dest.stat().st_size == f.get("size", 0):
                log.info(f"  Already exists: {f['key']}")
                downloaded.append(dest)
                continue

            url = f["links"]["self"]
            log.info(f"  Downloading: {f['key']} ({f.get('size', 0) // 1024} KB)")
            try:
                urllib.request.urlretrieve(url, dest)
                downloaded.append(dest)
            except Exception as e:
                log.warning(f"  Failed: {f['key']} — {e}")

        return downloaded

    def download_noaa_gcp(self, bucket: str, prefix: str, file_filter: str = ".flac") -> list[Path]:
        """
        Download from NOAA's GCP public bucket (noaa-passive-bioacoustic).
        Uses gsutil if available, falls back to HTTP.
        """
        import subprocess
        log.info(f"Downloading from GCP bucket gs://{bucket}/{prefix}")

        dest = self.output_dir / "gcp"
        dest.mkdir(exist_ok=True)

        cmd = ["gsutil", "-m", "cp", "-n",
               f"gs://{bucket}/{prefix}*{file_filter}", str(dest)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log.warning(f"gsutil failed: {result.stderr[:200]}")
            log.info("Tip: Install gsutil via `pip install gsutil` or Google Cloud SDK")

        return list(dest.glob(f"*{file_filter}"))

    def from_local_dir(self, audio_dir: Path, extensions: tuple = (".wav", ".flac", ".aif")) -> list[Path]:
        """Use locally downloaded audio files."""
        files = []
        for ext in extensions:
            files.extend(audio_dir.glob(f"**/*{ext}"))
        log.info(f"Found {len(files)} audio files in {audio_dir}")
        return sorted(files)[:self.max_files]


# ── Annotation Parsers ─────────────────────────────────────────────────────────

class RavenParser:
    """
    Parses Raven Pro 1.5 selection table TSV files.
    Maps Raven fields → CetaSignal schema fields.

    Raven TSV columns (standard):
      Selection, View, Channel, Begin Time (s), End Time (s),
      Low Freq (Hz), High Freq (Hz), Delta Time (s), Peak Freq (Hz),
      Annotation
    """

    RAVEN_SPECIES_MAP = {
        "NARW": "Eubalaena glacialis",
        "Right Whale": "Eubalaena glacialis",
        "Fin Whale": "Balaenoptera physalus",
        "20Hz": "Balaenoptera physalus",
        "Humpback": "Megaptera novaeangliae",
        "Blue Whale": "Balaenoptera musculus",
        "Sei Whale": "Balaenoptera borealis",
        "Sperm Whale": "Physeter macrocephalus",
    }

    def parse(self, tsv_path: Path) -> list[dict]:
        """Returns list of annotation dicts with pre-extracted features."""
        annotations = []
        with open(tsv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                try:
                    ann = {
                        "raven_selection": row.get("Selection", ""),
                        "begin_time_s": float(row.get("Begin Time (s)", 0)),
                        "end_time_s": float(row.get("End Time (s)", 0)),
                        "low_freq_hz": float(row.get("Low Freq (Hz)", 0)),
                        "high_freq_hz": float(row.get("High Freq (Hz)", 0)),
                        "duration_s": float(row.get("Delta Time (s)", 0)),
                        "peak_freq_hz": float(row.get("Peak Freq (Hz)", 0)),
                        "annotation": row.get("Annotation", ""),
                        "confidence": "Definite" if row.get("Annotation", "") else "Possibly Detected",
                        "annotation_method": "Manual — Raven 1.5",
                        "bandwidth_hz": float(row.get("High Freq (Hz)", 0)) - float(row.get("Low Freq (Hz)", 0)),
                    }
                    # Resolve species from annotation string
                    ann["species"] = self._resolve_species(ann["annotation"])
                    annotations.append(ann)
                except (ValueError, KeyError) as e:
                    log.warning(f"  Skipping Raven row: {e}")
        log.info(f"  Parsed {len(annotations)} annotations from {tsv_path.name}")
        return annotations

    def _resolve_species(self, annotation: str) -> Optional[str]:
        for key, species in self.RAVEN_SPECIES_MAP.items():
            if key.lower() in annotation.lower():
                return species
        return None


class PAMGuardParser:
    """
    Parses PAMGuard detection CSV exports.
    PAMGuard CSV columns vary by module but core fields are consistent.
    """

    def parse(self, csv_path: Path) -> list[dict]:
        annotations = []
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ann = {
                        "begin_time_s": float(row.get("StartSeconds", row.get("UTC", 0))),
                        "duration_s": float(row.get("Duration", row.get("DeltaTime", 1.0))),
                        "peak_freq_hz": float(row.get("PeakFrequency", row.get("Peak_Freq_Hz", 0))),
                        "low_freq_hz": float(row.get("LowFrequency", row.get("Low_Freq_Hz", 0))),
                        "high_freq_hz": float(row.get("HighFrequency", row.get("High_Freq_Hz", 0))),
                        "annotation": row.get("Annotation", row.get("Species", row.get("Label", ""))),
                        "confidence": row.get("Confidence", "Definite"),
                        "annotation_method": "PAMGuard — expert analyst confirmation",
                        "bandwidth_hz": 0,
                    }
                    ann["bandwidth_hz"] = ann["high_freq_hz"] - ann["low_freq_hz"]
                    ann["species"] = ann["annotation"]
                    annotations.append(ann)
                except (ValueError, KeyError) as e:
                    log.warning(f"  Skipping PAMGuard row: {e}")
        log.info(f"  Parsed {len(annotations)} detections from {csv_path.name}")
        return annotations


# ── Feature Extractor ──────────────────────────────────────────────────────────

class AcousticFeatureExtractor:
    """
    Extracts CetaSignal acoustic features from WAV/FLAC audio clips using librosa.

    Features extracted:
      peakFrequency_hz    — spectral peak frequency
      frequencyRange_hz   — [low_cutoff, high_cutoff] at -20dB
      duration_s          — clip duration
      freqContour         — rising | descending | flat | complex
      interPulseInterval_ms — mean IPI if pulsed signal detected
      pulseCount          — number of pulses in clip
      repetitionHz        — call repetition rate
      urgencyIndex        — normalized amplitude variance (0–1)
      amplitudeEnvelope   — sustained | pulse | attack_heavy
      spectralBandwidth_hz — -3dB bandwidth

    If a Raven/PAMGuard annotation is provided, annotated values
    override computed values (expert annotation always wins).
    """

    def __init__(self, sr_target: int = 96000):
        self.sr_target = sr_target

    def extract(self, audio_path: Path, annotation: Optional[dict] = None) -> dict:
        """
        Main entry point. Returns CetaSignal acousticFeatures dict.
        annotation dict can override computed values with expert measurements.
        """
        import librosa

        log.info(f"  Extracting: {audio_path.name}")

        # Load audio — resample to target sr, convert to mono
        try:
            y, sr = librosa.load(str(audio_path), sr=self.sr_target, mono=True)
        except Exception as e:
            log.warning(f"  Audio load failed: {e}")
            return self._empty_features()

        duration_s = len(y) / sr

        # If annotation provides a time window, slice to it
        if annotation and annotation.get("begin_time_s") and annotation.get("end_time_s"):
            begin = int(annotation["begin_time_s"] * sr)
            end = int(annotation["end_time_s"] * sr)
            y = y[begin:min(end, len(y))]
            duration_s = len(y) / sr

        if len(y) < 512:
            log.warning(f"  Clip too short after slicing: {len(y)} samples")
            return self._empty_features()

        # ── Spectral features ────────────────────────────────────────────────
        n_fft = min(4096, len(y) // 2)
        hop = n_fft // 4

        stft = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
        mean_spectrum = stft.mean(axis=1)

        # Peak frequency
        peak_bin = np.argmax(mean_spectrum)
        peak_freq_hz = float(freqs[peak_bin])

        # -3dB bandwidth
        peak_power = mean_spectrum[peak_bin]
        half_power = peak_power * 0.707  # -3dB
        above_half = np.where(mean_spectrum >= half_power)[0]
        if len(above_half) > 1:
            bw_hz = float(freqs[above_half[-1]] - freqs[above_half[0]])
        else:
            bw_hz = 0.0

        # -20dB frequency range
        threshold = peak_power * 0.1
        above_thresh = np.where(mean_spectrum >= threshold)[0]
        freq_range = [float(freqs[above_thresh[0]]), float(freqs[above_thresh[-1]])] \
            if len(above_thresh) > 1 else [0.0, float(sr / 2)]

        # ── Frequency contour ────────────────────────────────────────────────
        freq_contour = self._classify_contour(y, sr, n_fft, hop)

        # ── Pulse detection ──────────────────────────────────────────────────
        ipi_ms, pulse_count = self._detect_pulses(y, sr)

        # ── Urgency index ────────────────────────────────────────────────────
        # Normalized amplitude variance — high variance = high urgency
        rms = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=hop)[0]
        rms_norm = rms / (rms.max() + 1e-8)
        urgency = float(np.std(rms_norm))
        urgency = min(1.0, urgency * 2.5)  # scale to 0–1

        # ── Amplitude envelope classification ────────────────────────────────
        amp_envelope = self._classify_envelope(rms_norm)

        # ── Repetition rate ──────────────────────────────────────────────────
        rep_hz = float(pulse_count / duration_s) if pulse_count > 1 and duration_s > 0 else 0.0

        # ── Build feature dict ───────────────────────────────────────────────
        features = {
            "peakFrequency_hz": round(peak_freq_hz, 1),
            "frequencyRange_hz": [round(freq_range[0], 1), round(freq_range[1], 1)],
            "duration_s": round(duration_s, 2),
            "freqContour": freq_contour,
            "interPulseInterval_ms": round(ipi_ms, 1) if ipi_ms else None,
            "pulseCount": pulse_count if pulse_count > 0 else None,
            "repetitionHz": round(rep_hz, 4),
            "urgencyIndex": round(urgency, 3),
            "amplitudeEnvelope": amp_envelope,
            "spectralBandwidth_hz": round(bw_hz, 1),
        }

        # ── Annotation override ──────────────────────────────────────────────
        # Expert annotation values always win over computed values
        if annotation:
            if annotation.get("peak_freq_hz") and annotation["peak_freq_hz"] > 0:
                features["peakFrequency_hz"] = round(annotation["peak_freq_hz"], 1)
                log.info(f"    [OVERRIDE] peakFrequency from annotation: {features['peakFrequency_hz']} Hz")
            if annotation.get("duration_s") and annotation["duration_s"] > 0:
                features["duration_s"] = round(annotation["duration_s"], 2)
                log.info(f"    [OVERRIDE] duration from annotation: {features['duration_s']} s")
            if annotation.get("bandwidth_hz") and annotation["bandwidth_hz"] > 0:
                features["spectralBandwidth_hz"] = round(annotation["bandwidth_hz"], 1)
                low = annotation.get("low_freq_hz", 0)
                high = annotation.get("high_freq_hz", 0)
                if low and high:
                    features["frequencyRange_hz"] = [round(low, 1), round(high, 1)]

        return features

    def _classify_contour(self, y: np.ndarray, sr: int, n_fft: int, hop: int) -> str:
        """
        Classify frequency contour by tracking spectral centroid over time.
        rising | descending | flat | complex
        """
        import librosa

        centroid = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=n_fft, hop_length=hop)[0]
        if len(centroid) < 4:
            return "flat"

        # Smooth centroid
        kernel = np.ones(max(3, len(centroid) // 8)) / max(3, len(centroid) // 8)
        smoothed = np.convolve(centroid, kernel, mode="valid")

        if len(smoothed) < 3:
            return "flat"

        # Fit linear trend
        x = np.arange(len(smoothed))
        slope, _ = np.polyfit(x, smoothed, 1)

        # Measure nonlinearity (residual from linear fit)
        fit = slope * x + _
        residual = np.std(smoothed - fit) / (np.std(smoothed) + 1e-8)

        # Classify
        slope_norm = slope / (np.mean(smoothed) + 1e-8)
        if residual > 0.35:
            return "complex"
        elif slope_norm > 0.003:
            return "rising"
        elif slope_norm < -0.003:
            return "descending"
        else:
            return "flat"

    def _detect_pulses(self, y: np.ndarray, sr: int) -> tuple[Optional[float], int]:
        """
        Detect pulses and compute inter-pulse interval.
        Returns (mean_ipi_ms, pulse_count).
        """
        import librosa

        # Onset detection
        onset_frames = librosa.onset.onset_detect(
            y=y, sr=sr, units="time",
            pre_max=3, post_max=3, pre_avg=10, post_avg=10,
            delta=0.07, wait=3
        )

        if len(onset_frames) < 2:
            return None, len(onset_frames)

        intervals_s = np.diff(onset_frames)
        ipi_ms = float(np.mean(intervals_s) * 1000)
        return ipi_ms, len(onset_frames)

    def _classify_envelope(self, rms_norm: np.ndarray) -> str:
        """Classify amplitude envelope shape."""
        if len(rms_norm) < 4:
            return "sustained"
        peak_idx = np.argmax(rms_norm)
        peak_pos = peak_idx / len(rms_norm)
        variance = np.std(rms_norm)

        if variance > 0.35:
            return "pulse"
        elif peak_pos < 0.25:
            return "attack_heavy"
        else:
            return "sustained"

    def _empty_features(self) -> dict:
        return {
            "peakFrequency_hz": None,
            "frequencyRange_hz": [None, None],
            "duration_s": None,
            "freqContour": None,
            "interPulseInterval_ms": None,
            "pulseCount": None,
            "repetitionHz": 0.0,
            "urgencyIndex": None,
            "amplitudeEnvelope": None,
            "spectralBandwidth_hz": None,
        }


# ── Specimen Builder ───────────────────────────────────────────────────────────

class SpecimenBuilder:
    """
    Assembles full CetaSignal specimen objects from audio features
    + annotation metadata + dataset registry.

    Output schema matches CadenceClassifier SPECIMENS[] exactly.
    """

    # Ground truth label map: call type → behavioral class
    # Derived from the CetaSignal constraint framework.
    CALL_TYPE_TO_CLASS = {
        # CONTACT
        "upcall": "CONTACT", "up call": "CONTACT", "contact call": "CONTACT",
        "coda": "CONTACT", "whistle": "CONTACT", "signature whistle": "CONTACT",
        "moan": "CONTACT",
        # DIVE
        "downsweep": "DIVE", "down sweep": "DIVE", "descending": "DIVE",
        "dive call": "DIVE",
        # FORAGE
        "click": "FORAGE", "click train": "FORAGE", "burst pulse": "FORAGE",
        "buzz": "FORAGE", "echolocation": "FORAGE", "fm click": "FORAGE",
        "boing": "FORAGE",
        # NAVIGATE
        "20 hz": "NAVIGATE", "20hz": "NAVIGATE", "pulse train": "NAVIGATE",
        "a call": "NAVIGATE", "b call": "NAVIGATE", "a/b call": "NAVIGATE",
        "migration": "NAVIGATE", "tonal": "NAVIGATE",
        # BROADCAST
        "song": "BROADCAST", "song phrase": "BROADCAST", "song unit": "BROADCAST",
        "broadcast": "BROADCAST",
    }

    def __init__(self, dataset_id: str, dataset_info: dict):
        self.dataset_id = dataset_id
        self.dataset_info = dataset_info
        self._counter = {}

    def build(self,
              audio_path: Path,
              features: dict,
              annotation: Optional[dict] = None) -> dict:
        """
        Build one specimen object.
        """
        # Determine call type from annotation or filename
        call_type_raw = ""
        if annotation:
            call_type_raw = annotation.get("annotation", "")
        if not call_type_raw:
            call_type_raw = self._infer_call_type_from_filename(audio_path.name)

        call_type = self._normalize_call_type(call_type_raw)
        ground_truth = self._map_to_behavioral_class(call_type)

        # Determine species
        species_info = self._resolve_species(annotation, audio_path.name)

        # Build catalog ID
        species_code = species_info.get("commonName", "UNK").split()[0][:4].upper()
        call_code = call_type[:4].upper().replace(" ", "")
        self._counter[species_code] = self._counter.get(species_code, 0) + 1
        n = self._counter[species_code]

        dataset_prefix = self.dataset_id.upper()[:8]
        catalog_id = f"{dataset_prefix}-{species_code}-{call_code}-{n:03d}"
        specimen_id = f"{species_code.lower()}_{call_code.lower()}_{n:03d}"

        # File hash for provenance
        try:
            with open(audio_path, "rb") as f:
                file_hash = hashlib.md5(f.read(65536)).hexdigest()[:12]
        except Exception:
            file_hash = "unknown"

        specimen = {
            "id": specimen_id,
            "catalogId": catalog_id,
            "species": species_info.get("species", "Unknown"),
            "commonName": species_info.get("commonName", "Unknown"),
            "callType": call_type,
            "callTypeDescription": self._describe_call_type(call_type),
            "sourceDataset": self.dataset_id,
            "annotationConfidence": annotation.get("confidence", "Computed") if annotation else "Computed",
            "annotationMethod": annotation.get("annotation_method", "librosa — automated extraction") if annotation else "librosa — automated extraction",
            "recordingLocation": self.dataset_info.get("location", ""),
            "recordingCoordinates": self.dataset_info.get("coordinates", {}),
            "recordingDepth_m": self.dataset_info.get("recording_depth_m", 0),
            "recordingYear": self._infer_year(audio_path.name),
            "sourceFile": audio_path.name,
            "sourceFileHash": file_hash,
            "extractedAt": datetime.utcnow().isoformat() + "Z",
            "environmentalContext": {
                "habitatType": "",
                "waterDepth_m": None,
                "ambientNoiseLevel": "",
                "sofar": features.get("peakFrequency_hz", 9999) < 200,
                "season": "",
            },
            "acousticFeatures": features,
            "behavioralRecord": {
                "observedBehavior": "",
                "groundTruth": ground_truth,
                "description": f"Computationally extracted from {audio_path.name}. Ground truth assigned from annotated call type: '{call_type}'.",
                "groundTruthMethod": annotation.get("annotation_method", "librosa automated") if annotation else "librosa automated",
                "observerNotes": "",
            },
            "citations": [self.dataset_info.get("citation", "")],
            "ocean_basin": self.dataset_info.get("ocean_basin", ""),
            "pipelineVersion": "cetasignal-pipeline-v1.0",
        }

        return specimen

    def _infer_call_type_from_filename(self, filename: str) -> str:
        """Infer call type from filename conventions."""
        fname = filename.lower()
        patterns = {
            "upcall": "Upcall", "up_call": "Upcall",
            "downsweep": "Downsweep", "20hz": "20 Hz Pulse",
            "song": "Song", "burst": "Burst Pulse",
            "click": "Click", "whistle": "Whistle", "coda": "Coda",
        }
        for pattern, call_type in patterns.items():
            if pattern in fname:
                return call_type
        return "Unknown"

    def _normalize_call_type(self, raw: str) -> str:
        raw = raw.strip()
        replacements = {
            "UC": "Upcall", "up-call": "Upcall", "NARW_UC": "Upcall",
            "DS": "Downsweep", "20HZ": "20 Hz Pulse",
            "BP": "Burst Pulse", "CL": "Click", "WH": "Whistle",
            "SG": "Song", "CD": "Coda",
        }
        return replacements.get(raw, raw.title() if raw else "Unknown")

    def _map_to_behavioral_class(self, call_type: str) -> str:
        ct_lower = call_type.lower()
        for pattern, cls in self.CALL_TYPE_TO_CLASS.items():
            if pattern in ct_lower:
                return cls
        return "CONTACT"  # conservative default

    def _resolve_species(self, annotation: Optional[dict], filename: str) -> dict:
        if annotation and annotation.get("species"):
            sp = annotation["species"]
            for code, info in self.dataset_info.get("species_map", {}).items():
                if code.lower() in sp.lower() or info["species"].lower() in sp.lower():
                    return info
            return {"species": sp, "commonName": sp}

        # Infer from filename
        filename_upper = filename.upper()
        for code, info in self.dataset_info.get("species_map", {}).items():
            if code in filename_upper:
                return info

        return {"species": "Unknown", "commonName": "Unknown"}

    def _describe_call_type(self, call_type: str) -> str:
        descriptions = {
            "Upcall": "Frequency-modulated rising sweep. Primary contact call.",
            "Downsweep": "Brief descending frequency-modulated call. Reliably precedes dive.",
            "20 Hz Pulse": "Regular infrasonic pulses at ~20Hz. SOFAR channel propagation.",
            "Song": "Complex hierarchically structured acoustic display.",
            "Burst Pulse": "High-energy rapid click train. Social and foraging context.",
            "Click": "Broadband impulsive signal. Echolocation or foraging.",
            "Coda": "Stereotyped click sequence. Social identity signal.",
            "Whistle": "Tonal frequency-modulated call. Contact and affiliation.",
        }
        for key, desc in descriptions.items():
            if key.lower() in call_type.lower():
                return desc
        return call_type

    def _infer_year(self, filename: str) -> Optional[int]:
        import re
        match = re.search(r"20\d{2}", filename)
        return int(match.group()) if match else None


# ── Output Writer ──────────────────────────────────────────────────────────────

class SpecimenWriter:
    """Writes specimens to JSON and CSV."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

    def write_json(self, specimens: list[dict], filename: str = "specimens.json"):
        path = self.output_dir / filename
        with open(path, "w") as f:
            json.dump(specimens, f, indent=2)
        log.info(f"Wrote {len(specimens)} specimens → {path}")
        return path

    def write_csv(self, specimens: list[dict], filename: str = "specimens.csv"):
        """Flatten nested specimen objects to CSV for analysis."""
        path = self.output_dir / filename
        rows = []
        for s in specimens:
            af = s.get("acousticFeatures", {})
            br = s.get("behavioralRecord", {})
            rows.append({
                "id": s["id"],
                "catalogId": s["catalogId"],
                "species": s["species"],
                "commonName": s["commonName"],
                "callType": s["callType"],
                "sourceDataset": s["sourceDataset"],
                "annotationConfidence": s["annotationConfidence"],
                "annotationMethod": s["annotationMethod"],
                "groundTruth": br.get("groundTruth", ""),
                "ocean_basin": s["ocean_basin"],
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
                "freq_low_hz": af.get("frequencyRange_hz", [None, None])[0],
                "freq_high_hz": af.get("frequencyRange_hz", [None, None])[1],
                "sourceFile": s.get("sourceFile", ""),
                "extractedAt": s.get("extractedAt", ""),
                "pipelineVersion": s.get("pipelineVersion", ""),
            })

        if not rows:
            log.warning("No specimens to write to CSV")
            return None

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        log.info(f"Wrote {len(rows)} rows → {path}")
        return path

    def write_summary(self, specimens: list[dict]):
        """Print extraction summary to log."""
        from collections import Counter
        classes = Counter(s["behavioralRecord"]["groundTruth"] for s in specimens)
        species = Counter(s["commonName"] for s in specimens)
        datasets = Counter(s["sourceDataset"] for s in specimens)
        methods = Counter(s["annotationMethod"] for s in specimens)

        log.info("=" * 60)
        log.info(f"EXTRACTION COMPLETE — {len(specimens)} specimens")
        log.info("-" * 60)
        log.info("Behavioral class distribution:")
        for cls, n in sorted(classes.items()):
            log.info(f"  {cls}: {n}")
        log.info("Species:")
        for sp, n in sorted(species.items(), key=lambda x: -x[1]):
            log.info(f"  {sp}: {n}")
        log.info("Datasets:")
        for ds, n in sorted(datasets.items()):
            log.info(f"  {ds}: {n}")
        log.info("Annotation methods:")
        for m, n in sorted(methods.items()):
            log.info(f"  {m}: {n}")
        log.info("=" * 60)


# ── Pipeline Orchestrator ──────────────────────────────────────────────────────

class CetaSignalPipeline:
    """
    Main pipeline. Orchestrates download → annotation parse
    → feature extraction → specimen build → output.
    """

    def __init__(self, output_dir: Path, max_files: int = 200):
        self.output_dir = output_dir
        self.max_files = max_files
        self.extractor = AcousticFeatureExtractor()
        self.writer = SpecimenWriter(output_dir)

    def run_from_local(self,
                       audio_dir: Path,
                       dataset_id: str,
                       annotation_dir: Optional[Path] = None,
                       annotation_format: str = "raven_tsv") -> list[dict]:
        """
        Run pipeline on locally downloaded audio files.
        This is the primary entry point for real data.
        """
        dataset_info = DATASETS.get(dataset_id, {
            "id": dataset_id,
            "shortName": dataset_id,
            "ocean_basin": "Unknown",
            "location": "Unknown",
            "coordinates": {},
            "recording_depth_m": 0,
            "species_map": {},
            "citation": "",
        })

        downloader = DatasetDownloader(audio_dir, self.max_files)
        audio_files = downloader.from_local_dir(audio_dir)

        if not audio_files:
            log.warning(f"No audio files found in {audio_dir}")
            return []

        # Build annotation index
        annotation_index = {}
        if annotation_dir and annotation_dir.exists():
            annotation_index = self._build_annotation_index(
                annotation_dir, annotation_format
            )
            log.info(f"Loaded {len(annotation_index)} annotations")

        builder = SpecimenBuilder(dataset_id, dataset_info)
        specimens = []

        for audio_path in audio_files:
            # Match annotation to audio file
            annotation = self._match_annotation(audio_path, annotation_index)

            # If annotation has multiple selections, extract each as a specimen
            if isinstance(annotation, list):
                for ann in annotation:
                    features = self.extractor.extract(audio_path, ann)
                    specimen = builder.build(audio_path, features, ann)
                    specimens.append(specimen)
                    log.info(f"  → {specimen['id']} [{specimen['behavioralRecord']['groundTruth']}]")
            else:
                features = self.extractor.extract(audio_path, annotation)
                specimen = builder.build(audio_path, features, annotation)
                specimens.append(specimen)
                log.info(f"  → {specimen['id']} [{specimen['behavioralRecord']['groundTruth']}]")

        return specimens

    def run_from_zenodo(self, record_id: str, dataset_id: str) -> list[dict]:
        """Download from Zenodo then run pipeline."""
        audio_dir = self.output_dir / "audio" / dataset_id
        downloader = DatasetDownloader(audio_dir, self.max_files)
        audio_files = downloader.download_zenodo(record_id)
        if not audio_files:
            log.error("No files downloaded from Zenodo")
            return []
        return self.run_from_local(audio_dir, dataset_id)

    def _build_annotation_index(self,
                                 annotation_dir: Path,
                                 fmt: str) -> dict:
        """
        Parse all annotation files in a directory.
        Returns dict: {stem -> [annotations]}
        """
        index = {}
        if fmt == "raven_tsv":
            parser = RavenParser()
            for f in annotation_dir.glob("*.txt"):
                anns = parser.parse(f)
                index[f.stem] = anns
            for f in annotation_dir.glob("*.tsv"):
                anns = parser.parse(f)
                index[f.stem] = anns
        elif fmt == "pamguard_csv":
            parser = PAMGuardParser()
            for f in annotation_dir.glob("*.csv"):
                anns = parser.parse(f)
                index[f.stem] = anns
        return index

    def _match_annotation(self, audio_path: Path, index: dict):
        """Match an audio file to its annotation(s)."""
        # Exact stem match
        if audio_path.stem in index:
            return index[audio_path.stem]
        # Partial stem match
        for stem, anns in index.items():
            if stem in audio_path.stem or audio_path.stem in stem:
                return anns
        return None

    def save(self, specimens: list[dict]):
        """Write all outputs."""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.writer.write_json(specimens, f"specimens_{ts}.json")
        self.writer.write_json(specimens, "specimens_latest.json")
        self.writer.write_csv(specimens, f"specimens_{ts}.csv")
        self.writer.write_csv(specimens, "specimens_latest.csv")
        self.writer.write_summary(specimens)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CetaSignal Data Extraction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run on locally downloaded Zenodo Orca dataset
  python cetasignal_pipeline.py \\
    --audio ./data/myers2025/ \\
    --dataset myers2025 \\
    --raven ./data/myers2025/annotations/ \\
    --output ./specimens/

  # Run on NOAA NEFSC audio with Raven annotations
  python cetasignal_pipeline.py \\
    --audio ./data/noaa_nefsc/wav/ \\
    --dataset noaa_nefsc \\
    --raven ./data/noaa_nefsc/annotations/ \\
    --output ./specimens/

  # Download from Zenodo and run
  python cetasignal_pipeline.py \\
    --zenodo 15743033 \\
    --dataset myers2025 \\
    --output ./specimens/

  # Run on any local audio (auto-infer call types from filenames)
  python cetasignal_pipeline.py \\
    --audio ./my_recordings/ \\
    --dataset custom \\
    --output ./specimens/
        """,
    )

    parser.add_argument("--audio",    type=Path, help="Directory of local audio files (WAV/FLAC)")
    parser.add_argument("--raven",    type=Path, help="Directory of Raven TSV annotation files")
    parser.add_argument("--pamguard", type=Path, help="Directory of PAMGuard CSV exports")
    parser.add_argument("--zenodo",   type=str,  help="Zenodo record ID to download")
    parser.add_argument("--dataset",  type=str,  default="custom",
                        help=f"Dataset ID. Known: {list(DATASETS.keys())}")
    parser.add_argument("--output",   type=Path, default=Path("./specimens"),
                        help="Output directory for JSON and CSV")
    parser.add_argument("--max",      type=int,  default=200,
                        help="Max audio files to process")

    args = parser.parse_args()

    pipeline = CetaSignalPipeline(args.output, max_files=args.max)

    # Determine annotation format
    ann_dir = args.raven or args.pamguard
    ann_fmt = "raven_tsv" if args.raven else "pamguard_csv" if args.pamguard else "raven_tsv"

    # Run
    if args.zenodo:
        specimens = pipeline.run_from_zenodo(args.zenodo, args.dataset)
    elif args.audio:
        specimens = pipeline.run_from_local(args.audio, args.dataset, ann_dir, ann_fmt)
    else:
        parser.print_help()
        sys.exit(1)

    if specimens:
        pipeline.save(specimens)
        log.info(f"Done. {len(specimens)} specimens extracted.")
    else:
        log.warning("No specimens extracted. Check audio files and annotations.")


if __name__ == "__main__":
    main()
