import customtkinter as ctk
import pyperclip
import threading
import webbrowser
from config import ACTIONS, APP_NAME
from database import save_history, get_setting, set_setting, get_clipboard_history, delete_clipboard_item, delete_clipboard_items, has_donated, mark_donated, get_donation_url

class PopupWindow:
    def __init__(self, selected_text, on_action, on_chat):
        self.result_text = ""
        self.on_action = on_action
        self.on_chat = on_chat
        self.selected_text = selected_text

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

        title = ctk.CTkLabel(self.win, text=APP_NAME, font=("Segoe UI", 22, "bold"))
        title.grid(row=0, column=0, pady=(15, 2))

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

        self.result_box = ctk.CTkTextbox(self.win, wrap="word", font=("Segoe UI", 11))
        self.result_box.grid(row=3, column=0, padx=15, pady=(0, 5), sticky="nsew")
        self.result_box.insert("1.0", "Ask anything above or use Quick Actions...")
        self.result_box.configure(state="disabled")

        bottom = ctk.CTkFrame(self.win, fg_color="transparent")
        bottom.grid(row=4, column=0, padx=15, pady=(0, 12), sticky="ew")
        bottom.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(bottom, text="Copy Result", command=self._copy).grid(row=0, column=0, padx=3)
        ctk.CTkButton(bottom, text="Save to Clipboard", command=self._save_to_clip).grid(row=0, column=1, padx=3)
        ctk.CTkButton(bottom, text="Close", command=self.close).grid(row=0, column=2, padx=3)

    def _do_chat(self):
        text = self.input_entry.get().strip()
        if not text:
            return
        self._set_result("Thinking...")
        self.win.update()

        def process():
            result = self.on_chat(text)
            save_history("chat", text, result)
            self.win.after(0, lambda: self._set_result(result))

        threading.Thread(target=process, daemon=True).start()

    def _run_action(self, action_id):
        text = self.input_entry.get().strip()
        if not text:
            self._set_result("Type or select some text first.")
            return

        api_key = get_setting("api_key")
        if not api_key:
            self._set_result("Set your Gemini API key in Settings first.")
            return

        self._set_result("Processing...")
        self.win.update()

        def process():
            result = self.on_action(action_id, text)
            save_history(action_id, text, result)
            self.win.after(0, lambda: self._set_result(result))

        threading.Thread(target=process, daemon=True).start()

    def _set_result(self, text):
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
        self.result_box.configure(state="disabled")
        self.result_text = text

    def _copy(self):
        if self.result_text:
            pyperclip.copy(self.result_text)

    def _save_to_clip(self):
        if self.result_text:
            pyperclip.copy(self.result_text)

    def close(self):
        self.win.destroy()


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

        status = "♥ Thank You Supporter!" if has_donated() else "♡ Free User — Support the Project"
        ctk.CTkLabel(donate_frame, text=status, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(8, 2))

        ctk.CTkLabel(donate_frame, text="Your Payment Link (change this to your PayPal/UPI/etc):",
                      font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=(2, 2))
        self.donate_url_entry = ctk.CTkEntry(donate_frame, placeholder_text="https://your-payment-link.com")
        self.donate_url_entry.pack(fill="x", padx=12, pady=(0, 4))
        self.donate_url_entry.insert(0, get_donation_url())

        donate_btn_row = ctk.CTkFrame(donate_frame, fg_color="transparent")
        donate_btn_row.pack(fill="x", padx=12, pady=(2, 8))
        donate_btn_row.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(donate_btn_row, text="♥ Donate Now", command=self._open_donation,
                       fg_color="#f59e0b", hover_color="#d97706", text_color="black",
                       height=34).grid(row=0, column=0, padx=2)
        ctk.CTkButton(donate_btn_row, text="I've Donated ✓", command=self._mark_donated,
                       fg_color="#10b981", hover_color="#059669", height=34).grid(row=0, column=1, padx=2)

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
        set_donation_url(self.donate_url_entry.get().strip())
        self._saved = True
        from ai_actions import reset_client
        reset_client()
        self.close()

    def _open_donation(self):
        url = self.donate_url_entry.get().strip() or get_donation_url()
        webbrowser.open(url)

    def _mark_donated(self):
        mark_donated()
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


class DonationWindow:
    def __init__(self):
        self.win = ctk.CTkToplevel()
        self.win.title(f"{APP_NAME} - Support")
        self.win.geometry("400x320")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.focus_force()
        self.win.grab_set()

        ctk.CTkLabel(self.win, text="♥  Support WinQuick AI", font=("Segoe UI", 20, "bold")).pack(pady=(25, 5))
        ctk.CTkLabel(self.win, text="You've used the app a few times now!", font=("Segoe UI", 12)).pack()
        ctk.CTkLabel(self.win, text="If you find it useful, consider supporting the project.",
                      font=("Segoe UI", 11)).pack(pady=2)
        ctk.CTkLabel(self.win, text="Your support keeps the app free and updated.",
                      font=("Segoe UI", 11)).pack(pady=(0, 8))

        ctk.CTkLabel(self.win, text="", font=("Segoe UI", 1)).pack()

        url = get_donation_url()
        ctk.CTkButton(self.win, text="♥  Donate Now",
                       command=lambda: webbrowser.open(url),
                       fg_color="#f59e0b", hover_color="#d97706",
                       text_color="black", height=40,
                       font=("Segoe UI", 13, "bold")).pack(pady=6, padx=40, fill="x")

        ctk.CTkButton(self.win, text="✓  I've Already Donated",
                       command=self._donated,
                       fg_color="#10b981", hover_color="#059669",
                       height=34).pack(pady=3, padx=40, fill="x")

        ctk.CTkButton(self.win, text="Remind Later",
                       command=self.close,
                       fg_color="#6b7280", hover_color="#4b5563",
                       height=34).pack(pady=3, padx=40, fill="x")

        self.win.protocol("WM_DELETE_WINDOW", self.close)

    def _donated(self):
        mark_donated()
        self.close()

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
