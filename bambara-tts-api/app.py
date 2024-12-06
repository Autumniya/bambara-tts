from flask import Flask, request, jsonify, send_file, render_template, after_this_request
from flask_cors import CORS
from TTS.api import TTS
import os
import uuid
from tempfile import gettempdir

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Initialize TTS model
tts = TTS(model_name="tts_models/bam/fairseq/vits").to("cpu")

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
def generate_audio():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request, JSON body is required"}), 400

        # Extract text dynamically from the complex JSON
        text = extract_text(data)
        if not text:
            return jsonify({"error": "No valid text found in the provided JSON"}), 400

        # Generate unique filename in a temp directory
        unique_id = uuid.uuid4()
        output_audio_file_path = os.path.join(gettempdir(), f"output_{unique_id}.wav")

        # Generate audio file
        tts.tts_to_file(text, file_path=output_audio_file_path)

        @after_this_request
        def remove_file(response):
            try:
                if os.path.exists(output_audio_file_path):
                    os.remove(output_audio_file_path)
            except Exception as e:
                app.logger.error(f"Error deleting temp file: {e}")
            return response

        return send_file(output_audio_file_path, mimetype="audio/wav", as_attachment=True, download_name="output.wav")

    except Exception as e:
        app.logger.error(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
