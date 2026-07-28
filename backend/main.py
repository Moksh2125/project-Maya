import os
import asyncio
import json
import threading
import wave
import psutil
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# ── Real pipeline modules ──────────────────────────────────────────────────────
from router import route_task
from core.llm import generate_chat, warmup
from core.stt import transcribe
from core.tts import synthesize
from core.wakeword import wake_word_listener
from services.chat_history_service import save_session, get_all_sessions, get_session, delete_session

# -------------------------------------------------------------
# GLOBAL STATE
# -------------------------------------------------------------
active_websocket: WebSocket | None = None
maya_is_speaking = False          # Shared flag — read by wake_word thread

# ── Live session transcript buffer ────────────────────────────────────────────
session_messages: list[dict] = []
session_started_at: datetime | None = None

# -------------------------------------------------------------
# LIFESPAN & BACKGROUND TASKS
# -------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing OpenWakeWord Engine...")
    loop = asyncio.get_running_loop()

    ww_thread = threading.Thread(
        target=wake_word_listener,
        args=(loop, on_command_recorded, lambda: maya_is_speaking),
        daemon=True,
        name="WakeWordThread",
    )
    ww_thread.start()

    asyncio.create_task(warmup())
    yield
    print("Shutting down Maya Engine...")

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
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_percent": psutil.virtual_memory().percent,
    }

@app.get("/history")
async def list_history():
    """Returns every saved chat session, most recent first (for the sidebar)."""
    return get_all_sessions()

@app.get("/history/{session_id}")
async def read_history(session_id: int):
    """Returns a single saved chat session by id (for the main chat window)."""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.delete("/history/{session_id}")
async def remove_history(session_id: int):
    if not delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": session_id}

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
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
# UI HELPERS
# -------------------------------------------------------------
async def update_ui_state(status: str):
    if active_websocket:
        try:
            await active_websocket.send_text(json.dumps({"type": "state", "status": status}))
        except Exception:
            pass

async def update_ui_chat(sender: str, content: str):
    if active_websocket:
        try:
            await active_websocket.send_text(json.dumps({"type": "text", "sender": sender, "content": content}))
        except Exception:
            pass

def _record_turn(sender: str, content: str):
    global session_started_at
    if session_started_at is None:
        session_started_at = datetime.now()
    session_messages.append({
        "sender": sender,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    })

# -------------------------------------------------------------
# CORE PIPELINE
# -------------------------------------------------------------
async def on_command_recorded(wav_bytes: bytes):
    global maya_is_speaking
    await update_ui_state("listening")

    print("[1/3] Transcribing audio with Faster-Whisper...")
    await update_ui_state("processing")
    user_text = await transcribe(wav_bytes)

    if not user_text.strip():
        await update_ui_state("standby")
        return

    print(f"-> User said: '{user_text}'")
    await update_ui_chat("user", user_text)
    _record_turn("user", user_text)

    print("[2/3] Routing Task (Hybrid Engine)...")
    maya_response = await route_task(user_text, generate_chat)

    print(f"-> Maya says: '{maya_response}'")
    await update_ui_chat("maya", maya_response)
    _record_turn("maya", maya_response)

    print("[3/3] Synthesizing speech with Piper...")
    try:
        tts_audio_bytes = await synthesize(maya_response)
    except Exception as e:
        print(f"[TTS Error]: {e}")
        tts_audio_bytes = None

    if active_websocket and tts_audio_bytes:
        with wave.open(__import__("io").BytesIO(tts_audio_bytes)) as wf:
            duration_s = wf.getnframes() / wf.getframerate()

        mute_duration = duration_s + 0.5
        maya_is_speaking = True
        try:
            await active_websocket.send_bytes(tts_audio_bytes)
        except Exception:
            pass

        await asyncio.sleep(mute_duration)
        maya_is_speaking = False

        # ── EXECUTE SHUTDOWN & SAVE SESSION ──
        if maya_response == "Shutting down the system. Goodbye!":
            import signal
            
            # SAVES THE SESSION RIGHT BEFORE CLOSING!
            if session_messages:
                saved_id = save_session(session_messages, session_started_at, datetime.now())
                print(f"[History] Saved session #{saved_id} ({len(session_messages)} turns).")

            print("[System] Audio finished playing. Initiating global shutdown...")

            # Tell frontend to close
            try:
                await active_websocket.send_text(json.dumps({"type": "command", "action": "close"}))
            except Exception:
                pass

            # Terminate other apps
            TARGETS = ["node.exe", "ollama.exe", "ollama app.exe"]
            for proc in psutil.process_iter(['name', 'exe', 'cmdline']):
                try:
                    proc_name = (proc.info['name'] or "").lower()
                    proc_exe = (proc.info['exe'] or "").lower()
                    cmdline = " ".join(proc.info['cmdline'] or []).lower()
                    if proc_name in TARGETS or "antigravity" in proc_name or "antigravity" in proc_exe or "antigravity" in cmdline:
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            await asyncio.sleep(0.5)
            print("[System] Pulling the plug on the backend.")
            os.kill(os.getpid(), signal.SIGINT)

    else:
        await update_ui_state("standby")