import os
import string
import subprocess
from services.fallback_service import handle_hallucination

# Application lookup table for Windows.
# ── OPEN: use shell-friendly names that Windows' App Paths registry recognises.
#    Do NOT use "chrome.exe" — `start chrome.exe` fails if Chrome is not in PATH.
#    `start chrome` resolves through HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths.
# ── CLOSE: .exe suffix is added inside handle_close_app for taskkill.
APP_MAP = {
    "chrome":         "chrome",
    "google chrome":  "chrome",
    "edge":           "msedge",
    "microsoft edge": "msedge",
    "firefox":        "firefox",
    "vscode":         "code",
    "vs code":        "code",
    "visual studio code": "code",
    "code":           "code",
    "notepad":        "notepad",
    "calculator":     "calc",
    "cmd":            "cmd",
    "terminal":       "cmd",
    "file explorer":  "explorer",
    "explorer":       "explorer",
}

# Characters that Faster-Whisper commonly appends to the last word in a sentence.
_TRAILING_JUNK = string.punctuation + " "


def _clean(raw: str) -> str:
    """Lower-case, strip leading/trailing whitespace and trailing punctuation."""
    return raw.lower().strip().rstrip(_TRAILING_JUNK)


def handle_open_app(app_name: str) -> str:
    if not app_name:
        return handle_hallucination("App Service (Open)", "Empty App Name")

    app_clean = _clean(app_name)
    target = APP_MAP.get(app_clean, app_clean)

    try:
        # `start ""` sets an empty window title so `start` treats the next
        # token as the program name, not the title — avoids misparse on Windows.
        subprocess.Popen(f'start "" "{target}"', shell=True)
        return f"Opening {app_clean}."
    except Exception as e:
        print(f"[AppService Error]: {e}")
        return f"Failed to open {app_clean}."


def handle_close_app(app_name: str) -> str:
    """Finds and terminates the running process by its OS name."""
    if not app_name:
        return "I didn't catch the name of the application to close."

    app_name_lower = app_name.lower()
    
    # Check if we have a hardcoded map for this app, otherwise guess by adding .exe
    target_process = PROCESS_MAP.get(app_name_lower, f"{app_name_lower}.exe")
    
    closed_count = 0
    
    # Scan through all currently running Windows processes
    for proc in psutil.process_iter(['name']):
        try:
            # If the process name matches our target, kill it safely
            if proc.info['name'] and proc.info['name'].lower() == target_process.lower():
                proc.terminate() 
                closed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Ignore OS processes that we don't have permission to touch
            pass
            
    if closed_count > 0:
        return f"Closed {app_name}."
    else:
        return f"I couldn't find {app_name} running on your system."