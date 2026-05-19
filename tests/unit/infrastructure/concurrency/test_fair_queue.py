"""加权公平队列（WFQ）测试。"""

import pytest

from stock_analyzer.infrastructure.concurrency import FairQueue, FairTask


def test_fair_queue_dequeue_empty_returns_none() -> None:
    queue: FairQueue[str] = FairQueue()
    assert queue.dequeue() is None


def test_fair_queue_fifo_within_same_tenant() -> None:
    queue: FairQueue[int] = FairQueue()
    for i in range(3):
        queue.enqueue(FairTask(tenant_id="a", payload=i))
    assert queue.dequeue().payload == 0
    assert queue.dequeue().payload == 1
    assert queue.dequeue().payload == 2


def test_fair_queue_no_starvation() -> None:
    """大租户先提交 90 个任务后，小租户 10 个任务不应被饿死。"""
    queue: FairQueue[str] = FairQueue()
    for i in range(90):
        queue.enqueue(FairTask(tenant_id="heavy", payload=f"h{i}", cost=1.0))
    for i in range(10):
        queue.enqueue(FairTask(tenant_id="light", payload=f"l{i}", cost=1.0))

    first_light_index: int | None = None
    for idx in range(100):
        task = queue.dequeue()
        assert task is not None
        if task.tenant_id == "light" and first_light_index is None:
            first_light_index = idx

    assert first_light_index is not None
    # 小租户首个任务应在合理时间内被调度（远早于 90 之后）
    assert first_light_index < 20


def test_fair_queue_respects_weight() -> None:
    """权重更高（数值更大）的租户单位成本占用更少虚拟时间，更易被调度。"""
    queue: FairQueue[str] = FairQueue()
    queue.enqueue(FairTask(tenant_id="low", payload="a", cost=1.0, weight=1.0))
    queue.enqueue(FairTask(tenant_id="low", payload="b", cost=1.0, weight=1.0))
    queue.enqueue(FairTask(tenant_id="high", payload="x", cost=1.0, weight=10.0))

    first = queue.dequeue()
    second = queue.dequeue()
    assert first is not None and second is not None
    # high 权重租户首任务虚拟完成时间 0.1，应优先于 low 的第二个任务（VFT=2）
    assert first.tenant_id == "high"
    assert first.payload == "x"


def test_fair_queue_rejects_invalid_cost() -> None:
    queue: FairQueue[int] = FairQueue()
    with pytest.raises(ValueError, match="cost"):
        queue.enqueue(FairTask(tenant_id="a", payload=1, cost=0))


def test_fair_queue_rejects_invalid_weight() -> None:
    queue: FairQueue[int] = FairQueue()
    with pytest.raises(ValueError, match="weight"):
        queue.enqueue(FairTask(tenant_id="a", payload=1, weight=-1))
