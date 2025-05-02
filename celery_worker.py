from celery import Celery
from TTS.api import TTS
import os
import uuid
from tempfile import gettempdir

# Read broker and result backend from environment variables (or set default)
REDIS_URL = "redis://default:RZMtWYDySnhVgZSnSivZczIkeIpFCyDr@redis.railway.internal:6379"

celery_app = Celery("tts_tasks", broker=REDIS_URL, backend=REDIS_URL)

# Load model only once for the worker
tts_model = TTS(model_name="tts_models/bam/fairseq/vits").to("cpu")

@celery_app.task
def generate_audio_task(text):
    unique_id = uuid.uuid4()
    output_path = os.path.join(gettempdir(), f"output_{unique_id}.wav")
    tts_model.tts_to_file(text, file_path=output_path)
    return output_path
