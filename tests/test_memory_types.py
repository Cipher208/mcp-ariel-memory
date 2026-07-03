"""Tests for shared/memory_types.py — 13 typed memory categories."""

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


def test_validate_kind_accepts_known_rejects_unknown():
    assert validate_kind("fact")
    assert validate_kind("instruction")
    assert not validate_kind("banana")
    assert not validate_kind("")


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


def test_can_archive_instruction_false():
    assert not can_archive("instruction", 0.1, days_since_update=365 * 10)


def test_can_archive_rule_false():
    assert not can_archive("rule", 0.05, days_since_update=10000)


def test_can_archive_commitment_false():
    assert not can_archive("commitment", 0.05, days_since_update=2000)


def test_can_archive_fact_old_low_importance_true():
    assert can_archive("fact", 0.1, days_since_update=200)


def test_can_archive_recent_high_importance_false():
    assert not can_archive("fact", 0.9, days_since_update=200)


def test_kind_for_text_detects_commitment():
    assert kind_for_text("я обещаю сделать к пятнице") == MemoryKind.COMMITMENT
    assert kind_for_text("I commit to ship by Friday") == MemoryKind.COMMITMENT


def test_kind_for_text_detects_rule():
    assert kind_for_text("запрещено удалять базы данных") == MemoryKind.RULE
    assert kind_for_text("do not push to main") == MemoryKind.RULE


def test_kind_for_text_detects_goal():
    assert kind_for_text("моя цель — выучить Rust") == MemoryKind.GOAL


def test_kind_for_text_falls_back_to_fact():
    assert kind_for_text("что-то нейтральное") == MemoryKind.FACT


def test_boost_for_query_prefers_matching_type():
    boost_pref = boost_for_query("что я предпочитаю?", "preference")
    boost_fact = boost_for_query("что я предпочитаю?", "fact")
    assert boost_pref > boost_fact


def test_boost_capped():
    boost = boost_for_query("обязательно никогда не забывай important rule", "instruction")
    assert boost <= 0.5
