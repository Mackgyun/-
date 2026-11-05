"""환경변수(.env)에서 설정을 읽는다."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

KST = ZoneInfo("Asia/Seoul")


def _parse_times(raw: str) -> list[time]:
    times = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        hour, minute = part.split(":")
        times.append(time(int(hour), int(minute), tzinfo=KST))
    return times


def _parse_ids(raw: str) -> set[int]:
    return {int(x) for x in raw.replace(" ", "").split(",") if x}


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    dart_api_key: str
    admin_chat_ids: set[int] = field(default_factory=set)
    db_path: Path = Path("data/newsbot.db")
    rules_path: Path = Path("config/rules.toml")
    poll_interval_sec: int = 300
    digest_times: list[time] = field(default_factory=list)
    heartbeat_time: time = time(9, 0, tzinfo=KST)
    dart_daily_call_limit: int = 18000


def load_settings(env_file: str | None = ".env") -> Settings:
    if env_file:
        load_dotenv(env_file)

    missing = [k for k in ("TELEGRAM_BOT_TOKEN", "DART_API_KEY") if not os.getenv(k)]
    if missing:
        raise SystemExit(
            f".env 에 {', '.join(missing)} 값이 없습니다. .env.example 을 참고해 채워주세요."
        )

    return Settings(
        telegram_token=os.environ["TELEGRAM_BOT_TOKEN"],
        dart_api_key=os.environ["DART_API_KEY"],
        admin_chat_ids=_parse_ids(os.getenv("ADMIN_CHAT_IDS", "")),
        db_path=Path(os.getenv("DB_PATH", "data/newsbot.db")),
        rules_path=Path(os.getenv("RULES_PATH", "config/rules.toml")),
        poll_interval_sec=int(os.getenv("POLL_INTERVAL_SEC", "300")),
        digest_times=_parse_times(os.getenv("DIGEST_TIMES", "08:00,13:00,18:00,23:00")),
        heartbeat_time=_parse_times(os.getenv("HEARTBEAT_TIME", "09:00"))[0],
        dart_daily_call_limit=int(os.getenv("DART_DAILY_CALL_LIMIT", "18000")),
    )
