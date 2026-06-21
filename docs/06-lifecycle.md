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

Определение важных моментов по эмоциональным маркерам. Русский + английский + эмодзи + паттерны фраз.

```python
from lifecycle.emotion_trigger import EmotionTrigger

et = EmotionTrigger()

# Русский
should, reason, weight = et.should_save("Я тебя люблю!")
# (True, "emotion_love", 0.8)

should, reason, weight = et.should_save("Спасибо за помощь!")
# (True, "emotion_gratitude", 0.5)

# Английский
should, reason, weight = et.should_save("I love you so much")
# (True, "emotion_love", 0.8)

# Эмодзи
should, reason, weight = et.should_save("Отлично! 😊🎉")
# (True, "emotion_joy", 0.5)

# Шум — не сохранять
should, reason, weight = et.should_save("ok")
# (False, "", 0.0)
```

**Категории эмоций (8):**

| Эмоция | Примеры маркеров | Вес |
|--------|-----------------|-----|
| love | люблю, обожаю, love, ❤️ | 0.7-0.8 |
| fear | боюсь, страшно, afraid, 😨 | 0.6-0.7 |
| anger | ненавижу, бесит, hate, 😡 | 0.6-0.7 |
| joy | счастлив, рад, happy, 😊 | 0.5 |
| gratitude | спасибо, благодарю, thanks | 0.5 |
| importance | важно, запомни, remember | 0.7-0.8 |
| sadness | грустно, печально, sad, 😢 | 0.6 |
| surprise | удивлён, wow, 🤯 | 0.5 |

**Паттерны ф regex:** "я тебя люблю", "никогда не забудь", "это важно запомнить"

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
