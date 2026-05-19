"""令牌桶限流测试。"""

import time

import pytest

from stock_analyzer.infrastructure.concurrency import TokenBucket


def test_token_bucket_blocks_when_empty() -> None:
    bucket = TokenBucket(rate=10.0, capacity=2)
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False


def test_token_bucket_burst_allows_initial_capacity() -> None:
    bucket = TokenBucket(rate=1.0, capacity=5)
    for _ in range(5):
        assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False


def test_token_bucket_refills_over_time() -> None:
    bucket = TokenBucket(rate=100.0, capacity=1)
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False
    time.sleep(0.02)
    assert bucket.try_acquire() is True


def test_token_bucket_rejects_invalid_rate() -> None:
    with pytest.raises(ValueError, match="rate"):
        TokenBucket(rate=0, capacity=1)


def test_token_bucket_rejects_invalid_capacity() -> None:
    with pytest.raises(ValueError, match="capacity"):
        TokenBucket(rate=1.0, capacity=0)
