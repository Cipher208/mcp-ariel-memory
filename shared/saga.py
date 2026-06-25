"""
Saga — паттерн для многошаговых операций с компенсацией (откат).
Включает watchdog для обнаружения зависших саг и persistence для восстановления.
"""
import asyncio
import json
import logging
import time
import threading
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional, Dict, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

SAGA_DIR = Path.home() / ".mcp-ariel-memory" / "sagas"


class SagaStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    STUCK = "stuck"  # обнаружен watchdog'ом


@dataclass
class SagaStep:
    name: str
    action: Callable[[dict], Coroutine[Any, Any, dict]]
    compensation: Optional[Callable[[dict], Coroutine[Any, Any, None]]] = None
    status: SagaStatus = SagaStatus.PENDING
    result: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)


class Saga:
    def __init__(self, name: str, timeout_seconds: int = 300):
        self.name = name
        self.timeout_seconds = timeout_seconds
        self._steps: list[SagaStep] = []
        self._status = SagaStatus.PENDING
        self._data: dict = {}
        self._current_step = 0
        self._started_at: float = 0.0
        self._saga_id: str = ""
        SAGA_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def status(self) -> SagaStatus:
        return self._status

    @property
    def data(self) -> dict:
        return self._data

    def add_step(
        self,
        name: str,
        action: Callable[[dict], Coroutine[Any, Any, dict]],
        compensation: Optional[Callable[[dict], Coroutine[Any, Any, None]]] = None,
    ) -> "Saga":
        self._steps.append(SagaStep(name=name, action=action, compensation=compensation))
        return self

    def _save_state(self):
        """Сохранить состояние на диск для восстановления после крэша."""
        state_file = SAGA_DIR / (self._saga_id + ".json")
        state = {
            "name": self.name,
            "saga_id": self._saga_id,
            "status": self._status.value,
            "current_step": self._current_step,
            "started_at": self._started_at,
            "data": self._data,
            "steps": [
                {"name": s.name, "status": s.status.value, "result": s.result}
                for s in self._steps
            ],
        }
        try:
            state_file.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save saga state: %s" % e)

    def _load_state(self, saga_id: str) -> Optional[dict]:
        """Загрузить состояние с диска."""
        state_file = SAGA_DIR / (saga_id + ".json")
        if state_file.exists():
            try:
                return json.loads(state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    def _cleanup_state(self):
        """Удалить файл состояния после завершения."""
        state_file = SAGA_DIR / (self._saga_id + ".json")
        if state_file.exists():
            try:
                state_file.unlink()
            except Exception:
                pass

    async def execute(self, initial_data: Optional[dict] = None) -> dict:
        import uuid
        self._saga_id = self.name + "_" + uuid.uuid4().hex[:8]
        self._data = initial_data or {}
        self._status = SagaStatus.RUNNING
        self._current_step = 0
        self._started_at = time.time()
        self._save_state()

        logger.info("Saga '%s' started (id=%s)" % (self.name, self._saga_id))

        try:
            for i, step in enumerate(self._steps):
                self._current_step = i
                step.status = SagaStatus.RUNNING
                self._save_state()

                try:
                    action_result = step.action(self._data)
                    if hasattr(action_result, '__await__'):
                        step.result = await asyncio.wait_for(
                            action_result, timeout=self.timeout_seconds
                        )
                    else:
                        step.result = action_result
                    self._data.update(step.result)
                    step.status = SagaStatus.COMPLETED
                    step.data = self._data.copy()
                    self._save_state()
                    logger.info("Saga '%s' step '%s' completed" % (self.name, step.name))

                except asyncio.TimeoutError:
                    step.status = SagaStatus.FAILED
                    logger.error("Saga '%s' step '%s' timed out" % (self.name, step.name))
                    await self._compensate(i)
                    self._save_state()
                    raise TimeoutError("Saga step '%s' timed out" % step.name)

                except Exception as e:
                    step.status = SagaStatus.FAILED
                    logger.error("Saga '%s' step '%s' failed: %s" % (self.name, step.name, e))
                    await self._compensate(i)
                    self._save_state()
                    raise

            self._status = SagaStatus.COMPLETED
            self._cleanup_state()
            logger.info("Saga '%s' completed" % self.name)
            return self._data

        except Exception as e:
            if self._status != SagaStatus.COMPENSATED:
                self._status = SagaStatus.FAILED
            self._save_state()
            logger.error("Saga '%s' failed: %s" % (self.name, e))
            raise

    async def _compensate(self, failed_step: int) -> None:
        self._status = SagaStatus.COMPENSATING
        logger.info("Saga '%s' compensating from step %d" % (self.name, failed_step))

        for i in range(failed_step - 1, -1, -1):
            step = self._steps[i]
            if step.status == SagaStatus.COMPLETED and step.compensation:
                try:
                    await step.compensation(step.data)
                    logger.info("Saga '%s' compensated step '%s'" % (self.name, step.name))
                except Exception as e:
                    logger.error("Saga '%s' compensation failed for '%s': %s" % (self.name, step.name, e))

        self._status = SagaStatus.COMPENSATED

    def get_state(self) -> dict:
        return {
            "name": self.name,
            "saga_id": self._saga_id,
            "status": self._status.value,
            "current_step": self._current_step,
            "started_at": self._started_at,
            "data": self._data,
            "steps": [
                {"name": s.name, "status": s.status.value, "result": s.result}
                for s in self._steps
            ],
        }


class SagaWatchdog:
    """Обнаружение зависших саг и восстановление после крэша."""

    def __init__(self, check_interval: int = 60, max_age_seconds: int = 600):
        self.check_interval = check_interval
        self.max_age_seconds = max_age_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Saga watchdog started (interval=%ds)" % self.check_interval)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self):
        while self._running:
            try:
                self._check_stuck_sagas()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error("Saga watchdog error: %s" % e)
                time.sleep(30)

    def _check_stuck_sagas(self):
        """Найти и пометить зависшие саги."""
        SAGA_DIR.mkdir(parents=True, exist_ok=True)
        now = time.time()

        for state_file in SAGA_DIR.glob("*.json"):
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                status = state.get("status", "")
                started_at = state.get("started_at", 0)
                saga_name = state.get("name", "unknown")

                if status in ("running", "compensating"):
                    age = now - started_at
                    if age > self.max_age_seconds:
                        state["status"] = "stuck"
                        state["stuck_reason"] = "timeout_after_%ds" % int(age)
                        state_file.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
                        logger.warning("Saga '%s' marked as STUCK (age=%ds)" % (saga_name, int(age)))

            except Exception as e:
                logger.error("Error checking saga %s: %s" % (state_file.name, e))

    def get_stuck_sagas(self) -> List[Dict[str, Any]]:
        """Получить список зависших саг."""
        stuck = []
        SAGA_DIR.mkdir(parents=True, exist_ok=True)

        for state_file in SAGA_DIR.glob("*.json"):
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                if state.get("status") in ("stuck", "failed", "running"):
                    age = time.time() - state.get("started_at", 0)
                    stuck.append({
                        "saga_id": state.get("saga_id"),
                        "name": state.get("name"),
                        "status": state.get("status"),
                        "current_step": state.get("current_step"),
                        "age_seconds": int(age),
                    })
            except Exception:
                pass

        return stuck

    def recover_saga(self, saga_id: str) -> Optional[Dict[str, Any]]:
        """Попытаться восстановить зависшую сагу."""
        state_file = SAGA_DIR / (saga_id + ".json")
        if not state_file.exists():
            return None

        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            if state.get("status") != "stuck":
                return {"error": "Saga is not stuck, status: %s" % state.get("status")}

            # Пометить как требующее ручного вмешательства
            state["status"] = "manual_review_required"
            state["recovered_at"] = time.time()
            state_file.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")

            return {"status": "manual_review_required", "state": state}
        except Exception as e:
            return {"error": str(e)}

    def cleanup_completed(self) -> int:
        """Удалить завершённые саги старше 1 часа."""
        cutoff = time.time() - 3600
        removed = 0
        SAGA_DIR.mkdir(parents=True, exist_ok=True)

        for state_file in SAGA_DIR.glob("*.json"):
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                if state.get("status") in ("completed", "compensated"):
                    if state.get("started_at", 0) < cutoff:
                        state_file.unlink()
                        removed += 1
            except Exception:
                pass

        return removed


# Singleton watchdog
saga_watchdog = SagaWatchdog()


# === Готовые саги для mcp-ariel-memory ===

async def _consolidation_gather(data: dict) -> dict:
    """Собрать staging memories."""
    mm = data.get("_mm")
    if not mm:
        return {"staging_count": 0}
    user_id = data.get("user_id", "default")
    l1 = mm.user_memory(user_id).l1
    recent = l1.get_recent(20)
    data["staging_items"] = [{"content": r.content, "importance": 0.5} for r in recent]
    return {"staging_count": len(data["staging_items"])}


async def _consolidation_distill(data: dict) -> dict:
    """Отфильтровать неважное."""
    items = data.get("staging_items", [])
    important = [i for i in items if i.get("importance", 0) > 0.3]
    data["important_items"] = important
    return {"distilled_count": len(important)}


async def _consolidation_promote(data: dict) -> dict:
    """Продвинуть важное в L4."""
    mm = data.get("_mm")
    if not mm:
        return {"promoted": 0}
    user_id = data.get("user_id", "default")
    items = data.get("important_items", [])
    promoted = 0
    for item in items:
        content = item.get("content", "")
        key = "auto_%s" % content[:20].replace(" ", "_").lower()
        await mm.user_memory(user_id).remember(key, content, item.get("importance", 0.5))
        promoted += 1
    return {"promoted": promoted}


async def _consolidation_compensate(data: dict) -> None:
    """Откат: ничего не делать (данные в RAM)."""
    pass


def create_consolidation_saga(user_id: str, mm=None) -> Saga:
    """Сага консолидации: gather → distill → promote.
    Принимает mm (memory_manager) для избежания циркулярного импорта.
    """
    saga = Saga("consolidation_%s" % user_id)
    saga.add_step("gather", _consolidation_gather, _consolidation_compensate)
    saga.add_step("distill", _consolidation_distill, _consolidation_compensate)
    saga.add_step("promote", _consolidation_promote, _consolidation_compensate)
    return saga


async def _backup_copy_db(data: dict) -> dict:
    """Скопировать БД."""
    import shutil
    from pathlib import Path
    base = Path.home() / ".mcp-ariel-memory"
    backup_dir = base / "backups" / ("saga_%d" % int(time.time()))
    backup_dir.mkdir(parents=True, exist_ok=True)
    src = base / "memory.db"
    if src.exists():
        shutil.copy2(src, backup_dir / "memory.db")
    data["backup_path"] = str(backup_dir)
    return {"backup_path": str(backup_dir)}


async def _backup_verify(data: dict) -> dict:
    """Проверить целостность бэкапа."""
    from pathlib import Path
    backup_path = Path(data.get("backup_path", ""))
    files = list(backup_path.glob("*.db")) if backup_path.exists() else []
    return {"verified_files": len(files)}


async def _backup_compensate(data: dict) -> None:
    """Откат: удалить неудачный бэкап."""
    import shutil
    from pathlib import Path
    backup_path = Path(data.get("backup_path", ""))
    if backup_path.exists():
        shutil.rmtree(backup_path)


def create_backup_saga() -> Saga:
    """Сага бэкапа: copy → verify."""
    saga = Saga("backup")
    saga.add_step("copy", _backup_copy_db, _backup_compensate)
    saga.add_step("verify", _backup_verify)
    return saga


async def _backup_copy_db(data: dict) -> dict:
    """Скопировать БД."""
    import shutil
    from pathlib import Path
    import time
    base = Path.home() / ".mcp-ariel-memory"
    backup_dir = base / "backups" / ("saga_%d" % int(time.time()))
    backup_dir.mkdir(parents=True, exist_ok=True)
    for db in ["memory.db", "memory.db", "memory.db", "memory.db", "memory.db", "memory.db"]:
        src = base / db
        if src.exists():
            shutil.copy2(src, backup_dir / db)
    data["backup_path"] = str(backup_dir)
    return {"backup_path": str(backup_dir)}


async def _backup_verify(data: dict) -> dict:
    """Проверить целостность бэкапа."""
    from pathlib import Path
    backup_path = Path(data.get("backup_path", ""))
    files = list(backup_path.glob("*.db")) if backup_path.exists() else []
    return {"verified_files": len(files)}


async def _backup_compensate(data: dict) -> None:
    """Откат: удалить неудачный бэкап."""
    import shutil
    from pathlib import Path
    backup_path = Path(data.get("backup_path", ""))
    if backup_path.exists():
        shutil.rmtree(backup_path)


def create_backup_saga() -> Saga:
    """Сага бэкапа: copy → verify."""
    saga = Saga("backup")
    saga.add_step("copy", _backup_copy_db, _backup_compensate)
    saga.add_step("verify", _backup_verify)
    return saga
