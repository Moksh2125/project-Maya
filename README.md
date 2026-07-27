# Project Maya 🤖

Maya is a fast, completely offline AI desktop assistant with voice interaction. It features a modern Glassmorphism UI built with React & Electron, and a powerful Python backend that handles local Speech-to-Text, Large Language Models, and Text-to-Speech synthesis.

## 🚀 Tech Stack

### Backend (Python)
- **FastAPI**: Manages WebSocket connections for real-time streaming audio and chat.
- **Faster-Whisper**: High-performance local Speech-to-Text.
- **Ollama (Gemma 3 270M)**: Local LLM processing for fast, offline intelligence.
- **Piper TTS**: Rapid, high-quality Text-to-Speech synthesis (featuring the `en_US-amy-medium` female voice).
- **OpenWakeWord**: Continuous offline wake word detection (currently triggering on `"alexa"`).

### Frontend
- **React + Vite**: Fast, modern frontend development.
- **Electron**: Desktop application wrapper.
- **Tailwind CSS**: Beautiful, responsive Glassmorphism styling.

## 🛠️ Setup Instructions

This project runs entirely locally on your machine for maximum privacy and speed. 

### Prerequisites
- Python 3.10+
- Node.js & npm
- [Ollama](https://ollama.com/) installed and running locally with the `gemma` model pulled (`ollama run gemma`).

### 1. Backend Setup
1. Open a terminal and navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 2. Download Voice Models (Crucial Step)
Because the TTS binary and voice models are large, they are not tracked in Git. You **must** run the setup script to download them.

From the **root of the project**, open PowerShell and run:
```powershell
.\setup_piper.ps1
```
This will download the Piper executable and the required ONNX voice models directly into the backend directory.

### 3. Frontend Setup
1. Open a new terminal and navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install the Node modules:
   ```bash
   npm install
   ```

## 🏃‍♂️ Running Maya

To start Maya, you need to run both the backend server and the frontend app.

**1. Start the Backend:**
```bash
cd backend
.\venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**2. Start the Frontend:**
```bash
cd frontend
npm run dev
```

The Electron app will launch automatically, and Maya will begin listening for the wake word!

---
*Built for absolute privacy, speed, and a premium offline user experience.*
