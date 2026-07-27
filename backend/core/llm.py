import asyncio
import ollama

DEFAULT_MODEL = "gemma3:270m"


async def chat(messages: list, model: str = DEFAULT_MODEL) -> str:
    """Sends message history to Ollama and returns the AI response."""
    response = await asyncio.to_thread(
        ollama.chat,
        model=model,
        messages=messages
    )
    return response["message"]["content"]