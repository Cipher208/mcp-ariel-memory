"""
Emotion Trigger - saves important moments to episodic memory
"""
import re
from typing import Tuple

EMOTION_MARKERS = {
    "love": ["люблю", "love", "обожаю", "адорю"],
    "fear": ["боюсь", "afraid", "страшно"],
    "anger": ["ненавижу", "hate", "бесит"],
    "joy": ["счастлив", "happy", "рад"],
    "gratitude": ["спасибо", "thanks", "благодарю"],
    "importance": ["важно", "important", "запомни", "remember", "никогда не забудь"],
}

STATE_SHIFT_THRESHOLD = 0.15


class EmotionTrigger:
    def should_save(self, message: str, emotional_state: dict = None,
                    state_delta: dict = None) -> Tuple[bool, str, float]:
        msg_lower = message.lower()

        for emotion, markers in EMOTION_MARKERS.items():
            for marker in markers:
                if marker in msg_lower:
                    weight = 0.7 if emotion in ("love", "fear", "anger") else 0.5
                    return True, f"emotion_{emotion}", weight

        if emotional_state:
            if emotional_state.get("joy", 0) > 0.8 or emotional_state.get("interest", 0) > 0.8:
                return True, "high_emotion", 0.6

        if state_delta:
            for key, delta in state_delta.items():
                if abs(delta) > STATE_SHIFT_THRESHOLD:
                    return True, f"state_shift_{key}", 0.4

        if len(message) > 300:
            return True, "long_message", 0.3

        if message.count("?") >= 3:
            return True, "complex_question", 0.4

        return False, "", 0.0
