# Жизненный цикл — lifecycle/ (async)

## ForgettingSystem (`lifecycle/forgetting.py`)

Забывание: decay, архивация через `ArchivedMemories`, сжатие.

```python
from lifecycle.forgetting import ForgettingSystem
fs = ForgettingSystem()
stats = await fs.cleanup()
# {"decayed": 15, "archived": 3, "compressed": 2}

# Архивация: использует ArchivedMemories.archive()
await fs.archive_old_entries()
```

## ConsolidationEngine (`lifecycle/consolidation.py`)

```python
from lifecycle.consolidation import ConsolidationEngine
ce = ConsolidationEngine()
await ce.consolidate_staging("alice", staging_items, min_importance=0.7)
await ce.consolidate_episodes("alice", min_weight=0.7)
stats = await ce.get_stats("alice")
```

## EmotionTrigger (`lifecycle/emotion_trigger.py`)

Определение важных моментов. Русский + английский + эмодзи + regex паттерны.

```python
from lifecycle.emotion_trigger import EmotionTrigger
et = EmotionTrigger()

# Русский
et.should_save("Я тебя люблю!")     # (True, "emotion_love", 0.8)
et.should_save("Спасибо за помощь!") # (True, "emotion_gratitude", 0.5)
et.should_save("Это важно запомнить") # (True, "emotion_importance", 0.7)

# Английский
et.should_save("I love you so much") # (True, "emotion_love", 0.8)

# Эмодзи
et.should_save("Отлично! 😊🎉")     # (True, "emotion_joy", 0.5)

# Шум
et.should_save("ok")                 # (False, "", 0.0)
```

**8 категорий эмоций:**

| Эмоция | Примеры | Вес |
|--------|---------|-----|
| love | люблю, love, ❤️ | 0.7-0.8 |
| fear | боюсь, afraid, 😨 | 0.6-0.7 |
| anger | ненавижу, hate, 😡 | 0.6-0.7 |
| joy | счастлив, happy, 😊 | 0.5 |
| gratitude | спасибо, thanks | 0.5 |
| importance | важно, remember | 0.7-0.8 |
| sadness | грустно, sad, 😢 | 0.6 |
| surprise | удивлён, wow, 🤯 | 0.5 |

**Авто-тригеры:** joy > 0.8 (0.6), state_delta > 0.15 (0.4), >300 chars (0.3), 3+ вопросов (0.4), 2+ ! (0.3)

## ConsolidationEngine (`lifecycle/consolidation.py`)

```python
from lifecycle.consolidation import ConsolidationEngine
ce = ConsolidationEngine()
ce.consolidate_staging("alice", staging_items, min_importance=0.7)
ce.consolidate_episodes("alice", min_weight=0.7)
ce.get_stats("alice")
```
