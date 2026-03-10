#!/usr/bin/env python3
"""
extract_features.py
-------------------
Extracts cadence features from whale call WAV files.

Features extracted:
  - peak_freq_hz: dominant frequency
  - inter_pulse_interval_ms: timing between pulses (rhythm)
  - duration_s: call duration
  - freq_contour: rising / flat / descending / complex
  - amplitude_envelope: attack / sustain / decay profile
  - repetition_rate: autocorrelation-based repetition
  - mfcc_centroid: timbral centroid
  - bandwidth_hz: spectral bandwidth

Usage:
  python extract_features.py --input ../data/calls/ --output ../data/features.json
"""

import json
import argparse
import numpy as np
from pathlib import Path


def extract_features(wav_path: str) -> dict:
    """Extract cadence features from a single WAV file."""
    try:
        import librosa
        import scipy.signal as signal
        
        y, sr = librosa.load(wav_path, sr=None, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # ── Peak Frequency ──────────────────────────────
        fft = np.abs(np.fft.rfft(y))
        freqs = np.fft.rfftfreq(len(y), 1/sr)
        peak_freq = float(freqs[np.argmax(fft)])
        
        # ── Spectral Bandwidth ───────────────────────────
        spec_bw = float(librosa.feature.spectral_bandwidth(y=y, sr=sr).mean())
        
        # ── Frequency Contour ────────────────────────────
        # Track frequency over time — rising, falling, flat, or complex
        hop_length = 512
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr, hop_length=hop_length)
        pitch_track = []
        for i in range(pitches.shape[1]):
            idx = magnitudes[:, i].argmax()
            if magnitudes[idx, i] > 0.1:
                pitch_track.append(float(pitches[idx, i]))
        
        if len(pitch_track) > 2:
            pitch_arr = np.array([p for p in pitch_track if p > 0])
            if len(pitch_arr) > 2:
                slope = np.polyfit(range(len(pitch_arr)), pitch_arr, 1)[0]
                variance = float(np.std(pitch_arr))
                if variance > 100:
                    contour = 'complex'
                elif slope > 5:
                    contour = 'rising'
                elif slope < -5:
                    contour = 'descending'
                else:
                    contour = 'flat'
            else:
                contour = 'flat'
        else:
            contour = 'unknown'
        
        # ── Amplitude Envelope ───────────────────────────
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        rms_norm = rms / (rms.max() + 1e-8)
        
        # Characterize envelope shape
        mid = len(rms_norm) // 2
        first_half_mean = float(rms_norm[:mid].mean())
        second_half_mean = float(rms_norm[mid:].mean())
        peak_position = float(np.argmax(rms_norm) / len(rms_norm))
        
        if peak_position < 0.2:
            envelope_shape = 'attack_heavy'
        elif peak_position > 0.8:
            envelope_shape = 'buildup'
        elif abs(first_half_mean - second_half_mean) < 0.1:
            envelope_shape = 'sustained'
        else:
            envelope_shape = 'pulse'
        
        # ── Inter-Pulse Interval ─────────────────────────
        # Detect pulses via onset detection
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)
        
        if len(onset_times) > 1:
            intervals = np.diff(onset_times) * 1000  # convert to ms
            ipi_mean = float(intervals.mean())
            ipi_std = float(intervals.std())
            pulse_count = len(onset_times)
        else:
            ipi_mean = float(duration * 1000)
            ipi_std = 0.0
            pulse_count = 1
        
        # ── Repetition Rate ──────────────────────────────
        # Autocorrelation to detect repeating patterns
        autocorr = np.correlate(rms_norm, rms_norm, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        autocorr = autocorr / autocorr[0]
        
        # Find first significant peak after lag 0
        min_lag = max(1, int(0.1 * sr / hop_length))  # min 100ms
        peaks, _ = signal.find_peaks(autocorr[min_lag:], height=0.3)
        if len(peaks) > 0:
            rep_period_s = float((peaks[0] + min_lag) * hop_length / sr)
            repetition_hz = 1.0 / rep_period_s if rep_period_s > 0 else 0.0
        else:
            rep_period_s = float(duration)
            repetition_hz = 0.0
        
        # ── MFCC Features ────────────────────────────────
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_means = mfccs.mean(axis=1).tolist()
        
        # ── Zero Crossing Rate ───────────────────────────
        zcr = float(librosa.feature.zero_crossing_rate(y).mean())
        
        # ── Urgency Score ────────────────────────────────
        # Heuristic: high repetition + high amplitude + short IPI = high urgency
        urgency = 0.0
        if ipi_mean < 200:
            urgency += 0.4
        if repetition_hz > 2.0:
            urgency += 0.3
        if float(rms_norm.max()) > 0.8:
            urgency += 0.3
        
        return {
            'peak_freq_hz': round(peak_freq, 2),
            'spectral_bandwidth_hz': round(spec_bw, 2),
            'freq_contour': contour,
            'duration_s': round(duration, 3),
            'amplitude_envelope': envelope_shape,
            'inter_pulse_interval_ms': round(ipi_mean, 2),
            'ipi_std_ms': round(ipi_std, 2),
            'pulse_count': pulse_count,
            'repetition_hz': round(repetition_hz, 4),
            'rep_period_s': round(rep_period_s, 3),
            'mfcc_means': [round(m, 4) for m in mfcc_means],
            'zero_crossing_rate': round(zcr, 6),
            'urgency_score': round(urgency, 3),
            'sample_rate': sr,
            'extraction_success': True
        }
        
    except Exception as e:
        return {
            'extraction_success': False,
            'error': str(e)
        }


def main():
    parser = argparse.ArgumentParser(description='Extract cadence features from whale WAVs')
    parser.add_argument('--input', default='../data/calls/', help='Directory containing WAV files')
    parser.add_argument('--output', default='../data/features.json', help='Output features JSON')
    parser.add_argument('--manifest', default='../data/manifest.json', help='Call manifest JSON')
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_path = Path(args.output)
    
    print(f"\n🎼 CetaSignal Feature Extractor")
    print(f"{'='*50}")
    
    # Load manifest if available
    manifest_path = Path(args.manifest)
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path) as f:
            data = json.load(f)
            manifest = {item['id']: item for item in data}
        print(f"Loaded manifest: {len(manifest)} calls")
    
    # Find all WAV files
    wav_files = list(input_dir.glob('*.wav'))
    print(f"Found {len(wav_files)} WAV files\n")
    
    if not wav_files:
        print("No WAV files found. Run download_noaa.py first.")
        print("Creating feature template from manifest...")
        
        # Create feature templates from manifest metadata
        results = []
        for call_id, call in manifest.items():
            feature_template = {
                'call_id': call_id,
                'features': {
                    'peak_freq_hz': call.get('peak_freq_hz', 100),
                    'duration_s': call.get('duration_s', 1.0),
                    'freq_contour': 'unknown',
                    'amplitude_envelope': 'unknown',
                    'inter_pulse_interval_ms': 500,
                    'urgency_score': 0.5,
                    'extraction_success': False,
                    'note': 'Template — requires real WAV file'
                },
                'metadata': call
            }
            results.append(feature_template)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Template saved: {output_path}")
        return
    
    results = []
    for wav_path in wav_files:
        call_id = wav_path.stem
        print(f"🔬 Extracting: {call_id}")
        
        features = extract_features(str(wav_path))
        
        result = {
            'call_id': call_id,
            'wav_path': str(wav_path),
            'features': features,
            'metadata': manifest.get(call_id, {})
        }
        results.append(result)
        
        if features['extraction_success']:
            print(f"   Peak: {features['peak_freq_hz']}Hz | "
                  f"Duration: {features['duration_s']}s | "
                  f"Contour: {features['freq_contour']} | "
                  f"Urgency: {features['urgency_score']}")
        else:
            print(f"   ✗ Failed: {features.get('error', 'unknown')}")
        print()
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    success = sum(1 for r in results if r['features'].get('extraction_success'))
    print(f"{'='*50}")
    print(f"✅ Extracted: {success}/{len(results)} calls")
    print(f"   Saved: {output_path}")
    print(f"\nNext step: python train_model.py")


if __name__ == '__main__':
    main()
