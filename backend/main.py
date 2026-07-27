import asyncio
import threading
import psutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Import core modular scripts
# Import core modular scripts from the core package
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

# State flag used for software acoustic echo cancellation
maya_is_speaking = False

session_history = [
    {
        "role": "system",
        "content": "You are Maya, an offline AI desktop assistant. Keep answers concise, natural, and conversational.",
    }
]


def check_is_speaking() -> bool:
    """Helper callback for background listener to check mute status."""
    return maya_is_speaking


async def broadcast_ws(message: dict):
    """Broadcasting helper to push JSON data to connected UI client(s)."""
    for ws in list(active_websockets):
        try:
            await ws.send_json(message)
        except Exception:
            pass


async def process_voice_command(audio_bytes: bytes):
    """End-to-End Execution Pipeline: STT -> LLM -> TTS -> Audio Broadcast."""
    global maya_is_speaking
    try:
        await broadcast_ws({"type": "state", "status": "processing"})

        # 1. Speech-to-Text via Faster-Whisper
        print("[1/3] Transcribing audio with Faster-Whisper...")
        user_text = await stt.transcribe(audio_bytes)
        if not user_text:
            print("-> Empty speech result. Resetting state.")
            await broadcast_ws({"type": "state", "status": "standby"})
            return

        print(f"-> User said: '{user_text}'")
        await broadcast_ws({"type": "text", "sender": "user", "content": user_text})

        # 2. Local LLM via Gemma 3
        print("[2/3] Generating response with Gemma 3...")
        session_history.append({"role": "user", "content": user_text})
        maya_text = await llm.chat(session_history)
        session_history.append({"role": "assistant", "content": maya_text})

        print(f"-> Maya says: '{maya_text}'")
        await broadcast_ws({"type": "text", "sender": "maya", "content": maya_text})

        # 3. Speech Synthesis via Piper TTS
        print("[3/3] Synthesizing speech with Piper...")
        audio_response_bytes = await tts.synthesize(maya_text)

        # Turn on echo protection before playing audio
        maya_is_speaking = True

        # Stream audio payload to the frontend
        for ws in list(active_websockets):
            try:
                await ws.send_bytes(audio_response_bytes)
            except Exception as e:
                print(f"WebSocket audio streaming error: {e}")

        # Sleep to allow audio playback to clear through room speakers
        await asyncio.sleep(4)

    except Exception as e:
        print(f"!!! CRITICAL PIPELINE ERROR [{type(e).__name__}]: {e}")

    finally:
        maya_is_speaking = False
        await broadcast_ws({"type": "state", "status": "standby"})


@app.on_event("startup")
async def startup_event():
    """Spawns the continuous background wake word listener upon app boot."""
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
        active_websockets.remove(websocket)