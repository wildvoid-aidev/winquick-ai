import google.genai as genai
import json
from config import GEMINI_MODEL, GEMINI_TIMEOUT_MS, ACTIONS, PROVIDERS

_client = None
_current_key = None
_current_provider = "gemini"

def get_client(api_key, provider="gemini", model=None):
    global _client, _current_key, _current_provider
    key = f"{provider}:{api_key}:{model}"
    if _client is None or _current_key != key:
        _client = None
        if provider == "gemini":
            _client = genai.Client(api_key=api_key, http_options={"timeout": GEMINI_TIMEOUT_MS})
        elif provider == "openai":
            pass
        elif provider == "claude":
            pass
        _current_key = key
        _current_provider = provider
    return _client

def call_gemini(api_key, action_id, text, model=None):
    try:
        client = get_client(api_key, "gemini", model)
    except Exception as e:
        return f"API client error: {e}"
    if not client:
        return "Failed to create API client."

    action = next((a for a in ACTIONS if a["id"] == action_id), None)

    if action_id == "chat":
        prompt = text
    elif action and action["prompt"]:
        prompt = action["prompt"].format(text=text)
    else:
        return "Unknown action."

    model_name = model or GEMINI_MODEL
    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        return response.text
    except Exception as e:
        err = str(e)
        if "429" in err:
            return f"Rate limit hit. Please wait a moment and try again.\nDetails: {err[:200]}"
        if "timeout" in err.lower() or "deadline" in err.lower():
            return "Request timed out. Check your internet and try again."
        if "API_KEY" in err or "key" in err.lower() or "403" in err:
            return "Invalid API key. Update it in Settings."
        return f"Error: {err[:300]}"

def chat(api_key, message, model=None, provider="gemini"):
    if provider == "gemini":
        return call_gemini(api_key, "chat", message, model)
    elif provider == "openai":
        return "OpenAI support coming soon. Use Gemini for now."
    elif provider == "claude":
        return "Claude support coming soon. Use Gemini for now."
    else:
        return f"Provider '{provider}' not supported yet."
