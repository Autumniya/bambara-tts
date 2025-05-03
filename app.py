from flask import Flask, request, jsonify, send_file, render_template, after_this_request
from flask_cors import CORS
import os
import uuid
from tempfile import gettempdir
from celery import Celery
from TTS.api import TTS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Read broker and result backend from environment variables (or set default)

app.config['CELERY_BROKER_URL'] = 'redis://default:RZMtWYDySnhVgZSnSivZczIkeIpFCyDr@redis.railway.internal:6379'
app.config['CELERY_RESULT_BACKEND'] = 'redis://default:RZMtWYDySnhVgZSnSivZczIkeIpFCyDr@redis.railway.internal:6379'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'], backend=app.config['CELERY_RESULT_BACKEND'])
celery.conf.update(app.config)

# Only load model once
tts_model = TTS(model_name="tts_models/bam/fairseq/vits").to("cpu")

@celery.task
def generate_tts(text):
    filename = os.path.join(gettempdir(), f"{uuid.uuid4()}.wav")
    print(f"🔊 [SAVING TO] {filename}")
    try:
        tts_model.tts_to_file(text, file_path=filename)
        print(f"✅ [TASK DONE] File saved: {filename}")
        return filename
    except Exception as e:
        print(f"❌ [TASK FAILED] Error: {e}")
        raise e

@app.route('/')
def home():
    return render_template('index.html')

def extract_text(data):
    """
    Recursively searches the JSON structure for the first text field that can be used for TTS.
    """
    if isinstance(data, dict):
        # Check for known keys
        for key in ["title", "vocabaudio", "meaning", "name"]:
            if key in data and isinstance(data[key], str) and data[key].strip():
                return data[key].strip()
        # Recurse into nested dictionaries
        for value in data.values():
            result = extract_text(value)
            if result:
                return result
    elif isinstance(data, list):
        # Recurse into lists
        for item in data:
            result = extract_text(item)
            if result:
                return result
    return None


@app.route('/generate-audio', methods=['POST'])
def generate_audio_async():
    data = request.get_json()
    text = extract_text(data)
    if not text:
        return jsonify({"error": "No valid text found"}), 400

    task = generate_tts.delay(text)
    return jsonify({"task_id": task.id}), 202


@app.route('/check-status/<task_id>', methods=['GET'])
def check_status(task_id):
    from celery.result import AsyncResult
    result = AsyncResult(task_id)

    if result.state == 'PENDING':
        return jsonify({"status": "pending"}), 202
    elif result.state == 'SUCCESS':
        file_path = result.result
        filename = os.path.basename(file_path)
        return jsonify({"status": "ready", "url": f"/get-audio/{filename}"}), 200
    elif result.state == 'FAILURE':
        return jsonify({"status": "failed", "error": str(result.info)}), 500

    return jsonify({"status": result.state}), 200

@app.route('/get-audio/<filename>', methods=['GET'])
def get_audio(filename):
    file_path = os.path.join(gettempdir(), filename)

    @after_this_request
    def remove_file(response):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            app.logger.error(f"Error deleting temp file: {e}")
        return response

    if os.path.exists(file_path):
        return send_file(file_path, mimetype="audio/wav")
    else:
        return jsonify({"error": "File not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
