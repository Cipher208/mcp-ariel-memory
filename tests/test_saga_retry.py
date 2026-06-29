"""Tests for B7: Saga retry with exponential backoff."""

import pytest
from shared.saga import Saga


@pytest.mark.asyncio
async def test_transient_failure_retries_then_succeeds():
    """ConnectionError retries 3 times then succeeds."""
    call_count = {"n": 0}

    async def flaky(data):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise ConnectionError("boom")
        return {"value": 42}

    saga = Saga("flaky", timeout_seconds=30)
    saga.add_step(
        "call",
        flaky,
        retry_attempts=3,
        retry_backoff=0.01,
        retry_on=(ConnectionError,),
    )
    result = await saga.execute({})
    assert result["value"] == 42
    assert call_count["n"] == 3


@pytest.mark.asyncio
async def test_non_transient_error_propagates_immediately():
    """ValueError is NOT retryable — propagates without retry."""

    async def step(data):
        raise ValueError("permanent")

    saga = Saga("perm")
    saga.add_step("s", step, retry_attempts=5, retry_backoff=0.01)
    with pytest.raises(ValueError):
        await saga.execute({})


@pytest.mark.asyncio
async def test_retry_gives_up_after_attempts():
    """TimeoutError retries 2 times then gives up."""

    async def always_fail(data):
        raise TimeoutError("flaky network")

    saga = Saga("ttl")
    saga.add_step(
        "net",
        always_fail,
        retry_attempts=2,
        retry_backoff=0.01,
    )
    with pytest.raises(TimeoutError):
        await saga.execute({})


@pytest.mark.asyncio
async def test_retry_compensates_on_failure():
    """After retries exhausted, previous completed steps get compensated."""
    completed = []
    compensated = []

    async def succeed_step(data):
        completed.append("step1")
        return {"step1_done": True}

    async def fail_step(data):
        raise ConnectionError("down")

    async def undo(data):
        compensated.append("undo_step1")

    saga = Saga("comp_retry")
    saga.add_step("succeed", succeed_step, compensation=undo)
    saga.add_step(
        "will_fail",
        fail_step,
        retry_attempts=2,
        retry_backoff=0.01,
    )
    with pytest.raises(ConnectionError):
        await saga.execute({})
    # Step 1 completed → should be compensated
    assert "undo_step1" in compensated
