import ctypes
import ctypes.wintypes as wintypes
import threading
import time
import pyperclip
from config import CLIPBOARD_MONITOR_INTERVAL
from database import save_clipboard

# --- Clipboard capture ---

VK_CONTROL = 0x11
VK_C = 0x43
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32

def send_ctrl_c():
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_C, 0, 0, 0)
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

def capture_selected_text():
    for attempt in range(3):
        try:
            old = pyperclip.paste()
            pyperclip.copy("_WQ_CLIP_CHK_")
            time.sleep(0.05)
            send_ctrl_c()
            time.sleep(0.1)
            text = pyperclip.paste()
            pyperclip.copy(old)
            if text and text != "_WQ_CLIP_CHK_":
                return text.strip()
        except Exception:
            time.sleep(0.05)
    return ""

# --- Global hotkey: message-only window + background thread ---

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
VK_Z = 0x5A
HOTKEY_ID = 1
HWND_MESSAGE = wintypes.HWND(-3)

WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_longlong,
    ctypes.c_void_p,
    ctypes.c_uint,
    ctypes.c_void_p,
    ctypes.c_void_p
)

class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]

kernel32 = ctypes.windll.kernel32

user32.DefWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
user32.DefWindowProcW.restype = ctypes.c_longlong
user32.GetMessageW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
user32.GetMessageW.restype = ctypes.c_int
user32.PostThreadMessageW.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
user32.PostThreadMessageW.restype = ctypes.c_int
user32.RegisterClassW.argtypes = [ctypes.c_void_p]
user32.RegisterClassW.restype = wintypes.ATOM
user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
user32.RegisterHotKey.restype = ctypes.c_int
user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.UnregisterHotKey.restype = ctypes.c_int
user32.CreateWindowExW.argtypes = [ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p,
                                    ctypes.c_uint, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_void_p,
                                    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
user32.CreateWindowExW.restype = ctypes.c_void_p
user32.DestroyWindow.argtypes = [ctypes.c_void_p]
user32.DestroyWindow.restype = ctypes.c_int

_hotkey_callback = None
_hwnd = None
_thread = None
_ready = threading.Event()

@WNDPROC
def _wndproc(hwnd, msg, wparam, lparam):
    if msg == WM_HOTKEY and wparam == HOTKEY_ID:
        if _hotkey_callback:
            _hotkey_callback()
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

def _message_loop():
    _ready.set()
    msg = wintypes.MSG()
    while True:
        ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
        if ret <= 0:
            break
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
    if _hwnd:
        user32.UnregisterHotKey(_hwnd, HOTKEY_ID)
        user32.DestroyWindow(_hwnd)

def start_hotkey_listener(callback):
    global _hotkey_callback, _hwnd, _thread
    if _thread and _thread.is_alive():
        return

    _hotkey_callback = callback
    hinstance = kernel32.GetModuleHandleW(None)
    class_name = "WinQuickAI_HKWin_v3"

    wc = WNDCLASS()
    wc.style = 0
    wc.lpfnWndProc = ctypes.cast(_wndproc, ctypes.c_void_p).value
    wc.cbClsExtra = 0
    wc.cbWndExtra = 0
    wc.hInstance = hinstance
    wc.hIcon = None
    wc.hCursor = None
    wc.hbrBackground = None
    wc.lpszMenuName = None
    wc.lpszClassName = class_name
    user32.RegisterClassW(ctypes.byref(wc))

    _hwnd = user32.CreateWindowExW(0, class_name, "", 0, 0, 0, 0, 0,
                                   HWND_MESSAGE, None, hinstance, None)
    if not _hwnd:
        return False

    ok = user32.RegisterHotKey(_hwnd, HOTKEY_ID,
                                MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_Z)
    if not ok:
        user32.DestroyWindow(_hwnd)
        _hwnd = None
        return False

    _thread = threading.Thread(target=_message_loop, daemon=True)
    _thread.start()
    _ready.wait(timeout=2)
    return True

def stop_hotkey_listener():
    if _thread and _thread.is_alive():
        user32.PostThreadMessageW(_thread.ident, WM_QUIT, 0, 0)

# --- Clipboard monitor ---

_clipboard_monitor_running = False
_clipboard_monitor_thread = None
_last_clipboard_text = ""

def _clipboard_monitor():
    global _last_clipboard_text
    while _clipboard_monitor_running:
        try:
            text = pyperclip.paste()
            if text and text != _last_clipboard_text:
                _last_clipboard_text = text
                if len(text.strip()) > 3:
                    save_clipboard(text)
        except Exception:
            pass
        time.sleep(CLIPBOARD_MONITOR_INTERVAL)

def start_clipboard_monitor():
    global _clipboard_monitor_running, _clipboard_monitor_thread, _last_clipboard_text
    if _clipboard_monitor_running:
        return
    _clipboard_monitor_running = True
    try:
        _last_clipboard_text = pyperclip.paste()
    except Exception:
        _last_clipboard_text = ""
    _clipboard_monitor_thread = threading.Thread(target=_clipboard_monitor, daemon=True)
    _clipboard_monitor_thread.start()

def stop_clipboard_monitor():
    global _clipboard_monitor_running
    _clipboard_monitor_running = False
