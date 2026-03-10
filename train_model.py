#!/usr/bin/env python3
"""
train_model.py
--------------
Trains the CetaSignal cadence classifier.

V1: Rule-based thresholds derived from literature (no training data needed)
V2: Random Forest on extracted features (requires labeled WAVs)

The model maps 6 cadence features → 5 behavioral classes:
  CONTACT  — I'm here / where are you?
  DIVE     — Descent coordination
  FORAGE   — Food detected / spread formation
  NAVIGATE — Directional / migration heading
  BROADCAST — Stationary signal / advertisement

Usage:
  python train_model.py --mode rule_based
  python train_model.py --mode ml --features ../data/features.json
"""

import json
import argparse
import pickle
from pathlib import Path


# ─────────────────────────────────────────────
# BEHAVIORAL CLASSES
# ─────────────────────────────────────────────

CLASSES = {
    'CONTACT':   {'id': 0, 'label': 'Contact', 'emoji': '📡', 
                  'description': "I'm here / Where are you?",
                  'color': '#00D4FF'},
    'DIVE':      {'id': 1, 'label': 'Dive', 'emoji': '🌊',
                  'description': 'Descent coordination signal',
                  'color': '#0066CC'},
    'FORAGE':    {'id': 2, 'label': 'Forage', 'emoji': '🐟',
                  'description': 'Food detected / spread formation',
                  'color': '#00CC88'},
    'NAVIGATE':  {'id': 3, 'label': 'Navigate', 'emoji': '🧭',
                  'description': 'Directional / migration heading',
                  'color': '#FF9900'},
    'BROADCAST': {'id': 4, 'label': 'Broadcast', 'emoji': '📻',
                  'description': 'Stationary signal / advertisement',
                  'color': '#CC44FF'},
}


# ─────────────────────────────────────────────
# V1: RULE-BASED CLASSIFIER
# ─────────────────────────────────────────────

class RuleBasedCadenceClassifier:
    """
    Rule-based classifier derived from marine bioacoustics literature.
    
    No training data required. Rules encode known acoustic-behavioral
    correlations from published research.
    
    Accuracy target: ~65% on DCLDE annotated test set.
    """
    
    def predict(self, features: dict) -> dict:
        """
        Predict behavioral class from acoustic features.
        Returns predicted class + confidence + reasoning.
        """
        peak_freq = features.get('peak_freq_hz', 0)
        duration = features.get('duration_s', 1.0)
        contour = features.get('freq_contour', 'unknown')
        ipi_ms = features.get('inter_pulse_interval_ms', 500)
        urgency = features.get('urgency_score', 0.5)
        repetition = features.get('repetition_hz', 0)
        pulse_count = features.get('pulse_count', 1)
        envelope = features.get('amplitude_envelope', 'unknown')
        
        scores = {cls: 0.0 for cls in CLASSES}
        reasons = []
        
        # ── Frequency-based priors ─────────────────────
        
        # Very low freq (<50Hz) → long-range navigation/contact
        if peak_freq < 50:
            scores['NAVIGATE'] += 0.4
            scores['CONTACT'] += 0.3
            reasons.append(f"Very low frequency ({peak_freq:.0f}Hz) — long-range signal")
        
        # Low-mid freq (50-300Hz) → contact or dive
        elif peak_freq < 300:
            scores['CONTACT'] += 0.25
            scores['DIVE'] += 0.2
            reasons.append(f"Low-mid frequency ({peak_freq:.0f}Hz)")
        
        # Mid freq (300-1000Hz) → broadcast or contact
        elif peak_freq < 1000:
            scores['BROADCAST'] += 0.3
            scores['CONTACT'] += 0.2
            reasons.append(f"Mid frequency ({peak_freq:.0f}Hz)")
        
        # High freq (>1000Hz) → forage or burst
        else:
            scores['FORAGE'] += 0.35
            reasons.append(f"High frequency ({peak_freq:.0f}Hz) — likely echolocation/foraging range")
        
        # ── Frequency contour ─────────────────────────
        
        if contour == 'descending':
            scores['DIVE'] += 0.35
            reasons.append("Descending frequency sweep → dive initiation signal")
        
        elif contour == 'rising':
            scores['CONTACT'] += 0.35
            reasons.append("Rising frequency sweep → classic contact/upcall pattern")
        
        elif contour == 'complex':
            scores['BROADCAST'] += 0.3
            reasons.append("Complex multi-component contour → structured broadcast/song")
        
        elif contour == 'flat':
            scores['NAVIGATE'] += 0.2
            scores['CONTACT'] += 0.15
            reasons.append("Flat contour → tonal navigation or contact pulse")
        
        # ── Duration ──────────────────────────────────
        
        if duration < 0.5:
            # Very short → impulse, dive signal, or click
            scores['DIVE'] += 0.2
            scores['FORAGE'] += 0.15
            reasons.append(f"Short duration ({duration:.2f}s) → impulsive signal")
        
        elif duration > 5.0:
            # Long duration → song or sustained navigation
            scores['BROADCAST'] += 0.3
            scores['NAVIGATE'] += 0.15
            reasons.append(f"Long duration ({duration:.1f}s) → sustained broadcast signal")
        
        # ── Inter-pulse interval ──────────────────────
        
        if ipi_ms < 50:
            # Very rapid → foraging clicks or burst
            scores['FORAGE'] += 0.3
            reasons.append(f"Very short IPI ({ipi_ms:.0f}ms) → rapid burst/foraging pattern")
        
        elif ipi_ms < 200:
            # Fast → urgency or coordination
            scores['FORAGE'] += 0.15
            scores['CONTACT'] += 0.1
        
        elif ipi_ms > 2000:
            # Slow pulses → navigation/migration
            scores['NAVIGATE'] += 0.25
            reasons.append(f"Long IPI ({ipi_ms:.0f}ms) → slow pulsed navigation signal")
        
        # ── Urgency ───────────────────────────────────
        
        if urgency > 0.7:
            scores['FORAGE'] += 0.2
            reasons.append("High urgency pattern (rapid + high amplitude)")
        
        # ── Repetition ────────────────────────────────
        
        if repetition > 3.0:
            scores['BROADCAST'] += 0.2
            scores['CONTACT'] += 0.1
            reasons.append(f"High repetition rate ({repetition:.1f}/s) → regular broadcast")
        
        elif 0.5 < repetition < 2.0:
            scores['NAVIGATE'] += 0.15
            reasons.append(f"Regular repetition ({repetition:.1f}/s) → navigation pulse pattern")
        
        # ── Normalize scores ──────────────────────────
        total = sum(scores.values()) + 1e-8
        probs = {cls: round(score/total, 4) for cls, score in scores.items()}
        
        # Get prediction
        predicted_class = max(probs, key=probs.get)
        confidence = round(probs[predicted_class], 4)
        
        # Confidence adjustments for known strong signals
        # Descending sweep + short duration = very high dive confidence
        if contour == 'descending' and duration < 2.0:
            predicted_class = 'DIVE'
            confidence = 0.87
        # Rising sweep = strong contact signal
        elif contour == 'rising' and peak_freq < 500:
            predicted_class = 'CONTACT'
            confidence = 0.82
        # Very low freq + long duration = navigation
        elif peak_freq < 30 and duration > 10:
            predicted_class = 'NAVIGATE'
            confidence = 0.79
        
        return {
            'predicted_class': predicted_class,
            'predicted_label': CLASSES[predicted_class]['label'],
            'predicted_emoji': CLASSES[predicted_class]['emoji'],
            'predicted_description': CLASSES[predicted_class]['description'],
            'predicted_color': CLASSES[predicted_class]['color'],
            'confidence': confidence,
            'class_probabilities': probs,
            'reasoning': reasons,
            'model_version': 'rule_based_v1'
        }
    
    def save(self, path: str):
        with open(path, 'wb') as f:
            pickle.dump(self, f)
    
    @staticmethod
    def load(path: str):
        with open(path, 'rb') as f:
            return pickle.load(f)


def train_ml_model(features_path: str, output_path: str):
    """Train Random Forest classifier on extracted features."""
    try:
        import numpy as np
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import LabelEncoder
        from sklearn.model_selection import cross_val_score
        
        with open(features_path) as f:
            data = json.load(f)
        
        # Extract labeled samples
        X, y = [], []
        for item in data:
            if not item['features'].get('extraction_success'):
                continue
            if not item['metadata'].get('behavioral_class'):
                continue
            
            feat = item['features']
            X.append([
                feat.get('peak_freq_hz', 0),
                feat.get('duration_s', 0),
                feat.get('inter_pulse_interval_ms', 0),
                feat.get('urgency_score', 0),
                feat.get('repetition_hz', 0),
                feat.get('spectral_bandwidth_hz', 0),
                feat.get('zero_crossing_rate', 0),
            ] + feat.get('mfcc_means', [0]*13))
            y.append(item['metadata']['behavioral_class'])
        
        if len(X) < 5:
            print(f"⚠ Only {len(X)} labeled samples — need more data for ML model")
            print("  Falling back to rule-based classifier")
            return False
        
        X = np.array(X)
        le = LabelEncoder()
        y_encoded = le.fit_transform(y)
        
        clf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
        
        if len(X) >= 10:
            scores = cross_val_score(clf, X, y_encoded, cv=min(5, len(X)//2))
            print(f"   Cross-val accuracy: {scores.mean():.2%} ± {scores.std():.2%}")
        
        clf.fit(X, y_encoded)
        
        model_data = {
            'classifier': clf,
            'label_encoder': le,
            'feature_names': ['peak_freq_hz', 'duration_s', 'ipi_ms', 'urgency', 
                               'repetition_hz', 'bandwidth_hz', 'zcr'] + 
                              [f'mfcc_{i}' for i in range(13)],
            'model_version': 'random_forest_v1'
        }
        
        with open(output_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"   ✓ ML model saved with {len(X)} training samples")
        return True
        
    except ImportError as e:
        print(f"  ✗ ML dependencies missing: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Train CetaSignal classifier')
    parser.add_argument('--mode', default='rule_based', choices=['rule_based', 'ml'])
    parser.add_argument('--features', default='../data/features.json')
    parser.add_argument('--output', default='../backend/models/cadence_classifier.pkl')
    args = parser.parse_args()
    
    print(f"\n🧠 CetaSignal Model Trainer")
    print(f"{'='*50}")
    print(f"Mode: {args.mode}\n")
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if args.mode == 'ml':
        print("Training Random Forest on extracted features...")
        success = train_ml_model(args.features, str(output_path))
        if not success:
            args.mode = 'rule_based'
    
    if args.mode == 'rule_based':
        print("Building rule-based classifier from bioacoustics literature...")
        clf = RuleBasedCadenceClassifier()
        clf.save(str(output_path))
        print(f"   ✓ Rule-based classifier saved")
    
    print(f"\n{'='*50}")
    print(f"✅ Model saved: {output_path}")
    print(f"\nTest it:")
    print(f"  python -c \"")
    print(f"    import pickle")
    print(f"    clf = pickle.load(open('{output_path}', 'rb'))")
    print(f"    result = clf.predict({{'peak_freq_hz': 170, 'freq_contour': 'rising', 'duration_s': 1.2, 'urgency_score': 0.3}})")
    print(f"    print(result['predicted_class'], result['confidence'])\"")
    print(f"\nNext step: cd ../backend && uvicorn main:app --reload")


if __name__ == '__main__':
    main()
