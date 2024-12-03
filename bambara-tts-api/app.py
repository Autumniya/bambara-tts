import os
import torch
from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
from scipy.io.wavfile import write
from tempfile import gettempdir
import uuid
from fairseq.models.text_to_speech import VitsModel

app = Flask(__name__)
CORS(app)

# Load Fairseq VITS Model
model_dir = "bam"  # Replace with the directory containing your model files
vocab_file = os.path.join(model_dir, "vocab.txt")
config_file = os.path.join(model_dir, "config.json")
checkpoint_file = os.path.join(model_dir, "G_100000.pth")

assert os.path.isfile(config_file), f"{config_file} not found"
assert os.path.isfile(checkpoint_file), f"{checkpoint_file} not found"

print("Loading VITS model...")
vits_model = VitsModel.from_pretrained(
    model_dir,
    checkpoint_file=checkpoint_file,
    cfg_path=config_file,
    data_name_or_path=model_dir
)
vits_model.to("cpu")  # Change to "cuda" if you have GPU support
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

        # Preprocess text (if required by the model)
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

        # Return audio file
        return send_file(output_audio_file, as_attachment=True, download_name="output.wav")

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
