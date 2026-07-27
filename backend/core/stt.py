import io
import asyncio
from typing import Optional
from faster_whisper import WhisperModel

MODEL_SIZE = "base.en"  # tiny | base | small | medium | large-v3
DEVICE = "cpu"       # cpu | cuda
COMPUTE_TYPE = "int8"

_model: Optional[WhisperModel] = None


def get_model() -> WhisperModel:
    """Lazy-load the Whisper model singleton."""
    global _model
    if _model is None:
        _model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    return _model


async def transcribe(audio_bytes: bytes, language: str = "en") -> str:
    """Transcribe raw PCM/WAV audio bytes using Faster-Whisper with Silero VAD filtering."""
    model = get_model()
    audio_buffer = io.BytesIO(audio_bytes)
    
    # Run CPU/GPU bound transcription in a background thread worker
    segments, _ = await asyncio.to_thread(
        model.transcribe,
        audio_buffer,
        language=language,
        beam_size=1,
        vad_filter=True  # Filters out room ambient noise & silence to prevent hallucinations
    )
    return " ".join([seg.text.strip() for seg in segments]).strip()