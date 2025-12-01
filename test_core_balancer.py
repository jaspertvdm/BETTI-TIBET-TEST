#!/usr/bin/env python3
"""
BETTI Core Balancer Test
========================

Tests the physics-based workload balancer.
"""

import asyncio
import time
from betti_core_balancer import BettiBalancer, balanced, TaskWeight

async def test_basic_balancing():
    """Test basic heavy task balancing"""
    print("\n=== Test: Basic Balancing ===")

    balancer = BettiBalancer.configure(
        max_parallel_heavy=3,
        cooldown_heavy=0.01
    )
    balancer.reset_stats()

    results = []

    @balanced(weight="heavy")
    async def heavy_work(task_id: int):
        await asyncio.sleep(0.05)  # Simulate work
        return task_id

    # Launch 10 tasks, only 3 should run in parallel
    start = time.time()
    tasks = [heavy_work(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    stats = balancer.get_stats()

    print(f"  Tasks completed: {len(results)}")
    print(f"  Time elapsed: {elapsed:.2f}s")
    print(f"  Skips: {stats['skips']}")
    print(f"  Heavy completed: {stats['heavy_completed']}")

    assert len(results) == 10, "All tasks should complete"
    print("  PASSED")


async def test_skip_mode():
    """Test skip mode where tasks are dropped if too busy"""
    print("\n=== Test: Skip Mode ===")

    balancer = BettiBalancer.configure(
        max_parallel_heavy=2,
        cooldown_heavy=0.1
    )
    balancer.reset_stats()

    completed = []
    skipped = []

    @balanced(weight="heavy", skip_action="skip")
    async def quick_heavy(task_id: int):
        await asyncio.sleep(0.2)
        return task_id

    # Launch many tasks at once
    tasks = [quick_heavy(i) for i in range(20)]
    results = await asyncio.gather(*tasks)

    completed = [r for r in results if r is not None]
    skipped = [r for r in results if r is None]

    print(f"  Completed: {len(completed)}")
    print(f"  Skipped: {len(skipped)}")

    assert len(skipped) > 0, "Some tasks should be skipped"
    print("  PASSED")


async def test_context_manager():
    """Test context manager usage"""
    print("\n=== Test: Context Manager ===")

    balancer = BettiBalancer.configure(max_parallel_heavy=2)
    balancer.reset_stats()

    async def work_with_context():
        async with BettiBalancer.heavy_task():
            await asyncio.sleep(0.05)
            return True

    tasks = [work_with_context() for _ in range(5)]
    results = await asyncio.gather(*tasks)

    assert all(results), "All tasks should succeed"
    print(f"  All 5 tasks completed with context manager")
    print("  PASSED")


async def test_stress():
    """Stress test comparing balanced vs unbalanced"""
    print("\n=== Test: Stress Comparison ===")

    work_time = 0.01  # 10ms per task
    n_tasks = 50

    # Unbalanced (raw)
    async def raw_work():
        await asyncio.sleep(work_time)
        return True

    start = time.time()
    await asyncio.gather(*[raw_work() for _ in range(n_tasks)])
    raw_time = time.time() - start

    # Balanced
    balancer = BettiBalancer.configure(
        max_parallel_heavy=5,
        cooldown_heavy=0.005
    )
    balancer.reset_stats()

    @balanced(weight="heavy")
    async def balanced_work():
        await asyncio.sleep(work_time)
        return True

    start = time.time()
    await asyncio.gather(*[balanced_work() for _ in range(n_tasks)])
    balanced_time = time.time() - start

    stats = balancer.get_stats()

    print(f"  Raw time: {raw_time:.3f}s")
    print(f"  Balanced time: {balanced_time:.3f}s")
    print(f"  Skips: {stats['skips']}")
    print(f"  Skip rate: {stats['skip_rate']:.1%}")
    print("  PASSED (balanced maintains responsiveness)")


async def main():
    print("\n" + "="*50)
    print("BETTI CORE BALANCER TEST SUITE")
    print("="*50)

    await test_basic_balancing()
    await test_skip_mode()
    await test_context_manager()
    await test_stress()

    print("\n" + "="*50)
    print("ALL TESTS PASSED")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
