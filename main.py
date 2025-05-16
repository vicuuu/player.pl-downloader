import eel
import threading
import subprocess
import os
import sys
import io
import shlex
import re
import tkinter
import tkinter.filedialog as filedialog

from utils.core import run
from utils.auth import login as player_login, logout, load_session, player_login as get_user_info
from utils.config import CONFIG

buffer = io.StringIO()
sys.stdout = sys.stderr = buffer

eel.init("web")

@eel.expose
def choose_folder():
    root = tkinter.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    folder = filedialog.askdirectory()
    return folder or ""

@eel.expose
def start_fetching(url_list):
    if not url_list or not isinstance(url_list, list) or not url_list[0].startswith("http"):
        eel.update_status("🚫 Wprowadź poprawny URL")
        return
    threading.Thread(target=fetching_worker, args=(url_list,), daemon=True).start()

@eel.expose
def login_player():
    threading.Thread(target=login_worker, daemon=True).start()

@eel.expose
def logout_user():
    logout()

@eel.expose
def check_logged_in():
    session = load_session()
    if session.get("access_token") and session.get("headers"):
        try:
            user = get_user_info()
            eel.on_login_success(user["username"])
        except Exception as e:
            eel.update_status(f"ℹ️ Brak aktywnej sesji: {e}")

def login_worker():
    try:
        eel.update_status("🔐 Rozpoczynanie logowania")
        user_info = player_login()
        eel.on_login_success(user_info["username"])
    except:
        pass

def fetching_worker(url_list):
    try:
        eel.update_status("🚀 Rozpoczynanie przechwytywania")
        run(url_list)
        with open(CONFIG["OUTPUT"]["CMD_FILE"], encoding="utf-8") as f:
            for cmd in f:
                eel.update_status(cmd.strip())
        with open(CONFIG["OUTPUT"]["FAILED_FILE"], encoding="utf-8") as f:
            failed = f.readlines()
        if failed:
            for fail in failed:
                eel.update_status(f"❌ Niepowodzenie: {fail.strip()}")
        else:
            eel.update_status("✅ Sukces!")
        eel.update_progress(1.0)
    except Exception as e:
        eel.update_status(str(e))

@eel.expose
def load_commands():
    try:
        with open(CONFIG["OUTPUT"]["CMD_FILE"], encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

@eel.expose
def start_download(cmd_list, resolution, audio, save_folder):
    if not save_folder:
        eel.update_status("🚫 Wybierz folder zapisu!")
        return
    if not cmd_list or not any(cmd.strip() for cmd in cmd_list):
        eel.update_status("🚫 Brak poleceń do pobrania!")
        return
    threading.Thread(
        target=download_worker,
        args=(cmd_list, resolution, audio, save_folder),
        daemon=True
    ).start()

def download_worker(cmd_list, resolution, audio, save_folder):
    eel.update_status(f"🚀 Rozpoczynam pobieranie do: {save_folder}")
    total = len(cmd_list)
    if getattr(sys, 'frozen', False):
        bin_dir = os.path.join(sys._MEIPASS, 'bin')  
    else:
        bin_dir = os.path.abspath("bin")  

    lang_map = {"polski": "pol", "angielski": "eng"}
    lang_code = lang_map.get(audio.lower(), audio)

    progress_re = re.compile(r"(\d{1,3}(?:\.\d+)?)%")

    for idx, raw_cmd in enumerate(cmd_list, start=1):
        eel.update_status(f"▶️ Przygotowuję zadanie {idx}/{total}")
        parts = shlex.split(raw_cmd)

        exe, *args = parts

        args = args + [
            "--save-dir", save_folder,
            "--tmp-dir", os.path.join(save_folder, "tmp"),
            "-sv", f"res={resolution}",
            "-sa", f"lang='{lang_code}|{lang_code.upper()}':for=best2",
            "-M", "format=mkv:muxer=mkvmerge",
            "--no-log"
        ]
        

        eel.update_status(f"▶️ Wykonuję: {exe} {' '.join(args)}")
        full_exe = os.path.join(bin_dir, exe)

        try:
            proc = subprocess.Popen(
                [full_exe] + args,
                cwd=bin_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False
            )
            task_progress = 0.0
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                text = line.decode(errors="ignore").strip()
                eel.update_status(text)
                m = progress_re.search(text)
                if m:
                    task_progress = float(m.group(1)) / 100.0
                    overall = ((idx - 1) + task_progress) / total
                    eel.update_progress(overall)
            proc.wait()
            eel.update_status(f"✅ Pobieranie {idx}/{total} zakończone")
        except Exception as e:
            eel.update_status(f"❌ Błąd zadania {idx}/{total}: {e}")
        eel.update_progress(idx / total)

    eel.update_status("✅ Wszystkie zadania zakończone")
    eel.update_progress(1.0)

@eel.expose
def overwrite_commands(new_cmds):
    try:
        with open(CONFIG["OUTPUT"]["CMD_FILE"], "w", encoding="utf-8") as f:
            f.write("\n".join(new_cmds) + "\n")
    except Exception as e:
        eel.update_status(f"❌ Błąd zapisu poleceń: {e}")



if __name__ == "__main__":
    eel.start("index.html", size=(600, 900))
