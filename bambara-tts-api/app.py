from flask import Flask, request, jsonify, send_file, render_template, after_this_request
from flask_cors import CORS
from TTS.api import TTS
import os
import uuid
from tempfile import gettempdir

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Initialize using local model paths
tts = TTS(
    model_path="bam/G_100000.pth",
    config_path="bam/config.json"
).to("cpu")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate-audio', methods=['POST'])
def generate_audio():
    try:
        # Get JSON data from request
        data = request.get_json()
        text = data.get('title', '')

        # Validate and sanitize input text
        if not text.strip():
            return jsonify({"error": "No text provided or text is empty"}), 400
        sanitized_text = text.replace('.', '').strip()

        # Generate a unique file name using UUID in the system's temp directory
        temp_dir = gettempdir()  # Use temporary directory for portability
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)  # Ensure the temp directory exists
        unique_id = uuid.uuid4()
        output_audio_file_path = os.path.join(temp_dir, f"output_{unique_id}.wav")

        # Generate the audio file
        tts.tts_to_file(sanitized_text, file_path=output_audio_file_path)

        # Schedule file deletion after the response is sent
        @after_this_request
        def remove_file(response):
            try:
                if os.path.exists(output_audio_file_path):
                    os.remove(output_audio_file_path)
            except Exception as e:
                print(f"Error cleaning up file: {e}")
            return response

        # Serve the file as a response
        return send_file(output_audio_file_path, as_attachment=True, download_name="output.wav")
    except Exception as e:
        # Log the error and return a JSON response
        print(f"Error during file generation or serving: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Use host 0.0.0.0 for accessibility in containerized environments
    app.run(host="0.0.0.0", port=8080)
