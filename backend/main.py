import asyncio
import json
import threading
import wave
import psutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# ── Real pipeline modules ──────────────────────────────────────────────────────
from router import route_task
from core.llm import generate_chat, warmup
from core.stt import transcribe
from core.tts import synthesize
from core.wakeword import wake_word_listener

# -------------------------------------------------------------
# GLOBAL STATE
# -------------------------------------------------------------
active_websocket: WebSocket | None = None
maya_is_speaking = False          # Shared flag — read by wake_word thread

# -------------------------------------------------------------
# LIFESPAN & BACKGROUND TASKS
# -------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the real OpenWakeWord listener in a daemon thread on startup."""
    print("Initializing OpenWakeWord Engine...")

    loop = asyncio.get_running_loop()

    # wake_word_listener is a BLOCKING function (PyAudio reads).
    # Run it in a background daemon thread so it never blocks the event loop.
    ww_thread = threading.Thread(
        target=wake_word_listener,
        args=(loop, on_command_recorded, lambda: maya_is_speaking),
        daemon=True,           # Dies automatically when the server shuts down
        name="WakeWordThread",
    )
    ww_thread.start()

    # Pre-warm the LLM so the first conversational query isn't cold-slow.
    # Runs concurrently — doesn't block the server from accepting requests.
    asyncio.create_task(warmup())

    yield
    print("Shutting down Maya Engine...")


# Initialize FastAPI with the lifespan manager
app = FastAPI(lifespan=lifespan)

# Allow React / Electron frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# API ENDPOINTS
# -------------------------------------------------------------
@app.get("/status")
async def get_status():
    """Provides live telemetry to the React UI."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_percent": psutil.virtual_memory().percent,
    }

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    """Handles the real-time connection with the React frontend."""
    global active_websocket
    await websocket.accept()
    active_websocket = websocket
    print("INFO: WebSocket /ws/audio [accepted]")

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websocket = None
        print("INFO: WebSocket disconnected.")

# -------------------------------------------------------------
# UI HELPERS (safe to call from any coroutine)
# -------------------------------------------------------------
async def update_ui_state(status: str):
    """Push a state change to the React UI."""
    if active_websocket:
        try:
            await active_websocket.send_text(
                json.dumps({"type": "state", "status": status})
            )
        except Exception:
            pass

async def update_ui_chat(sender: str, content: str):
    """Push a chat bubble to the React UI."""
    if active_websocket:
        try:
            await active_websocket.send_text(
                json.dumps({"type": "text", "sender": sender, "content": content})
            )
        except Exception:
            pass

# -------------------------------------------------------------
# CORE PIPELINE — called by the wake word thread via run_coroutine_threadsafe
# -------------------------------------------------------------
async def on_command_recorded(wav_bytes: bytes):
    """
    Full async pipeline triggered once the wake word thread captures a command.
    Runs on the main asyncio event loop.

    Flow: WAV bytes → STT → Router (regex / LLM) → TTS → WebSocket
    """
    global maya_is_speaking

    await update_ui_state("listening")

    # ── 1. TRANSCRIPTION ──────────────────────────────────────────────────────
    print("[1/3] Transcribing audio with Faster-Whisper...")
    await update_ui_state("processing")

    user_text = await transcribe(wav_bytes)

    if not user_text.strip():
        print("-> Empty speech result. Resetting state.")
        await update_ui_state("standby")
        return

    print(f"-> User said: '{user_text}'")
    await update_ui_chat("user", user_text)

    # ── 2. HYBRID ROUTER (Regex → Python services → LLM) ────────────────────
    print("[2/3] Routing Task (Hybrid Engine)...")
    maya_response = await route_task(user_text, generate_chat)

    print(f"-> Maya says: '{maya_response}'")
    await update_ui_chat("maya", maya_response)

    # ── 3. SPEECH SYNTHESIS ───────────────────────────────────────────────────
    print("[3/3] Synthesizing speech with Piper...")
    try:
        tts_audio_bytes = await synthesize(maya_response)
    except Exception as e:
        print(f"[TTS Error]: {e}")
        tts_audio_bytes = None

    if active_websocket and tts_audio_bytes:
        # Calculate exact playback duration so the wake word thread mutes for
        # exactly as long as the audio plays (avoids echo false-triggers).
        with wave.open(__import__("io").BytesIO(tts_audio_bytes)) as wf:
            duration_s = wf.getnframes() / wf.getframerate()

        mute_duration = duration_s + 0.5   # +0.5s echo tail
        print(f"[Pipeline] Muting mic for {mute_duration:.1f}s audio + 0.5s echo tail")

        maya_is_speaking = True
        try:
            await active_websocket.send_bytes(tts_audio_bytes)
        except Exception:
            pass

        await asyncio.sleep(mute_duration)
        maya_is_speaking = False
        
        # ── NEW: EXECUTE SHUTDOWN AFTER AUDIO FINISHES ──
        if maya_response == "Shutting down the system. Goodbye!":
            import os
            import signal
            print("[System] Audio finished playing. Pulling the plug.")
            os.kill(os.getpid(), signal.SIGINT)

    else:
        await update_ui_state("standby")