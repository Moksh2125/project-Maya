import os
import subprocess
import asyncio
from pathlib import Path

# Resolve executable name portable across OS targets
_piper_exe = "piper.exe" if os.name == "nt" else "piper"
PIPER_BINARY = Path(__file__).parent.parent / "piper" / _piper_exe
VOICES_DIR   = Path(__file__).parent.parent / "piper" / "voices"

# ── Voice selection ────────────────────────────────────────────────────────────
# en_US-amy-medium    → female ✅ (correct for Maya)
# en_US-lessac-medium → male  ✗
DEFAULT_VOICE = "en_US-amy-medium.onnx"


def _run_piper(text: str, model_path: Path) -> bytes:
    """
    Synchronous Piper call — runs in a thread pool via asyncio.to_thread().

    WINDOWS FIX 1 — DLL conflict (STATUS_STACK_BUFFER_OVERRUN / 0xC0000409):
    Python's faster-whisper ships its own onnxruntime.dll. When piper.exe is
    spawned as a subprocess, Windows DLL search finds Python's onnxruntime first
    instead of piper's bundled one, causing a C++ stack-buffer-overrun crash.
    Setting cwd to the piper/ directory makes Windows prioritise piper's own DLLs.

    WINDOWS FIX 2 — stdout pipe crash:
    '--output_file -' (write WAV to stdout) crashes on this Piper build on Windows.
    We write to a NamedTemporaryFile instead and read it back.

    WINDOWS FIX 3 — ESPEAK_DATA_PATH:
    Piper looks for espeak-ng-data at the hardcoded Linux path /usr/share/espeak-ng-data.
    We override ESPEAK_DATA_PATH to point at the piper/ directory where those
    files (phontab, phondata, phonindex …) are bundled alongside piper.exe.
    """
    import tempfile

    env = os.environ.copy()
    # Point espeak-ng to its own isolated data directory.
    # MUST NOT point to piper/ root — that contains our ONNX voices/ which
    # espeak would try to parse as text voice definitions, causing a crash.
    env["ESPEAK_DATA_PATH"] = str(PIPER_BINARY.parent / "espeak-ng-data")

    # Write to a temp WAV file — avoids the stdout-pipe crash on Windows
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [str(PIPER_BINARY), "--model", str(model_path), "--output_file", tmp_path],
            input=text.encode("utf-8") + b"\n",  # Piper reads stdin line-by-line
            capture_output=True,
            env=env,
            cwd=str(PIPER_BINARY.parent),        # DLL search starts in piper/ dir
        )

        if result.returncode not in (0, 3221226505):
            # 3221226505 (0xC0000409) is a known false-positive crash code from
            # piper's C++ runtime on Windows — the file is still written correctly.
            raise RuntimeError(
                f"Piper TTS failed (exit {result.returncode}):\n"
                f"{result.stderr.decode(errors='replace')}"
            )

        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            raise RuntimeError(
                f"Piper produced no audio output.\n"
                f"Stderr: {result.stderr.decode(errors='replace')}"
            )

        with open(tmp_path, "rb") as f:
            return f.read()

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


async def synthesize(text: str, voice_model: str = DEFAULT_VOICE) -> bytes:
    """Async wrapper — offloads the blocking Piper subprocess to a thread."""
    if not PIPER_BINARY.is_file():
        raise FileNotFoundError(
            f"Piper binary not found at: {PIPER_BINARY}\n"
            "Run setup_piper.ps1 from the project root first."
        )

    model_path = VOICES_DIR / voice_model
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Voice model not found at: {model_path}\n"
            "Run setup_piper.ps1 from the project root first.\n"
            f"Available voices: {[f.name for f in VOICES_DIR.glob('*.onnx')]}"
        )

    return await asyncio.to_thread(_run_piper, text, model_path)