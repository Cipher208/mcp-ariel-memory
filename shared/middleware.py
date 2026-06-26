"""
Middleware Pipeline — цепочка обработчиков для перехвата и модификации запросов.
Аналог middleware_pipeline.py из ariel.
"""
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MiddlewareContext:
    """Контекст, передаваемый через pipeline."""
    tool_name: str = ""
    user_id: str = "default"
    args: Dict = field(default_factory=dict)
    result: Any = None
    metadata: Dict = field(default_factory=dict)
    start_time: float = 0.0
    blocked: bool = False
    block_reason: str = ""


MiddlewareNext = Callable[[MiddlewareContext], Any]


class Middleware:
    """Базовый класс middleware."""
    name: str = "base"

    async def process(self, ctx: MiddlewareContext, next: MiddlewareNext) -> Any:
        return await next(ctx)


class RateLimitMiddleware(Middleware):
    """Ограничение частоты запросов."""
    name = "rate_limit"

    def __init__(self, max_per_minute: int = 100):
        self._max = max_per_minute
        self._requests: Dict[str, List[float]] = {}

    async def process(self, ctx: MiddlewareContext, next: MiddlewareNext) -> Any:
        now = time.time()
        user_requests = self._requests.setdefault(ctx.user_id, [])
        user_requests[:] = [t for t in user_requests if now - t < 60]

        if len(user_requests) >= self._max:
            ctx.blocked = True
            ctx.block_reason = "Rate limit exceeded (%d/min)" % self._max
            logger.warning("Rate limit hit for user %s" % ctx.user_id)
            return {"error": ctx.block_reason}

        user_requests.append(now)
        return await next(ctx)


class AuditMiddleware(Middleware):
    """Логирование всех вызовов."""
    name = "audit"

    async def process(self, ctx: MiddlewareContext, next: MiddlewareNext) -> Any:
        ctx.start_time = time.time()
        logger.info("Tool call: %s (user=%s)" % (ctx.tool_name, ctx.user_id))

        result = await next(ctx)

        elapsed = time.time() - ctx.start_time
        logger.info("Tool completed: %s in %.3fs" % (ctx.tool_name, elapsed))
        ctx.metadata["elapsed"] = elapsed
        return result


class ImportanceGateMiddleware(Middleware):
    """Фильтр шума — пропускает только важные сообщения.
    Полная версия из agent_core/cognitive/importance_gate.py"""

    def __init__(self, min_length: int = 15, threshold: float = 0.3,
                 technical_weight: float = 0.3, question_weight: float = 0.2):
        self._min_length = min_length
        self._threshold = threshold
        self._technical_weight = technical_weight
        self._question_weight = question_weight
        import re
        self._technical_pattern = re.compile(
            r"\b(баг|функция|класс|ошибка|конфиг|redis|sqlite|api|endpoint|"
            r"модуль|сервис|деплой|тест|репозиторий|коммит|branch|merge|"
            r"database|query|schema|migration|cache|queue|handler|middleware|"
            r"async|await|payload|metadata|event|state|saga|fsa)\b",
            re.IGNORECASE,
        )
        self._noise_pattern = re.compile(
            r"^(ок|да|нет|понял|хорошо|спасибо|ага|угу|йес|норм|ясно|"
            r"ok|yes|no|thanks|got it|fine|well|cool|great|nice)$",
            re.IGNORECASE,
        )

    async def process(self, ctx: MiddlewareContext, next: MiddlewareNext) -> Any:
        if ctx.tool_name not in ("memory_user_remember", "memory_agent_remember",
                                  "memory_user_episode_save", "memory_agent_episode_save"):
            return await next(ctx)

        text = ctx.args.get("value", ctx.args.get("summary", ""))
        importance = ctx.args.get("importance", 0.5)

        if importance < self._threshold:
            ctx.metadata["bypassed"] = True
            return {"status": "skipped", "reason": "below_importance_threshold"}

        return await next(ctx)

    def calculate_score(self, text: str) -> float:
        """Полный расчёт importance из оригинала."""
        if not text:
            return 0.0
        if self._noise_pattern.match(text):
            return 0.1

        score = 0.3
        if len(text) > self._min_length:
            score += 0.2
        if len(text) > 100:
            score += 0.1
        if "?" in text:
            score += self._question_weight
        if self._technical_pattern.search(text):
            score += self._technical_weight
        if text.count("\n") > 2:
            score += 0.1
        if any(c.isdigit() for c in text) and len(text) > 30:
            score += 0.1
        return min(1.0, score)


class ValidationMiddleware(Middleware):
    """Валидация параметров."""
    name = "validation"

    async def process(self, ctx: MiddlewareContext, next: MiddlewareNext) -> Any:
        if not ctx.user_id:
            ctx.blocked = True
            ctx.block_reason = "user_id is required"
            return {"error": ctx.block_reason}

        if ctx.tool_name in ("memory_user_remember", "memory_agent_remember"):
            if not ctx.args.get("key"):
                ctx.blocked = True
                ctx.block_reason = "key is required"
                return {"error": ctx.block_reason}

        return await next(ctx)


class DedupMiddleware(Middleware):
    """Дедупликация запросов."""
    name = "dedup"

    def __init__(self, window_seconds: int = 5):
        self._window = window_seconds
        self._recent: Dict[str, float] = {}

    async def process(self, ctx: MiddlewareContext, next: MiddlewareNext) -> Any:
        now = time.time()
        key = "%s:%s:%s" % (ctx.user_id, ctx.tool_name, str(sorted(ctx.args.items())))

        if key in self._recent and now - self._recent[key] < self._window:
            ctx.metadata["deduped"] = True
            return {"status": "deduped"}

        self._recent[key] = now
        return await next(ctx)


class MiddlewarePipeline:
    """Цепочка middleware."""

    def __init__(self):
        self._middlewares: List[Middleware] = []

    def add(self, middleware: Middleware) -> "MiddlewarePipeline":
        self._middlewares.append(middleware)
        return self

    async def execute(self, ctx: MiddlewareContext, handler: Callable) -> Any:
        async def _run(index: int, ctx: MiddlewareContext) -> Any:
            if index >= len(self._middlewares):
                result = handler(ctx)
                if hasattr(result, '__await__'):
                    return await result
                return result
            return await self._middlewares[index].process(ctx, lambda c: _run(index + 1, c))

        return await _run(0, ctx)

    def list_middlewares(self) -> List[str]:
        return [m.name for m in self._middlewares]


# Default pipeline
default_pipeline = MiddlewarePipeline()
default_pipeline.add(ValidationMiddleware())
default_pipeline.add(RateLimitMiddleware())
default_pipeline.add(ImportanceGateMiddleware())
default_pipeline.add(AuditMiddleware())
default_pipeline.add(DedupMiddleware())
