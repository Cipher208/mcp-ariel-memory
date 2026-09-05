"""Fractional index keys (S1 order_key) — CC0 fractional-indexing паттерн на hex-цифрах.

Ключ — строка hex-цифр; лексикографический порядок строк = порядок записей.
Без внешних зависимостей (S12: vendor-минимум вместо пакета).
"""

from __future__ import annotations

_START = "08000000"
_DIGITS = "0123456789abcdef"
_MID = "8"


def midpoint(a: str | None = None, b: str | None = None) -> str:
    """Ключ, лексикографически следующий после ``a`` и перед ``b``.

    - midpoint(None, None) — стартовый ключ;
    - midpoint(a, None) — следующий за a (монотонный append);
    - midpoint(None, b) — предыдущий перед b;
    - midpoint(a, b) — между a и b при a < b; при исчерпании глубины
      ключ расширяется (a + "8"), а не вырождается.

    Raises:
        ValueError: a >= b либо пустой интервал (a — префикс b из нулей).

    """
    if not a and not b:
        return _START
    if not a:
        return _decrement(b or "")
    if not b:
        return _increment(a)
    if a >= b:
        msg = f"midpoint: a >= b ({a!r} >= {b!r})"
        raise ValueError(msg)
    for i in range(max(len(a), len(b))):
        da = _DIGITS.index(a[i]) if i < len(a) else 0
        db = _DIGITS.index(b[i]) if i < len(b) else 0
        if db > da:
            if db - da >= 2:
                # a[:i] дополнен нулями, когда i за концом a (a — префикс b)
                return a[:i].ljust(i, "0") + _DIGITS[(da + db) // 2]
            # соседние цифры: уходим на уровень глубже за концом a
            return a + _MID
    msg = f"no key between {a!r} and {b!r} (adjacent zero-prefixes)"
    raise ValueError(msg)


def _increment(a: str) -> str:
    """Следующий за a: бамп последней цифры; хвост из 'f' → расширение строки."""
    if not a:
        return _START
    if a[-1] != "f":
        return a[:-1] + _DIGITS[_DIGITS.index(a[-1]) + 1]
    return a + "0"


def _decrement(b: str) -> str:
    """Предыдущий перед b; у пола ('0'-хвост) поднимаемся на цифру выше."""
    if not b:
        msg = "cannot decrement empty key"
        raise ValueError(msg)
    if b[-1] != "0":
        return b[:-1] + _DIGITS[_DIGITS.index(b[-1]) - 1]
    return _decrement(b[:-1]) + "f"
