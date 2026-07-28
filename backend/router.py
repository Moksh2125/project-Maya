import re
import os
import signal
import asyncio
from services.system_service import handle_system_info
from services.app_service import handle_open_app, handle_close_app
from services.browser_service import handle_browser_search
from services.memory_service import handle_memory

async def route_task(user_text: str, llm_engine) -> str:
    """
    Hybrid Router: 
    1. Deterministic Regex matching for 100% reliable OS commands.
    2. Fallback to Gemma LLM for conversational chat.
    """
    text = user_text.lower().strip()

    clean_text = re.sub(r'[^\w\s]', '', text).strip()
    # ── 0. SYSTEM TERMINATION (Kill Switch) ──────────────────────────
    if clean_text in ["stop", "alexa stop", "exit", "quit", "shut down", "terminate"]:
        print("\n[System] Termination command received. Shutting down Maya...")
        return "Shutting down the system. Goodbye!"
    
    # ── 1. SYSTEM COMMANDS (100% Deterministic) ──────────────────────
    if any(word in text for word in ["time", "clock", "what time is it"]):
        return handle_system_info("time")
        
    if any(word in text for word in ["date", "day is it", "today"]):
        return handle_system_info("date")
        
    if any(word in text for word in ["ram", "memory usage"]):
        return handle_system_info("ram")
        
    if any(word in text for word in ["cpu", "processor"]):
        return handle_system_info("cpu")

    # ── 2. APPLICATION CONTROL (Entity Extraction via Regex) ─────────
    # Matches: "open chrome", "launch vscode", "start calculator"
    open_match = re.search(r"\b(open|launch|start)\s+(.+)", text)
    if open_match:
        app_name = open_match.group(2).strip()
        return handle_open_app(app_name)

    # Matches: "close chrome", "kill vscode", "exit calculator"
    close_match = re.search(r"\b(close|kill|exit)\s+(.+)", text)
    if close_match:
        app_name = close_match.group(2).strip()
        return handle_close_app(app_name)

    # ── 3. BROWSER SEARCH ────────────────────────────────────────────
    # Matches: "search google for python", "search for react"
    search_match = re.search(r"\b(?:search|google|find)\b(?:.*?for)?\s+(.+)", text)
    if search_match:
        query = search_match.group(1).strip()
        return handle_browser_search(query, raw_text=text)

    # ── 4. PERSISTENT MEMORY ─────────────────────────────────────────
    # ── 4. PERSISTENT MEMORY ─────────────────────────────────────────
    if "what do you remember" in text or "recall memory" in text:
        return handle_memory("recall")
        
    if "clear memory" in text or "forget everything" in text:
        return handle_memory("clear")

    # \W* seamlessly absorbs commas, spaces, and colons added by Whisper
    remember_match = re.search(r"\b(?:remember|save)\b\W*(?:that\W*)?(.+)", text)
    if remember_match:
        fact = remember_match.group(1).strip()
        return handle_memory("save", fact)

    # ── 5. LLM FALLBACK (Conversational Chat) ────────────────────────
    # If no regex rules matched, the user is just chatting.
    # Hand the raw text over to Gemma for a natural response.
    print("[Router] No rules matched. Routing to Gemma for chat...")
    chat_response = await llm_engine(text)
    return chat_response