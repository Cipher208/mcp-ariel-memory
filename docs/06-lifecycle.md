# Жизненный цикл — lifecycle/

## ForgettingSystem (`lifecycle/forgetting.py`)

Забывание: decay, архивация, сжатие.

```python
from lifecycle.forgetting import ForgettingSystem

fs = ForgettingSystem()
stats = fs.cleanup()
# {"decayed": 15, "archived": 3, "compressed": 2}

fs.decay_importance()        # экспоненциальный decay
fs.archive_old_entries()     # архивация > 90 дней + importance < 0.3
fs.compress_duplicates()     # удаление дубликатов
```

## EmotionTrigger (`lifecycle/emotion_trigger.py`)

Определение важных моментов по эмоциональным маркерам.

```python
from lifecycle.emotion_trigger import EmotionTrigger

et = EmotionTrigger()
should, reason, weight = et.should_save("I love this!")
# (True, "emotion_love", 0.7)

should, reason, weight = et.should_save("ok")
# (False, "", 0.0)
```

**Эмоциональные маркеры:**

| Эмоция | Маркеры | Вес |
|--------|---------|-----|
| love | люблю, love, обожаю | 0.7 |
| fear | боюсь, afraid, страшно | 0.7 |
| anger | ненавижу, hate, бесит | 0.7 |
| joy | счастлив, happy, рад | 0.5 |
| gratitude | спасибо, thanks | 0.5 |
| importance | важно, important, запомни | 0.5 |

**Авто-тригеры:**
- joy > 0.8 → weight 0.6
- state_delta > 0.15 → weight 0.4
- > 300 символов → weight 0.3
- 3+ вопросов → weight 0.4

## ConsolidationEngine (`lifecycle/consolidation.py`)

Консолидация из staging и эпизодов в L4.

```python
from lifecycle.consolidation import ConsolidationEngine

ce = ConsolidationEngine()
result = ce.consolidate_staging("alice", staging_items, min_importance=0.7)
# {"promoted": 3, "skipped": 2}

count = ce.consolidate_episodes("alice", min_weight=0.7)
stats = ce.get_stats("alice")
# {"total": 45, "high_importance": 12, "low_importance": 8}
```
