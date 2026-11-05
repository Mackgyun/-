"""공시 중요도 규칙 (config/rules.toml)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

RED, YELLOW, GRAY = "red", "yellow", "gray"
LEVEL_EMOJI = {RED: "🔴", YELLOW: "🟡", GRAY: "⚪"}


def _norm(text: str) -> str:
    """띄어쓰기와 대괄호 접두어 차이를 무시하기 위해 공백을 모두 지운다."""
    return "".join(text.split())


@dataclass(frozen=True)
class Rules:
    industry_prefixes: tuple[str, ...] = ()
    always_include: frozenset[str] = frozenset()
    always_exclude: frozenset[str] = frozenset()
    red: tuple[str, ...] = ()
    gray: tuple[str, ...] = ()
    _red_norm: tuple[str, ...] = field(default=(), repr=False)
    _gray_norm: tuple[str, ...] = field(default=(), repr=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Rules":
        health = data.get("health", {})
        levels = data.get("levels", {})
        red = tuple(levels.get("red", []))
        gray = tuple(levels.get("gray", []))
        return cls(
            industry_prefixes=tuple(health.get("industry_prefixes", [])),
            always_include=frozenset(health.get("always_include", [])),
            always_exclude=frozenset(health.get("always_exclude", [])),
            red=red,
            gray=gray,
            _red_norm=tuple(_norm(k) for k in red),
            _gray_norm=tuple(_norm(k) for k in gray),
        )

    @classmethod
    def load(cls, path: Path) -> "Rules":
        with open(path, "rb") as f:
            return cls.from_dict(tomllib.load(f))

    def is_health(self, corp_name: str, induty_code: str | None) -> bool:
        if corp_name in self.always_exclude:
            return False
        if corp_name in self.always_include:
            return True
        if not induty_code:
            return False
        return any(induty_code.startswith(p) for p in self.industry_prefixes)

    def classify(self, report_nm: str) -> tuple[str, str | None]:
        """(등급, 걸린 키워드)를 돌려준다."""
        title = _norm(report_nm)
        for raw, key in zip(self.red, self._red_norm):
            if key in title:
                return RED, raw
        for raw, key in zip(self.gray, self._gray_norm):
            if key in title:
                return GRAY, raw
        return YELLOW, None
