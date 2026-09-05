"""S11: LoCoMo dataset loader — локальный JSON, offline (сеть не нужна).

Источник схемы: официальный бенчмарк LoCoMo — github.com/snap-research/locomo
(ACL 2024, «Evaluating Very Long-Term Conversational Memory of LLM Agents»),
файл data/locomo10.json. Форма сверена с реальным файлом и README (раздел
Data) + task_eval/evaluation.py (семантика категорий) на момент реализации.
Тестовый фрагмент — tests/fixtures/locomo_mini.json, собран вручную по этой
схеме (не выдуман).

Официальная схема: JSON-массив из ~10 «сэмплов» (разговоров):
  [
    {
      "sample_id": ...,
      "conversation": {
        "speaker_a": "...", "speaker_b": "...",
        "session_<num>": [ {"speaker": "...", "dia_id": "D<num>:<turn>",
                            "text": "..."}, ... ],
        "session_<num>_date_time": "..."
      },
      "qa": [ {"question": ..., "answer": ..., "category": 1..5,
               "evidence": ["D1:3", ...],            # dia_id turn-ов с ответом
               "adversarial": true|false             # не во всех выгрузках; cat 5 = adversarial
              } ]
    }, ...
  ]

Категории (task_eval/evaluation.py официального репо):
  1 multi_hop, 2 temporal, 3 open_domain, 4 single_hop, 5 adversarial.

Adversarial (cat 5 / флаг adversarial): в официальном eval зачёт только при
воздержании («no information available») → в контракте этого harness это
abstention: expected_answer="" (честная система НЕ отвечает).

Контракт как у eval/datasets.load_eval_bundle: (list[EvalQuestion], {session_id: text})
— corpus полный, questions ограничены limit.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from eval.datasets import EvalQuestion

CATEGORY_NAMES = {1: "multi_hop", 2: "temporal", 3: "open_domain", 4: "single_hop", 5: "adversarial"}
_DIA_ID_RE = re.compile(r"^D(\d+):")
_SESSION_KEY_RE = re.compile(r"^session_(\d+)$")


def _evidence_sessions(sample_id: str, evidence: list[Any]) -> list[str]:
    """dia_id 'D1:3' → session id corpus (первое число — номер сессии)."""
    out = []
    for item in evidence:
        m = _DIA_ID_RE.match(str(item))
        if m:
            out.append(f"conv{sample_id}-s{m.group(1)}")
    return out


def load_locomo(path: str | Path, limit: int = 50, include_adversarial: bool = True) -> tuple[list[EvalQuestion], dict[str, str]]:
    """LoCoMo JSON → (questions, sessions) — тот же контракт, что load_eval_bundle.

    sessions: session_id = 'conv<sample_id>-s<num>' → «speaker: text» строки.
    evidence dia_id маппится в session id (для recall@k harness).
    include_adversarial=False выкидывает adversarial QA (cat 5 / флаг).
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    questions: list[EvalQuestion] = []
    sessions: dict[str, str] = {}
    for conv_idx, sample in enumerate(data):
        sample_id = str(sample.get("sample_id", conv_idx))
        conv = sample.get("conversation") or {}
        for key, turns in conv.items():
            m = _SESSION_KEY_RE.match(str(key))
            if m:
                sid = f"conv{sample_id}-s{m.group(1)}"
                sessions[sid] = "\n".join(f"{t.get('speaker', '?')}: {t.get('text', '')}" for t in turns)
        for qa_idx, qa in enumerate(sample.get("qa") or []):
            adversarial = bool(qa.get("adversarial")) or qa.get("category") == 5
            if adversarial and not include_adversarial:
                continue
            category = CATEGORY_NAMES.get(qa.get("category"), f"cat{qa.get('category')}")
            if adversarial:
                category = "adversarial"
            questions.append(
                EvalQuestion(
                    q_id=f"locomo-{sample_id}-{qa.get('question_id', qa_idx)}",
                    question=str(qa.get("question") or ""),
                    expected_answer="" if adversarial else str(qa.get("answer") or ""),
                    category=category,
                    evidence_session_ids=_evidence_sessions(sample_id, qa.get("evidence") or []),
                )
            )
    return questions[:limit] if limit else questions, sessions


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="LoCoMo loader stats (S11): parse local JSON, map categories — read-only")
    ap.add_argument("json_path", help="path to LoCoMo JSON (official locomo10.json schema)")
    ap.add_argument("--limit", type=int, default=50, help="max QA questions (default 50)")
    ap.add_argument("--dry-run", action="store_true", help="no-op: loader is read-only, corpus is not ingested")
    args = ap.parse_args(argv)
    questions, sessions = load_locomo(args.json_path, args.limit)
    cats: dict[str, int] = {}
    for q in questions:
        cats[q.category] = cats.get(q.category, 0) + 1
    print(f"sessions: {len(sessions)}")
    print(f"qa: {len(questions)} (limit={args.limit})")
    print(f"categories: {json.dumps(cats, ensure_ascii=False)}")
    print("mapping: 1=multi_hop 2=temporal 3=open_domain 4=single_hop 5=adversarial(→abstention)")
    print("dry-run: corpus not ingested")
    return 0


if __name__ == "__main__":
    sys.exit(main())
