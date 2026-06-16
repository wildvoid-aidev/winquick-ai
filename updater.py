import json
import os
import sys
import re
import urllib.request
import threading
import tempfile
import shutil
from config import APP_VERSION, GITHUB_REPO


def parse_version(v):
    return tuple(int(x) for x in re.split(r"[^\d]+", v) if x)

def get_latest_version():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WinQuickAI"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            tag = data.get("tag_name", "").lstrip("v")
            return tag, data
    except Exception:
        return None, None

def check_update(callback=None):
    def task():
        latest_version, release_data = get_latest_version()
        if latest_version and parse_version(latest_version) > parse_version(APP_VERSION):
            for asset in release_data.get("assets", []):
                if asset["name"] == "WinQuickAI.exe":
                    url = asset["browser_download_url"]
                    if callback:
                        callback(latest_version, url)
                    return
        if callback:
            callback(None, None)
    threading.Thread(target=task, daemon=True).start()

def download_update(url, dest_path, progress_callback=None):
    def task():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WinQuickAI"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(dest_path, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            progress_callback(downloaded / total)
            return True
        except Exception:
            return False
    thread = threading.Thread(target=task, daemon=True)
    thread.start()
    return thread

def apply_update(new_exe_path):
    current = sys.argv[0]
    if getattr(sys, "frozen", False):
        try:
            os.remove(current)
        except OSError:
            pass
        shutil.move(new_exe_path, current)
        os.startfile(current)
        sys.exit(0)
