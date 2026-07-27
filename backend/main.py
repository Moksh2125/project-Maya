import asyncio
import struct
import threading
import psutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core import stt, llm, tts, wakeword

app = FastAPI(title="Maya AI Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket tracking set
active_websockets = set()

# ── Echo Cancellation State ───────────────────────────────────────────────────
# maya_is_speaking: tells wakeword thread to mute the mic.
# pipeline_running: prevents a second pipeline from starting while one is active.
maya_is_speaking = False
pipeline_running = False

session_history = [
    {
        "role": "system",
        "content": "You are Maya, an offline AI desktop assistant. Keep answers concise, natural, and conversational.",
    }
]


def get_wav_duration(wav_bytes: bytes) -> float:
    """
    Parse the RIFF/WAV header to extract the exact audio duration in seconds.
    This lets us mute the mic for precisely as long as the audio plays, rather
    than using a blind fixed sleep.

    WAV header layout (all little-endian):
      offset 22 → num_channels (uint16)
      offset 24 → sample_rate  (uint32)
      offset 34 → bits_per_sample (uint16)
      offset 40 → data chunk size in bytes (uint32)
    """
    try:
        num_channels   = struct.unpack_from('<H', wav_bytes, 22)[0]
        sample_rate    = struct.unpack_from('<I', wav_bytes, 24)[0]
        bits_per_sample = struct.unpack_from('<H', wav_bytes, 34)[0]
        data_size      = struct.unpack_from('<I', wav_bytes, 40)[0]
        bytes_per_frame = num_channels * (bits_per_sample // 8)
        num_frames     = data_size // bytes_per_frame
        return num_frames / sample_rate
    except Exception:
        return 5.0  # safe fallback if header is malformed


def check_is_speaking() -> bool:
    """Callback for the wakeword thread — returns True when mic should be muted."""
    return maya_is_speaking


async def broadcast_ws(message: dict):
    """Push a JSON message to all connected UI clients."""
    for ws in list(active_websockets):
        try:
            await ws.send_json(message)
        except Exception:
            pass


async def process_voice_command(audio_bytes: bytes):
    """End-to-End Pipeline: STT → LLM → TTS → Audio Broadcast."""
    global maya_is_speaking, pipeline_running

    # ── Concurrency Guard (Bug 3 fix) ────────────────────────────────────────
    # Drop any new trigger that arrives while a pipeline is already running.
    # This prevents overlapping calls caused by the mic briefly capturing
    # audio right before the mute flag is set.
    if pipeline_running:
        print("[Pipeline] Already running — dropping duplicate trigger.")
        return
    pipeline_running = True

    try:
        await broadcast_ws({"type": "state", "status": "processing"})

        # ── Step 1: Speech-to-Text ────────────────────────────────────────────
        print("[1/3] Transcribing audio with Faster-Whisper...")
        user_text = await stt.transcribe(audio_bytes)
        if not user_text:
            print("-> Empty speech result. Resetting state.")
            await broadcast_ws({"type": "state", "status": "standby"})
            return

        print(f"-> User said: '{user_text}'")
        await broadcast_ws({"type": "text", "sender": "user", "content": user_text})

        # ── Step 2: Local LLM ─────────────────────────────────────────────────
        print("[2/3] Generating response with Gemma 3...")
        session_history.append({"role": "user", "content": user_text})
        maya_text = await llm.chat(session_history)
        session_history.append({"role": "assistant", "content": maya_text})

        print(f"-> Maya says: '{maya_text}'")
        await broadcast_ws({"type": "text", "sender": "maya", "content": maya_text})

        # ── Step 3: TTS Synthesis ─────────────────────────────────────────────
        print("[3/3] Synthesizing speech with Piper...")
        audio_response_bytes = await tts.synthesize(maya_text)

        # Calculate exact playback duration from WAV header BEFORE sending.
        audio_duration = get_wav_duration(audio_response_bytes)
        mute_duration = audio_duration + 0.5  # +0.5s buffer for room echo tail

        # ── Mute BEFORE sending (Bug 2 + timing fix) ─────────────────────────
        # Set the flag here so the wakeword thread starts draining the mic
        # buffer the instant audio hits the speakers — not 4 seconds later.
        maya_is_speaking = True
        print(f"[Pipeline] Muting mic for {audio_duration:.1f}s audio + 0.5s echo tail")

        # Broadcast audio bytes to frontend
        for ws in list(active_websockets):
            try:
                await ws.send_bytes(audio_response_bytes)
            except Exception as e:
                print(f"[Pipeline] WebSocket audio error: {e}")

        # Sleep for the exact duration of the audio clip + echo tail
        await asyncio.sleep(mute_duration)

    except Exception as e:
        print(f"!!! CRITICAL PIPELINE ERROR [{type(e).__name__}]: {e}")

    finally:
        # Always clear both flags so the system returns to standby
        maya_is_speaking = False
        pipeline_running = False
        await broadcast_ws({"type": "state", "status": "standby"})


@app.on_event("startup")
async def startup_event():
    """Spawns the background wake word listener on app boot."""
    loop = asyncio.get_running_loop()
    threading.Thread(
        target=wakeword.wake_word_listener,
        args=(loop, process_voice_command, check_is_speaking),
        daemon=True,
    ).start()


@app.get("/status")
async def get_system_status():
    """System hardware telemetry endpoint for UI gauges."""
    return {
        "cpu_percent": psutil.cpu_percent(),
        "ram_percent": psutil.virtual_memory().percent,
        "ai_engine": "Ollama (Gemma 3 270M)",
        "status": "online",
    }


@app.websocket("/ws/audio")
async def audio_endpoint(websocket: WebSocket):
    """Main control channel connecting Python backend to React UI."""
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets.discard(websocket)