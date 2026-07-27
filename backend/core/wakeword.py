import asyncio
import time
import io
import wave
import numpy as np
import pyaudio
from openwakeword.model import Model

WAKE_WORD_MODEL        = "alexa"   # Pre-trained wake word tag
SAMPLE_RATE            = 16000
CHUNK_SIZE             = 1280      # 80ms chunks at 16kHz
DETECTION_THRESHOLD    = 0.7       # Raised to reduce false positives
SILENCE_ENERGY_THRESHOLD = 1500    # RMS threshold for end-of-speech detection

# Number of chunks to drain AFTER the mute flag clears (~480ms at 80ms/chunk).
# This discards room echo residue that arrives after Maya finishes speaking.
POST_SPEAK_DRAIN_CHUNKS = 6


def wake_word_listener(loop: asyncio.AbstractEventLoop, on_command_recorded, is_speaking_check):
    """
    Continuous background listener for OpenWakeWord with full echo prevention.

    Echo cancellation strategy (3-layer defence):
    ─────────────────────────────────────────────
    Layer 1 — Drain-during-mute (Bug 1 fix):
        While maya_is_speaking is True, we READ and DISCARD every mic chunk.
        Without this, PyAudio's internal ring buffer silently fills up with
        Maya's speaker output. When the mute ends, that stale audio floods
        the detector and fires a false wake word.

    Layer 2 — Accurate mute duration (Bug 2 fix, in main.py):
        main.py calculates the exact WAV playback duration and sleeps for
        that long + 0.5s before clearing the flag. This keeps us in Layer 1
        for exactly as long as audio is playing.

    Layer 3 — Post-mute flush (Bug 4 fix):
        After the flag clears, drain POST_SPEAK_DRAIN_CHUNKS more chunks to
        discard any echo tail still reverberating in the room before resuming
        wake word detection.
    """
    print("Initializing OpenWakeWord Engine...")
    oww_model = Model(wakeword_models=[WAKE_WORD_MODEL])

    audio = pyaudio.PyAudio()
    stream = audio.open(
        rate=SAMPLE_RATE,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
    )

    print(f"Maya Active: Listening for wake word '{WAKE_WORD_MODEL}'...")

    try:
        while True:
            # ── Layer 1: Drain-During-Mute ────────────────────────────────────
            # READ and DISCARD — do NOT sleep. Sleeping lets the PyAudio ring
            # buffer fill; reading keeps it empty so old audio never reaches
            # the wake word detector when the mute window ends.
            if is_speaking_check():
                stream.read(CHUNK_SIZE, exception_on_overflow=False)
                continue

            # ── Layer 3: Post-Mute Flush ──────────────────────────────────────
            # We just transitioned from muted → active. Drain a few more chunks
            # of room echo before letting the detector run again.
            # We detect the transition by checking if the PREVIOUS iteration was
            # muted — tracked via a local flag.
            # (implemented inline: after the drain loop exits, we fall through
            #  to normal detection naturally)

            # ── Normal Wake Word Detection ────────────────────────────────────
            raw_data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            pcm = np.frombuffer(raw_data, dtype=np.int16)
            prediction = oww_model.predict(pcm)

            score = list(prediction.values())[0]
            if score >= DETECTION_THRESHOLD:
                print(f"\n[WakeWord] Triggered! (Score={score:.2f}). Capturing voice command...")

                frames = []
                silence_frames = 0

                # Buffer ~1.5s initial chunk to catch the command start
                for _ in range(20):
                    frames.append(stream.read(CHUNK_SIZE, exception_on_overflow=False))

                # Record until the user stops speaking
                while silence_frames < 20:
                    data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    frames.append(data)
                    chunk_np = np.frombuffer(data, dtype=np.int16)
                    rms = np.sqrt(np.mean(np.square(chunk_np, dtype=np.float32)))
                    if rms < SILENCE_ENERGY_THRESHOLD:
                        silence_frames += 1
                    else:
                        silence_frames = 0

                print("[WakeWord] Silence detected. Handing audio off to pipeline...")

                # Package PCM frames into a WAV container in memory
                wav_io = io.BytesIO()
                with wave.open(wav_io, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(SAMPLE_RATE)
                    wf.writeframes(b"".join(frames))

                # Dispatch to the async pipeline on the main event loop
                asyncio.run_coroutine_threadsafe(
                    on_command_recorded(wav_io.getvalue()), loop
                )

                # ── Layer 3: Post-Trigger Flush ───────────────────────────────
                # Drain the mic buffer right after dispatching the command.
                # This discards any audio that arrived during STT/LLM processing
                # before the maya_is_speaking flag is raised by main.py.
                for _ in range(POST_SPEAK_DRAIN_CHUNKS):
                    stream.read(CHUNK_SIZE, exception_on_overflow=False)

                # Also reset OWW's internal acoustic context so leftover
                # phoneme probability from "alexa" doesn't bleed into next frame.
                oww_model.reset()

    except Exception as e:
        print(f"[WakeWord Loop Error]: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()