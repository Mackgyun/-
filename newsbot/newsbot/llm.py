"""AI(LLM) 호출 계층. Claude와 OpenAI를 같은 방식으로 쓰고, 사용량·비용을 기록한다.

등급(tier)
  fast  : 정기 브리핑 요약 등 대량·단순 작업
  main  : 질문 답변
  draft : 스타일북 분석, 기사 초안
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from .config import Settings
from .db import Database, now, now_iso

log = logging.getLogger(__name__)

# 100만 토큰당 달러 (입력, 출력). Claude는 Anthropic 요금표(2026-10 기준),
# OpenAI는 공개 요금 정리 글 기준이라 실제 청구서와 대조가 필요하다.
PRICES_USD = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-opus-5-5": (4.0, 20.0),
    "gpt-6-luna": (0.10, 0.50),
    "gpt-6.1-terra": (1.0, 5.0),
    "gpt-6.1-sol": (2.0, 10.0),
    "gpt-6-astra": (10.0, 50.0),
}
UNKNOWN_PRICE = (4.0, 20.0)  # 모르는 모델은 비싸게 잡아 한도를 넘지 않게
EFFORT = {"fast": "low", "main": "medium", "draft": "high"}
MAX_TOKENS = {"fast": 2000, "main": 4000, "draft": 8000}


class LLMError(Exception):
    """사용자에게 그대로 보여줄 수 있는 문구를 담는다."""


class BudgetExceeded(LLMError):
    pass


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    func: Callable[[dict], Any]


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0


@dataclass
class AgentResult:
    text: str
    trace: list = field(default_factory=list)
    model: str = ""


def _run_tool(tools: dict[str, Tool], name: str, args: dict) -> str:
    tool = tools.get(name)
    if not tool:
        return json.dumps({"error": f"없는 도구: {name}"}, ensure_ascii=False)
    try:
        result = tool.func(args or {})
    except Exception as e:  # noqa: BLE001 - 도구 오류는 모델에게 알려 다시 시도하게 함
        log.exception("tool %s failed", name)
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
    return text[:20000]


class ClaudeBackend:
    name = "claude"

    def __init__(self, api_key: str, client=None):
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key, max_retries=3, timeout=180.0)
        self.client = client

    @staticmethod
    def _extra(model: str) -> dict:
        # Sonnet 5.5 / Opus 5.5는 안전 분류기가 거절하면 서버가 다른 모델로 다시 돌려준다.
        if "sonnet-5-5" in model or "opus-5" in model or "fable" in model:
            return {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        return {}

    def _call(self, model, system, messages, tools, tier):
        kwargs = dict(
            model=model,
            max_tokens=MAX_TOKENS[tier],
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            output_config={"effort": EFFORT[tier]},
            **self._extra(model),
        )
        if tools:
            kwargs["tools"] = [{"name": t.name, "description": t.description, "input_schema": t.schema}
                               for t in tools]
        resp = self.client.beta.messages.create(**kwargs)
        u = resp.usage
        usage = Usage(u.input_tokens, u.output_tokens,
                      getattr(u, "cache_read_input_tokens", 0) or 0,
                      getattr(u, "cache_creation_input_tokens", 0) or 0)
        if resp.stop_reason == "refusal":
            raise LLMError("AI가 이 요청을 처리하지 않았어요. 표현을 바꿔 다시 시도해 주세요.")
        return resp, usage

    def complete(self, model, system, prompt, tier):
        resp, usage = self._call(model, system, [{"role": "user", "content": prompt}], None, tier)
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return text, [usage]

    def agent(self, model, system, history, tools, tier, max_steps):
        by_name = {t.name: t for t in tools}
        messages = list(history)
        usages, trace = [], []
        for _ in range(max_steps):
            resp, usage = self._call(model, system, messages, tools, tier)
            usages.append(usage)
            if resp.stop_reason != "tool_use":
                text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                return text, trace, usages
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for b in resp.content:
                if getattr(b, "type", "") == "tool_use":
                    out = _run_tool(by_name, b.name, b.input)
                    trace.append({"tool": b.name, "input": b.input, "output": out[:2000]})
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
            messages.append({"role": "user", "content": results})
        return "조회를 여러 번 했지만 답을 정리하지 못했어요. 질문을 좁혀 주세요.", trace, usages


class OpenAIBackend:
    name = "openai"

    def __init__(self, api_key: str, client=None):
        if client is None:
            import openai

            client = openai.OpenAI(api_key=api_key, max_retries=3, timeout=180.0)
        self.client = client

    def _call(self, model, messages, tools, tier):
        kwargs = dict(model=model, messages=messages, max_completion_tokens=MAX_TOKENS[tier])
        if tools:
            kwargs["tools"] = [{"type": "function", "function": {
                "name": t.name, "description": t.description, "parameters": t.schema}} for t in tools]
        resp = self.client.chat.completions.create(**kwargs)
        u = resp.usage
        return resp, Usage(getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0)

    def complete(self, model, system, prompt, tier):
        resp, usage = self._call(model, [{"role": "system", "content": system},
                                         {"role": "user", "content": prompt}], None, tier)
        return resp.choices[0].message.content or "", [usage]

    def agent(self, model, system, history, tools, tier, max_steps):
        by_name = {t.name: t for t in tools}
        messages = [{"role": "system", "content": system}, *history]
        usages, trace = [], []
        for _ in range(max_steps):
            resp, usage = self._call(model, messages, tools, tier)
            usages.append(usage)
            msg = resp.choices[0].message
            calls = msg.tool_calls or []
            if not calls:
                return msg.content or "", trace, usages
            messages.append({"role": "assistant", "content": msg.content,
                             "tool_calls": [c.model_dump() if hasattr(c, "model_dump") else c for c in calls]})
            for c in calls:
                try:
                    args = json.loads(c.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                out = _run_tool(by_name, c.function.name, args)
                trace.append({"tool": c.function.name, "input": args, "output": out[:2000]})
                messages.append({"role": "tool", "tool_call_id": c.id, "content": out})
        return "조회를 여러 번 했지만 답을 정리하지 못했어요. 질문을 좁혀 주세요.", trace, usages


class LLM:
    def __init__(self, settings: Settings, db: Database, backend=None):
        self.settings = settings
        self.db = db
        self._backend = backend

    @property
    def available(self) -> bool:
        return self._backend is not None or self.settings.llm_ready

    @property
    def backend(self):
        if self._backend is None:
            if not self.settings.llm_ready:
                raise LLMError("AI API 키가 아직 없어요. 관리자가 .env 에 키를 넣으면 켜집니다.")
            if self.settings.llm_provider == "claude":
                self._backend = ClaudeBackend(self.settings.anthropic_api_key)
            else:
                self._backend = OpenAIBackend(self.settings.openai_api_key)
        return self._backend

    def model_for(self, tier: str) -> str:
        models = self.settings.openai_models if self.backend.name == "openai" else self.settings.claude_models
        return models[tier]

    # --- 비용 -----------------------------------------------------------
    def cost_krw(self, model: str, usage: Usage) -> float:
        pin, pout = PRICES_USD.get(model, UNKNOWN_PRICE)
        usd = (usage.input_tokens * pin + usage.cache_write * pin * 1.25 + usage.cache_read * pin * 0.1
               + usage.output_tokens * pout) / 1_000_000
        return round(usd * self.settings.usd_krw, 2)

    def month_spent(self, user_id: int | None = None) -> float:
        start = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
        if user_id is None:
            row = self.db.one("SELECT COALESCE(SUM(cost_krw),0) s FROM llm_usage WHERE at >= ?", (start,))
        else:
            row = self.db.one("SELECT COALESCE(SUM(cost_krw),0) s FROM llm_usage WHERE at >= ? AND user_id=?",
                              (start, user_id))
        return float(row["s"])

    def limit_for(self, user_id: int) -> int:
        row = self.db.one("SELECT monthly_limit_krw FROM users WHERE id=?", (user_id,))
        return int(row["monthly_limit_krw"]) if row and row["monthly_limit_krw"] else \
            self.settings.default_monthly_limit_krw

    def _check_budget(self, user_id: int | None) -> None:
        if user_id is None:
            return
        if self.month_spent(user_id) >= self.limit_for(user_id):
            raise BudgetExceeded("이번 달 AI 사용 한도를 다 썼어요. 관리자에게 한도 조정을 요청해 주세요.")

    def _record(self, user_id, model, purpose, usages: list[Usage]) -> None:
        for u in usages:
            self.db.execute(
                """INSERT INTO llm_usage(user_id, at, provider, model, purpose, input_tokens, output_tokens, cost_krw)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (user_id, now_iso(), self.backend.name, model, purpose,
                 u.input_tokens + u.cache_read + u.cache_write, u.output_tokens, self.cost_krw(model, u)))

    # --- 호출 -----------------------------------------------------------
    def complete(self, system: str, prompt: str, tier: str, user_id: int | None, purpose: str) -> tuple[str, str]:
        self._check_budget(user_id)
        model = self.model_for(tier)
        try:
            text, usages = self.backend.complete(model, system, prompt, tier)
        except LLMError:
            raise
        except Exception as e:  # noqa: BLE001
            log.exception("llm complete failed")
            raise LLMError(f"AI 호출에 실패했어요: {type(e).__name__}") from e
        self._record(user_id, model, purpose, usages)
        return text, model

    def agent(self, system: str, history: list[dict], tools: list[Tool], tier: str, user_id: int | None,
              purpose: str, max_steps: int = 6) -> AgentResult:
        self._check_budget(user_id)
        model = self.model_for(tier)
        try:
            text, trace, usages = self.backend.agent(model, system, history, tools, tier, max_steps)
        except LLMError:
            raise
        except Exception as e:  # noqa: BLE001
            log.exception("llm agent failed")
            raise LLMError(f"AI 호출에 실패했어요: {type(e).__name__}") from e
        self._record(user_id, model, purpose, usages)
        return AgentResult(text=text, trace=trace, model=model)
