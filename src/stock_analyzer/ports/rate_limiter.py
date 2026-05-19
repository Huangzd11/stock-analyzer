"""限流器端口。"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class IRateLimiter(Protocol):
    """限流器接口，供爬取层注入。"""

    def try_acquire(self, tokens: float = 1.0) -> bool:
        """非阻塞获取令牌。"""
        ...
