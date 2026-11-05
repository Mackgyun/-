"""환경변수(.env)에서 설정을 읽는다."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

KST = ZoneInfo("Asia/Seoul")
BASE_DIR = Path(__file__).resolve().parent.parent  # newsbot/ 폴더 (작업 스케줄러가 System32에서 띄워도 안전)


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else BASE_DIR / p


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _times(raw: str) -> tuple[str, ...]:
    return tuple(t.strip() for t in raw.split(",") if t.strip())


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
    alio_path: Path = BASE_DIR / "config/alio.toml"
    data_dir: Path = BASE_DIR / "data"
    poll_interval_sec: int = 300
    dart_rescan_pages: int = 3
    dart_daily_call_limit: int = 18000

    # AI
    llm_provider: str = ""  # claude | openai | "" (꺼짐)
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    claude_models: dict = field(default_factory=lambda: {
        "fast": "claude-haiku-5-5", "main": "claude-sonnet-5-5", "draft": "claude-opus-5-5"})
    openai_models: dict = field(default_factory=lambda: {
        "fast": "gpt-6-luna", "main": "gpt-6.1-sol", "draft": "gpt-6.1-sol"})
    usd_krw: float = 1400.0
    default_monthly_limit_krw: int = 30000

    # 알리오·메일·자사 기사·브리핑
    alio_enabled: bool = True
    alio_poll_hours: int = 6
    alio_verify_ssl: bool = True
    mail_enabled: bool = False  # 법무·IT 검토 후 켬
    mail_ai_summary: bool = False  # 메일 본문을 해외 AI API로 보내 요약 (국외 이전 검토 필요)
    mail_poll_minutes: int = 5
    docdoc_base: str = "https://www.docdocdoc.co.kr"
    digest_times: tuple = ("08:00", "13:00", "18:00", "23:00")

    @property
    def notify_enabled(self) -> bool:
        return self.alert_mode == "notify"

    @property
    def secure_cookies(self) -> bool:
        return self.public_url.startswith("https://")

    @property
    def llm_ready(self) -> bool:
        return (self.llm_provider == "claude" and bool(self.anthropic_api_key)) or (
            self.llm_provider == "openai" and bool(self.openai_api_key))


def load_settings(env_file: Path | None = None) -> Settings:
    load_dotenv(env_file or BASE_DIR / ".env")
    mode = os.getenv("ALERT_MODE", "log").strip().lower()
    if mode not in ("log", "notify"):
        raise SystemExit("ALERT_MODE 는 log 또는 notify 여야 합니다.")
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider not in ("", "claude", "openai"):
        raise SystemExit("LLM_PROVIDER 는 claude 또는 openai 여야 합니다.")
    db_path = _path(os.getenv("DB_PATH", "data/newsbot.db"))
    d = Settings()
    return Settings(
        dart_api_key=os.getenv("DART_API_KEY", "").strip(),
        alert_mode=mode,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        public_url=os.getenv("PUBLIC_URL", "http://localhost:8000").rstrip("/"),
        vapid_contact=os.getenv("VAPID_CONTACT", "mailto:admin@example.com"),
        db_path=db_path,
        rules_path=_path(os.getenv("RULES_PATH", "config/rules.toml")),
        alio_path=_path(os.getenv("ALIO_PATH", "config/alio.toml")),
        data_dir=db_path.parent,
        poll_interval_sec=max(60, int(os.getenv("POLL_INTERVAL_SEC", "300"))),
        dart_rescan_pages=max(1, int(os.getenv("DART_RESCAN_PAGES", "3"))),
        dart_daily_call_limit=int(os.getenv("DART_DAILY_CALL_LIMIT", "18000")),
        llm_provider=provider,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        claude_models={k: os.getenv(f"CLAUDE_MODEL_{k.upper()}", v) for k, v in d.claude_models.items()},
        openai_models={k: os.getenv(f"OPENAI_MODEL_{k.upper()}", v) for k, v in d.openai_models.items()},
        usd_krw=float(os.getenv("USD_KRW", "1400")),
        default_monthly_limit_krw=int(os.getenv("MONTHLY_LIMIT_KRW", "30000")),
        alio_enabled=_bool("ALIO_ENABLED", True),
        alio_poll_hours=max(1, int(os.getenv("ALIO_POLL_HOURS", "6"))),
        alio_verify_ssl=_bool("ALIO_VERIFY_SSL", True),
        mail_enabled=_bool("MAIL_ENABLED", False),
        mail_ai_summary=_bool("MAIL_AI_SUMMARY", False),
        mail_poll_minutes=max(1, int(os.getenv("MAIL_POLL_MINUTES", "5"))),
        docdoc_base=os.getenv("DOCDOC_BASE", "https://www.docdocdoc.co.kr").rstrip("/"),
        digest_times=_times(os.getenv("DIGEST_TIMES", "08:00,13:00,18:00,23:00")),
    )
