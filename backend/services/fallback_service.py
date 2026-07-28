def handle_hallucination(service_name: str, invalid_data: str = "Unknown") -> str:
    """
    Catches LLM hallucinations, prints a dev warning, 
    and returns a polite TTS response.
    """
    # 1. Terminal print for you (the developer)
    print(f"⚠️ [Hallucination Blocked] {service_name} received invalid data: '{invalid_data}'")
    
    # 2. Voice response for Maya (the user experience)
    return "I am sorry, I got a bit confused there. Could you say that one more time?"