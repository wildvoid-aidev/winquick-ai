import threading
import queue
import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw
from config import APP_NAME
from database import init_db, get_setting, has_donated, get_launch_count, increment_launch_count, get_last_donation_reminder, set_last_donation_reminder
from utils import start_hotkey_listener, stop_hotkey_listener, capture_selected_text, start_clipboard_monitor, stop_clipboard_monitor
from ai_actions import chat
from ui import PopupWindow, SettingsWindow, HistoryWindow, ClipboardHistoryWindow, DonationWindow

event_queue = queue.Queue()
tray_icon = None
app_root = None

def create_tray_image():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, 62, 62], fill="#2563EB")
    draw.ellipse([10, 10, 54, 54], fill="#1D4ED8")
    draw.polygon([(28, 18), (28, 30), (38, 30), (34, 46), (38, 46), (38, 34), (28, 34), (32, 18)], fill="white")
    return img

def on_hotkey():
    text = capture_selected_text()
    event_queue.put(("show_popup", text))

def tray_show(_icon, _item):
    event_queue.put(("show_popup_from_tray", None))

def tray_settings(_icon, _item):
    event_queue.put(("show_settings", None))

def tray_history(_icon, _item):
    event_queue.put(("show_history", None))

def tray_clipboard(_icon, _item):
    event_queue.put(("show_clipboard", None))

def tray_donate(_icon, _item):
    event_queue.put(("show_donation", None))

def tray_quit(_icon, _item):
    event_queue.put(("quit", None))

def run_tray():
    global tray_icon
    menu = pystray.Menu(
        pystray.MenuItem(f"Open {APP_NAME}", tray_show, default=True),
        pystray.MenuItem("Settings", tray_settings),
        pystray.MenuItem("AI History", tray_history),
        pystray.MenuItem("Clipboard History", tray_clipboard),
        pystray.MenuItem("♥ Support", tray_donate),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", tray_quit),
    )
    icon = pystray.Icon("winquick", create_tray_image(), APP_NAME, menu)
    tray_icon = icon
    icon.run()

_process_active_popup = None

def _handle_action(action_id, text):
    api_key = get_setting("api_key")
    if not api_key:
        return "Set your API key in Settings first."
    provider = get_setting("provider", "gemini")
    model = get_setting("model", "gemini-2.5-flash")
    from ai_actions import call_gemini
    return call_gemini(api_key, action_id, text, model)

def _handle_chat(message):
    api_key = get_setting("api_key")
    if not api_key:
        return "Set your API key in Settings first."
    provider = get_setting("provider", "gemini")
    model = get_setting("model", "gemini-2.5-flash")
    return chat(api_key, message, model, provider)

def process_events():
    global _process_active_popup, app_root
    try:
        while True:
            evt, data = event_queue.get_nowait()

            if evt == "show_popup":
                if _process_active_popup is not None:
                    try:
                        _process_active_popup.close()
                    except Exception:
                        pass
                popup = PopupWindow(data, _handle_action, _handle_chat)
                _process_active_popup = popup

            elif evt == "show_popup_from_tray":
                text = capture_selected_text()
                if _process_active_popup is not None:
                    try:
                        _process_active_popup.close()
                    except Exception:
                        pass
                popup = PopupWindow(text, _handle_action, _handle_chat)
                _process_active_popup = popup

            elif evt == "show_settings":
                SettingsWindow()

            elif evt == "show_history":
                HistoryWindow()

            elif evt == "show_clipboard":
                ClipboardHistoryWindow()

            elif evt == "show_donation":
                DonationWindow()

            elif evt == "quit":
                stop_hotkey_listener()
                stop_clipboard_monitor()
                if tray_icon:
                    tray_icon.stop()
                app_root.quit()
                return

    except queue.Empty:
        pass

    if app_root:
        app_root.after(50, process_events)

def check_first_launch():
    if not get_setting("api_key"):
        SettingsWindow(blocking=True)
    _check_donation_reminder()

def _check_donation_reminder():
    if has_donated():
        return
    launch_count = get_launch_count()
    increment_launch_count()
    if launch_count < 2:
        return
    from datetime import datetime
    last = get_last_donation_reminder()
    now = int(datetime.now().timestamp())
    if last > 0 and (now - last) < 604800:
        return
    set_last_donation_reminder()
    event_queue.put(("show_donation", None))

def main():
    global app_root

    init_db()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app_root = ctk.CTk()
    app_root.withdraw()

    app_root.after(500, check_first_launch)
    app_root.after(1000, start_clipboard_monitor)

    tray_thread = threading.Thread(target=run_tray, daemon=True)
    tray_thread.start()

    start_hotkey_listener(on_hotkey)

    app_root.after(50, process_events)
    app_root.mainloop()

if __name__ == "__main__":
    main()
