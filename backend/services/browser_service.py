import webbrowser
import urllib.parse
from services.fallback_service import handle_hallucination

def handle_browser_search(query: str, raw_text: str = "") -> str:
    if not query:
        return handle_hallucination("Browser Service", "Empty Search Query")

    safe_query = urllib.parse.quote(query)
    check_text = (raw_text or query).lower()

    if "youtube" in check_text:
        search_url = f"https://www.youtube.com/results?search_query={safe_query}"
        engine = "YouTube"
    elif "github" in check_text:
        search_url = f"https://github.com/search?q={safe_query}"
        engine = "GitHub"
    else:
        search_url = f"https://www.google.com/search?q={safe_query}"
        engine = "Google"

    try:
        webbrowser.open(search_url)
        return f"Searching {engine} for {query}."
    except Exception as e:
        print(f"[BrowserService Error]: {e}")
        return "I encountered an error trying to open the browser."