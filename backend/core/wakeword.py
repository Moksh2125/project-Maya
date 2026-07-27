import asyncio
import time
import io
import wave
import numpy as np
import pyaudio
from openwakeword.model import Model

WAKE_WORD_MODEL = "alexa"  # Pre-trained wake word tag
SAMPLE_RATE = 16000
CHUNK_SIZE = 1280          # 80ms chunks at 16kHz
DETECTION_THRESHOLD = 0.7  # Raised threshold to reduce ghost triggers
SILENCE_ENERGY_THRESHOLD = 1500  # Adjusted threshold for built-in microphones


def wake_word_listener(loop: asyncio.AbstractEventLoop, on_command_recorded, is_speaking_check):
    """
    Continuous background listener for OpenWakeWord with echo loop prevention.
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
            # Pause mic evaluation while Maya is actively playing audio back through speakers
            if is_speaking_check():
                time.sleep(0.1)
                continue

            raw_data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            pcm = np.frombuffer(raw_data, dtype=np.int16)
            prediction = oww_model.predict(pcm)

            score = list(prediction.values())[0]
            if score >= DETECTION_THRESHOLD:
                print(f"\n[WakeWord] Triggered! (Score={score:.2f}). Capturing voice command...")

                frames = []
                silence_frames = 0

                # Buffer ~1.5s initial recording chunk
                for _ in range(20):
                    frames.append(stream.read(CHUNK_SIZE, exception_on_overflow=False))

                # Record continuously until speaker pauses speaking
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

                # Package recorded PCM frames into WAV container in memory
                wav_io = io.BytesIO()
                with wave.open(wav_io, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(SAMPLE_RATE)
                    wf.writeframes(b"".join(frames))

                # Safely execute async pipeline task on the main event loop
                asyncio.run_coroutine_threadsafe(
                    on_command_recorded(wav_io.getvalue()), loop
                )

                time.sleep(1)
    except Exception as e:
        print(f"[WakeWord Loop Error]: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()