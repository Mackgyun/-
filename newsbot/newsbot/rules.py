"""공시 분류 규칙 (config/rules.toml)."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

RED, YELLOW, GRAY = "red", "yellow", "gray"
LEVELS = (RED, YELLOW, GRAY)

_PREFIX = re.compile(r"^\s*\[([^\]]+)\]")


def _norm(text: str) -> str:
    """띄어쓰기 차이를 무시하기 위해 공백을 모두 지운다."""
    return "".join(text.split())


def split_prefix(report_nm: str) -> tuple[str | None, str]:
    """'[기재정정]주요사항보고서...' → ('기재정정', '주요사항보고서...')."""
    m = _PREFIX.match(report_nm)
    if not m:
        return None, report_nm.strip()
    return m.group(1).strip(), report_nm[m.end():].strip()


@dataclass(frozen=True)
class Classification:
    level: str
    keyword: str | None
    is_correction: bool
    prefix: str | None

    @property
    def should_alert(self) -> bool:
        return self.level == RED and not self.is_correction


@dataclass(frozen=True)
class Rules:
    watch: frozenset[str] = frozenset()
    industry_prefixes: tuple[str, ...] = ()
    always_exclude: frozenset[str] = frozenset()
    red: tuple[str, ...] = ()
    red_exclude: tuple[str, ...] = ()
    gray: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict) -> "Rules":
        levels = data.get("levels", {})
        health = data.get("health", {})
        return cls(
            watch=frozenset(_norm(c) for c in data.get("watch", {}).get("companies", [])),
            industry_prefixes=tuple(health.get("industry_prefixes", [])),
            always_exclude=frozenset(_norm(c) for c in health.get("always_exclude", [])),
            red=tuple(levels.get("red", [])),
            red_exclude=tuple(levels.get("red_exclude", [])),
            gray=tuple(levels.get("gray", [])),
        )

    @classmethod
    def load(cls, path: Path) -> "Rules":
        with open(path, "rb") as f:
            return cls.from_dict(tomllib.load(f))

    def is_watched(self, corp_name: str) -> bool:
        return _norm(corp_name) in self.watch

    def is_relevant(self, corp_name: str, induty_code: str | None) -> bool:
        """피드에 넣을 회사인가: 감시 목록이거나 보건의료 업종."""
        name = _norm(corp_name)
        if name in self.always_exclude:
            return False
        if name in self.watch:
            return True
        return bool(induty_code) and any(induty_code.startswith(p) for p in self.industry_prefixes)

    def needs_industry_lookup(self, corp_name: str) -> bool:
        return _norm(corp_name) not in self.watch and _norm(corp_name) not in self.always_exclude

    def classify(self, report_nm: str) -> Classification:
        prefix, body = split_prefix(report_nm)
        is_correction = bool(prefix) and "정정" in prefix
        title = _norm(body)

        level, keyword = YELLOW, None
        if not any(_norm(x) in title for x in self.red_exclude):
            for k in self.red:
                if _norm(k) in title:
                    level, keyword = RED, k
                    break
        if level == YELLOW:
            for k in self.gray:
                if _norm(k) in title:
                    level, keyword = GRAY, k
                    break
        return Classification(level, keyword, is_correction, prefix)
