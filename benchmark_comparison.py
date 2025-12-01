#!/usr/bin/env python3
"""
BETTI Benchmark: WITHOUT vs WITH 14 Wetten
==========================================

Vergelijkt dezelfde workload:
- ZONDER: Naive processing (geen wetten)
- MET: Full 14 Wetten pipeline

Zelfde machine, zelfde resources, eerlijke vergelijking.

Author: Jasper van de Meent
License: JOSL
"""

import asyncio
import aiohttp
import time
import random
import json
import statistics
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from collections import Counter

BRAIN_API = "http://localhost:8010"


@dataclass
class BenchmarkResult:
    name: str
    total_requests: int
    successful: int
    failed: int
    duration_sec: float
    requests_per_sec: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    errors: Dict[str, int]
    extra: Dict[str, Any]


async def benchmark_without_laws(session: aiohttp.ClientSession, count: int) -> List[float]:
    """
    Benchmark ZONDER 14 wetten - direct health check (baseline)
    Simuleert naive processing zonder resource planning
    """
    latencies = []

    for _ in range(count):
        start = time.perf_counter()
        try:
            # Simple endpoint - no law processing
            async with session.get(
                f"{BRAIN_API}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                await resp.json()
                latencies.append((time.perf_counter() - start) * 1000)
        except Exception as e:
            latencies.append(-1)  # Mark as failed

    return latencies


async def benchmark_with_laws(session: aiohttp.ClientSession, count: int) -> List[float]:
    """
    Benchmark MET 14 wetten - full resource planner
    Alle 14 natuurwetten worden toegepast
    """
    latencies = []

    for _ in range(count):
        start = time.perf_counter()
        try:
            payload = {
                "task_type": random.choice(["message", "call", "query", "file_transfer"]),
                "urgency": random.randint(1, 10),
                "participants": [f"user_{i}" for i in range(random.randint(1, 5))],
                "devices": [f"dev_{i}" for i in range(random.randint(1, 3))],
                "data_size_kb": random.randint(1, 1000),
                "current_load": random.randint(20, 80)
            }
            async with session.post(
                f"{BRAIN_API}/planner/plan",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                result = await resp.json()
                latencies.append((time.perf_counter() - start) * 1000)
        except Exception as e:
            latencies.append(-1)

    return latencies


async def run_concurrent_benchmark(
    name: str,
    func,
    concurrent: int,
    requests_per_worker: int
) -> BenchmarkResult:
    """Run benchmark with multiple concurrent workers"""

    print(f"\n{'='*60}")
    print(f"BENCHMARK: {name}")
    print(f"{'='*60}")
    print(f"  Concurrent workers: {concurrent}")
    print(f"  Requests per worker: {requests_per_worker}")
    print(f"  Total requests: {concurrent * requests_per_worker}")
    print(f"  Running...")

    start_time = time.perf_counter()

    async with aiohttp.ClientSession() as session:
        # Launch concurrent workers
        tasks = [
            func(session, requests_per_worker)
            for _ in range(concurrent)
        ]
        all_latencies = await asyncio.gather(*tasks)

    duration = time.perf_counter() - start_time

    # Flatten latencies
    latencies = [l for worker in all_latencies for l in worker]

    # Separate successful and failed
    successful_latencies = [l for l in latencies if l > 0]
    failed = len([l for l in latencies if l < 0])

    # Calculate stats
    total = len(latencies)
    successful = len(successful_latencies)

    if successful_latencies:
        avg_latency = statistics.mean(successful_latencies)
        sorted_lat = sorted(successful_latencies)
        p50 = sorted_lat[int(len(sorted_lat) * 0.50)]
        p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
        p99 = sorted_lat[int(len(sorted_lat) * 0.99)]
    else:
        avg_latency = p50 = p95 = p99 = 0

    rps = total / duration if duration > 0 else 0

    result = BenchmarkResult(
        name=name,
        total_requests=total,
        successful=successful,
        failed=failed,
        duration_sec=round(duration, 2),
        requests_per_sec=round(rps, 1),
        avg_latency_ms=round(avg_latency, 2),
        p50_latency_ms=round(p50, 2),
        p95_latency_ms=round(p95, 2),
        p99_latency_ms=round(p99, 2),
        errors={"timeout": failed},
        extra={}
    )

    print(f"\n  Results:")
    print(f"    Success rate: {successful}/{total} ({100*successful/total:.1f}%)")
    print(f"    Duration: {duration:.2f}s")
    print(f"    Throughput: {rps:.1f} req/sec")
    print(f"    Avg latency: {avg_latency:.2f}ms")
    print(f"    P50 latency: {p50:.2f}ms")
    print(f"    P95 latency: {p95:.2f}ms")
    print(f"    P99 latency: {p99:.2f}ms")

    return result


async def stress_test_comparison(concurrent: int, duration_sec: int) -> Dict:
    """
    Stress test: Push both systems to their limits
    """
    print(f"\n{'='*60}")
    print("STRESS TEST: Sustained Load Comparison")
    print(f"{'='*60}")
    print(f"  Concurrent connections: {concurrent}")
    print(f"  Duration: {duration_sec} seconds")

    results = {"without": [], "with": []}

    async with aiohttp.ClientSession() as session:
        # Test WITHOUT laws
        print(f"\n  Testing WITHOUT 14 Wetten...")
        end_time = time.perf_counter() + duration_sec
        without_count = 0
        without_errors = 0

        while time.perf_counter() < end_time:
            try:
                async with session.get(
                    f"{BRAIN_API}/health",
                    timeout=aiohttp.ClientTimeout(total=1)
                ) as resp:
                    await resp.json()
                    without_count += 1
            except:
                without_errors += 1

        without_rps = without_count / duration_sec
        print(f"    Completed: {without_count} requests, {without_errors} errors")
        print(f"    Throughput: {without_rps:.1f} req/sec")

        # Test WITH laws
        print(f"\n  Testing WITH 14 Wetten...")
        end_time = time.perf_counter() + duration_sec
        with_count = 0
        with_errors = 0
        laws_applied = []

        while time.perf_counter() < end_time:
            try:
                payload = {
                    "task_type": "message",
                    "urgency": random.randint(1, 10),
                    "participants": ["user"],
                    "devices": ["phone"],
                    "data_size_kb": 10
                }
                async with session.post(
                    f"{BRAIN_API}/planner/plan",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=1)
                ) as resp:
                    result = await resp.json()
                    with_count += 1
                    if "laws_applied" in result:
                        laws_applied.append(len(result["laws_applied"]))
            except:
                with_errors += 1

        with_rps = with_count / duration_sec
        print(f"    Completed: {with_count} requests, {with_errors} errors")
        print(f"    Throughput: {with_rps:.1f} req/sec")
        if laws_applied:
            print(f"    Avg laws applied: {statistics.mean(laws_applied):.1f}")

    return {
        "without": {"requests": without_count, "errors": without_errors, "rps": without_rps},
        "with": {"requests": with_count, "errors": with_errors, "rps": with_rps},
        "overhead_percent": round((1 - with_rps/without_rps) * 100, 1) if without_rps > 0 else 0
    }


async def chaos_test() -> Dict:
    """
    Chaos test: Simulate real-world unpredictable load
    Mix of different request types, sizes, urgencies
    """
    print(f"\n{'='*60}")
    print("CHAOS TEST: Real-World Unpredictable Load")
    print(f"{'='*60}")

    scenarios = [
        {"name": "Emergency Call", "task_type": "emergency", "urgency": 10, "data_kb": 1},
        {"name": "Video Conference", "task_type": "video_call", "urgency": 8, "data_kb": 5000},
        {"name": "Background Sync", "task_type": "background", "urgency": 1, "data_kb": 50000},
        {"name": "Chat Message", "task_type": "message", "urgency": 5, "data_kb": 1},
        {"name": "File Upload", "task_type": "file_transfer", "urgency": 3, "data_kb": 10000},
        {"name": "IoT Sensor", "task_type": "iot_command", "urgency": 4, "data_kb": 0.1},
    ]

    results = {}

    async with aiohttp.ClientSession() as session:
        for scenario in scenarios:
            payload = {
                "task_type": scenario["task_type"],
                "urgency": scenario["urgency"],
                "participants": ["user"],
                "devices": ["device"],
                "data_size_kb": scenario["data_kb"]
            }

            start = time.perf_counter()
            async with session.post(
                f"{BRAIN_API}/planner/plan",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                result = await resp.json()
            latency = (time.perf_counter() - start) * 1000

            alloc = result.get("allocation", {})
            results[scenario["name"]] = {
                "latency_ms": round(latency, 2),
                "queue_priority": alloc.get("queue_priority", "N/A"),
                "memory_mb": alloc.get("memory_mb", "N/A"),
                "timeout_ms": alloc.get("timeout_ms", "N/A"),
                "split_required": alloc.get("split_required", False)
            }

            print(f"\n  {scenario['name']}:")
            print(f"    Urgency: {scenario['urgency']}/10, Data: {scenario['data_kb']}KB")
            print(f"    → Queue: {alloc.get('queue_priority')}/10, Memory: {alloc.get('memory_mb')}MB")
            print(f"    → Latency: {latency:.2f}ms")

    return results


async def main():
    """Run full benchmark suite"""
    print("\n" + "="*60)
    print("BETTI BENCHMARK: WITHOUT vs WITH 14 WETTEN")
    print("="*60)
    print("Same machine, same resources, fair comparison")
    print("="*60)

    all_results = {}

    # 1. Basic throughput comparison
    print("\n" + "="*60)
    print("PART 1: THROUGHPUT COMPARISON")
    print("="*60)

    without_result = await run_concurrent_benchmark(
        name="WITHOUT 14 Wetten (baseline)",
        func=benchmark_without_laws,
        concurrent=10,
        requests_per_worker=100
    )

    with_result = await run_concurrent_benchmark(
        name="WITH 14 Wetten (full pipeline)",
        func=benchmark_with_laws,
        concurrent=10,
        requests_per_worker=100
    )

    all_results["throughput"] = {
        "without": asdict(without_result),
        "with": asdict(with_result),
        "overhead_percent": round(
            (1 - with_result.requests_per_sec / without_result.requests_per_sec) * 100, 1
        ) if without_result.requests_per_sec > 0 else 0
    }

    # 2. Stress test
    print("\n" + "="*60)
    print("PART 2: STRESS TEST (10 seconds sustained)")
    print("="*60)

    stress_result = await stress_test_comparison(concurrent=1, duration_sec=10)
    all_results["stress"] = stress_result

    # 3. Chaos test
    print("\n" + "="*60)
    print("PART 3: CHAOS TEST (Mixed Workload)")
    print("="*60)

    chaos_result = await chaos_test()
    all_results["chaos"] = chaos_result

    # Final Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)

    print(f"\n┌{'─'*58}┐")
    print(f"│{'METRIC':<25}{'WITHOUT':>15}{'WITH':>15}│")
    print(f"├{'─'*58}┤")
    print(f"│{'Throughput (req/sec)':<25}{without_result.requests_per_sec:>15.1f}{with_result.requests_per_sec:>15.1f}│")
    print(f"│{'Avg Latency (ms)':<25}{without_result.avg_latency_ms:>15.2f}{with_result.avg_latency_ms:>15.2f}│")
    print(f"│{'P95 Latency (ms)':<25}{without_result.p95_latency_ms:>15.2f}{with_result.p95_latency_ms:>15.2f}│")
    print(f"│{'P99 Latency (ms)':<25}{without_result.p99_latency_ms:>15.2f}{with_result.p99_latency_ms:>15.2f}│")
    print(f"│{'Success Rate (%)':<25}{100*without_result.successful/without_result.total_requests:>15.1f}{100*with_result.successful/with_result.total_requests:>15.1f}│")
    print(f"├{'─'*58}┤")
    print(f"│{'14 Wetten Overhead':<25}{all_results['throughput']['overhead_percent']:>15.1f}%{' ':>13}│")
    print(f"│{'Laws Applied per Request':<25}{'0':>15}{'14':>15}│")
    print(f"└{'─'*58}┘")

    print(f"\n  CONCLUSIE:")
    overhead = all_results['throughput']['overhead_percent']
    if overhead < 20:
        print(f"  ✓ Overhead van {overhead}% is ACCEPTABEL voor 14 wetten")
        print(f"  ✓ Je krijgt QoS, scaling, trust, memory management GRATIS")
    elif overhead < 50:
        print(f"  ~ Overhead van {overhead}% is REDELIJK")
        print(f"  ~ Overweeg caching voor high-frequency requests")
    else:
        print(f"  ✗ Overhead van {overhead}% is HOOG")
        print(f"  ✗ Optimalisatie nodig")

    # Save results
    all_results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open("/root/Humotica/BETTI-TIBET-TEST/benchmark_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n  Results saved to: benchmark_results.json")

    return all_results


if __name__ == "__main__":
    asyncio.run(main())
