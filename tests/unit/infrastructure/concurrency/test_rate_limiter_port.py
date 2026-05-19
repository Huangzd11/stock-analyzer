"""限流器端口契约测试。"""

from stock_analyzer.infrastructure.concurrency import TokenBucket
from stock_analyzer.ports.rate_limiter import IRateLimiter


def test_token_bucket_implements_rate_limiter_port() -> None:
    bucket = TokenBucket(rate=5.0, capacity=3)
    assert isinstance(bucket, IRateLimiter)
