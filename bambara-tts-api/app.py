import os
import requests
import uuid
import torch
from tempfile import gettempdir
from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
from scipy.io.wavfile import write
from fairseq.models.text_to_speech import SynthesizerTrn
from examples.mms.tts.utils import get_hparams_from_file, load_checkpoint, TextMapper

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Define model paths and URLs
model_dir = "bam"
model_path = os.path.join(model_dir, "G_100000.pth")
config_path = os.path.join(model_dir, "config.json")
vocab_path = os.path.join(model_dir, "vocab.txt")
model_url = "https://firebasestorage.googleapis.com/v0/b/donniya.appspot.com/o/G_100000.pth?alt=media&token=fa232852-a45a-4b96-8083-e9333e039e7b"  # Replace with actual URL

# Ensure model directory exists
os.makedirs(model_dir, exist_ok=True)

# Download model weights if not already present
if not os.path.exists(model_path):
    print("Downloading model weights...")
    response = requests.get(model_url, stream=True)
    response.raise_for_status()
    with open(model_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Model downloaded and saved to {model_path}")

# Validate configuration and vocab files
assert os.path.isfile(config_path), f"{config_path} doesn't exist"
assert os.path.isfile(vocab_path), f"{vocab_path} doesn't exist"

# Load configuration
hps = get_hparams_from_file(config_path)

# Initialize TextMapper and SynthesizerTrn
text_mapper = TextMapper(vocab_path)
net_g = SynthesizerTrn(
    len(text_mapper.symbols),
    hps.data.filter_length // 2 + 1,
    hps.train.segment_size // hps.data.hop_length,
    **hps.model
)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
net_g.to(device)
_ = net_g.eval()

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

        # Preprocess and tokenize text
        preprocessed_text = text_mapper.preprocess_text(text, hps, lang="bam")  # Adjust "bam" to your language
        tokens = text_mapper.get_text(preprocessed_text, hps)

        # Generate audio
        with torch.no_grad():
            x_tst = tokens.unsqueeze(0).to(device)
            x_tst_lengths = torch.LongTensor([tokens.size(0)]).to(device)
            audio = net_g.infer(
                x_tst, x_tst_lengths, noise_scale=0.667,
                noise_scale_w=0.8, length_scale=1.0
            )[0][0, 0].cpu().float().numpy()

        # Save audio to a temporary file
        temp_dir = gettempdir()
        unique_id = uuid.uuid4()
        output_audio_file = os.path.join(temp_dir, f"output_{unique_id}.wav")
        write(output_audio_file, hps.data.sampling_rate, (audio * 32767).astype("int16"))

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
