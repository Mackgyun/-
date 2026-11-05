import json
from types import SimpleNamespace as NS

import pytest

from newsbot.config import Settings
from newsbot.db import Database
from newsbot.llm import LLM, BudgetExceeded, ClaudeBackend, LLMError, OpenAIBackend, Tool
from newsbot.writing import check_numbers

TOOL = Tool("lookup", "찾기", {"type": "object", "properties": {"q": {"type": "string"}}},
            lambda a: {"found": a.get("q", "") + "!"})


class FakeClaude:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        return self.responses.pop(0)


def c_resp(content, stop="end_turn"):
    return NS(content=content, stop_reason=stop,
              usage=NS(input_tokens=1000, output_tokens=200, cache_read_input_tokens=0, cache_creation_input_tokens=0))


def test_claude_tool_loop_and_fallback_params():
    fake = FakeClaude([
        c_resp([NS(type="tool_use", id="t1", name="lookup", input={"q": "유한"})], stop="tool_use"),
        c_resp([NS(type="text", text="답: 유한!")]),
    ])
    b = ClaudeBackend("k", client=fake)
    text, trace, usages = b.agent("claude-sonnet-5-5", "sys", [{"role": "user", "content": "질문"}], [TOOL], "main", 5)
    assert text == "답: 유한!" and trace[0]["tool"] == "lookup" and len(usages) == 2
    first, second = fake.calls
    assert first["fallbacks"] == "default" and first["betas"] == ["server-side-fallback-2026-07-01"]
    assert first["output_config"] == {"effort": "medium"}
    assert "temperature" not in first and "tool_choice" not in first
    tool_result = second["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and json.loads(tool_result["content"]) == {"found": "유한!"}


def test_haiku_has_no_fallbacks_and_refusal_raises():
    fake = FakeClaude([c_resp([], stop="refusal")])
    with pytest.raises(LLMError):
        ClaudeBackend("k", client=fake).complete("claude-haiku-5-5", "s", "p", "fast")
    assert "fallbacks" not in fake.calls[0]


def test_openai_tool_loop():
    calls = []

    def create(**kw):
        calls.append(kw)
        if len(calls) == 1:
            tc = NS(id="c1", function=NS(name="lookup", arguments='{"q":"한미"}'),
                    model_dump=lambda: {"id": "c1", "type": "function", "function": {"name": "lookup", "arguments": '{"q":"한미"}'}})
            msg = NS(content=None, tool_calls=[tc])
        else:
            msg = NS(content="답: 한미!", tool_calls=None)
        return NS(choices=[NS(message=msg)], usage=NS(prompt_tokens=500, completion_tokens=50))

    b = OpenAIBackend("k", client=NS(chat=NS(completions=NS(create=create))))
    text, trace, _ = b.agent("gpt-6.1-sol", "sys", [{"role": "user", "content": "q"}], [TOOL], "main", 5)
    assert text == "답: 한미!" and calls[1]["messages"][-1]["role"] == "tool"


def test_budget_and_cost(tmp_path):
    db = Database(":memory:")
    db.execute("INSERT INTO users(id, username, display_name, pw_hash, created_at, monthly_limit_krw) VALUES(1,'a','A','x','t',100)")
    fake = FakeClaude([c_resp([NS(type="text", text="ok")])] * 3)
    llm = LLM(Settings(llm_provider="claude", anthropic_api_key="k", data_dir=tmp_path), db, backend=ClaudeBackend("k", client=fake))
    text, model = llm.complete("s", "p", "main", user_id=1, purpose="t")
    # sonnet 5.5: 1000*2 + 200*10 = 4000 / 1e6 USD = 0.004 USD = 5.6원
    assert model == "claude-sonnet-5-5" and llm.month_spent(1) == pytest.approx(5.6)
    db.execute("UPDATE users SET monthly_limit_krw=5 WHERE id=1")
    with pytest.raises(BudgetExceeded):
        llm.complete("s", "p", "main", user_id=1, purpose="t")


def test_check_numbers():
    checks = check_numbers("매출 1,234억원, 15% 증가, 2026년", "매출액 1234억원 ... 2026년 실적")
    found = {c["number"]: c["found"] for c in checks}
    assert found == {"1,234": True, "15": False, "2026": True}
