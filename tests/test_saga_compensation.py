"""Tests for saga compensation — verifies actual DB rollback."""
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Ensure migrations run
async def _setup():
    from shared.migrations import migration_manager
    await migration_manager.migrate()
asyncio.run(_setup())


def test_saga_compensation_rolls_back():
    """Verify that consolidation compensate actually deletes from core_memory."""
    from core import memory_manager
    from shared.saga import Saga

    async def test():
        mm = memory_manager

        # Step 1: Manually save a fact (simulating what promote does)
        await mm.user_memory("saga_test").remember("key1", "value1", 0.9)
        results = await mm.user_memory("saga_test").recall("key1")
        assert len(results) > 0, "Fact should exist before compensation"

        # Step 2: Create a saga that fails after the first step
        async def succeed_step(data):
            # Simulate promote saving data
            await mm.user_memory("saga_test").remember("saga_key", "saga_value", 0.8)
            return {"promoted": 1}

        async def fail_step(data):
            raise RuntimeError("Simulated failure")

        async def compensate(data):
            # This should delete the promoted data
            await mm.user_memory("saga_test").forget("saga_key")

        saga = Saga("test_compensate")
        saga.add_step("promote", succeed_step, compensate)
        saga.add_step("will_fail", fail_step)

        # Step 3: Execute saga — step 2 fails, compensate runs
        try:
            await saga.execute({"user_id": "saga_test"})
        except RuntimeError:
            pass

        # Step 4: Verify compensation worked
        results = await mm.user_memory("saga_test").recall("saga_key")
        assert len(results) == 0, "saga_key should be deleted after compensation"

        # Verify original fact still exists
        results = await mm.user_memory("saga_test").recall("key1")
        assert len(results) > 0, "key1 should still exist (not rolled back)"

        print("Compensation test PASSED: saga_key deleted, key1 preserved")

    asyncio.run(test())


def test_saga_compensation_partial():
    """Verify compensation handles partial failures gracefully."""
    from core import memory_manager
    from shared.saga import Saga

    async def test():
        mm = memory_manager

        # Save two facts
        await mm.user_memory("saga_partial").remember("keep_me", "yes", 0.9)
        await mm.user_memory("saga_partial").remember("delete_me", "no", 0.5)

        async def promote_step(data):
            # This succeeds
            return {"promoted": 1}

        async def fail_step(data):
            raise RuntimeError("Boom")

        async def compensate(data):
            # Try to delete — should not crash even if key doesn't exist
            await mm.user_memory("saga_partial").forget("delete_me")

        saga = Saga("test_partial")
        saga.add_step("promote", promote_step, compensate)
        saga.add_step("fail", fail_step)

        try:
            await saga.execute()
        except RuntimeError:
            pass

        # Verify
        results = await mm.user_memory("saga_partial").recall("keep_me")
        assert len(results) > 0, "keep_me should survive"

        print("Partial compensation test PASSED")

    asyncio.run(test())


def test_saga_success_no_compensation():
    """Verify compensation is NOT called on success."""
    from shared.saga import Saga

    async def test():
        compensate_called = False

        async def step1(data):
            return {"r": 1}

        async def compensate1(data):
            nonlocal compensate_called
            compensate_called = True

        saga = Saga("test_success")
        saga.add_step("step1", step1, compensate1)

        await saga.execute()
        assert not compensate_called, "Compensate should not be called on success"
        assert saga.status.value == "completed"

        print("Success test PASSED: compensate not called")

    asyncio.run(test())
