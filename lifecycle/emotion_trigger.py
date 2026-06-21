"""
Emotion Trigger — определение важных моментов по эмоциональным маркерам.
Поддержка русского + английского языков. Rule-based + pattern detection.
"""
import re
from typing import Tuple

# Маркеры эмоций (русский + английский)
EMOTION_MARKERS = {
    "love": [
        "люблю", "обожаю", "адорю", "влюблён", "дорогой", "родной",
        "love", "adore", "beloved", "dear",
    ],
    "fear": [
        "боюсь", "страшно", "ужас", "паник", "тревог", "опасаюсь",
        "afraid", "scared", "terrified", "panic", "anxiety",
    ],
    "anger": [
        "ненавижу", "бесит", "злюсь", "раздраж", "гнев", "отвращ",
        "hate", "angry", "furious", "frustrated", "annoyed",
    ],
    "joy": [
        "счастлив", "рад", "весел", "отличн", "прекрасн", "восхитительн",
        "ура", "класс", "супер", "круто",
        "happy", "glad", "cheerful", "wonderful", "amazing", "awesome",
    ],
    "gratitude": [
        "спасибо", "благодарю", "благодарн", "признателен",
        "thanks", "thank you", "grateful", "appreciate",
    ],
    "importance": [
        "важно", "критично", "срочно", "необходимо", "обязательно",
        "запомни", "никогда не забудь", "запиши",
        "important", "critical", "urgent", "remember", "never forget",
    ],
    "sadness": [
        "грустно", "печальн", "тоск", "одинок", "жаль", "жалею",
        "грусть", "слёзы", "плач",
        "sad", "sorrow", "lonely", "regret", "tears",
    ],
    "surprise": [
        "удивлён", "неожиданн", "внезапно", "нечаянно",
        "surprised", "unexpected", "suddenly", "wow",
    ],
}

# Паттерны фраз (русский)
PHRASE_PATTERNS = [
    (r"я тебя (люблю|обожаю)", "love", 0.8),
    (r"мне (нравится|нравишься)", "love", 0.6),
    (r"(боюсь|страшно) что", "fear", 0.6),
    (r"я (злюсь|раздражён)", "anger", 0.6),
    (r"(спасибо|благодарю) за", "gratitude", 0.5),
    (r"(важно|критично) чтобы", "importance", 0.7),
    (r"никогда не (забудь|забывай)", "importance", 0.8),
    (r"(хорошо|отлично|прекрасно) что", "joy", 0.5),
    (r"мне (грустно|печально)", "sadness", 0.6),
    (r"как (неожиданно|удивительно)", "surprise", 0.5),
]

# Паттерны фраз (английский)
PHRASE_PATTERNS_EN = [
    (r"i (love|adore) you", "love", 0.8),
    (r"i (really |so )?(like|enjoy)", "love", 0.6),
    (r"i('m| am) (afraid|scared) that", "fear", 0.6),
    (r"i (hate|despise)", "anger", 0.6),
    (r"(thank you|thanks) (so much|a lot|for)", "gratitude", 0.5),
    (r"(important|critical) that", "importance", 0.7),
    (r"never (forget|forget this)", "importance", 0.8),
    (r"(great|wonderful|amazing) that", "joy", 0.5),
    (r"i('m| am) (sad|upset)", "sadness", 0.6),
    (r"(wow|oh my god|no way)", "surprise", 0.5),
]

# Эмодзи-маркер
EMOJI_MARKERS = {
    "love": ["❤️", "😍", "🥰", "💕", "❤"],
    "fear": ["😨", "😱", "😰", "😥"],
    "anger": ["😡", "🤬", "😤", "💢"],
    "joy": ["😊", "🎉", "😄", "🥳", "😁"],
    "sadness": ["😢", "😭", "😞", "😔"],
    "surprise": ["😲", "🤯", "😮", "❗"],
}

STATE_SHIFT_THRESHOLD = 0.15


class EmotionTrigger:
    def should_save(self, message: str, emotional_state: dict = None,
                    state_delta: dict = None) -> Tuple[bool, str, float]:
        msg_lower = message.lower()

        # 1. Паттерны фраз (высокий приоритет)
        all_patterns = PHRASE_PATTERNS + PHRASE_PATTERNS_EN
        for pattern, emotion, weight in all_patterns:
            if re.search(pattern, msg_lower):
                return True, f"emotion_{emotion}", weight

        # 2. Маркеры эмоций
        for emotion, markers in EMOTION_MARKERS.items():
            for marker in markers:
                if marker in msg_lower:
                    weight = 0.7 if emotion in ("love", "fear", "anger") else 0.5
                    return True, f"emotion_{emotion}", weight

        # 3. Эмодзи
        for emotion, emojis in EMOJI_MARKERS.items():
            for emoji in emojis:
                if emoji in message:
                    weight = 0.7 if emotion in ("love", "fear", "anger") else 0.5
                    return True, f"emotion_{emotion}", weight

        # 4. Эмоциональное состояние из контекста
        if emotional_state:
            if emotional_state.get("joy", 0) > 0.8 or emotional_state.get("interest", 0) > 0.8:
                return True, "high_emotion", 0.6

        # 5. State shift
        if state_delta:
            for key, delta in state_delta.items():
                if abs(delta) > STATE_SHIFT_THRESHOLD:
                    return True, f"state_shift_{key}", 0.4

        # 6. Длинное сообщение
        if len(message) > 300:
            return True, "long_message", 0.3

        # 7. Много вопросов
        if message.count("?") >= 3:
            return True, "complex_question", 0.4

        # 8. Восклицательные знаки
        if message.count("!") >= 2:
            return True, "exclamation", 0.3

        return False, "", 0.0
