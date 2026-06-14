import os
from pathlib import Path

APP_NAME = "WinQuick AI"
APP_VERSION = "2.1.0"
DONATION_URL = "https://your-payment-link.com"  # User can change in Settings

APPDATA_DIR = Path(os.environ.get('LOCALAPPDATA', '.')) / APP_NAME
DB_PATH = APPDATA_DIR / "winquick.db"
APPDATA_DIR.mkdir(parents=True, exist_ok=True)

HOTKEY = "ctrl+shift+z"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TIMEOUT_MS = 60000
CLIPBOARD_MONITOR_INTERVAL = 3
CLIPBOARD_HISTORY_DAYS = 30

ACTIONS = [
    {"id": "summarize",   "label": "Summarize",       "prompt": "Summarize the following text concisely in 3-5 bullet points:\n\n{text}"},
    {"id": "professional", "label": "Make Professional","prompt": "Rewrite the following text in a professional, formal tone:\n\n{text}"},
    {"id": "shorten",     "label": "Shorten",          "prompt": "Shorten the following text while keeping all key information:\n\n{text}"},
    {"id": "expand",      "label": "Expand",           "prompt": "Expand the following text with more details and relevant examples:\n\n{text}"},
    {"id": "reply",       "label": "Generate Reply",   "prompt": "Generate a polite and contextually appropriate reply for:\n\n{text}"},
    {"id": "explain",     "label": "Explain",          "prompt": "Explain the following text in simple, easy to understand terms:\n\n{text}"},
    {"id": "chat",        "label": "Free Chat",        "prompt": None},
]

PROVIDERS = {
    "gemini": {"name": "Google Gemini", "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-1.5-pro"], "default": "gemini-2.5-flash"},
    "openai": {"name": "OpenAI", "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1", "o1-mini", "o3-mini"], "default": "gpt-4o-mini"},
    "claude": {"name": "Anthropic Claude", "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"], "default": "claude-3-haiku-20240307"},
    "custom": {"name": "Custom (OpenAI-compatible)", "models": [], "default": ""},
}
