"""
cadence_engine.py
─────────────────
Python implementation of the CetaSignal cadence-to-behavior classifier.

Direct port of runCadenceModel() from the JavaScript frontend.
Both implementations must stay in sync — this is the validation layer.

Accepts either:
  - A dict of acoustic features
  - A pandas Series (one row from dataset)
  - A pandas DataFrame (batch prediction)

Output schema per specimen:
  {
    predicted_class : str,
    confidence      : float,
    probabilities   : dict,
    rule_trace      : list[dict],
    model_version   : str
  }

Usage:
  from cadence_engine import CadenceEngine
  engine = CadenceEngine()
  result = engine.predict({'peakFrequency_hz': 170, 'freqContour': 'rising', ...})
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import Optional

# ── Constants ────────────────────────────────────────────────────

MODEL_VERSION = 'CadenceClassifier-v1.0-python (rule-based)'

BEHAVIORAL_CLASSES = ['CONTACT', 'DIVE', 'FORAGE', 'NAVIGATE', 'BROADCAST']

# Base score ensures no class is completely shut out before rules apply
BASE_SCORE = 0.05


# ── Data structures ───────────────────────────────────────────────

@dataclass
class RuleTrace:
    rule: str
    contribution: str
    rationale: str
    feature_value: str


@dataclass
class PredictionResult:
    predicted_class: str
    confidence: float
    probabilities: dict
    rule_trace: list
    model_version: str = MODEL_VERSION

    def to_dict(self):
        return asdict(self)


# ── Engine ───────────────────────────────────────────────────────

class CadenceEngine:
    """
    Rule-based acoustic cadence → behavioral class classifier.

    Designed for transparency: every inference step is recorded in rule_trace.
    This is intentional — transparent classifiers are more publishable than
    black-box models for scientific validation purposes.
    """

    def predict(self, features) -> PredictionResult:
        """
        Predict behavioral class from acoustic features.

        Args:
            features : dict, pd.Series, or single-row pd.DataFrame

        Returns:
            PredictionResult
        """
        if isinstance(features, pd.DataFrame):
            if len(features) == 1:
                features = features.iloc[0]
            else:
                raise ValueError("Use predict_batch() for multiple rows.")
        if isinstance(features, pd.Series):
            features = features.to_dict()

        return self._run(features)

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Batch predict across a DataFrame.
        Returns DataFrame with prediction columns appended.
        """
        results = []
        for _, row in df.iterrows():
            r = self._run(row.to_dict())
            results.append({
                'predicted_class': r.predicted_class,
                'confidence':      r.confidence,
                'rule_count':      len(r.rule_trace),
                **{f'prob_{cls}': r.probabilities.get(cls, 0) for cls in BEHAVIORAL_CLASSES}
            })
        result_df = pd.DataFrame(results, index=df.index)
        return pd.concat([df, result_df], axis=1)

    def _run(self, f: dict) -> PredictionResult:
        pf  = float(f.get('peakFrequency_hz', 200) or 200)
        fc  = str(f.get('freqContour', 'flat') or 'flat').lower().strip()
        dur = float(f.get('duration_s', 1.0) or 1.0)
        urg = float(f.get('urgencyIndex', 0.3) or 0.3)
        rep = float(f.get('repetitionHz', 0.0) or 0.0)

        raw_ipi = f.get('interPulseInterval_ms')
        ipi = None if (raw_ipi is None or (isinstance(raw_ipi, float) and np.isnan(raw_ipi))) \
              else float(raw_ipi)

        scores = {cls: BASE_SCORE for cls in BEHAVIORAL_CLASSES}
        trace  = []

        # ── Peak Frequency ────────────────────────────────────
        if pf < 50:
            scores['NAVIGATE'] += 0.35; scores['CONTACT'] += 0.25
            trace.append(RuleTrace('Peak frequency < 50 Hz', 'NAVIGATE +0.35 · CONTACT +0.25',
                'Infrasonic range. SOFAR channel exploitation. Long-range navigation or basin-scale contact.',
                f'{pf:.1f} Hz'))
        elif pf < 300:
            scores['CONTACT'] += 0.22; scores['DIVE'] += 0.18
            trace.append(RuleTrace('Peak frequency 50–300 Hz', 'CONTACT +0.22 · DIVE +0.18',
                'Low-mid baleen range. Contact calls and dive coordination signals cluster here.',
                f'{pf:.1f} Hz'))
        elif pf < 1200:
            scores['BROADCAST'] += 0.28; scores['CONTACT'] += 0.18
            trace.append(RuleTrace('Peak frequency 300–1200 Hz', 'BROADCAST +0.28 · CONTACT +0.18',
                'Mid-range. Humpback song and delphinid contact whistles.',
                f'{pf:.1f} Hz'))
        else:
            # FIX 1: IPI-first disambiguation for high-frequency calls.
            # Sperm whale codas and beluga chirps are social (CONTACT) at 2-8kHz
            # but forage clicks are also high frequency. IPI is the separator:
            # social codas: IPI 55-350ms → CONTACT
            # foraging clicks: IPI < 50ms → FORAGE
            # no IPI data: ambiguous, split the prior
            if ipi is not None and ipi >= 55 and ipi <= 400:
                scores['CONTACT'] += 0.38; scores['FORAGE'] += 0.08
                trace.append(RuleTrace('Peak frequency > 1200 Hz + IPI 55–400 ms', 'CONTACT +0.38 · FORAGE +0.08',
                    'High-frequency social signal. IPI 55-400ms matches odontocete coda/social range, not foraging burst.',
                    f'{pf:.1f} Hz, IPI={ipi:.1f}ms'))
            elif ipi is not None and ipi < 55:
                scores['FORAGE'] += 0.38
                trace.append(RuleTrace('Peak frequency > 1200 Hz + IPI < 55 ms', 'FORAGE +0.38',
                    'High-frequency + rapid IPI: odontocete foraging burst pulse. IPI below social coda threshold.',
                    f'{pf:.1f} Hz, IPI={ipi:.1f}ms'))
            else:
                # FIX 2: No IPI data at high frequency.
                # Beaked whale deep foraging clicks (Cuvier's, Blainville's): 38-55kHz, urg 0.55-0.85, no IPI logged
                # Delphinid social whistles: 5-18kHz, urg 0.12-0.45, no IPI (tonal)
                # Urgency splits them cleanly.
                if urg > 0.50:
                    scores['FORAGE'] += 0.38; scores['CONTACT'] += 0.04
                    trace.append(RuleTrace('Peak frequency > 1200 Hz + no IPI + high urgency',
                        'FORAGE +0.38 · CONTACT +0.04',
                        'High-frequency + high urgency + no IPI: beaked whale / odontocete deep foraging click. '
                        'Urgency > 0.50 excludes delphinid social whistles (urg < 0.45). '
                        'Ref: Johnson et al. 2004; Madsen et al. 2005.',
                        f'{pf:.1f} Hz, urg={urg:.3f}'))
                else:
                    scores['FORAGE'] += 0.14; scores['CONTACT'] += 0.28
                    trace.append(RuleTrace('Peak frequency > 1200 Hz + no IPI + low-moderate urgency',
                        'CONTACT +0.28 · FORAGE +0.14',
                        'High-frequency + moderate urgency + no IPI: delphinid social whistle range. '
                        'Urgency < 0.50 consistent with social signaling, not active foraging pursuit. '
                        'Ref: Lammers & Au 2003; Rankin & Barlow 2005.',
                        f'{pf:.1f} Hz, urg={urg:.3f}'))

        # ── Frequency Contour ─────────────────────────────────
        if fc == 'descending':
            scores['DIVE'] += 0.38
            trace.append(RuleTrace('Descending frequency contour', 'DIVE +0.38',
                'Descending sweeps reliably precede dive initiation in baleen whale records.',
                fc))
        elif fc == 'rising':
            scores['CONTACT'] += 0.38
            trace.append(RuleTrace('Rising frequency contour', 'CONTACT +0.38',
                'Rising sweeps (upcall pattern) are the canonical contact call shape.',
                fc))
        elif fc == 'complex':
            # FIX 1a: Complex contour alone is not sufficient for BROADCAST.
            # Delphinid social whistles (spinners, spotted, common, pilot, humpback social)
            # are contour-complex but are CONTACT signals with urgency 0.12-0.45.
            # True broadcast songs (humpback, bowhead, Omura's) have urgency < 0.20
            # and duration > 4s. Gate the BROADCAST score behind those constraints.
            if urg < 0.22 and dur > 3.0:
                scores['BROADCAST'] += 0.32
                trace.append(RuleTrace('Complex contour + low urgency + sustained duration',
                    'BROADCAST +0.32',
                    'Hierarchically structured low-urgency sustained call: song/broadcast signature. '
                    'Urgency gate (< 0.22) excludes delphinid social whistles (urg 0.12-0.45, dur < 3s).',
                    f'{fc}, urg={urg:.3f}, dur={dur:.2f}s'))
            else:
                # Complex contour + moderate urgency or short duration = social contact
                scores['CONTACT'] += 0.28
                trace.append(RuleTrace('Complex contour + moderate urgency or short duration',
                    'CONTACT +0.28',
                    'Complex contour with urgency >= 0.22 or duration <= 3s matches delphinid '
                    'social whistle pattern (spinner, pilot whale, humpback social calls). '
                    'Not broadcast — broadcast songs are low-urgency sustained signals.',
                    f'{fc}, urg={urg:.3f}, dur={dur:.2f}s'))
        elif fc == 'flat':
            scores['NAVIGATE'] += 0.18; scores['CONTACT'] += 0.10
            trace.append(RuleTrace('Flat (tonal) contour', 'NAVIGATE +0.18 · CONTACT +0.10',
                'Tonal flat calls are characteristic of regular navigation pulse trains.',
                fc))

        # ── Duration ──────────────────────────────────────────
        if dur > 5:
            scores['BROADCAST'] += 0.22; scores['NAVIGATE'] += 0.12
            trace.append(RuleTrace('Duration > 5 s', 'BROADCAST +0.22 · NAVIGATE +0.12',
                'Extended duration: sustained broadcast or long-period navigation signal.',
                f'{dur:.2f} s'))
        elif dur < 0.5:
            scores['DIVE'] += 0.16; scores['FORAGE'] += 0.12
            trace.append(RuleTrace('Duration < 0.5 s', 'DIVE +0.16 · FORAGE +0.12',
                'Brief impulsive signal. Dive initiation or foraging click burst.',
                f'{dur:.2f} s'))

        # FIX 2: Phrase-level repetition window for BROADCAST.
        # Broadcast signals (song, boing, slow click series) repeat at 0.04–0.25 Hz.
        # This band is distinct from contact (0.05–0.5 Hz overlaps) but combined
        # with low urgency and moderate duration creates a near-diagnostic signature.
        # Minke boing: ~0.1-0.3 Hz. Bowhead song phrases: ~0.05-0.15 Hz.
        # Sperm whale slow clicks: ~0.03-0.10 Hz.
        if rep > 0.03 and rep < 0.28 and urg < 0.22 and dur > 0.6:
            scores['BROADCAST'] += 0.30
            trace.append(RuleTrace('Broadcast repetition band (0.03–0.28 Hz) + low urgency',
                'BROADCAST +0.30',
                'Repetition rate and urgency profile matches broadcast/song behavior. '
                'Covers minke boing (0.1-0.3Hz), bowhead song (0.05-0.15Hz), sperm slow click (0.03-0.10Hz).',
                f'rep={rep:.3f}Hz, urg={urg:.3f}, dur={dur:.2f}s'))

        # ── Inter-Pulse Interval ──────────────────────────────
        if ipi is not None:
            if ipi < 50:
                scores['FORAGE'] += 0.28
                trace.append(RuleTrace('IPI < 50 ms', 'FORAGE +0.28',
                    'Very rapid IPI: odontocete foraging burst pulses. Below social coda threshold.',
                    f'{ipi:.1f} ms'))
            elif ipi < 55:
                # Boundary zone — ambiguous between rapid social and slow foraging
                scores['FORAGE'] += 0.14; scores['CONTACT'] += 0.14
                trace.append(RuleTrace('IPI 50–55 ms (boundary zone)', 'FORAGE +0.14 · CONTACT +0.14',
                    'IPI near foraging/social boundary. Ambiguous — split prior.',
                    f'{ipi:.1f} ms'))
            elif ipi <= 400:
                # FIX 3: Social coda range. Was incorrectly boosting FORAGE here.
                # Sperm whale codas: 60-300ms. Beluga social: 80-350ms.
                # This is the contact/social IPI band, not foraging.
                scores['CONTACT'] += 0.22
                trace.append(RuleTrace('IPI 55–400 ms (social coda range)', 'CONTACT +0.22',
                    'IPI matches odontocete social coda range (sperm whale 60-300ms, beluga 80-350ms). '
                    'Well above foraging burst threshold. Social/contact signal.',
                    f'{ipi:.1f} ms'))
            elif ipi > 5000:
                scores['NAVIGATE'] += 0.22
                trace.append(RuleTrace('IPI > 5000 ms', 'NAVIGATE +0.22',
                    'Very slow pulse rate: long-period navigation signal.',
                    f'{ipi:.1f} ms'))
            elif ipi <= 2000:
                # IPI 400-2000ms: slow broadcast phrase rhythm or inter-call navigation
                scores['NAVIGATE'] += 0.10; scores['BROADCAST'] += 0.12
                trace.append(RuleTrace('IPI 400–2000 ms', 'BROADCAST +0.12 · NAVIGATE +0.10',
                    'Slow inter-call interval. Overlaps broadcast phrase rhythm and patrol navigation.',
                    f'{ipi:.1f} ms'))
            else:
                # IPI 2000-5000ms: strongly navigation
                scores['NAVIGATE'] += 0.28
                trace.append(RuleTrace('IPI 2000–5000 ms', 'NAVIGATE +0.28',
                    'Slow pulse rate above broadcast phrase interval. Migration/navigation pulse trains.',
                    f'{ipi:.1f} ms'))

        # ── Urgency Index ─────────────────────────────────────
        if urg > 0.65:
            scores['FORAGE'] += 0.16
            trace.append(RuleTrace('Urgency index > 0.65', 'FORAGE +0.16',
                'High urgency composite: active prey pursuit or foraging coordination.',
                f'{urg:.3f}'))
        elif urg < 0.15:
            scores['NAVIGATE'] += 0.10; scores['BROADCAST'] += 0.10
            trace.append(RuleTrace('Urgency index < 0.15', 'NAVIGATE +0.10 · BROADCAST +0.10',
                'Low urgency: sustained low-energy navigation or broadcast signal.',
                f'{urg:.3f}'))

        # ── Strong-signal overrides ───────────────────────────
        final_class, confidence = None, None

        # OVERRIDE 0: Ultrasonic + high urgency = deep odontocete foraging click.
        # Extended gate covers: (a) no IPI logged, and (b) IPI 200-400ms.
        # Cuvier's/Blainville's beaked whales: 38-56kHz, IPI 200-400ms, urg 0.55-0.85.
        # At pf > 30kHz, IPI 200-400ms is inter-click interval within a foraging bout,
        # NOT a social coda. Social codas are produced at 2-8kHz only.
        # Ref: Johnson et al. 2004; Madsen et al. 2005; Zimmer et al. 2005.
        if pf > 30000 and urg > 0.50 and (ipi is None or ipi <= 400):
            final_class, confidence = 'FORAGE', 0.91
            trace.append(RuleTrace(
                'OVERRIDE 0: Ultrasonic + high urgency + no IPI → FORAGE',
                '→ FORAGE (conf: 0.91)',
                'Ultrasonic frequency (> 30kHz) + high urgency + no inter-pulse interval logged: '
                'beaked whale or deep odontocete foraging click pattern. '
                'Cuvier\'s beaked whale: 38-55kHz, urgency 0.55-0.85 (Johnson et al. 2004). '
                'Blainville\'s: 38-52kHz, urgency 0.55-0.82 (Madsen et al. 2005). '
                'These clicks are produced exclusively during deep foraging dives.',
                f'{pf:.0f}Hz, urg={urg:.3f}'))

        elif fc == 'descending' and dur < 2.0:
            final_class, confidence = 'DIVE', 0.87
            trace.append(RuleTrace(
                'OVERRIDE: Descending contour + short duration',
                '→ DIVE (conf: 0.87)',
                'Near-diagnostic. Short descending sweeps precede dive events in all available baleen records.',
                f'{fc}, {dur:.2f}s'))

        elif fc == 'rising' and pf < 500:
            final_class, confidence = 'CONTACT', 0.82
            trace.append(RuleTrace(
                'OVERRIDE: Rising contour + low frequency',
                '→ CONTACT (conf: 0.82)',
                'Low-frequency rising sweep matches upcall pattern across NARW, humpback, bowhead.',
                f'{fc}, {pf:.1f}Hz'))

        elif pf < 30 and dur > 10:
            final_class, confidence = 'NAVIGATE', 0.79
            trace.append(RuleTrace(
                'OVERRIDE: Infrasonic + long duration',
                '→ NAVIGATE (conf: 0.79)',
                'Blue/fin whale SOFAR navigation signature.',
                f'{pf:.1f}Hz, {dur:.2f}s'))

        elif pf > 1500 and ipi is not None and ipi < 50:
            final_class, confidence = 'FORAGE', 0.88
            trace.append(RuleTrace(
                'OVERRIDE: High frequency + rapid IPI < 50ms',
                '→ FORAGE (conf: 0.88)',
                'Odontocete foraging burst pulse. IPI below social coda threshold — unambiguous foraging.',
                f'{pf:.1f}Hz, {ipi:.1f}ms IPI'))

        elif pf > 1500 and ipi is not None and ipi >= 55 and ipi <= 400:
            final_class, confidence = 'CONTACT', 0.84
            trace.append(RuleTrace(
                'OVERRIDE: High frequency + social IPI 55–400ms',
                '→ CONTACT (conf: 0.84)',
                'High-frequency social signal. IPI in coda/social range (sperm whale coda: 60-300ms, '
                'beluga social: 80-350ms). Physical constraint: cannot be foraging at this IPI rate.',
                f'{pf:.1f}Hz, {ipi:.1f}ms IPI'))


        # OVERRIDE B: Long complex broadcast song fires before IPI navigate gate.
        # Omura's whale (complex, dur 8-22s, urg 0.05-0.14, pf 25-55Hz, IPI 5-15s)
        # and Antarctic blue whale song (complex, dur 10-28s, urg 0.04-0.11, IPI 8-20s)
        # were captured by the IPI > 2000ms navigate override. Separator: nav pulses are
        # short (< 6s) and/or flat. Broadcast songs are long + complex.
        # Ref: Cerchio et al. 2015 R.Soc.Open.Sci; Lewis et al. 2018 JASA.
        elif fc == 'complex' and dur > 6.0 and urg < 0.20:
            final_class, confidence = 'BROADCAST', 0.83
            trace.append(RuleTrace(
                'OVERRIDE B: Complex + long duration + low urgency',
                '-> BROADCAST (conf: 0.83)',
                'Complex hierarchical structure + extended duration (> 6s) + low urgency = broadcast song. '
                'Navigation pulses are short flat-contour signals. '
                'Ref: Cerchio et al. 2015; Lewis et al. 2018.',
                f'fc={fc}, dur={dur:.1f}s, urg={urg:.3f}'))

        elif ipi is not None and ipi > 2000 and urg < 0.22 and pf < 200:
            # FIX 3: Omura's whale and Antarctic blue whale low-freq broadcast songs sit at
            # 25-55Hz with IPI 5000-20000ms — inside the original pf < 200 gate.
            # Separator: navigation pulses are SHORT (< 5s) and FLAT contour.
            # Broadcast songs are LONG (> 8s) and COMPLEX/FLAT with slow rep rate.
            # Duration + contour together break the tie.
            if dur > 6.0 and fc in ('complex',):
                # Long complex low-freq call with slow IPI = broadcast song (Omura's, Antarctic blue)
                final_class, confidence = 'BROADCAST', 0.80
                trace.append(RuleTrace(
                    'OVERRIDE: Low-freq long-IPI + complex contour + extended duration → BROADCAST',
                    '→ BROADCAST (conf: 0.80)',
                    'Low-frequency (< 200Hz) + IPI > 2000ms + duration > 6s + complex contour: '
                    'broadcast song signature. Omura\'s whale song (25-55Hz, IPI 5-15s, dur 8-22s) '
                    'and Antarctic blue whale song (25-50Hz, IPI 8-20s, dur 10-28s) match this profile. '
                    'Navigation pulses are short-duration flat-contour signals. '
                    'Ref: Cerchio et al. 2015; Lewis et al. 2018.',
                    f'pf={pf:.1f}Hz, IPI={ipi:.0f}ms, dur={dur:.2f}s, fc={fc}'))
            else:
                final_class, confidence = 'NAVIGATE', 0.85
                trace.append(RuleTrace(
                    'OVERRIDE: Long IPI > 2000ms + low urgency + low frequency → NAVIGATE',
                    '→ NAVIGATE (conf: 0.85)',
                    'IPI > 2000ms + pf < 200Hz + short/flat signal: navigation pulse train. '
                    'Gray whale migration moans (100-800Hz, IPI 4-12s), minke navigation (60-140Hz, IPI 6-18s). '
                    'Duration + contour gate excludes low-freq broadcast songs (> 6s, complex). '
                    'Ref: Dahlheim 1987; Gedamke et al. 2001.',
                    f'IPI={ipi:.0f}ms, urg={urg:.3f}, pf={pf:.1f}Hz, dur={dur:.2f}s, fc={fc}'))

        # FIX C: High-freq short-dur whistle contact — fires before broadcast rep band.
        # Delphinid and odontocete contact whistles (1200Hz+, dur < 3.5s, complex/rising,
        # urg 0.12-0.25, rep 0.10-0.35Hz) were tripping the broadcast rep band override.
        # Separator: broadcast = long duration (> 4s) or very low urgency (< 0.12).
        # Contact whistles are short, moderate urgency, and produced by social animals.
        # Ref: Lammers & Au 2003; Matthews et al. 1999; Van Parijs & Corkeron 2001.
        elif pf > 1200 and dur < 3.5 and urg >= 0.12 and fc in ('complex', 'rising') and rep < 0.40 and (ipi is None or ipi > 400):
            final_class, confidence = 'CONTACT', 0.82
            trace.append(RuleTrace(
                'FIX C: High-freq short whistle + moderate urgency -> CONTACT',
                '-> CONTACT (conf: 0.82)',
                'High-frequency (> 1200Hz) + short duration (< 3.5s) + moderate urgency + '
                'complex/rising contour = delphinid or odontocete contact whistle. '
                'Not broadcast: too short, urgency too high, IPI not in slow broadcast range. '
                'Ref: Lammers & Au 2003; Matthews et al. 1999; Van Parijs & Corkeron 2001.',
                f'pf={pf:.0f}Hz, dur={dur:.2f}s, urg={urg:.3f}, fc={fc}'))

        elif rep > 0.03 and rep < 0.28 and urg < 0.20 and dur > 0.5 and fc in ('flat', 'complex'):
            # FIX 4: Antarctic blue Z-calls (flat, rep 0.02-0.05Hz, IPI 18-32s) and
            # river/porpoise navigate pulses were tripping this broadcast override.
            # True broadcast songs do NOT have very long IPI (song inter-phrase < 5s).
            # Navigation pulses with rep 0.03-0.08Hz have IPI > 8000ms by definition.
            # Gate: if IPI > 8000ms, this is navigation, not broadcast.
            if ipi is not None and ipi > 8000:
                final_class, confidence = 'NAVIGATE', 0.83
                trace.append(RuleTrace(
                    'OVERRIDE: Broadcast rep band BUT IPI > 8000ms → NAVIGATE',
                    '→ NAVIGATE (conf: 0.83)',
                    'Repetition rate 0.03-0.28Hz with IPI > 8000ms resolves to navigation. '
                    'Broadcast inter-phrase intervals are < 5000ms. '
                    'Antarctic blue Z-call (rep 0.02-0.05Hz, IPI 18-32s), '
                    'harbour porpoise nav scan (IPI 9-22s), Dall\'s porpoise (IPI 8-25s). '
                    'Ref: Sirovic et al. 2009; Verfuss et al. 2009; Kyhn et al. 2010.',
                    f'rep={rep:.3f}Hz, IPI={ipi:.0f}ms'))
            else:
                final_class, confidence = 'BROADCAST', 0.81
                trace.append(RuleTrace(
                    'OVERRIDE: Broadcast repetition signature',
                    '→ BROADCAST (conf: 0.81)',
                    'Repetition rate 0.03-0.28Hz + low urgency + sustained duration + IPI < 8000ms: '
                    'broadcast/song behavior. Covers minke boing (0.1-0.3Hz), bowhead song (0.05-0.15Hz), '
                    'sperm whale slow click series (0.03-0.10Hz). '
                    'IPI gate (< 8000ms) excludes navigation pulses. '
                    'Ref: Cummings & Holliday 1987; Stafford et al. 2018.',
                    f'rep={rep:.3f}Hz, urg={urg:.3f}, dur={dur:.2f}s, IPI={ipi:.0f}ms' if ipi else
                    f'rep={rep:.3f}Hz, urg={urg:.3f}, dur={dur:.2f}s'))

        elif fc == 'complex' and dur > 4:
            final_class, confidence = 'BROADCAST', 0.76
            trace.append(RuleTrace(
                'OVERRIDE: Complex contour + extended duration',
                '→ BROADCAST (conf: 0.76)',
                'Humpback song / broadcast behavior signature.',
                f'{fc}, {dur:.2f}s'))

        # Weighted score fallback
        if final_class is None:
            total = sum(scores.values()) + 1e-8
            probs = {k: v / total for k, v in scores.items()}
            final_class  = max(probs, key=probs.get)
            confidence   = round(probs[final_class], 4)

        # Always compute full probability distribution
        total = sum(scores.values()) + 1e-8
        probabilities = {k: round(v / total, 4) for k, v in scores.items()}

        return PredictionResult(
            predicted_class = final_class,
            confidence      = confidence,
            probabilities   = probabilities,
            rule_trace      = [asdict(t) for t in trace],
        )
