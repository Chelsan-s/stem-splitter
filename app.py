"""Stem Splitter: local stem separation + multitrack library."""

import gc
import json
import queue
import shutil
import threading
import time
import traceback
import uuid
from pathlib import Path

import soundfile as sf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path.home() / "Music" / "StemSplitter"
SONGS = ROOT / "songs"
MODELS = ROOT / "models"
WORK = ROOT / ".work"
for d in (SONGS, MODELS, WORK):
    d.mkdir(parents=True, exist_ok=True)

MODES = {
    # Demucs runs on the M1 GPU and fits in 8 GB. Heavier/better alternatives:
    # "model_bs_roformer_ep_317_sdr_12.9755.ckpt" (2) and "htdemucs_ft.yaml" (4).
    # Mode 2 = htdemucs vocals + (drums + bass + other) summed as instrumental.
    "2": ("htdemucs.yaml", ["vocals", "instrumental"]),
    "4": ("htdemucs.yaml", ["vocals", "drums", "bass", "other"]),
    "6": ("htdemucs_6s.yaml", ["vocals", "drums", "bass", "guitar", "piano", "other"]),
}

jobs: "queue.Queue[str]" = queue.Queue()
meta_lock = threading.Lock()


def meta_path(song_id: str) -> Path:
    return SONGS / song_id / "meta.json"


def read_meta(song_id: str) -> dict:
    return json.loads(meta_path(song_id).read_text())


def write_meta(meta: dict) -> None:
    with meta_lock:
        p = meta_path(meta["id"])
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        tmp.replace(p)


# Live progress of the song being processed (not persisted).
progress = {"id": None, "stage": "", "pct": 0.0, "t0": 0.0}


def set_stage(stage: str, pct: float = 0.0) -> None:
    if progress["stage"] != stage:
        progress["t0"] = time.time()
    progress.update(stage=stage, pct=pct)


def hook_progress_bars() -> None:
    """Route audio-separator's tqdm bars (model download, separation) into `progress`."""
    import tqdm

    class Bar(tqdm.tqdm):
        def __init__(self, *args, **kwargs):
            self._download = kwargs.get("unit") == "iB"
            kwargs["disable"] = True
            super().__init__(*args, **kwargs)

        def _report(self, n: float) -> None:
            if self.total:
                set_stage("download" if self._download else "separating", min(1.0, n / self.total))

        def __iter__(self):
            for i, x in enumerate(self.iterable):
                self._report(i)
                yield x
            self._report(self.total or 0)

        def update(self, n: float = 1) -> None:
            self.n += n
            self._report(self.n)

    tqdm.tqdm = Bar  # modules using `from tqdm import tqdm` must be imported after this


def worker() -> None:
    hook_progress_bars()
    from audio_separator.separator import Separator

    loaded: tuple[str, Separator] | None = None  # keep one model in memory at a time
    while True:
        song_id = jobs.get()
        try:
            meta = read_meta(song_id)
        except FileNotFoundError:
            continue  # deleted while queued
        model, stems = MODES[meta["mode"]]
        meta.update(status="processing", started=time.time())
        progress["id"] = song_id
        set_stage("loading")
        write_meta(meta)
        try:
            if loaded is None or loaded[0] != model:
                loaded = None
                gc.collect()
                sep = Separator(
                    model_file_dir=str(MODELS), output_dir=str(WORK), output_format="FLAC",
                    demucs_params={"segment_size": "Default", "shifts": 1, "overlap": 0.25, "segments_enabled": True},
                )
                sep.load_model(model)
                loaded = (model, sep)
            sep = loaded[1]
            for f in WORK.iterdir():
                f.unlink()
            produced = MODES["4"][1] if meta["mode"] == "2" else stems
            set_stage("reading")
            sep.separate(str(SONGS / song_id / meta["source"]), custom_output_names={s: s for s in produced})
            set_stage("saving")
            if meta["mode"] == "2":
                parts = [sf.read(WORK / f"{s}.flac") for s in ("drums", "bass", "other")]
                sf.write(WORK / "instrumental.flac", sum(a for a, _ in parts), parts[0][1])
            out = SONGS / song_id / "stems"
            out.mkdir(exist_ok=True)
            found = []
            for s in stems:
                src = WORK / f"{s}.flac"
                if not src.exists():
                    raise RuntimeError(f"stem ausente: {s}")
                shutil.move(src, out / f"{s}.flac")
                found.append(s)
            if not (SONGS / song_id).exists():
                shutil.rmtree(out, ignore_errors=True)
                continue
            meta.update(status="done", stems=found, finished=time.time())
        except Exception as e:  # noqa: BLE001 - report any failure to the UI
            traceback.print_exc()
            meta.update(status="error", error=str(e))
        progress["id"] = None
        if (SONGS / song_id).exists():
            write_meta(meta)


app = FastAPI()


@app.on_event("startup")
def startup() -> None:
    threading.Thread(target=worker, daemon=True).start()
    for m in sorted(SONGS.glob("*/meta.json"), key=lambda p: p.stat().st_mtime):
        meta = json.loads(m.read_text())
        if meta["status"] in ("queued", "processing"):
            meta["status"] = "queued"
            write_meta(meta)
            jobs.put(meta["id"])


@app.get("/api/songs")
def list_songs() -> list[dict]:
    items = [json.loads(m.read_text()) for m in SONGS.glob("*/meta.json")]
    waiting = list(jobs.queue)
    for m in items:
        if m["status"] == "queued" and m["id"] in waiting:
            m["queue_pos"] = waiting.index(m["id"]) + 1
        if m["status"] == "processing" and progress["id"] == m["id"]:
            pct, elapsed = progress["pct"], time.time() - progress["t0"]
            m["progress"] = {
                "stage": progress["stage"],
                "pct": pct,
                "eta": elapsed / pct * (1 - pct) if progress["stage"] == "separating" and pct > 0.03 else None,
            }
    return sorted(items, key=lambda m: m["created"], reverse=True)


@app.post("/api/songs")
async def upload(file: UploadFile = File(...), mode: str = Form("4")) -> dict:
    if mode not in MODES:
        raise HTTPException(400, "modo inválido")
    song_id = uuid.uuid4().hex[:12]
    d = SONGS / song_id
    d.mkdir()
    ext = Path(file.filename or "audio").suffix.lower() or ".audio"
    source = f"source{ext}"
    with open(d / source, "wb") as f:
        shutil.copyfileobj(file.file, f)
    meta = {
        "id": song_id,
        "title": Path(file.filename or "Sem título").stem,
        "mode": mode,
        "source": source,
        "status": "queued",
        "stems": [],
        "created": time.time(),
    }
    write_meta(meta)
    jobs.put(song_id)
    return meta


@app.delete("/api/songs/{song_id}")
def delete(song_id: str) -> dict:
    d = SONGS / song_id
    if not d.is_dir() or d.parent != SONGS:
        raise HTTPException(404)
    shutil.rmtree(d)
    return {"ok": True}


@app.get("/files/{song_id}/{stem}.flac")
def stem_file(song_id: str, stem: str) -> FileResponse:
    p = SONGS / song_id / "stems" / f"{stem}.flac"
    if p.parent.parent.parent != SONGS or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p, media_type="audio/flac")


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
