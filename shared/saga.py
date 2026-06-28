"""
Saga — pattern for multi-step operations with compensation (rollback).
Includes watchdog for detecting stuck sagas and persistence for recovery.
"""

import asyncio
import json
import logging
import threading
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SAGA_DIR = Path.home() / ".mcp-ariel-memory" / "sagas"


class SagaStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    STUCK = "stuck"  # detected by watchdog


@dataclass
class SagaStep:
    name: str
    action: Callable[[dict], Coroutine[Any, Any, dict]]
    compensation: Callable[[dict], Coroutine[Any, Any, None]] | None = None
    timeout_seconds: int | None = None  # step timeout (None = use saga timeout)
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
        compensation: Callable[[dict], Coroutine[Any, Any, None]] | None = None,
        timeout_seconds: int | None = None,
    ) -> "Saga":
        self._steps.append(
            SagaStep(name=name, action=action, compensation=compensation, timeout_seconds=timeout_seconds)
        )
        return self

    def _save_state(self):
        """Save state to disk for crash recovery."""
        state_file = SAGA_DIR / (self._saga_id + ".json")
        state = {
            "name": self.name,
            "saga_id": self._saga_id,
            "status": self._status.value,
            "current_step": self._current_step,
            "started_at": self._started_at,
            "data": self._data,
            "steps": [{"name": s.name, "status": s.status.value, "result": s.result} for s in self._steps],
        }
        try:
            state_file.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save saga state: %s" % e)

    def _load_state(self, saga_id: str) -> dict | None:
        """Load state from disk."""
        state_file = SAGA_DIR / (saga_id + ".json")
        if state_file.exists():
            try:
                return json.loads(state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    def _cleanup_state(self):
        """Delete state file after completion."""
        state_file = SAGA_DIR / (self._saga_id + ".json")
        if state_file.exists():
            try:
                state_file.unlink()
            except Exception:
                pass

    async def execute(self, initial_data: dict | None = None) -> dict:
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
                    # Support for nested sagas
                    step_timeout = step.timeout_seconds or self.timeout_seconds
                    if isinstance(step.action, Saga):
                        inner = step.action
                        step.result = await asyncio.wait_for(inner.execute(self._data), timeout=step_timeout)
                    else:
                        action_result = step.action(self._data)
                        if hasattr(action_result, "__await__"):
                            step.result = await asyncio.wait_for(action_result, timeout=step_timeout)
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
            if step.status != SagaStatus.COMPLETED:
                continue

            # Nested sagas: compensate all completed steps of the inner saga
            if isinstance(step.action, Saga):
                inner = step.action
                for j in range(len(inner._steps) - 1, -1, -1):
                    inner_step = inner._steps[j]
                    if inner_step.status == SagaStatus.COMPLETED and inner_step.compensation:
                        try:
                            await inner_step.compensation(inner_step.data)
                            logger.info("Saga '%s' compensated inner step '%s'" % (self.name, inner_step.name))
                        except Exception as e:
                            logger.error(
                                "Saga '%s' inner compensation failed for '%s': %s" % (self.name, inner_step.name, e)
                            )
            elif step.compensation:
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
            "steps": [{"name": s.name, "status": s.status.value, "result": s.result} for s in self._steps],
        }


class SagaWatchdog:
    """Detect stuck sagas and recover from crashes."""

    def __init__(self, check_interval: int = 60, max_age_seconds: int = 600):
        self.check_interval = check_interval
        self.max_age_seconds = max_age_seconds
        self._running = False
        self._thread: threading.Thread | None = None

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
        """Find and mark stuck sagas."""
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

    def get_stuck_sagas(self) -> list[dict[str, Any]]:
        """Get list of stuck sagas."""
        stuck = []
        SAGA_DIR.mkdir(parents=True, exist_ok=True)

        for state_file in SAGA_DIR.glob("*.json"):
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                if state.get("status") in ("stuck", "failed", "running"):
                    age = time.time() - state.get("started_at", 0)
                    stuck.append(
                        {
                            "saga_id": state.get("saga_id"),
                            "name": state.get("name"),
                            "status": state.get("status"),
                            "current_step": state.get("current_step"),
                            "age_seconds": int(age),
                        }
                    )
            except Exception:
                pass

        return stuck

    def recover_saga(self, saga_id: str) -> dict[str, Any] | None:
        """Attempt to recover a stuck saga."""
        state_file = SAGA_DIR / (saga_id + ".json")
        if not state_file.exists():
            return None

        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            if state.get("status") != "stuck":
                return {"error": "Saga is not stuck, status: %s" % state.get("status")}

            # Mark as requiring manual intervention
            state["status"] = "manual_review_required"
            state["recovered_at"] = time.time()
            state_file.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")

            return {"status": "manual_review_required", "state": state}
        except Exception as e:
            return {"error": str(e)}

    def cleanup_completed(self) -> int:
        """Delete completed sagas older than 1 hour."""
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


# === Ready-made sagas for mcp-ariel-memory ===


async def _consolidation_gather(data: dict) -> dict:
    """Gather staging memories."""
    mm = data.get("_mm")
    if not mm:
        return {"staging_count": 0}
    user_id = data.get("user_id", "default")
    l1 = mm.user_memory(user_id).l1
    recent = l1.get_recent(20)
    data["staging_items"] = [{"content": r.content, "importance": 0.5} for r in recent]
    return {"staging_count": len(data["staging_items"])}


async def _consolidation_distill(data: dict) -> dict:
    """Filter out unimportant items."""
    items = data.get("staging_items", [])
    important = [i for i in items if i.get("importance", 0) > 0.3]
    data["important_items"] = important
    return {"distilled_count": len(important)}


async def _consolidation_promote(data: dict) -> dict:
    """Promote important items to L4."""
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
    """Rollback: delete promoted entries from core_memory."""
    mm = data.get("_mm")
    if not mm:
        return
    user_id = data.get("user_id", "default")
    items = data.get("important_items", []) + data.get("staging_items", [])
    for item in items:
        content = item.get("content", "")
        key = "auto_%s" % content[:20].replace(" ", "_").lower()
        try:
            await mm.user_memory(user_id).forget(key)
        except Exception:
            pass


def create_consolidation_saga(user_id: str, mm=None) -> Saga:
    """Consolidation saga: gather → distill → promote.
    Takes mm (memory_manager) to avoid circular imports.
    """
    saga = Saga("consolidation_%s" % user_id)
    saga.add_step("gather", _consolidation_gather, _consolidation_compensate)
    saga.add_step("distill", _consolidation_distill, _consolidation_compensate)
    saga.add_step("promote", _consolidation_promote, _consolidation_compensate)
    return saga


async def _backup_copy_db(data: dict) -> dict:
    """Copy the database."""
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
    """Verify backup integrity."""
    from pathlib import Path

    backup_path = Path(data.get("backup_path", ""))
    files = list(backup_path.glob("*.db")) if backup_path.exists() else []
    return {"verified_files": len(files)}


async def _backup_compensate(data: dict) -> None:
    """Rollback: delete failed backup."""
    import shutil
    from pathlib import Path

    backup_path = Path(data.get("backup_path", ""))
    if backup_path.exists():
        shutil.rmtree(backup_path)


def create_backup_saga() -> Saga:
    """Backup saga: copy → verify."""
    saga = Saga("backup")
    saga.add_step("copy", _backup_copy_db, _backup_compensate)
    saga.add_step("verify", _backup_verify)
    return saga
