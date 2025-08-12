from fastapi import FastAPI, Body, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import hashlib, io, zipfile, os

from maliba_ai.tts.inference import BambaraTTSInference
from maliba_ai.config.settings import Speakers

app = FastAPI(title="Bambara TTS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

AUDIO_DIR = Path("data/audio"); AUDIO_DIR.mkdir(parents=True, exist_ok=True)
SPEAKERS = ["Adama","Moussa","Bourama","Modibo","Seydou","Amadou","Bakary","Ngolo","Ibrahima","Amara"]  # HF card
SPEAKER_DEFAULT = os.getenv("SPEAKER_DEFAULT", "Bourama")

# Load once (uses GPU automatically when available)
tts = BambaraTTSInference()

def _speaker_enum(name: str):
    return getattr(Speakers, name)

def _wav_path(text: str, speaker: str):
    key = hashlib.sha1(f"{speaker}|{text}".encode("utf-8")).hexdigest()
    return AUDIO_DIR / f"{key}.wav"

def synth_to_wav(text: str, speaker: str):
    out = _wav_path(text, speaker)
    if not out.exists():
        tts.generate_speech(text=text, speaker_id=_speaker_enum(speaker), output_filename=str(out))
    return out

@app.get("/ping")
def ping():
    return {"status":"ok"}

@app.get("/", response_class=HTMLResponse)
def ui():
    return f"""
<!doctype html><meta charset="utf-8" />
<h2>Bambara TTS (MALIBA)</h2>
<form onsubmit="event.preventDefault(); go()">
  <label>Speaker:</label>
  <select id="sp">{''.join(f'<option>{s}</option>' for s in SPEAKERS)}</select>
  <br/><textarea id="tx" rows="3" cols="60" placeholder="Aw ni ce. I ka kɛnɛ wa?"></textarea>
  <br/><button>Speak</button>
</form>
<audio id="au" controls></audio>
<script>
async function go(){{
  const r = await fetch('/synthesize', {{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{ text: document.getElementById('tx').value, speaker: document.getElementById('sp').value }})
  }});
  const blob = await r.blob();
  document.getElementById('au').src = URL.createObjectURL(blob);
}}
</script>
"""

class SynthesizeIn(BaseModel):
    text: str
    speaker: str | None = None
    return_path: bool = False

@app.post("/synthesize")
def synth(req: SynthesizeIn):
    speaker = req.speaker or SPEAKER_DEFAULT
    path = synth_to_wav(req.text.strip(), speaker)
    if req.return_path:
        return {"url": f"/audio/{path.name}", "speaker": speaker}
    return FileResponse(path, media_type="audio/wav", filename=path.name)

class BatchIn(BaseModel):
    items: dict[str, str]   # {"key":"bambara text", ...}
    speaker: str | None = None

@app.post("/batch.zip")
def batch(req: BatchIn):
    speaker = req.speaker or SPEAKER_DEFAULT
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        for k, bm in req.items.items():
            p = synth_to_wav(bm.strip(), speaker)
            z.write(p, arcname=f"{k}.wav")
    mem.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="bambara_tts.zip"'}
    return Response(mem.read(), media_type="application/zip", headers=headers)

@app.get("/audio/{fname}")
def serve_cached(fname: str):
    path = AUDIO_DIR / fname
    return FileResponse(path, media_type="audio/wav")
