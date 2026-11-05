"""환경변수(.env)에서 설정을 읽는다."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

KST = ZoneInfo("Asia/Seoul")
BASE_DIR = Path(__file__).resolve().parent.parent  # newsbot/ 폴더 (작업 스케줄러가 System32에서 띄워도 안전)


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else BASE_DIR / p


@dataclass(frozen=True)
class Settings:
    dart_api_key: str = ""
    alert_mode: str = "log"  # log | notify
    host: str = "127.0.0.1"
    port: int = 8000
    public_url: str = "http://localhost:8000"
    vapid_contact: str = "mailto:admin@example.com"
    db_path: Path = BASE_DIR / "data/newsbot.db"
    rules_path: Path = BASE_DIR / "config/rules.toml"
    data_dir: Path = BASE_DIR / "data"
    poll_interval_sec: int = 300
    dart_rescan_pages: int = 3
    dart_daily_call_limit: int = 18000

    @property
    def notify_enabled(self) -> bool:
        return self.alert_mode == "notify"

    @property
    def secure_cookies(self) -> bool:
        return self.public_url.startswith("https://")


def load_settings(env_file: Path | None = None) -> Settings:
    load_dotenv(env_file or BASE_DIR / ".env")
    mode = os.getenv("ALERT_MODE", "log").strip().lower()
    if mode not in ("log", "notify"):
        raise SystemExit("ALERT_MODE 는 log 또는 notify 여야 합니다.")
    db_path = _path(os.getenv("DB_PATH", "data/newsbot.db"))
    return Settings(
        dart_api_key=os.getenv("DART_API_KEY", "").strip(),
        alert_mode=mode,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        public_url=os.getenv("PUBLIC_URL", "http://localhost:8000").rstrip("/"),
        vapid_contact=os.getenv("VAPID_CONTACT", "mailto:admin@example.com"),
        db_path=db_path,
        rules_path=_path(os.getenv("RULES_PATH", "config/rules.toml")),
        data_dir=db_path.parent,
        poll_interval_sec=max(60, int(os.getenv("POLL_INTERVAL_SEC", "300"))),
        dart_rescan_pages=max(1, int(os.getenv("DART_RESCAN_PAGES", "3"))),
        dart_daily_call_limit=int(os.getenv("DART_DAILY_CALL_LIMIT", "18000")),
    )
