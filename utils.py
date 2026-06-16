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
INPUT_KEYBOARD = 1

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
MARKER = "_WQ_TXT_"

class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_void_p)]

class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_void_p)]

class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT), ("hi", _HARDWAREINPUT)]

class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUT_UNION)]

def send_ctrl_c():
    events = []
    events.append(_INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=_KEYBDINPUT(VK_CONTROL, 0, 0, 0, None))))
    events.append(_INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=_KEYBDINPUT(VK_C, 0, 0, 0, None))))
    events.append(_INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=_KEYBDINPUT(VK_C, 0, KEYEVENTF_KEYUP, 0, None))))
    events.append(_INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=_KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, None))))
    inputs = (_INPUT * 4)(*events)
    user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(_INPUT))

def copy_with_keybd_event():
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_C, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

def copy_with_wm_copy():
    fg = user32.GetForegroundWindow()
    if not fg:
        return
    target_tid = user32.GetWindowThreadProcessId(fg, None)
    if not target_tid:
        return
    class _GUITHREADINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("hwndActive", wintypes.HWND),
            ("hwndFocus", wintypes.HWND),
            ("hwndCapture", wintypes.HWND),
            ("hwndMenuOwner", wintypes.HWND),
            ("hwndMoveSize", wintypes.HWND),
            ("hwndCaret", wintypes.HWND),
            ("rcCaret", wintypes.RECT),
        ]
    gti = _GUITHREADINFO()
    gti.cbSize = ctypes.sizeof(_GUITHREADINFO)
    if user32.GetGUIThreadInfo(target_tid, ctypes.byref(gti)) and gti.hwndFocus:
        user32.SendMessageW(gti.hwndFocus, 0x0301, 0, 0)

def _set_marker():
    try:
        pyperclip.copy(MARKER)
        time.sleep(0.05)
        if pyperclip.paste() != MARKER:
            user32.OpenClipboard(None)
            user32.EmptyClipboard()
            user32.CloseClipboard()
            pyperclip.copy(MARKER)
            time.sleep(0.05)
    except:
        pass

def _try_copy_methods():
    send_ctrl_c()
    time.sleep(0.15)
    text = pyperclip.paste()
    if text and text.strip() != MARKER:
        return text
    copy_with_keybd_event()
    time.sleep(0.15)
    text = pyperclip.paste()
    if text and text.strip() != MARKER:
        return text
    copy_with_wm_copy()
    time.sleep(0.15)
    text = pyperclip.paste()
    if text and text.strip() != MARKER:
        return text
    return ""

def _is_console_window(hwnd):
    buf = ctypes.create_unicode_buffer(128)
    user32.GetClassNameW(hwnd, buf, 128)
    return buf.value in ("ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS", "WindowsTerminal")

def _force_accessibility(hwnd):
    if not hwnd:
        return
    try:
        oleacc = ctypes.windll.oleacc
        OBJID_CLIENT = 0xFFFFFFFC
        pAcc = ctypes.c_void_p()
        oleacc.AccessibleObjectFromWindow(
            hwnd, OBJID_CLIENT,
            ctypes.byref(_IID_IAccessible),
            ctypes.byref(pAcc)
        )
        if pAcc and pAcc.value:
            _com_call(pAcc, _Release, _ReleaseFunc)
        time.sleep(0.1)
    except:
        pass

def capture_selected_text():
    text = get_selected_text_uia()
    if text:
        return text
    is_console = _is_console_window(user32.GetForegroundWindow())
    old = ""
    try:
        old = pyperclip.paste()
        if is_console and old and old.strip() != MARKER:
            return old.strip()
        _set_marker()
        text = _try_copy_methods()
        if text and text.strip() != MARKER:
            if old:
                pyperclip.copy(old)
            return text.strip()
    except Exception:
        pass
    return ""

# --- UI Automation text capture (works with Chrome, all Windows apps) ---

class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]

_CLSID_CUIAutomation = _GUID(
    0xFF48DBA4, 0x60EF, 0x4201,
    (0xAA, 0x87, 0x54, 0x10, 0x3E, 0xEF, 0x59, 0x4E)
)
_IID_IUIAutomation = _GUID(
    0x30CBE57D, 0xD9D0, 0x452A,
    (0xAB, 0x13, 0x7A, 0xC5, 0xAC, 0x48, 0x25, 0xEE)
)

_IID_IAccessible = _GUID(
    0x618736E0, 0x3C3D, 0x11CF,
    (0x81, 0x0C, 0x00, 0xAA, 0x00, 0x38, 0x9B, 0x71)
)

_COINIT_APARTMENTTHREADED = 2
_CLSCTX_INPROC_SERVER = 1
_UIA_TextPatternId = 10014
_UIA_ValuePatternId = 10002

_ReleaseFunc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)
_GetFocusedElementFunc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
)
_GetCurrentPatternFunc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)
)
_GetSelectionFunc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
)
_GetTextFunc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)
)
_GetValueFunc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
)

_UIA_GetFocusedElement = 8
_UIA_ElementFromHandle = 6
_UIAElement_GetCurrentPattern = 16
_TextPattern_GetSelection = 3
_TextRange_GetText = 12
_ValuePattern_Value = 5
_Release = 2

_ElementFromHandleFunc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, wintypes.HWND, ctypes.POINTER(ctypes.c_void_p)
)

def _com_call(obj, index, functype, *args):
    vtable = ctypes.cast(
        ctypes.cast(obj, ctypes.POINTER(ctypes.c_void_p))[0],
        ctypes.POINTER(ctypes.c_void_p)
    )
    func = ctypes.cast(vtable[index], functype)
    return func(obj, *args)

def _uia_get_text_from_element(pElement, oleaut32):
    if not pElement or not pElement.value:
        return None
    # Try TextPattern (selected text)
    pPat = ctypes.c_void_p()
    hr = _com_call(pElement, _UIAElement_GetCurrentPattern, _GetCurrentPatternFunc,
                   _UIA_TextPatternId, ctypes.byref(pPat))
    if hr >= 0 and pPat.value:
        text = None
        pSa = ctypes.c_void_p()
        pRange = ctypes.c_void_p()
        try:
            hr = _com_call(pPat, _TextPattern_GetSelection, _GetSelectionFunc, ctypes.byref(pSa))
            if hr >= 0 and pSa.value:
                ubound = wintypes.LONG(-1)
                oleaut32.SafeArrayGetUBound(pSa, 1, ctypes.byref(ubound))
                if ubound.value >= 0:
                    idx = wintypes.LONG(0)
                    hr = oleaut32.SafeArrayGetElement(pSa, ctypes.byref(idx), ctypes.byref(pRange))
                    if hr >= 0 and pRange.value:
                        pBstr = ctypes.c_void_p()
                        hr = _com_call(pRange, _TextRange_GetText, _GetTextFunc, -1, ctypes.byref(pBstr))
                        if hr >= 0 and pBstr.value:
                            t = ctypes.cast(pBstr, ctypes.c_wchar_p).value or ""
                            oleaut32.SysFreeString(pBstr)
                            if t.strip():
                                text = t.strip()
        finally:
            if pRange and pRange.value:
                _com_call(pRange, _Release, _ReleaseFunc)
            if pSa and pSa.value:
                oleaut32.SafeArrayDestroy(pSa)
            if pPat and pPat.value:
                _com_call(pPat, _Release, _ReleaseFunc)
        if text:
            return text
    # Fallback: try ValuePattern (full field text)
    pVal = ctypes.c_void_p()
    hr = _com_call(pElement, _UIAElement_GetCurrentPattern, _GetCurrentPatternFunc,
                   _UIA_ValuePatternId, ctypes.byref(pVal))
    if hr >= 0 and pVal.value:
        try:
            pBstr = ctypes.c_void_p()
            hr = _com_call(pVal, _ValuePattern_Value, _GetValueFunc, ctypes.byref(pBstr))
            if hr >= 0 and pBstr.value:
                t = ctypes.cast(pBstr, ctypes.c_wchar_p).value or ""
                oleaut32.SysFreeString(pBstr)
                if t.strip():
                    return t.strip()
        finally:
            if pVal and pVal.value:
                _com_call(pVal, _Release, _ReleaseFunc)
    return None

def get_selected_text_uia():
    ole32 = ctypes.windll.ole32
    oleaut32 = ctypes.windll.oleaut32
    pUIA = ctypes.c_void_p()
    pElement = ctypes.c_void_p()
    co_inited = False
    try:
        hr = ole32.CoInitializeEx(None, _COINIT_APARTMENTTHREADED)
        if hr < 0:
            return ""
        co_inited = True
        hr = ole32.CoCreateInstance(
            ctypes.byref(_CLSID_CUIAutomation), None,
            _CLSCTX_INPROC_SERVER,
            ctypes.byref(_IID_IUIAutomation),
            ctypes.byref(pUIA)
        )
        if hr < 0 or not pUIA.value:
            return ""
        fg = user32.GetForegroundWindow()
        _force_accessibility(fg)
        hr = _com_call(pUIA, _UIA_GetFocusedElement, _GetFocusedElementFunc, ctypes.byref(pElement))
        if hr >= 0 and pElement.value:
            text = _uia_get_text_from_element(pElement, oleaut32)
            if text:
                return text
        if fg:
            if pElement.value:
                _com_call(pElement, _Release, _ReleaseFunc)
                pElement.value = None
            hr = _com_call(pUIA, _UIA_ElementFromHandle, _ElementFromHandleFunc,
                          fg, ctypes.byref(pElement))
            if hr >= 0 and pElement.value:
                text = _uia_get_text_from_element(pElement, oleaut32)
                if text:
                    return text
        return ""
    except:
        return ""
    finally:
        if pElement and pElement.value:
            _com_call(pElement, _Release, _ReleaseFunc)
        if pUIA and pUIA.value:
            _com_call(pUIA, _Release, _ReleaseFunc)
        if co_inited:
            ole32.CoUninitialize()

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
