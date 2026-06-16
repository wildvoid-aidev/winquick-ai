import os
import urllib.request
import customtkinter as ctk
import pyperclip
import threading
import webbrowser
from config import ACTIONS, APP_NAME
from database import save_history, get_setting, set_setting, get_clipboard_history, delete_clipboard_item, delete_clipboard_items
from database import get_donation_url, get_upi_id, get_international_url, mark_donated

class PopupWindow:
    def __init__(self, selected_text, on_action, on_chat, on_close=None, on_quit=None):
        self.result_text = ""
        self.on_action = on_action
        self.on_chat = on_chat
        self.selected_text = selected_text
        self.pinned = True
        self.messages = []
        self._closed = False
        self._on_close = on_close
        self._on_quit = on_quit

        self.win = ctk.CTkToplevel()
        self.win.title(f"{APP_NAME}")
        w, h = 600, 700
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.focus_force()
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self._build_ui()

    def _build_ui(self):
        self.win.grid_columnconfigure(0, weight=1)
        self.win.grid_rowconfigure(3, weight=1)

        title_row = ctk.CTkFrame(self.win, fg_color="transparent")
        title_row.grid(row=0, column=0, padx=15, pady=(10, 2), sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(title_row, text=APP_NAME, font=("Segoe UI", 22, "bold")).grid(row=0, column=0)

        self.pin_btn = ctk.CTkButton(title_row, text="📌", width=32, height=28, command=self._toggle_pin)
        self.pin_btn.grid(row=0, column=1, padx=(0, 3))
        ctk.CTkButton(title_row, text="➖", width=32, height=28, command=self._hide_to_tray).grid(row=0, column=2)

        main_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        main_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        main_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(main_frame, text="Ask anything or use actions below:",
                      font=("Segoe UI", 11)).pack(anchor="w")

        input_row = ctk.CTkFrame(main_frame, fg_color="transparent")
        input_row.pack(fill="x", pady=(2, 8))
        input_row.grid_columnconfigure(0, weight=1)

        self.input_entry = ctk.CTkEntry(input_row, placeholder_text="Type your question here...",
                                         font=("Segoe UI", 12), height=35)
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.input_entry.insert(0, self.selected_text[:500] if self.selected_text else "")
        self.input_entry.bind("<Return>", lambda e: self._do_chat())

        self.send_btn = ctk.CTkButton(input_row, text="Send", command=self._do_chat, width=70, height=35)
        self.send_btn.grid(row=0, column=1)

        actions_label = ctk.CTkLabel(main_frame, text="Quick Actions:",
                                      font=("Segoe UI", 11, "bold"))
        actions_label.pack(anchor="w")

        actions_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        actions_frame.pack(fill="x")
        actions_frame.grid_columnconfigure((0, 1, 2), weight=1)

        for i, a in enumerate([a for a in ACTIONS if a["id"] != "chat"]):
            btn = ctk.CTkButton(actions_frame, text=a["label"],
                                command=lambda aid=a["id"]: self._run_action(aid),
                                height=34, font=("Segoe UI", 11))
            btn.grid(row=i // 3, column=i % 3, padx=2, pady=2, sticky="ew")

        result_label = ctk.CTkLabel(self.win, text="Result:", font=("Segoe UI", 13, "bold"))
        result_label.grid(row=2, column=0, padx=15, pady=(8, 2), sticky="w")

        self.scroll_frame = ctk.CTkScrollableFrame(self.win)
        self.scroll_frame.grid(row=3, column=0, padx=15, pady=(0, 5), sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self._add_message("system", "Ask anything above or use Quick Actions...")

        bottom = ctk.CTkFrame(self.win, fg_color="transparent")
        bottom.grid(row=4, column=0, padx=15, pady=(0, 12), sticky="ew")
        bottom.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        ctk.CTkButton(bottom, text="Copy Result", command=self._copy).grid(row=0, column=0, padx=3)
        ctk.CTkButton(bottom, text="Save to Clipboard", command=self._save_to_clip).grid(row=0, column=1, padx=3)
        ctk.CTkButton(bottom, text="Use as Input", command=self._use_as_input).grid(row=0, column=2, padx=3)
        ctk.CTkButton(bottom, text="Clear Chat", command=self._confirm_clear,
                       fg_color="#ef4444", hover_color="#dc2626").grid(row=0, column=3, padx=3)
        ctk.CTkButton(bottom, text="✕ Quit", command=self._quit_app, width=60,
                       fg_color="#b91c1c", hover_color="#991b1b").grid(row=0, column=4, padx=3)

    def _toggle_pin(self):
        self.pinned = not self.pinned
        self.win.attributes("-topmost", self.pinned)
        self.pin_btn.configure(text="📌" if self.pinned else "📌")

    def _hide_to_tray(self):
        self.win.withdraw()

    def _add_message(self, sender, text):
        card = ctk.CTkFrame(self.scroll_frame)
        card.pack(fill="x", pady=3)
        card.grid_columnconfigure(0, weight=1)

        label = "You" if sender == "user" else ("AI" if sender == "ai" else "System")
        color = "#00f0ff" if sender == "ai" else "#94a3b8" if sender == "system" else "#7c3aed"
        ctk.CTkLabel(card, text=label, font=("Segoe UI", 10, "bold"),
                      text_color=color).grid(row=0, column=0, sticky="w", padx=8, pady=(4, 0))
        msg = ctk.CTkTextbox(card, wrap="word", font=("Segoe UI", 11), height=min(200, max(40, len(text) // 2)))
        msg.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
        msg.insert("1.0", text)
        msg.configure(state="disabled")
        self.messages.append({"sender": sender, "text": text})
        self.result_text = text
        self.scroll_frame.update_idletasks()

    def _do_chat(self):
        text = self.input_entry.get().strip()
        if not text:
            return
        self._add_message("user", text)
        self._add_message("ai", "Thinking...")
        self.input_entry.delete(0, "end")
        self.win.update()

        def process():
            result = self.on_chat(text)
            save_history("chat", text, result)
            self.win.after(0, lambda: self._update_last_ai(result))

        threading.Thread(target=process, daemon=True).start()

    def _run_action(self, action_id):
        text = self.input_entry.get().strip()
        if not text:
            return
        self._add_message("user", f"[{action_id}] {text}")
        self.input_entry.delete(0, "end")
        self._add_message("ai", "Processing...")

        api_key = get_setting("api_key")
        if not api_key:
            self._update_last_ai("Set your API key in Settings first.")
            return

        self.win.update()

        def process():
            result = self.on_action(action_id, text)
            save_history(action_id, text, result)
            self.win.after(0, lambda: self._update_last_ai(result))

        threading.Thread(target=process, daemon=True).start()

    def _update_last_ai(self, text):
        for w in self.scroll_frame.winfo_children():
            pass
        self.messages[-1]["text"] = text
        self.result_text = text
        children = list(self.scroll_frame.winfo_children())
        if len(children) >= 2:
            last_card = children[-1]
            textboxes = [c for c in last_card.winfo_children() if isinstance(c, ctk.CTkTextbox)]
            if textboxes:
                tb = textboxes[-1]
                tb.configure(state="normal")
                tb.delete("1.0", "end")
                tb.insert("1.0", text)
                tb.configure(state="disabled")
                h = min(200, max(40, len(text) // 2))
                tb.configure(height=h)
        self.scroll_frame.update_idletasks()
        self.scroll_frame._parent_canvas.yview_moveto(1.0)

    def _copy(self):
        if self.result_text:
            pyperclip.copy(self.result_text)

    def _save_to_clip(self):
        if self.result_text:
            pyperclip.copy(self.result_text)

    def _use_as_input(self):
        if self.result_text:
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, self.result_text[:500])
            self.input_entry.focus()

    def _confirm_clear(self):
        dialog = ctk.CTkToplevel(self.win)
        dialog.title("Clear Chat")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.grab_set()
        dialog.transient(self.win)

        ctk.CTkLabel(dialog, text="Are you sure?", font=("Segoe UI", 16, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(dialog, text="This will clear all chat messages.", font=("Segoe UI", 11), text_color="gray").pack()

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=(12, 0))
        ctk.CTkButton(btn_row, text="Yes, Clear", command=lambda: self._clear_chat(dialog),
                       fg_color="#ef4444", hover_color="#dc2626", height=32, width=90).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="No", command=dialog.destroy,
                       fg_color="#6b7280", hover_color="#4b5563", height=32, width=90).pack(side="left", padx=5)

    def _clear_chat(self, dialog):
        dialog.destroy()
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self.messages.clear()
        self.result_text = ""
        self._add_message("system", "Chat cleared. Start a new conversation!")

    def update_input(self, text):
        if self._closed:
            return
        self.selected_text = text
        self.input_entry.delete(0, "end")
        self.input_entry.insert(0, text[:500] if text else "")
        self.input_entry.focus()
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()

    def _quit_app(self):
        if self._on_quit:
            self._on_quit()

    def close(self):
        self._closed = True
        self.win.destroy()
        if self._on_close:
            self._on_close()


class SettingsWindow:
    def __init__(self, on_close_callback=None, blocking=False):
        self.on_close = on_close_callback
        self.blocking = blocking
        self._saved = False
        self.win = ctk.CTkToplevel()
        self.win.title(f"{APP_NAME} - Settings")
        self.win.geometry("480x520")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.focus_force()
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        ctk.CTkLabel(self.win, text="Settings", font=("Segoe UI", 20, "bold")).pack(pady=(18, 6))

        if blocking:
            ctk.CTkLabel(self.win, text="Enter your API Key to continue",
                          font=("Segoe UI", 12), text_color="#f59e0b").pack()

        # --- API Provider ---
        frame = ctk.CTkFrame(self.win)
        frame.pack(padx=20, pady=5, fill="x")

        ctk.CTkLabel(frame, text="AI Provider", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 2))

        self.provider_var = ctk.StringVar(value=get_setting("provider", "gemini"))
        provider_row = ctk.CTkFrame(frame, fg_color="transparent")
        provider_row.pack(fill="x", padx=12)
        for p_id, p_info in [("gemini", "Google Gemini"), ("openai", "OpenAI"), ("claude", "Claude")]:
            ctk.CTkRadioButton(provider_row, text=p_info, variable=self.provider_var,
                                value=p_id, command=self._on_provider_change).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(frame, text="API Key", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
        self.api_entry = ctk.CTkEntry(frame, placeholder_text="Enter your API key")
        self.api_entry.pack(fill="x", padx=12, pady=(0, 4))
        saved_key = get_setting("api_key")
        if saved_key:
            self.api_entry.insert(0, saved_key)

        self.error_label = ctk.CTkLabel(frame, text="", text_color="#ef4444", font=("Segoe UI", 11))
        self.error_label.pack(anchor="w", padx=12)

        # --- Model ---
        ctk.CTkLabel(frame, text="Model", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
        model_row = ctk.CTkFrame(frame, fg_color="transparent")
        model_row.pack(fill="x", padx=12, pady=(0, 8))
        self.model_var = ctk.StringVar(value=get_setting("model", "gemini-2.5-flash"))
        self.model_dropdown = ctk.CTkOptionMenu(model_row, variable=self.model_var, values=[])
        self.model_dropdown.pack(side="left", fill="x", expand=True)
        self._update_model_list()

        # --- Info ---
        ctk.CTkLabel(frame, text="Hotkey: Ctrl+Shift+Z  |  Clipboard history: 30 days",
                      font=("Segoe UI", 10), text_color="gray").pack(anchor="w", padx=12, pady=(2, 2))

        ctk.CTkButton(frame, text="Save Settings", command=self._save).pack(pady=(6, 6))

        # --- Donation Section ---
        donate_frame = ctk.CTkFrame(self.win)
        donate_frame.pack(padx=20, pady=4, fill="x")

        ctk.CTkLabel(donate_frame, text="♥ Donation Settings", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(8, 2))

        ctk.CTkLabel(donate_frame, text="UPI Link (India)", font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=(2, 0))
        self.upi_link_entry = ctk.CTkEntry(donate_frame, placeholder_text="https://upi.pe/yourupiid@ybl")
        self.upi_link_entry.pack(fill="x", padx=12, pady=(0, 2))
        self.upi_link_entry.insert(0, get_donation_url())

        ctk.CTkLabel(donate_frame, text="UPI ID", font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=(2, 0))
        self.upi_id_entry = ctk.CTkEntry(donate_frame, placeholder_text="yourupiid@ybl")
        self.upi_id_entry.pack(fill="x", padx=12, pady=(0, 2))
        self.upi_id_entry.insert(0, get_upi_id())

        ctk.CTkLabel(donate_frame, text="International Link (Ko-fi / PayPal / etc.)", font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=(2, 0))
        self.intl_link_entry = ctk.CTkEntry(donate_frame, placeholder_text="https://ko-fi.com/yourname")
        self.intl_link_entry.pack(fill="x", padx=12, pady=(0, 2))
        self.intl_link_entry.insert(0, get_international_url())

        ctk.CTkLabel(donate_frame, text="Change these anytime in Settings", font=("Segoe UI", 9), text_color="gray").pack(anchor="w", padx=12, pady=(0, 6))

    def _on_provider_change(self):
        self._update_model_list()

    def _update_model_list(self):
        from config import PROVIDERS
        p = self.provider_var.get()
        info = PROVIDERS.get(p, PROVIDERS["gemini"])
        models = info["models"] if info["models"] else ["custom"]
        self.model_dropdown.configure(values=models)
        saved = get_setting("model")
        if saved in models:
            self.model_var.set(saved)
        else:
            self.model_var.set(info["default"])

    def _save(self):
        key = self.api_entry.get().strip()
        if not key:
            self.error_label.configure(text="API key is required.")
            return
        self.error_label.configure(text="")
        set_setting("api_key", key)
        set_setting("provider", self.provider_var.get())
        set_setting("model", self.model_var.get())
        set_setting("donation_url", self.upi_link_entry.get().strip())
        set_setting("upi_id", self.upi_id_entry.get().strip())
        set_setting("international_url", self.intl_link_entry.get().strip())
        self._saved = True
        from ai_actions import reset_client
        reset_client()
        self.close()

    def _on_close(self):
        if self.blocking and not self._saved:
            return
        self.close()

    def close(self):
        self.win.grab_release()
        self.win.destroy()
        if self.on_close:
            self.on_close()


class UpdateWindow:
    def __init__(self, version, download_url):
        self.download_url = download_url
        self.win = ctk.CTkToplevel()
        self.win.title(f"{APP_NAME} - Update Available")
        self.win.geometry("400x200")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.focus_force()
        self.win.grab_set()

        ctk.CTkLabel(self.win, text="⚡ Update Available", font=("Segoe UI", 18, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(self.win, text=f"Version {version} is ready!", font=("Segoe UI", 12)).pack()
        self.status_label = ctk.CTkLabel(self.win, text="", font=("Segoe UI", 11), text_color="gray")
        self.status_label.pack(pady=2)

        btn_row = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_row.pack(pady=(10, 0))
        ctk.CTkButton(btn_row, text="Download Update", command=self._download,
                       fg_color="#10b981", hover_color="#059669", height=34).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Later", command=self.close,
                       fg_color="#6b7280", hover_color="#4b5563", height=34).pack(side="left", padx=5)

        self.win.protocol("WM_DELETE_WINDOW", self.close)

    def _download(self):
        import tempfile
        self.status_label.configure(text="Downloading...")
        self.win.update()
        dest = os.path.join(tempfile.gettempdir(), "WinQuickAI_update.exe")
        threading.Thread(target=self._do_download, args=(dest,), daemon=True).start()

    def _do_download(self, dest):
        try:
            req = urllib.request.Request(self.download_url, headers={"User-Agent": "WinQuickAI"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            self.win.after(0, lambda: self._apply(dest))
        except Exception as e:
            self.win.after(0, lambda: self.status_label.configure(text=f"Failed: {str(e)[:50]}"))

    def _apply(self, dest):
        from updater import apply_update
        self.status_label.configure(text="Installing...")
        self.win.update()
        apply_update(dest)

    def close(self):
        self.win.grab_release()
        self.win.destroy()

class DonationWindow:
    def __init__(self):
        self.win = ctk.CTkToplevel()
        self.win.title(f"{APP_NAME} - Support")
        self.win.geometry("460x480")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.focus_force()
        self.win.grab_set()

        ctk.CTkLabel(self.win, text="♥ Support WinQuick AI", font=("Segoe UI", 20, "bold")).pack(pady=(18, 4))
        ctk.CTkLabel(self.win, text="Free for everyone. Your support keeps it going!",
                      font=("Segoe UI", 11), text_color="gray").pack()

        main = ctk.CTkFrame(self.win, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=8)

        # --- India: UPI ---
        upi_frame = ctk.CTkFrame(main)
        upi_frame.pack(fill="x", pady=4)
        ctk.CTkLabel(upi_frame, text="🇮🇳 India — UPI / PhonePe / GPay",
                      font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=12, pady=(10, 2))

        upi_id = get_upi_id()
        upi_link = get_donation_url()

        id_row = ctk.CTkFrame(upi_frame, fg_color="transparent")
        id_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(id_row, text=f"UPI ID: {upi_id}", font=("Segoe UI", 12)).pack(side="left")
        ctk.CTkButton(id_row, text="📋 Copy", width=60, height=24,
                       font=("Segoe UI", 10),
                       command=lambda: pyperclip.copy(upi_id)).pack(side="right")

        ctk.CTkButton(upi_frame, text="❤️ Donate via UPI",
                       font=("Segoe UI", 13, "bold"),
                       height=40, fg_color="#2563EB", hover_color="#1D4ED8",
                       command=lambda: webbrowser.open(upi_link)).pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(upi_frame, text="Opens your browser → scan QR or tap to pay",
                      font=("Segoe UI", 9), text_color="gray").pack(pady=(0, 8))

        # --- International ---
        intl_url = get_international_url()
        if intl_url:
            intl_frame = ctk.CTkFrame(main)
            intl_frame.pack(fill="x", pady=4)
            ctk.CTkLabel(intl_frame, text="🌍 International — Card / PayPal",
                          font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
            ctk.CTkButton(intl_frame, text="🌍 Donate via Card / PayPal",
                           font=("Segoe UI", 13, "bold"),
                           height=40, fg_color="#10b981", hover_color="#059669",
                           command=lambda: webbrowser.open(intl_url)).pack(fill="x", padx=12, pady=6)
        else:
            intl_frame = ctk.CTkFrame(main)
            intl_frame.pack(fill="x", pady=4)
            ctk.CTkLabel(intl_frame, text="🌍 International — Coming Soon",
                          font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
            ctk.CTkLabel(intl_frame, text="International payment support coming soon!",
                          font=("Segoe UI", 10), text_color="gray").pack(anchor="w", padx=12, pady=(0, 10))

        # --- I've Donated ---
        donated_frame = ctk.CTkFrame(main)
        donated_frame.pack(fill="x", pady=4)
        ctk.CTkButton(donated_frame, text="✓ I've Donated — Don't ask again",
                       font=("Segoe UI", 11),
                       height=34, fg_color="#6b7280", hover_color="#4b5563",
                       command=self._mark_donated).pack(fill="x", padx=12, pady=10)

        # --- Footer ---
        ctk.CTkButton(self.win, text="Close", command=self.close,
                       fg_color="#6b7280", hover_color="#4b5563",
                       height=34).pack(pady=(4, 12))

        self.win.protocol("WM_DELETE_WINDOW", self.close)

    def _mark_donated(self):
        mark_donated()
        ctk.CTkButton(self.win, text="✓ Thank You! ❤️", fg_color="#10b981",
                       hover_color="#059669", height=34, state="disabled").pack(pady=(4, 12))

    def close(self):
        self.win.grab_release()
        self.win.destroy()


class ClipboardHistoryWindow:
    def __init__(self):
        self.checkboxes = {}
        self.win = ctk.CTkToplevel()
        self.win.title(f"{APP_NAME} - Clipboard History")
        self.win.geometry("600x500")
        self.win.resizable(True, True)
        self.win.attributes("-topmost", True)
        self.win.focus_force()
        self.win.grab_set()

        top_bar = ctk.CTkFrame(self.win, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=(12, 2))
        top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top_bar, text="Clipboard History (30 days)",
                      font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")

        btn_row = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        btn_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.del_btn = ctk.CTkButton(btn_row, text="Delete Selected", command=self._delete_selected,
                                      fg_color="#ef4444", hover_color="#dc2626", height=30)
        self.del_btn.grid(row=0, column=0, padx=2)

        ctk.CTkButton(btn_row, text="Select All", command=self._select_all, height=30).grid(row=0, column=1, padx=2)
        ctk.CTkButton(btn_row, text="Deselect All", command=self._deselect_all, height=30).grid(row=0, column=2, padx=2)

        self.scroll = ctk.CTkScrollableFrame(self.win)
        self.scroll.pack(fill="both", expand=True, padx=15, pady=(8, 8))

        self._refresh()

        bottom = ctk.CTkFrame(self.win, fg_color="transparent")
        bottom.pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkLabel(bottom, text="Click checkbox to select | Copy button to restore",
                      font=("Segoe UI", 10), text_color="gray").pack(side="left")
        ctk.CTkButton(bottom, text="Close", command=self.close).pack(side="right")

    def _refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self.checkboxes.clear()

        items = get_clipboard_history(100)
        if not items:
            ctk.CTkLabel(self.scroll, text="No clipboard history yet.", text_color="gray").pack(pady=30)
            return

        for item in items:
            card = ctk.CTkFrame(self.scroll)
            card.pack(fill="x", pady=2)
            card.grid_columnconfigure(1, weight=1)

            var = ctk.BooleanVar()
            cb = ctk.CTkCheckBox(card, text="", variable=var, width=20, checkbox_width=18, checkbox_height=18)
            cb.grid(row=0, column=0, rowspan=3, padx=(6, 2))
            self.checkboxes[item["id"]] = var

            ts = item["timestamp"][:19] if item["timestamp"] else ""
            ctk.CTkLabel(card, text=f"  {ts}", font=("Segoe UI", 10, "bold"),
                          text_color="gray").grid(row=0, column=1, sticky="w", padx=2, pady=(4, 0))

            preview = item["text"][:150] + ("..." if len(item["text"]) > 150 else "")
            ctk.CTkLabel(card, text=preview, font=("Segoe UI", 10),
                          wraplength=400, justify="left").grid(row=1, column=1, sticky="w", padx=2)

            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.grid(row=2, column=1, sticky="e", padx=2, pady=(0, 4))
            ctk.CTkButton(btn_frame, text="Copy", width=55, height=22,
                           command=lambda t=item["text"]: pyperclip.copy(t)).pack(side="left", padx=1)
            ctk.CTkButton(btn_frame, text="Delete", width=55, height=22,
                           fg_color="#6b7280", hover_color="#ef4444",
                           command=lambda iid=item["id"]: self._delete_one(iid)).pack(side="left", padx=1)

        self.scroll.update_idletasks()

    def _delete_one(self, item_id):
        delete_clipboard_item(item_id)
        self._refresh()

    def _delete_selected(self):
        selected = [iid for iid, var in self.checkboxes.items() if var.get()]
        if not selected:
            return
        delete_clipboard_items(selected)
        self._refresh()

    def _select_all(self):
        for var in self.checkboxes.values():
            var.set(True)

    def _deselect_all(self):
        for var in self.checkboxes.values():
            var.set(False)

    def close(self):
        self.win.grab_release()
        self.win.destroy()


class HistoryWindow:
    def __init__(self):
        self.win = ctk.CTkToplevel()
        self.win.title(f"{APP_NAME} - AI History")
        self.win.geometry("600x500")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.focus_force()
        self.win.grab_set()

        ctk.CTkLabel(self.win, text="AI Response History", font=("Segoe UI", 20, "bold")).pack(pady=(15, 8))

        scroll = ctk.CTkScrollableFrame(self.win)
        scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        from database import get_history as db_get_history
        items = db_get_history()
        if not items:
            ctk.CTkLabel(scroll, text="No history yet.", text_color="gray").pack(pady=30)
        else:
            for item in items:
                card = ctk.CTkFrame(scroll)
                card.pack(fill="x", pady=4)
                action_label = next((a["label"] for a in ACTIONS if a["id"] == item["action"]), item["action"])
                ctk.CTkLabel(card, text=f"{action_label}  |  {item['timestamp'][:19]}",
                              font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
                preview = item["original_text"][:100] + ("..." if len(item["original_text"]) > 100 else "")
                ctk.CTkLabel(card, text=f"Text: {preview}", font=("Segoe UI", 10),
                              text_color="gray").pack(anchor="w", padx=10, pady=(0, 6))

        close_btn = ctk.CTkButton(self.win, text="Close", command=self.close)
        close_btn.pack(pady=(0, 12))

    def close(self):
        self.win.grab_release()
        self.win.destroy()
