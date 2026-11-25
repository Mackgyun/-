"""청년의사 브리핑 PC 알림 프로그램.

작업 표시줄 오른쪽 아래(트레이)에 떠 있다가, 브리핑 서버에 새 알림이 생기면 Windows 알림을 띄운다.
브라우저와 상관없이 동작하고, Windows를 켤 때 자동으로 실행된다.

서버와는 롱폴링으로 연결한다: GET /api/device/alerts?after=<마지막 번호> 가 새 알림이 생길 때까지(최대 25초)
기다렸다가 돌려준다. 로그인은 처음 한 번만 하고, 서버가 준 기기 토큰을 Windows 보호 저장소(DPAPI)로
암호화해 %APPDATA%\\ChungnyunBriefing\\config.json 에 둔다. 비밀번호는 저장하지 않는다.
"""

from __future__ import annotations

import base64
import ctypes
import ctypes.wintypes as wt
import json
import logging
import os
import pathlib
import platform
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
import winreg
from datetime import datetime

APP_NAME = "청년의사 브리핑"
APP_ID = "Chungnyun.Briefing.Notifier"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "ChungnyunBriefing"
HOME = pathlib.Path(os.environ.get("APPDATA", pathlib.Path.home())) / "ChungnyunBriefing"
CONFIG = HOME / "config.json"
DEFAULT_SERVER = "http://localhost:8000"
WAIT = 25           # 서버가 알림을 기다려 주는 시간(초)
STALE_MIN = 30      # 이보다 오래된 알림이 여러 건 밀려 있으면 '놓친 알림 N건'으로 묶는다
VERSION = "1.0.0"

log = logging.getLogger("notifier")


def resource(name: str) -> pathlib.Path:
    """PyInstaller로 묶었을 때와 소스로 실행할 때 모두 같은 자원 경로."""
    base = pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).parent))
    return base / "assets" / name


# --- Windows 보호 저장소 (DPAPI): 이 Windows 계정에서만 풀 수 있게 암호화 ------------------
class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(data: bytes, protect: bool) -> bytes:
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    buf = ctypes.create_string_buffer(data, len(data))
    src, out = _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), _Blob()
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if not fn(ctypes.byref(src), None, None, None, None, 0x1, ctypes.byref(out)):  # 0x1 = UI 띄우지 않음
        raise OSError("DPAPI 실패")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(out.pbData)


# --- 설정 -------------------------------------------------------------------------------
def load_config() -> dict:
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if cfg.get("token_enc"):
        try:
            cfg["token"] = _dpapi(base64.b64decode(cfg["token_enc"]), False).decode()
        except (OSError, ValueError):
            cfg.pop("token", None)
    return cfg


def save_config(cfg: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    out = {k: v for k, v in cfg.items() if k not in ("token", "token_enc")}
    if cfg.get("token"):
        out["token_enc"] = base64.b64encode(_dpapi(cfg["token"].encode(), True)).decode()
    tmp = CONFIG.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(CONFIG)


def default_server() -> str:
    """exe 옆에 server.txt 가 있으면 그 주소를 기본값으로 (편집국 배포용)."""
    here = pathlib.Path(sys.executable if getattr(sys, "frozen", False) else __file__).parent
    try:
        url = (here / "server.txt").read_text(encoding="utf-8").strip()
        return url.rstrip("/") or DEFAULT_SERVER
    except OSError:
        return DEFAULT_SERVER


# --- 서버 통신 ----------------------------------------------------------------------------
class AuthError(Exception):
    pass


def call(server: str, method: str, path: str, token: str | None = None, body: dict | None = None,
         timeout: float = 15) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(server.rstrip("/") + path, data=data, method=method)
    req.add_header("User-Agent", f"ChungnyunBriefingNotifier/{VERSION}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("detail", "")
        except ValueError:
            detail = ""
        if e.code == 401:
            raise AuthError(detail or "다시 로그인하세요.") from None
        raise RuntimeError(detail or f"서버 오류 {e.code}") from None


# --- 자동 실행 ----------------------------------------------------------------------------
def launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pyw = pathlib.Path(sys.executable).with_name("pythonw.exe")
    return f'"{pyw if pyw.exists() else sys.executable}" "{pathlib.Path(__file__).resolve()}"'


def autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            return bool(winreg.QueryValueEx(k, RUN_VALUE)[0])
    except OSError:
        return False


def set_autostart(on: bool) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, RUN_VALUE, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(k, RUN_VALUE)
            except FileNotFoundError:
                pass


# --- 알림 창 --------------------------------------------------------------------------------
class Toaster:
    def __init__(self):
        from windows_toasts import InteractableWindowsToaster
        from windows_toasts.register_hkey_aumid import register_hkey

        HOME.mkdir(parents=True, exist_ok=True)
        icon = HOME / "icon.ico"
        try:
            shutil.copyfile(resource("icon.ico"), icon)
            # 알림에 'Python'이 아니라 앱 이름과 아이콘이 보이도록 이 사용자 계정에 등록
            register_hkey(APP_ID, APP_NAME, icon)
            self.toaster = InteractableWindowsToaster(APP_NAME, APP_ID)
        except Exception:  # noqa: BLE001 - 등록이 막힌 PC에서도 알림은 뜨게
            log.exception("AUMID 등록 실패, 기본 알림으로 표시")
            self.toaster = InteractableWindowsToaster(APP_NAME)

    def show(self, title: str, body: str, url: str | None = None, tag: str | None = None) -> None:
        from windows_toasts import Toast

        t = Toast([title, body])
        if tag:
            t.tag = str(tag)[:60]
        if url:
            t.on_activated = lambda _args, u=url: webbrowser.open(u)
        try:
            self.toaster.show_toast(t)
        except Exception:  # noqa: BLE001
            log.exception("알림 표시 실패")


# --- 로그인 창 (tkinter) ------------------------------------------------------------------
def login_dialog(server: str, username: str = "", message: str = "") -> dict | None:
    """로그인에 성공하면 {server, token, display_name, last_id, username}, 취소하면 None."""
    import tkinter as tk
    from tkinter import ttk

    result: dict = {}
    root = tk.Tk()
    root.title(f"{APP_NAME} 알림 · 로그인")
    root.resizable(False, False)
    try:
        root.iconbitmap(str(resource("icon.ico")))
    except tk.TclError:
        pass
    frm = ttk.Frame(root, padding=18)
    frm.grid()
    ttk.Label(frm, text=APP_NAME, font=("Malgun Gothic", 13, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
    ttk.Label(frm, text="브리핑 계정으로 로그인하면 이 PC로 공시 알림이 옵니다.",
              font=("Malgun Gothic", 9)).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 12))
    v_server, v_user, v_pw = tk.StringVar(value=server), tk.StringVar(value=username), tk.StringVar()
    rows = (("서버 주소", v_server, ""), ("아이디", v_user, ""), ("비밀번호", v_pw, "•"))
    entries = []
    for i, (label, var, show) in enumerate(rows, start=2):
        ttk.Label(frm, text=label, font=("Malgun Gothic", 9)).grid(row=i, column=0, sticky="w", pady=3)
        e = ttk.Entry(frm, textvariable=var, width=34, show=show)
        e.grid(row=i, column=1, pady=3)
        entries.append(e)
    status = ttk.Label(frm, text=message, foreground="#b42318", font=("Malgun Gothic", 9), wraplength=330)
    status.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
    btn = ttk.Button(frm, text="로그인")
    btn.grid(row=6, column=1, sticky="e", pady=(10, 0))

    def submit(_e=None):
        srv = v_server.get().strip().rstrip("/")
        if not srv.startswith(("http://", "https://")):
            srv = "http://" + srv
        status.config(text="연결하는 중…", foreground="#475467")
        root.update_idletasks()
        try:
            r = call(srv, "POST", "/api/device/login",
                     body={"username": v_user.get().strip(), "password": v_pw.get(), "name": platform.node()[:60]})
        except AuthError as e:
            status.config(text=str(e), foreground="#b42318")
            return
        except (OSError, RuntimeError) as e:
            status.config(text=f"서버에 연결하지 못했습니다. 주소를 확인하세요.\n({e})", foreground="#b42318")
            return
        result.update(server=srv, token=r["token"], display_name=r.get("display_name", ""),
                      last_id=int(r.get("last_id", 0)), username=v_user.get().strip())
        root.destroy()

    btn.config(command=submit)
    root.bind("<Return>", submit)
    (entries[2] if username else entries[1]).focus_set()
    root.attributes("-topmost", True)
    root.after(300, lambda: root.attributes("-topmost", False))
    root.mainloop()
    return result or None


# --- 트레이 앱 -----------------------------------------------------------------------------
class App:
    def __init__(self):
        import pystray
        from PIL import Image, ImageOps

        self.cfg = load_config()
        self.toaster = Toaster()
        base = Image.open(resource("icon.png")).convert("RGBA").resize((64, 64))
        gray = ImageOps.grayscale(base).convert("RGBA")
        gray.putalpha(base.getchannel("A").point(lambda a: a * 0.55))
        self.img_ok, self.img_off = base, gray
        self.state = "연결 중…"
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.login_lock = threading.Lock()
        M = pystray.MenuItem
        self.icon = pystray.Icon(APP_ID, self.img_off, APP_NAME, menu=pystray.Menu(
            M(lambda _i: self.status_line(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            M("브리핑 열기", self.open_web, default=True),
            M("테스트 알림 받기", self.test_alert, enabled=lambda _i: bool(self.cfg.get("token"))),
            M("Windows 시작 시 실행", self.toggle_autostart, checked=lambda _i: autostart_enabled()),
            pystray.Menu.SEPARATOR,
            M(lambda _i: "로그아웃" if self.cfg.get("token") else "로그인", self.login_or_logout),
            M("종료", self.quit),
        ))

    # 메뉴 ------------------------------------------------------------------------------------
    def status_line(self) -> str:
        who = self.cfg.get("display_name") or self.cfg.get("username") or ""
        return f"{self.state}{' · ' + who if who and self.cfg.get('token') else ''}"

    def set_state(self, text: str, ok: bool) -> None:
        self.state = text
        self.icon.icon = self.img_ok if ok else self.img_off
        self.icon.title = f"{APP_NAME} · {text}"
        self.icon.update_menu()

    def open_web(self, *_):
        webbrowser.open(self.cfg.get("server", default_server()) + "/")

    def test_alert(self, *_):
        def run():
            try:
                call(self.cfg["server"], "POST", "/api/device/test", self.cfg["token"])
            except Exception as e:  # noqa: BLE001
                self.toaster.show(APP_NAME, f"테스트 요청에 실패했습니다: {e}")
        threading.Thread(target=run, daemon=True).start()

    def toggle_autostart(self, *_):
        set_autostart(not autostart_enabled())
        self.icon.update_menu()

    def login_or_logout(self, *_):
        if self.cfg.get("token"):
            try:
                call(self.cfg["server"], "DELETE", "/api/device", self.cfg["token"], timeout=8)
            except Exception:  # noqa: BLE001 - 서버가 꺼져 있어도 이 PC에서는 로그아웃
                pass
            self.cfg.pop("token", None)
            save_config(self.cfg)
            self.set_state("로그아웃됨", False)
        else:
            threading.Thread(target=self.ask_login, daemon=True).start()

    def ask_login(self, message: str = "") -> bool:
        if not self.login_lock.acquire(blocking=False):
            return False
        try:
            r = login_dialog(self.cfg.get("server", default_server()), self.cfg.get("username", ""), message)
            if not r:
                return False
            first = not CONFIG.exists()
            self.cfg.update(r)
            save_config(self.cfg)
            if first or self.cfg.get("autostart_default") is None:
                set_autostart(True)  # 처음 로그인하면 Windows 시작 시 실행을 켠다 (메뉴에서 끌 수 있음)
                self.cfg["autostart_default"] = True
                save_config(self.cfg)
            self.toaster.show(APP_NAME, f"{r.get('display_name') or r['username']} 님, 이제 이 PC로 알림이 옵니다.")
            self.wake.set()
            return True
        finally:
            self.login_lock.release()

    def quit(self, *_):
        self.stop.set()
        self.wake.set()
        self.icon.stop()

    # 알림 받기 ----------------------------------------------------------------------------------
    def deliver(self, items: list[dict]) -> None:
        cutoff = time.time() - STALE_MIN * 60
        stale = [i for i in items if _ts(i.get("created_at")) < cutoff]
        fresh = [i for i in items if i not in stale]
        if len(stale) > 1:  # PC가 꺼져 있던 동안 쌓인 알림은 한 통으로
            names = " / ".join(dict.fromkeys(i.get("title", "").split(" · ")[0] for i in stale))
            self.toaster.show(f"놓친 알림 {len(stale)}건", names[:200], self.cfg["server"] + "/#s/red", "missed")
        else:
            fresh = stale + fresh
        for i in fresh[-10:]:
            self.toaster.show(i.get("title", APP_NAME), i.get("body", ""), i.get("url"), i.get("tag"))

    def poll_loop(self) -> None:
        backoff = 3
        while not self.stop.is_set():
            if not self.cfg.get("token"):
                self.set_state("로그인 필요", False)
                self.wake.wait()
                self.wake.clear()
                continue
            try:
                r = call(self.cfg["server"], "GET", f"/api/device/alerts?after={int(self.cfg.get('last_id', 0))}"
                         f"&wait={WAIT}", self.cfg["token"], timeout=WAIT + 15)
                backoff = 3
                mode = "" if r.get("alert_mode") == "notify" else " (서버가 기록 모드라 알림 없음)"
                self.cfg["display_name"] = r.get("display_name", self.cfg.get("display_name"))
                self.set_state("연결됨" + mode, True)
                if r.get("items"):
                    self.deliver(r["items"])
                if int(r.get("last_id", 0)) != int(self.cfg.get("last_id", 0)):
                    self.cfg["last_id"] = int(r["last_id"])
                    save_config(self.cfg)
            except AuthError:
                self.cfg.pop("token", None)
                save_config(self.cfg)
                self.set_state("로그인 필요", False)
                self.toaster.show(APP_NAME, "로그인이 해제되었습니다. 트레이 아이콘에서 다시 로그인하세요.")
            except Exception as e:  # noqa: BLE001 - 네트워크 끊김, 서버 재시작 등
                log.warning("poll failed: %s", e)
                self.set_state("서버에 연결할 수 없음 · 다시 시도 중", False)
                self.wake.wait(backoff)
                self.wake.clear()
                backoff = min(backoff * 2, 60)

    def run(self) -> None:
        def setup(icon):
            icon.visible = True
            threading.Thread(target=self.poll_loop, daemon=True).start()
            if not self.cfg.get("token"):
                threading.Thread(target=self.ask_login, daemon=True).start()
        self.icon.run(setup=setup)


def _ts(iso: str | None) -> float:
    try:
        return datetime.fromisoformat(iso).timestamp() if iso else time.time()
    except ValueError:
        return time.time()


def single_instance() -> bool:
    """이미 실행 중이면 False (같은 사용자 세션에서 하나만)."""
    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\ChungnyunBriefingNotifier")
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def main() -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=HOME / "notifier.log", level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(levelname)s %(message)s")
    if "--uninstall" in sys.argv:  # 자동 실행·알림 등록·설정을 지운다
        set_autostart(False)
        try:
            from windows_toasts.register_hkey_aumid import unregister_hkey
            unregister_hkey(APP_ID)
        except Exception:  # noqa: BLE001
            pass
        shutil.rmtree(HOME, ignore_errors=True)
        return
    if not single_instance():
        return
    App().run()


if __name__ == "__main__":
    main()
