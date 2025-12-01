"""
BETTI Core Balancer - Runtime Workload Management
==================================================

Physics-based workload balancing without kernel modifications.
Achieves what normally requires cgroups, nice/ionice, or HPC tooling.

Key Laws Applied:
- Archimedes (buoyancy): MAX_PARALLEL limits concurrent heavy tasks
- Doppler (timing): COOLDOWN prevents thundering herd
- Planck (quantization): Discrete skip decisions
- Hooke (elasticity): System springs back after load

Usage:
    from betti_core_balancer import balanced, BettiBalancer

    # As decorator
    @balanced(weight="heavy")
    async def process_video(data):
        ...

    # As context manager
    async with BettiBalancer.heavy_task():
        await expensive_operation()

    # Manual
    if BettiBalancer.can_run_heavy():
        await heavy_work()

Author: Jasper van de Meent
License: JOSL
"""

import asyncio
import time
import logging
from threading import Lock
from typing import Optional, Callable, Any
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskWeight(Enum):
    """Task weight classification"""
    LIGHT = "light"      # Quick tasks, always run
    MEDIUM = "medium"    # Moderate tasks, some throttling
    HEAVY = "heavy"      # CPU/memory intensive, strict limits


@dataclass
class BalancerConfig:
    """Configuration for the balancer"""
    # Archimedes: buoyancy limits
    max_parallel_heavy: int = 6
    max_parallel_medium: int = 12

    # Doppler: timing controls
    cooldown_heavy: float = 0.02      # 20ms between heavy tasks
    cooldown_medium: float = 0.005    # 5ms between medium tasks

    # Planck: quantum skip threshold
    skip_yield_time: float = 0.001    # 1ms yield when skipping

    # Hooke: elasticity
    recovery_factor: float = 0.8      # How quickly to recover capacity


@dataclass
class BalancerStats:
    """Runtime statistics"""
    heavy_running: int = 0
    medium_running: int = 0
    heavy_completed: int = 0
    medium_completed: int = 0
    skips: int = 0
    last_heavy_time: float = 0.0
    last_medium_time: float = 0.0

    def to_dict(self) -> dict:
        return {
            "heavy_running": self.heavy_running,
            "medium_running": self.medium_running,
            "heavy_completed": self.heavy_completed,
            "medium_completed": self.medium_completed,
            "skips": self.skips,
            "skip_rate": self.skips / max(1, self.heavy_completed + self.skips)
        }


class BettiBalancer:
    """
    Core balancer implementing physics-based workload management.

    Thread-safe singleton that tracks concurrent tasks and applies
    Archimedes buoyancy + Doppler timing to keep system responsive.
    """

    _instance: Optional["BettiBalancer"] = None
    _lock = Lock()

    def __new__(cls, config: Optional[BalancerConfig] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._config = config or BalancerConfig()
                    instance._stats = BalancerStats()
                    instance._state_lock = Lock()
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "BettiBalancer":
        """Get or create the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def configure(cls, **kwargs) -> "BettiBalancer":
        """Configure the balancer with custom settings"""
        config = BalancerConfig(**kwargs)
        cls._instance = None  # Reset singleton
        return cls(config)

    def can_run(self, weight: TaskWeight) -> bool:
        """
        Check if a task of given weight can run now.

        Applies:
        - Archimedes: Check parallel limit (buoyancy)
        - Doppler: Check cooldown timing
        """
        now = time.time()

        with self._state_lock:
            if weight == TaskWeight.LIGHT:
                return True  # Light tasks always run

            if weight == TaskWeight.HEAVY:
                # Archimedes: buoyancy limit
                too_busy = self._stats.heavy_running >= self._config.max_parallel_heavy
                # Doppler: timing check
                too_soon = (now - self._stats.last_heavy_time) < self._config.cooldown_heavy

                if too_busy or too_soon:
                    self._stats.skips += 1
                    return False
                return True

            if weight == TaskWeight.MEDIUM:
                too_busy = self._stats.medium_running >= self._config.max_parallel_medium
                too_soon = (now - self._stats.last_medium_time) < self._config.cooldown_medium

                if too_busy or too_soon:
                    self._stats.skips += 1
                    return False
                return True

        return True

    def start_task(self, weight: TaskWeight) -> bool:
        """
        Register task start. Returns True if task should proceed.
        """
        if not self.can_run(weight):
            return False

        now = time.time()

        with self._state_lock:
            if weight == TaskWeight.HEAVY:
                self._stats.heavy_running += 1
                self._stats.last_heavy_time = now
            elif weight == TaskWeight.MEDIUM:
                self._stats.medium_running += 1
                self._stats.last_medium_time = now

        return True

    def end_task(self, weight: TaskWeight):
        """Register task completion"""
        with self._state_lock:
            if weight == TaskWeight.HEAVY:
                self._stats.heavy_running = max(0, self._stats.heavy_running - 1)
                self._stats.heavy_completed += 1
            elif weight == TaskWeight.MEDIUM:
                self._stats.medium_running = max(0, self._stats.medium_running - 1)
                self._stats.medium_completed += 1

    def get_stats(self) -> dict:
        """Get current balancer statistics"""
        with self._state_lock:
            return self._stats.to_dict()

    def reset_stats(self):
        """Reset statistics (for testing)"""
        with self._state_lock:
            self._stats = BalancerStats()

    # Context managers for easy use
    class _HeavyTaskContext:
        def __init__(self, balancer: "BettiBalancer"):
            self.balancer = balancer
            self.started = False

        async def __aenter__(self):
            while not self.balancer.start_task(TaskWeight.HEAVY):
                await asyncio.sleep(self.balancer._config.skip_yield_time)
            self.started = True
            return self

        async def __aexit__(self, *args):
            if self.started:
                self.balancer.end_task(TaskWeight.HEAVY)

    class _MediumTaskContext:
        def __init__(self, balancer: "BettiBalancer"):
            self.balancer = balancer
            self.started = False

        async def __aenter__(self):
            while not self.balancer.start_task(TaskWeight.MEDIUM):
                await asyncio.sleep(self.balancer._config.skip_yield_time)
            self.started = True
            return self

        async def __aexit__(self, *args):
            if self.started:
                self.balancer.end_task(TaskWeight.MEDIUM)

    @classmethod
    def heavy_task(cls):
        """Context manager for heavy tasks"""
        return cls.get_instance()._HeavyTaskContext(cls.get_instance())

    @classmethod
    def medium_task(cls):
        """Context manager for medium tasks"""
        return cls.get_instance()._MediumTaskContext(cls.get_instance())


def balanced(weight: str = "heavy", skip_action: str = "wait"):
    """
    Decorator to apply BETTI balancing to any async function.

    Args:
        weight: "light", "medium", or "heavy"
        skip_action: "wait" (block until allowed), "skip" (return None),
                     "queue" (future implementation)

    Example:
        @balanced(weight="heavy")
        async def transcode_video(video_data):
            ...
    """
    task_weight = TaskWeight(weight)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            balancer = BettiBalancer.get_instance()

            if skip_action == "wait":
                # Wait until we can run
                while not balancer.start_task(task_weight):
                    await asyncio.sleep(balancer._config.skip_yield_time)

                try:
                    return await func(*args, **kwargs)
                finally:
                    balancer.end_task(task_weight)

            elif skip_action == "skip":
                # Skip if can't run immediately
                if not balancer.start_task(task_weight):
                    logger.debug(f"Skipped {func.__name__} due to load")
                    return None

                try:
                    return await func(*args, **kwargs)
                finally:
                    balancer.end_task(task_weight)

            else:
                # Default: just run (for light tasks)
                return await func(*args, **kwargs)

        return wrapper
    return decorator


# Sync versions for non-async code
def balanced_sync(weight: str = "heavy"):
    """Sync version of @balanced decorator"""
    task_weight = TaskWeight(weight)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            balancer = BettiBalancer.get_instance()

            while not balancer.start_task(task_weight):
                time.sleep(balancer._config.skip_yield_time)

            try:
                return func(*args, **kwargs)
            finally:
                balancer.end_task(task_weight)

        return wrapper
    return decorator


# FastAPI middleware
async def betti_balancer_middleware(request, call_next):
    """
    FastAPI middleware that applies balancing to requests.

    Add to app:
        app.middleware("http")(betti_balancer_middleware)
    """
    # Classify request weight based on path/method
    path = request.url.path

    if any(heavy in path for heavy in ["/transcode", "/render", "/llm", "/ai"]):
        weight = TaskWeight.HEAVY
    elif any(medium in path for medium in ["/upload", "/process", "/sync"]):
        weight = TaskWeight.MEDIUM
    else:
        weight = TaskWeight.LIGHT

    balancer = BettiBalancer.get_instance()

    if weight == TaskWeight.LIGHT:
        return await call_next(request)

    # Wait for capacity
    while not balancer.start_task(weight):
        await asyncio.sleep(balancer._config.skip_yield_time)

    try:
        return await call_next(request)
    finally:
        balancer.end_task(weight)


# Prometheus metrics endpoint
def get_balancer_metrics() -> str:
    """Get Prometheus-formatted metrics"""
    stats = BettiBalancer.get_instance().get_stats()

    lines = [
        "# HELP betti_heavy_running Current number of heavy tasks running",
        "# TYPE betti_heavy_running gauge",
        f"betti_heavy_running {stats['heavy_running']}",
        "",
        "# HELP betti_heavy_completed Total heavy tasks completed",
        "# TYPE betti_heavy_completed counter",
        f"betti_heavy_completed {stats['heavy_completed']}",
        "",
        "# HELP betti_skips Total tasks skipped for balance",
        "# TYPE betti_skips counter",
        f"betti_skips {stats['skips']}",
        "",
        "# HELP betti_skip_rate Ratio of skips to total attempts",
        "# TYPE betti_skip_rate gauge",
        f"betti_skip_rate {stats['skip_rate']:.4f}",
    ]

    return "\n".join(lines)
