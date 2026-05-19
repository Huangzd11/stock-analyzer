"""加权公平队列（WFQ 简化实现）。"""

import heapq
import itertools
import threading
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(order=True)
class _HeapEntry(Generic[T]):
    """堆元素：按虚拟完成时间排序，相同时按序号 FIFO。"""

    virtual_finish: float
    sequence: int
    task: "FairTask[T]" = field(compare=False)


@dataclass(frozen=True)
class FairTask(Generic[T]):
    """公平队列任务。"""

    tenant_id: str
    payload: T
    cost: float = 1.0
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.cost <= 0:
            msg = f"cost 必须 > 0，当前为 {self.cost}"
            raise ValueError(msg)
        if self.weight <= 0:
            msg = f"weight 必须 > 0，当前为 {self.weight}"
            raise ValueError(msg)
        if not self.tenant_id:
            msg = "tenant_id 不能为空"
            raise ValueError(msg)


class FairQueue(Generic[T]):
    """多租户加权公平队列。

    每个租户维护虚拟完成时间 VFT，入队时 ``VFT += cost / weight``，
    出队时取 VFT 最小的任务，避免单租户大批量任务饿死其他租户。
    """

    def __init__(self) -> None:
        self._heap: list[_HeapEntry[T]] = []
        self._tail_vft: dict[str, float] = {}
        self._sequence = itertools.count()
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)

    def enqueue(self, task: FairTask[T]) -> None:
        with self._lock:
            tenant_vft = self._tail_vft.get(task.tenant_id, 0.0)
            virtual_finish = tenant_vft + task.cost / task.weight
            self._tail_vft[task.tenant_id] = virtual_finish
            entry = _HeapEntry(virtual_finish, next(self._sequence), task)
            heapq.heappush(self._heap, entry)

    def dequeue(self) -> FairTask[T] | None:
        with self._lock:
            if not self._heap:
                return None
            entry = heapq.heappop(self._heap)
            return entry.task
