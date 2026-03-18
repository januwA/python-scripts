import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import pyperclip
import requests
import win32api
import win32con
import win32gui
import win32com.client
import pythoncom
import re
import subprocess


# 配置
OLLAMA_API = "http://localhost:11434/api/chat"
MODEL_NAME = "gemma3:1b"
REQUEST_TIMEOUT = 30
RETRY_COUNT = 2
RETRY_DELAY = 1.0

WINDOW = None
STATUS_VAR = None
MODEL_VAR = None
INPUT_TEXT = None
OUTPUT_TEXT = None
TRANSLATE_BUTTON = None
COPY_BUTTON = None
MODEL_BOX = None
EVENT_QUEUE = queue.Queue()
TRAY = None


def translate_text(text):
    text = text.strip()
    if not text:
        return ""

    model_name = MODEL_VAR.get() if MODEL_VAR is not None else MODEL_NAME
    if model_name.startswith("[远程] "):
        model_name = model_name.replace("[远程] ", "", 1)
    if model_name.startswith("[本地] "):
        model_name = model_name.replace("[本地] ", "", 1)

    zh_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    en_count = len(re.findall(r'[a-zA-Z]', text))
    target_lang = "English" if zh_count > en_count else "Chinese"

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": f"You are a translation bot. Translate EVERYTHING to {target_lang}. No side comments."},
            {"role": "user", "content": "Translate to Chinese:\n\"\"\"\nSay hello to everyone.\n\"\"\""},
            {"role": "assistant", "content": "向大家打个招呼。"},
            {"role": "user", "content": "Translate to Chinese:\n\"\"\"\nRule 1: Never stop.\nRule 2: Keep going.\n\"\"\""},
            {"role": "assistant", "content": "规则 1：永不停止。\n规则 2：继续前进。"},
            {
                "role": "user",
                "content": f"Translate to {target_lang}:\n\"\"\"\n{text}\n\"\"\"",
            },
        ],
        "stream": False,
        "keep_alive": "5m",
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
        },
    }

    last_error = None
    for attempt in range(RETRY_COUNT + 1):
        try:
            response = requests.post(OLLAMA_API, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            result = response.json().get("message", {}).get("content", "").strip()
            return result
        except Exception as exc:
            last_error = exc
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY)
    raise last_error


def set_status(message):
    if STATUS_VAR is not None:
        STATUS_VAR.set(message)


def set_output(text):
    if OUTPUT_TEXT is None:
        return
    OUTPUT_TEXT.config(state="normal")
    OUTPUT_TEXT.delete("1.0", tk.END)
    OUTPUT_TEXT.insert(tk.END, text)
    OUTPUT_TEXT.config(state="disabled")


def fetch_models():
    local_models = []
    remote_models = []

    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        response.raise_for_status()
        local_models = [item.get("name", "") for item in response.json().get("models", []) if item.get("name")]
    except Exception:
        local_models = []

    try:
        result = subprocess.run(
            ["ollama", "list"],
            check=True,
            capture_output=True,
            text=True,
        )
        lines = result.stdout.splitlines()
        for line in lines[1:]:
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            if name.endswith("cloud"):
                remote_models.append(name)
            elif name not in local_models:
                local_models.append(name)
    except Exception:
        pass

    return local_models, remote_models


def refresh_models():
    if MODEL_VAR is None:
        return

    set_status("刷新模型中...")

    def worker():
        local_models, remote_models = fetch_models()
        local_set = set(local_models)
        remote_filtered = [name for name in remote_models if name and name not in local_set]

        local_options = []
        remote_options = []
        for name in local_models:
            if name.endswith("cloud"):
                remote_options.append(name)
            else:
                local_options.append(name)
        remote_options += sorted(remote_filtered)

        options = [f"[本地] {name}" for name in local_options]
        options += [f"[远程] {name}" for name in sorted(set(remote_options))]
        if not options:
            options = [MODEL_NAME]

        def update_ui():
            if MODEL_BOX is None:
                return
            MODEL_BOX["values"] = options
            current = MODEL_VAR.get()
            if current not in options:
                MODEL_VAR.set(options[0])
            set_status("模型已刷新。")

        WINDOW.after(0, update_ui)

    threading.Thread(target=worker, daemon=True).start()


def run_translation():
    if TRANSLATE_BUTTON is None:
        return
    text = INPUT_TEXT.get("1.0", tk.END)
    if not text.strip():
        set_status("请输入要翻译的文本。")
        return

    TRANSLATE_BUTTON.config(state="disabled")
    COPY_BUTTON.config(state="disabled")
    set_status("翻译中...")

    def worker():
        start_time = time.time()
        try:
            result = translate_text(text)
            if not result:
                message = "模型返回内容为空。"
            else:
                duration = time.time() - start_time
                message = f"完成，耗时 {duration:.2f}s"
        except requests.exceptions.ConnectionError:
            result = "错误: 无法连接到 Ollama 服务。"
            message = "连接失败"
        except Exception as exc:
            result = f"翻译过程中出现未知错误: {exc}"
            message = "翻译失败"

        def update_ui():
            set_output(result)
            set_status(message)
            TRANSLATE_BUTTON.config(state="normal")
            COPY_BUTTON.config(state="normal")

        WINDOW.after(0, update_ui)

    threading.Thread(target=worker, daemon=True).start()


def copy_output():
    text = OUTPUT_TEXT.get("1.0", tk.END).strip()
    if text:
        pyperclip.copy(text)
        set_status("已复制译文到剪贴板。")


def speak_text(text):
    if not text.strip():
        set_status("没有可朗读的内容。")
        return

    def worker():
        try:
            pythoncom.CoInitialize()
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
            WINDOW.after(0, lambda: set_status("朗读完成。"))
        except Exception as exc:
            WINDOW.after(0, lambda: set_status(f"朗读失败: {exc}"))
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    threading.Thread(target=worker, daemon=True).start()


def speak_input():
    text = INPUT_TEXT.get("1.0", tk.END)
    speak_text(text)


def speak_output():
    text = OUTPUT_TEXT.get("1.0", tk.END)
    speak_text(text)


def hide_window():
    if WINDOW is not None:
        WINDOW.withdraw()


def show_window():
    if WINDOW is None:
        return
    WINDOW.deiconify()
    WINDOW.lift()
    WINDOW.focus_force()


def build_window():
    global WINDOW, STATUS_VAR, MODEL_VAR, INPUT_TEXT, OUTPUT_TEXT, TRANSLATE_BUTTON, COPY_BUTTON, MODEL_BOX
    WINDOW = tk.Tk()
    WINDOW.title("Ollama 翻译助手")
    WINDOW.geometry("720x520")
    WINDOW.protocol("WM_DELETE_WINDOW", hide_window)

    STATUS_VAR = tk.StringVar(value="就绪")
    MODEL_VAR = tk.StringVar(value=f"[本地] {MODEL_NAME}")

    frame = tk.Frame(WINDOW, padx=10, pady=10)
    frame.pack(fill="both", expand=True)

    top_row = tk.Frame(frame)
    top_row.pack(fill="x")
    tk.Label(top_row, text="模型").pack(side="left")
    MODEL_BOX = ttk.Combobox(top_row, textvariable=MODEL_VAR, width=32, state="readonly")
    MODEL_BOX.pack(side="left", padx=6)
    tk.Button(top_row, text="刷新模型", command=refresh_models).pack(side="left")

    tk.Label(frame, text="输入").pack(anchor="w", pady=(8, 0))
    INPUT_TEXT = scrolledtext.ScrolledText(frame, height=10, wrap=tk.WORD)
    INPUT_TEXT.pack(fill="both", expand=True)
    INPUT_TEXT.bind("<Control-Return>", lambda event: run_translation())

    button_row = tk.Frame(frame)
    button_row.pack(fill="x", pady=6)
    TRANSLATE_BUTTON = tk.Button(button_row, text="翻译", command=run_translation)
    TRANSLATE_BUTTON.pack(side="left")
    COPY_BUTTON = tk.Button(button_row, text="复制译文", command=copy_output)
    COPY_BUTTON.pack(side="left", padx=8)
    tk.Button(button_row, text="朗读输入", command=speak_input).pack(side="left", padx=8)
    tk.Button(button_row, text="朗读译文", command=speak_output).pack(side="left", padx=8)
    tk.Label(frame, text="输出").pack(anchor="w")
    OUTPUT_TEXT = scrolledtext.ScrolledText(frame, height=12, wrap=tk.WORD)
    OUTPUT_TEXT.config(state="disabled")
    OUTPUT_TEXT.pack(fill="both", expand=True)

    status_bar = tk.Label(frame, textvariable=STATUS_VAR, anchor="w")
    status_bar.pack(fill="x", pady=(6, 0))

    WINDOW.after(0, WINDOW.focus_force)
    refresh_models()


class TrayThread(threading.Thread):
    def __init__(self, event_queue):
        super().__init__(daemon=True)
        self.event_queue = event_queue
        self.hwnd = None

    def run(self):
        message_map = {
            win32con.WM_COMMAND: self.on_command,
            win32con.WM_DESTROY: self.on_destroy,
            win32con.WM_USER + 20: self.on_notify,
        }
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "OllamaTranslatorTray"
        wc.lpfnWndProc = message_map
        try:
            win32gui.RegisterClass(wc)
        except win32gui.error:
            pass

        self.hwnd = win32gui.CreateWindow(
            wc.lpszClassName,
            "OllamaTranslator",
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            wc.hInstance,
            None,
        )

        icon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        nid = (
            self.hwnd,
            0,
            win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
            win32con.WM_USER + 20,
            icon,
            "Ollama 翻译助手",
        )
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        win32gui.PumpMessages()

    def stop(self):
        if self.hwnd is not None:
            win32gui.PostMessage(self.hwnd, win32con.WM_DESTROY, 0, 0)

    def on_notify(self, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_LBUTTONUP:
            self.event_queue.put("show")
        elif lparam == win32con.WM_RBUTTONUP:
            self.show_menu()
        return True

    def show_menu(self):
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1, "打开")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 2, "退出")
        x, y = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        cmd = win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON | win32con.TPM_RETURNCMD,
            x,
            y,
            0,
            self.hwnd,
            None,
        )
        if cmd == 1:
            self.event_queue.put("show")
        elif cmd == 2:
            self.event_queue.put("quit")
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)

    def on_command(self, hwnd, msg, wparam, lparam):
        return True

    def on_destroy(self, hwnd, msg, wparam, lparam):
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self.hwnd, 0))
        win32gui.PostQuitMessage(0)
        return True


def process_events():
    try:
        while True:
            event = EVENT_QUEUE.get_nowait()
            if event == "show":
                show_window()
            elif event == "quit":
                if TRAY is not None:
                    TRAY.stop()
                if WINDOW is not None:
                    WINDOW.destroy()
    except queue.Empty:
        pass

    if WINDOW is not None:
        WINDOW.after(100, process_events)


def start_app():
    global TRAY
    build_window()
    show_window()
    TRAY = TrayThread(EVENT_QUEUE)
    TRAY.start()
    process_events()
    WINDOW.mainloop()


if __name__ == "__main__":
    start_app()
