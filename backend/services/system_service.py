import datetime
import psutil
from services.fallback_service import handle_hallucination

def handle_system_info(query: str) -> str:
    query = (query or "").lower()
    
    if "time" in query:
        now = datetime.datetime.now().strftime("%I:%M %p")
        return f"The current time is {now}."
    elif "date" in query:
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")
        return f"Today is {today}."
    elif "ram" in query or "memory" in query:
        ram = psutil.virtual_memory().percent
        return f"Current RAM usage is at {ram}%."
    elif "cpu" in query:
        cpu = psutil.cpu_percent(interval=0.1)
        return f"Current CPU load is at {cpu}%."
    else:
       return handle_hallucination("System Service", query)