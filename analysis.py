"""Song analysis on separated stems: key, tempo/beats and synced lyrics."""

from pathlib import Path

import numpy as np
import soundfile as sf

SR = 22050  # analysis rate for key/beats
NOTES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
# Krumhansl-Kessler key profiles.
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
LYRICS_MODEL = "mlx-community/whisper-large-v3-turbo-q4"  # ~460 MB, fits 8 GB Macs


def _mono(path: Path, sr: int) -> np.ndarray:
    import librosa

    y, rate = sf.read(path, dtype="float32", always_2d=True)
    return librosa.resample(y.mean(axis=1), orig_sr=rate, target_sr=sr)


def _sum(paths: list[Path], sr: int) -> np.ndarray:
    out = None
    for p in paths:
        y = _mono(p, sr)
        out = y if out is None else out[: len(y)] + y[: len(out)]
    return out


def key_and_beats(stems: dict[str, Path]) -> dict:
    """Key from the harmonic stems (no drums/vocals), tempo and beat times from the full mix."""
    import librosa

    harmonic = [p for s, p in stems.items() if s not in ("drums", "vocals")] or list(stems.values())
    chroma = librosa.feature.chroma_cqt(y=_sum(harmonic, SR), sr=SR, hop_length=4096).mean(axis=1)
    scores = [(np.corrcoef(np.roll(prof, k), chroma)[0, 1], k, mode)
              for mode, prof in (("major", MAJOR), ("minor", MINOR)) for k in range(12)]
    _, tonic, mode = max(scores)

    tempo, beats = librosa.beat.beat_track(y=_sum(list(stems.values()), SR), sr=SR, units="time")
    return {
        "key": {"tonic": tonic, "mode": mode},  # tonic = pitch class 0..11 (C = 0)
        "bpm": round(float(np.atleast_1d(tempo)[0]), 1),
        "beats": [round(float(b), 3) for b in beats],
    }


def lyrics(vocals: Path) -> dict:
    import mlx.core as mx
    import mlx_whisper
    from mlx_whisper.transcribe import ModelHolder

    try:
        result = mlx_whisper.transcribe(
            _mono(vocals, 16000), path_or_hf_repo=LYRICS_MODEL, verbose=False,
            condition_on_previous_text=False,  # avoids repetition loops on sung audio
            word_timestamps=True, hallucination_silence_threshold=2.0,
        )
    finally:
        ModelHolder.model = None  # free the model between songs (8 GB Macs)
        mx.clear_cache()
    segments = [{"start": round(float(s["start"]), 2), "end": round(float(s["end"]), 2), "text": s["text"].strip()}
                for s in result["segments"] if s["text"].strip()]
    return {"language": result.get("language"), "segments": segments}
