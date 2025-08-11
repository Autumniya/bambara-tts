# tasks_gpu.py
import os, hashlib
from pathlib import Path
from app import celery  # get the Celery instance without importing Flask routes

# Lazy singletons (loaded only in the worker process)
_TTS = None
_Speakers = None

AUDIO_DIR = os.environ.get("AUDIO_DIR", "/data/audio")
Path(AUDIO_DIR).mkdir(parents=True, exist_ok=True)

def _stable_filename(text: str, speaker: str | None) -> str:
    h = hashlib.sha1(f"{speaker or ''}|{text}".encode("utf-8")).hexdigest()
    return f"{h}.wav"

def _load_engine():
    global _TTS, _Speakers
    if _TTS is None:
        # Import here so web process never touches Unsloth/GPU
        from maliba_ai.tts.inference import BambaraTTSInference
        from maliba_ai.config.settings import Speakers
        _TTS = BambaraTTSInference()   # auto-detects GPU; Unsloth requires GPU
        _Speakers = Speakers
    return _TTS, _Speakers

@celery.task(name="tasks_gpu.generate_tts_task")
def generate_tts_task(text: str, speaker_name: str | None = None) -> str:
    tts, Speakers = _load_engine()
    default_name = os.getenv("MALIBA_TTS_SPEAKER", "Bourama")
    sp = getattr(Speakers, (speaker_name or default_name), Speakers.Bourama)
    out_name = _stable_filename(text, getattr(sp, "name", str(sp)))
    out_path = os.path.join(AUDIO_DIR, out_name)
    if not os.path.exists(out_path):
        tts.generate_speech(text=text, speaker_id=sp, output_path=out_path)  # 16k WAV
    return out_name
