import asyncio
import ollama

DEFAULT_MODEL = "gemma3:270m"

SYSTEM_PROMPT = """You are Maya, a highly capable, concise, and helpful local AI assistant.
Your goal is to answer general questions, solve logic problems, and chat naturally with the user.
Keep your answers brief, conversational, and friendly.
Do NOT use markdown, emojis, or code blocks, as your output is being sent directly to a text-to-speech engine."""

# Use a lazy-loaded singleton to prevent asyncio loop-binding hangs
_client = None

def get_client() -> ollama.AsyncClient:
    """Lazy-loads the client inside the active Uvicorn event loop."""
    global _client
    if _client is None:
        _client = ollama.AsyncClient()
    return _client

async def warmup() -> None:
    """Pre-loads the model into Ollama's memory at server startup."""
    print(f"[LLM] Pre-warming model '{DEFAULT_MODEL}' in Ollama...")
    try:
        client = get_client()
        await client.chat(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": "hi"}],
            options={"num_predict": 1},
        )
        print(f"[LLM] Model '{DEFAULT_MODEL}' is hot and ready.")
    except Exception as e:
        print(f"[LLM] Warmup failed (Ollama may not be running): {e}")

async def generate_chat(user_text: str) -> str:
    """
    Takes the raw user text and generates a natural language response.
    Includes robust error handling so UI doesn't freeze on failure.
    """
    client = get_client()
    try:
        response = await client.chat(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_text},
            ],
        )
        
        # Safely handle both Object and Dictionary response types depending on ollama-python version
        if isinstance(response, dict):
            return response['message']['content'].strip()
        return response.message.content.strip()
        
    except Exception as e:
        print(f"\n[LLM ERROR]: Failed to generate response. {e}")
        return "I am having trouble connecting to my language model right now. Please check if Ollama is running."