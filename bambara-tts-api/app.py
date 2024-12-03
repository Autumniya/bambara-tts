import os
import requests
import uuid
from tempfile import gettempdir
from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
from scipy.io.wavfile import write
from fairseq.models.text_to_speech import VitsModel

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Define model paths and URL
model_dir = "bam"
model_path = os.path.join(model_dir, "G_100000.pth")
config_path = os.path.join(model_dir, "config.json")
model_url = "https://firebasestorage.googleapis.com/v0/b/donniya.appspot.com/o/G_100000.pth?alt=media&token=fa232852-a45a-4b96-8083-e9333e039e7b"  # Replace with your URL

# Ensure model directory exists
os.makedirs(model_dir, exist_ok=True)

# Download the model if it doesn't exist locally
if not os.path.exists(model_path):
    print("Downloading model weights...")
    response = requests.get(model_url, stream=True)
    response.raise_for_status()
    with open(model_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Model downloaded and saved to {model_path}")

# Load VITS model
vits_model = VitsModel.from_pretrained(
    model_dir,
    checkpoint_file=model_path,
    cfg_path=config_path,
    data_name_or_path=model_dir
)
vits_model.to("cpu")  # Change to "cuda" if GPU is available
vits_model.eval()

@app.route('/')
def home():
    return "Welcome to the VITS TTS API!"

@app.route('/generate-audio', methods=['POST'])
def generate_audio():
    try:
        # Parse request data
        data = request.get_json()
        text = data.get('title', '')

        # Validate input
        if not text.strip():
            return jsonify({"error": "No text provided"}), 400

        # Preprocess text for the VITS model
        preprocessed_text = vits_model.preprocess_text(text)
        tokens = vits_model.encode_text(preprocessed_text)

        # Generate audio
        with torch.no_grad():
            audio = vits_model.generate(tokens)

        # Save audio to a temporary file
        temp_dir = gettempdir()
        unique_id = uuid.uuid4()
        output_audio_file = os.path.join(temp_dir, f"output_{unique_id}.wav")
        write(output_audio_file, vits_model.sampling_rate, audio.numpy())

        # Schedule file deletion after response
        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(output_audio_file):
                    os.remove(output_audio_file)
            except Exception as e:
                print(f"Failed to delete temporary file: {e}")
            return response

        # Return the audio file
        return send_file(output_audio_file, as_attachment=True, download_name="output.wav")

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
