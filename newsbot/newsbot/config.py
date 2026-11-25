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
    out = []
    for t in (x.strip() for x in raw.split(",")):
        if not t:
            continue
        h, sep, m = t.partition(":")
        if not (sep and h.isdigit() and m.isdigit() and 0 <= int(h) < 24 and 0 <= int(m) < 60):
            raise SystemExit(f"DIGEST_TIMES 의 '{t}' 를 읽지 못했습니다. 08:00,13:00 처럼 시:분 으로 적어 주세요.")
        out.append(f"{int(h):02d}:{int(m):02d}")
    return tuple(out)


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
    llm_provider: str = ""  # claude | openai | gemini(무료 등급) | ollama(이 PC에서 실행, 무료) | "" (꺼짐)
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    ollama_url: str = "http://localhost:11434/v1"
    claude_models: dict = field(default_factory=lambda: {
        "fast": "claude-haiku-5-5", "main": "claude-sonnet-5-5", "draft": "claude-opus-5-5"})
    openai_models: dict = field(default_factory=lambda: {
        "fast": "gpt-6-luna", "main": "gpt-6.1-sol", "draft": "gpt-6.1-sol"})
    # Google AI Studio 무료 등급 (2026-11 요금표 기준 무료 모델)
    gemini_models: dict = field(default_factory=lambda: {
        "fast": "gemini-3.5-flash-lite", "main": "gemini-3.8-flash", "draft": "gemini-3.8-flash"})
    # 무료 등급은 모델이 붐비면 503을 돌려준다. 그때 차례로 바꿔 부를 모델
    gemini_fallback_models: list = field(default_factory=lambda: ["gemini-3.6-flash", "gemini-3.5-flash-lite"])
    ollama_models: dict = field(default_factory=lambda: {
        "fast": "qwen3:8b", "main": "qwen3:8b", "draft": "qwen3:8b"})
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
    # 식약처(공공데이터포털)·국회(열린국회정보) 수집. 키가 있는 쪽만 돈다
    data_go_kr_api_key: str = ""
    assembly_api_key: str = ""
    gov_enabled: bool = True
    gov_poll_minutes: int = 30
    digest_times: tuple = ("08:00", "13:00", "18:00", "23:00")

    # 원격 MCP: 기자가 자기 Claude·ChatGPT에 이 앱을 커넥터로 연결 (기자 계정으로 OAuth 로그인)
    mcp_enabled: bool = True
    # 커넥터가 로그인 후 돌아갈 수 있는 주소의 호스트 (쉼표로 구분)
    mcp_redirect_hosts: tuple = ("claude.ai", "claude.com", "chatgpt.com", "chat.openai.com", "localhost", "127.0.0.1")

    @property
    def notify_enabled(self) -> bool:
        return self.alert_mode == "notify"

    @property
    def secure_cookies(self) -> bool:
        return self.public_url.startswith("https://")

    @property
    def llm_ready(self) -> bool:
        return ((self.llm_provider == "claude" and bool(self.anthropic_api_key))
                or (self.llm_provider == "openai" and bool(self.openai_api_key))
                or (self.llm_provider == "gemini" and bool(self.gemini_api_key))
                or self.llm_provider == "ollama")

    @property
    def llm_free(self) -> bool:
        """무료 등급·로컬 모델은 비용을 0원으로 기록한다."""
        return self.llm_provider in ("gemini", "ollama")


def load_settings(env_file: Path | None = None) -> Settings:
    load_dotenv(env_file or BASE_DIR / ".env")
    mode = os.getenv("ALERT_MODE", "log").strip().lower()
    if mode not in ("log", "notify"):
        raise SystemExit("ALERT_MODE 는 log 또는 notify 여야 합니다.")
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider not in ("", "claude", "openai", "gemini", "ollama"):
        raise SystemExit("LLM_PROVIDER 는 claude, openai, gemini, ollama 중 하나여야 합니다.")
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
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434/v1").rstrip("/"),
        claude_models={k: os.getenv(f"CLAUDE_MODEL_{k.upper()}", v) for k, v in d.claude_models.items()},
        openai_models={k: os.getenv(f"OPENAI_MODEL_{k.upper()}", v) for k, v in d.openai_models.items()},
        gemini_models={k: os.getenv(f"GEMINI_MODEL_{k.upper()}", v) for k, v in d.gemini_models.items()},
        gemini_fallback_models=[m.strip() for m in os.getenv(
            "GEMINI_FALLBACK_MODELS", ",".join(d.gemini_fallback_models)).split(",") if m.strip()],
        ollama_models={k: os.getenv(f"OLLAMA_MODEL_{k.upper()}", v) for k, v in d.ollama_models.items()},
        usd_krw=float(os.getenv("USD_KRW", "1400")),
        default_monthly_limit_krw=int(os.getenv("MONTHLY_LIMIT_KRW", "30000")),
        alio_enabled=_bool("ALIO_ENABLED", True),
        alio_poll_hours=max(1, int(os.getenv("ALIO_POLL_HOURS", "6"))),
        alio_verify_ssl=_bool("ALIO_VERIFY_SSL", True),
        mail_enabled=_bool("MAIL_ENABLED", False),
        mail_ai_summary=_bool("MAIL_AI_SUMMARY", False),
        mail_poll_minutes=max(1, int(os.getenv("MAIL_POLL_MINUTES", "5"))),
        docdoc_base=os.getenv("DOCDOC_BASE", "https://www.docdocdoc.co.kr").rstrip("/"),
        data_go_kr_api_key=os.getenv("DATA_GO_KR_API_KEY", "").strip(),
        assembly_api_key=os.getenv("ASSEMBLY_API_KEY", "").strip(),
        gov_enabled=_bool("GOV_ENABLED", True),
        gov_poll_minutes=max(10, int(os.getenv("GOV_POLL_MINUTES", "30"))),
        digest_times=_times(os.getenv("DIGEST_TIMES", "08:00,13:00,18:00,23:00")),
        mcp_enabled=_bool("MCP_ENABLED", True),
        mcp_redirect_hosts=tuple(h.strip().lower() for h in os.getenv("MCP_REDIRECT_HOSTS", "").split(",") if h.strip())
        or d.mcp_redirect_hosts,
    )
