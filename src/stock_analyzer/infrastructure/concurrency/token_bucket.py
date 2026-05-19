"""令牌桶限流器：控制全局/单域名 QPS。"""

import asyncio
import threading
import time


class TokenBucket:
    """线程安全的令牌桶。

    Args:
        rate: 每秒补充的令牌数（QPS）
        capacity: 桶容量（突发上限）
    """

    def __init__(self, rate: float, capacity: int) -> None:
        if rate <= 0:
            msg = f"rate 必须 > 0，当前为 {rate}"
            raise ValueError(msg)
        if capacity < 1:
            msg = f"capacity 必须 >= 1，当前为 {capacity}"
            raise ValueError(msg)
        self._rate = rate
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    @property
    def rate(self) -> float:
        return self._rate

    @property
    def capacity(self) -> int:
        return int(self._capacity)

    def _refill(self, now: float) -> None:
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now

    def try_acquire(self, tokens: float = 1.0) -> bool:
        """非阻塞获取令牌；不足时返回 False。"""
        if tokens <= 0:
            msg = f"tokens 必须 > 0，当前为 {tokens}"
            raise ValueError(msg)
        with self._lock:
            now = time.monotonic()
            self._refill(now)
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def acquire(self, tokens: float = 1.0) -> None:
        """阻塞直到获取到指定数量令牌。"""
        while not self.try_acquire(tokens):
            with self._lock:
                now = time.monotonic()
                self._refill(now)
                deficit = tokens - self._tokens
                wait_seconds = deficit / self._rate if self._rate > 0 else 0.01
            time.sleep(min(max(wait_seconds, 0.001), 1.0))

    async def acquire_async(self, tokens: float = 1.0) -> None:
        """异步阻塞获取令牌（供 asyncio 爬取流程使用）。"""
        while not self.try_acquire(tokens):
            with self._lock:
                now = time.monotonic()
                self._refill(now)
                deficit = tokens - self._tokens
                wait_seconds = deficit / self._rate if self._rate > 0 else 0.01
            await asyncio.sleep(min(max(wait_seconds, 0.001), 1.0))
