"""Tests for shared/memory_types.py — parametrized."""

import math
import pytest
from shared.memory_types import (
    MemoryKind,
    _REGISTRY,
    apply_decay,
    can_archive,
    kind_for_text,
    validate_kind,
    boost_for_query,
    get_policy,
)


def test_all_kinds_have_policy():
    for k in MemoryKind:
        assert k in _REGISTRY, f"missing policy for {k}"


@pytest.mark.parametrize("text,valid", [
    ("fact", True),
    ("instruction", True),
    ("banana", False),
    ("", False),
])
def test_validate_kind(text, valid):
    if valid:
        assert validate_kind(text)
    else:
        assert not validate_kind(text)


def test_default_kind_recovery():
    p_banana = get_policy("banana")
    p_fact = get_policy("fact")
    assert p_banana == p_fact


def test_apply_decay_instruction_never_decays():
    assert apply_decay(0.7, "instruction", 30) == 0.7
    assert apply_decay(0.95, "instruction", 3650) == 0.95


def test_apply_decay_fact_exponential():
    days = 30
    val = apply_decay(0.5, "fact", days)
    expected = max(0.01, 0.5 * math.exp(-0.01 * days))
    assert val == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize("kind", ["instruction", "rule", "commitment"])
def test_can_archive_protected(kind):
    assert not can_archive(kind, 0.05, days_since_update=10000)


def test_can_archive_fact_conditions():
    assert can_archive("fact", 0.1, days_since_update=200)  # old, low importance
    assert not can_archive("fact", 0.9, days_since_update=200)  # high importance


@pytest.mark.parametrize("text,expected_kind", [
    ("я обещаю сделать к пятнице", MemoryKind.COMMITMENT),
    ("I commit to ship by Friday", MemoryKind.COMMITMENT),
    ("запрещено удалять базы данных", MemoryKind.RULE),
    ("do not push to main", MemoryKind.RULE),
    ("моя цель — выучить Rust", MemoryKind.GOAL),
    ("что-то нейтральное", MemoryKind.FACT),
])
def test_kind_for_text(text, expected_kind):
    assert kind_for_text(text) == expected_kind


def test_boost_for_query():
    boost_pref = boost_for_query("что я предпочитаю?", "preference")
    boost_fact = boost_for_query("что я предпочитаю?", "fact")
    assert boost_pref > boost_fact


def test_boost_capped():
    boost = boost_for_query("обязательно никогда не забывай important rule", "instruction")
    assert boost <= 0.5
