"""
Lifecycle Module - forgetting, emotion trigger, consolidation
"""
from .forgetting import ForgettingSystem
from .emotion_trigger import EmotionTrigger
from .consolidation import ConsolidationEngine

__all__ = ["ForgettingSystem", "EmotionTrigger", "ConsolidationEngine"]
