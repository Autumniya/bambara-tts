# app.py
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import os, uuid, hashlib
from pathlib import Path
from celery import Celery

# ✨ NEW: MALIBA-AI TTS
from maliba_ai.tts.inference import BambaraTTSInference
from maliba_ai.config.settings import Speakers  # enum of available speakers

app = Flask(__name__)
CORS(app)

# --- Celery ---
app.config['CELERY_BROKER_URL'] = os.environ.get('CELERY_BROKER_URL')
app.config['CELERY_RESULT_BACKEND'] = os.environ.get('CELERY_RESULT_BACKEND')
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'],
                backend=app.config['CELERY_RESULT_BACKEND'])
celery.conf.update(app.config)

# --- Storage ---
PERSIST_DIR = os.environ.get("AUDIO_DIR", "/tmp/tts")
Path(PERSIST_DIR).mkdir(parents=True, exist_ok=True)

def stable_filename(text: str, speaker: str) -> str:
    key = hashlib.sha1(f"{speaker}|{text}".encode("utf-8")).hexdigest()
    return f"{key}.wav"  # model outputs 16kHz WAV by default

# --- Load model ONCE (not inside the task) ---
DEFAULT_SPEAKER_NAME = os.getenv("MALIBA_TTS_SPEAKER", "Bourama")
DEFAULT_SPEAKER = getattr(Speakers, DEFAULT_SPEAKER_NAME, Speakers.Bourama)

TTS_ENGINE = BambaraTTSInference()  # basic usage per model card

def extract_text(data):
    if isinstance(data, dict):
        for key in ["title", "vocabaudio", "meaning", "name"]:
            v = data.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for v in data.values():
            t = extract_text(v)
            if t: return t
    elif isinstance(data, list):
        for it in data:
            t = extract_text(it)
            if t: return t
    return None

@celery.task
def generate_tts_task(text: str, speaker_name: str | None):
    sp = getattr(Speakers, speaker_name, DEFAULT_SPEAKER) if speaker_name else DEFAULT_SPEAKER
    fn = stable_filename(text, sp.name if hasattr(sp, "name") else str(sp))
    out_path = os.path.join(PERSIST_DIR, fn)
    if not os.path.exists(out_path):
        # MALIBA-AI basic call
        TTS_ENGINE.generate_speech(text=text, speaker_id=sp, output_path=out_path)  # 16kHz WAV
    return fn  # return filename only

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/speakers', methods=['GET'])
def speakers():
    # quick helper endpoint
    return jsonify([s.name for s in Speakers])

@app.route('/generate-audio', methods=['POST'])
def generate_audio_async():
    payload = request.get_json(silent=True) or {}
    text = extract_text(payload)
    speaker = payload.get("speaker")  # optional, e.g., "Bourama"
    if not text:
        return jsonify({"error": "No valid text found"}), 400
    task = generate_tts_task.delay(text, speaker)
    return jsonify({"task_id": task.id}), 202

@app.route('/check-status/<task_id>', methods=['GET'])
def check_status(task_id):
    from celery.result import AsyncResult
    r = AsyncResult(task_id)
    if r.state == 'PENDING':
        return jsonify({"status": "pending"}), 202
    if r.state == 'SUCCESS':
        filename = r.result
        return jsonify({"status": "ready", "url": f"/get-audio/{filename}"}), 200
    if r.state == 'FAILURE':
        return jsonify({"status": "failed", "error": str(r.info)}), 500
    return jsonify({"status": r.state}), 200

@app.route('/get-audio/<path:filename>', methods=['GET'])
def get_audio(filename):
    file_path = os.path.join(PERSIST_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    resp = send_file(
        file_path,
        mimetype="audio/wav",
        as_attachment=True,
        download_name=filename,
        conditional=True
    )
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
