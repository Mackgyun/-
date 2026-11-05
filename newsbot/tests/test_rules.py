from pathlib import Path

from newsbot.rules import GRAY, RED, YELLOW, Rules, split_prefix

RULES = Rules.load(Path(__file__).resolve().parent.parent / "config" / "rules.toml")


def test_red_keyword():
    c = RULES.classify("주요사항보고서(유상증자결정)")
    assert c.level == RED and c.keyword == "유상증자" and c.should_alert


def test_spaces_ignored():
    assert RULES.classify("투자판단관련주요경영사항 (임상시험 계획 승인)").level == RED


def test_correction_keeps_level_but_no_alert():
    c = RULES.classify("[기재정정]주요사항보고서(유상증자결정)")
    assert c.level == RED and c.is_correction and not c.should_alert
    assert c.prefix == "기재정정"


def test_red_exclude_downgrades():
    assert RULES.classify("합병등종료보고서(흡수합병)").level == YELLOW
    assert RULES.classify("주요사항보고서(주식분할결정)").level == YELLOW


def test_gray():
    assert RULES.classify("임원ㆍ주요주주특정증권등소유상황보고서").level == GRAY


def test_default_yellow():
    c = RULES.classify("분기보고서 (2026.09)")
    assert c.level == YELLOW and c.keyword is None


def test_split_prefix():
    assert split_prefix("[발행조건확정]증권신고서") == ("발행조건확정", "증권신고서")
    assert split_prefix("사업보고서") == (None, "사업보고서")


def test_relevance():
    assert RULES.is_relevant("유한양행", None)          # 감시 목록
    assert RULES.is_relevant("어떤제약", "21102")        # 의약품 제조
    assert RULES.is_relevant("어떤의료기기", "27112")
    assert not RULES.is_relevant("어떤은행", "64121")
    assert not RULES.is_relevant("어떤회사", None)
