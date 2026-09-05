"""Wire-тест: tier_l0 должен стоять в ночной цепочке backup_cron (S6, живой вызов)."""

from pathlib import Path


def test_tier_l0_wired_into_nightly_hooks() -> None:
    src = Path("features/backup_cron.py").read_text(encoding="utf-8")
    assert "from lifecycle.l0_tiers import tier_l0" in src
    assert "tier_l0()" in src  # вызов в _fire_nightly_hooks, а не только импорт
    assert "L0 tiering" in src  # результат попадает в отчёт
