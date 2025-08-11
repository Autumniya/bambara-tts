# app.py
import os, hashlib
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from celery import Celery

app = Flask(__name__)
CORS(app)

# ---- Celery (shared broker/backend) ----
app.config['CELERY_BROKER_URL'] = os.environ['CELERY_BROKER_URL']
app.config['CELERY_RESULT_BACKEND'] = os.environ['CELERY_RESULT_BACKEND']
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'],
                backend=app.config['CELERY_RESULT_BACKEND'])
celery.conf.update(app.config)

# ---- Storage ----
PERSIST_DIR = os.environ.get("AUDIO_DIR", "/data/audio")
Path(PERSIST_DIR).mkdir(parents=True, exist_ok=True)

def extract_text(data):
    if isinstance(data, dict):
        for k in ["title","vocabaudio","meaning","name"]:
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for v in data.values():
            t = extract_text(v)
            if t: return t
    elif isinstance(data, list):
        for it in data:
            t = extract_text(it); 
            if t: return t
    return None

@app.route('/generate-audio', methods=['POST'])
def generate_audio_async():
    payload = request.get_json(silent=True) or {}
    text = extract_text(payload)
    speaker = payload.get("speaker")  # optional
    if not text:
        return jsonify({"error": "No valid text found"}), 400
    # Call the worker task by **name** (avoids importing the GPU module here)
    task = celery.send_task('tasks_gpu.generate_tts_task', args=[text, speaker])
    return jsonify({"task_id": task.id}), 202

@app.route('/check-status/<task_id>', methods=['GET'])
def check_status(task_id):
    from celery.result import AsyncResult
    r = AsyncResult(task_id, app=celery)
    if r.state == 'PENDING':
        return jsonify({"status":"pending"}), 202
    if r.state == 'SUCCESS':
        return jsonify({"status":"ready", "url": f"/get-audio/{r.result}"}), 200
    if r.state == 'FAILURE':
        return jsonify({"status":"failed","error": str(r.info)}), 500
    return jsonify({"status": r.state}), 200

@app.route('/get-audio/<path:filename>', methods=['GET'])
def get_audio(filename):
    file_path = os.path.join(PERSIST_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"error":"File not found"}), 404
    resp = send_file(file_path, mimetype="audio/wav",
                     as_attachment=True, download_name=filename, conditional=True)
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
