"""S11: LoCoMo loader — фикстура-мини по официальной схеме (snap-research/locomo)."""

import json
from pathlib import Path

import pytest

from eval.datasets import EvalQuestion
from eval.locomo import CATEGORY_NAMES, load_locomo

FIXTURE = Path(__file__).parents[1] / "fixtures" / "locomo_mini.json"


def test_schema_docstring_names_official_source() -> None:
    """Докстринг обязан называть источник схемы (не выдуманная)."""
    import eval.locomo as mod

    assert "snap-research/locomo" in (mod.__doc__ or "")


def test_fixture_parses_and_maps_categories() -> None:
    questions, sessions = load_locomo(FIXTURE)
    assert set(sessions) == {"conv0-s1", "conv0-s2"}
    assert "Caroline: " in sessions["conv0-s1"]
    cats = {q.category for q in questions}
    assert cats == {"multi_hop", "temporal", "single_hop", "adversarial"}
    assert cats <= set(CATEGORY_NAMES.values())


def test_qa_contract_matches_harness_dataset() -> None:
    questions, _ = load_locomo(FIXTURE)
    for q in questions:
        assert isinstance(q, EvalQuestion)
        assert q.q_id.startswith("locomo-")
        assert q.question
        assert isinstance(q.expected_answer, str)
        assert set(q.evidence_session_ids) <= {"conv0-s1", "conv0-s2"}, "evidence dia_id → session id корпуса"


def test_adversarial_becomes_abstention_and_is_filterable() -> None:
    questions, _ = load_locomo(FIXTURE)
    adv = [q for q in questions if q.category == "adversarial"]
    assert len(adv) == 1 and adv[0].expected_answer == "", "adversarial → пустой expected (abstention-контракт harness)"

    filtered, _ = load_locomo(FIXTURE, include_adversarial=False)
    assert all(q.category != "adversarial" for q in filtered)
    assert len(filtered) == len(questions) - 1


def test_limit_and_official_flag_field() -> None:
    limited, _ = load_locomo(FIXTURE, limit=2)
    assert len(limited) == 2
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert all("adversarial" in qa for qa in raw[0]["qa"]), "fixture использует официальный qa-флаг adversarial"


def test_cli_dry_run_stats(capsys: pytest.CaptureFixture[str]) -> None:
    from eval.locomo import main

    rc = main([str(FIXTURE), "--limit", "10", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "sessions: 2" in out and "qa: 4 (limit=10)" in out
    assert '"adversarial": 1' in out
