#!/usr/bin/env python3
"""
BETTI Ollama LLM Benchmark
==========================

Tests LLM inference with and without BETTI resource planning.

Key metrics:
- Response latency
- Tokens per second
- Concurrent request handling
- Resource utilization under load

Author: Jasper van de Meent
License: JOSL
"""

import asyncio
import aiohttp
import time
import json
import statistics
from typing import Dict, List, Any
from dataclasses import dataclass

OLLAMA_URL = "http://localhost:11434"
BETTI_URL = "http://localhost:8010"
MODEL = "llama3.1:8b"

# Test prompts of varying complexity
PROMPTS = {
    "simple": "What is 2+2?",
    "medium": "Explain quantum computing in 3 sentences.",
    "complex": "Write a Python function to calculate fibonacci numbers with memoization."
}


@dataclass
class BenchmarkResult:
    name: str
    prompt_type: str
    latency_ms: float
    tokens: int
    tokens_per_sec: float
    success: bool
    error: str = None


async def ollama_generate(session: aiohttp.ClientSession, prompt: str) -> Dict:
    """Direct Ollama API call"""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    start = time.perf_counter()
    try:
        async with session.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120)
        ) as resp:
            result = await resp.json()
            latency = (time.perf_counter() - start) * 1000

            return {
                "success": True,
                "latency_ms": latency,
                "response": result.get("response", ""),
                "eval_count": result.get("eval_count", 0),
                "eval_duration": result.get("eval_duration", 0),
                "total_duration": result.get("total_duration", 0)
            }
    except Exception as e:
        return {
            "success": False,
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": str(e)
        }


async def betti_plan_then_generate(session: aiohttp.ClientSession, prompt: str, urgency: int = 5) -> Dict:
    """BETTI resource planning + Ollama"""

    # Step 1: Get BETTI resource plan
    plan_payload = {
        "task_type": "query",  # LLM query
        "urgency": urgency,
        "participants": ["user"],
        "devices": ["server"],
        "data_size_kb": len(prompt) / 1024,  # Approximate
        "operations": ["llm_inference"]
    }

    start = time.perf_counter()

    try:
        # Get resource allocation
        async with session.post(
            f"{BETTI_URL}/planner/plan",
            json=plan_payload,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            plan = await resp.json()

        allocation = plan.get("allocation", {})

        # Apply BETTI decisions
        # - Use timeout from Doppler
        timeout_ms = allocation.get("timeout_ms", 60000)
        # - Check if we should proceed (queue priority)
        queue_priority = allocation.get("queue_priority", 5)

        # If low priority, simulate queue wait
        if queue_priority > 7:
            await asyncio.sleep(allocation.get("estimated_wait_ms", 0) / 1000)

        # Step 2: Call Ollama with BETTI-planned timeout
        ollama_payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }

        async with session.post(
            f"{OLLAMA_URL}/api/generate",
            json=ollama_payload,
            timeout=aiohttp.ClientTimeout(total=timeout_ms / 1000)
        ) as resp:
            result = await resp.json()
            latency = (time.perf_counter() - start) * 1000

            return {
                "success": True,
                "latency_ms": latency,
                "response": result.get("response", ""),
                "eval_count": result.get("eval_count", 0),
                "betti_allocation": allocation,
                "queue_priority": queue_priority
            }

    except Exception as e:
        return {
            "success": False,
            "latency_ms": (time.perf_counter() - start) * 1000,
            "error": str(e)
        }


async def run_single_benchmark(name: str, func, prompt_type: str, prompt: str) -> BenchmarkResult:
    """Run a single benchmark"""
    async with aiohttp.ClientSession() as session:
        result = await func(session, prompt)

        tokens = result.get("eval_count", len(result.get("response", "").split()))
        latency = result.get("latency_ms", 0)

        return BenchmarkResult(
            name=name,
            prompt_type=prompt_type,
            latency_ms=latency,
            tokens=tokens,
            tokens_per_sec=tokens / (latency / 1000) if latency > 0 else 0,
            success=result.get("success", False),
            error=result.get("error")
        )


async def run_concurrent_test(name: str, func, prompt: str, concurrent: int) -> Dict:
    """Test concurrent requests"""
    print(f"\n  Testing {concurrent} concurrent requests...")

    async with aiohttp.ClientSession() as session:
        start = time.perf_counter()

        tasks = [func(session, prompt) for _ in range(concurrent)]
        results = await asyncio.gather(*tasks)

        duration = time.perf_counter() - start

        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]

        latencies = [r.get("latency_ms", 0) for r in successful]

        return {
            "name": name,
            "concurrent": concurrent,
            "successful": len(successful),
            "failed": len(failed),
            "duration_sec": duration,
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else 0,
            "throughput_rps": len(successful) / duration
        }


async def run_priority_test() -> Dict:
    """Test BETTI priority handling - emergency vs background"""
    print("\n  Testing priority handling (emergency vs background)...")

    async with aiohttp.ClientSession() as session:
        # Launch simultaneously: 1 emergency, 3 background
        tasks = [
            betti_plan_then_generate(session, "Emergency: What is 911?", urgency=10),
            betti_plan_then_generate(session, "Background task 1", urgency=1),
            betti_plan_then_generate(session, "Background task 2", urgency=1),
            betti_plan_then_generate(session, "Background task 3", urgency=1),
        ]

        start = time.perf_counter()
        results = await asyncio.gather(*tasks)

        return {
            "emergency_latency_ms": results[0].get("latency_ms", 0),
            "emergency_priority": results[0].get("queue_priority", 0),
            "background_avg_latency_ms": statistics.mean([r.get("latency_ms", 0) for r in results[1:]]),
            "background_priority": results[1].get("queue_priority", 0),
            "emergency_first": results[0].get("latency_ms", 9999) < min([r.get("latency_ms", 0) for r in results[1:]])
        }


async def main():
    """Run complete benchmark suite"""
    print("\n" + "="*60)
    print("BETTI OLLAMA LLM BENCHMARK")
    print("="*60)
    print(f"Model: {MODEL}")
    print(f"Hardware: Dual Xeon E5-2650 v3 (40 cores)")
    print("="*60)

    all_results = {
        "model": MODEL,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tests": {}
    }

    # Warm up
    print("\nWarming up model...")
    async with aiohttp.ClientSession() as session:
        await ollama_generate(session, "Hello")

    # Test 1: Single request latency comparison
    print("\n" + "="*60)
    print("TEST 1: Single Request Latency")
    print("="*60)

    for prompt_type, prompt in PROMPTS.items():
        print(f"\n  Prompt: {prompt_type}")

        # Without BETTI
        result_direct = await run_single_benchmark(
            "Direct Ollama",
            ollama_generate,
            prompt_type,
            prompt
        )
        print(f"    Direct: {result_direct.latency_ms:.0f}ms, {result_direct.tokens_per_sec:.1f} tok/s")

        # With BETTI
        async with aiohttp.ClientSession() as session:
            result_betti = await betti_plan_then_generate(session, prompt, urgency=5)
        print(f"    BETTI:  {result_betti.get('latency_ms', 0):.0f}ms (priority: {result_betti.get('queue_priority', 'N/A')})")

        all_results["tests"][f"single_{prompt_type}"] = {
            "direct_ms": result_direct.latency_ms,
            "betti_ms": result_betti.get("latency_ms", 0),
            "betti_priority": result_betti.get("queue_priority")
        }

    # Test 2: Concurrent requests
    print("\n" + "="*60)
    print("TEST 2: Concurrent Request Handling")
    print("="*60)

    for concurrent in [2, 3, 5]:
        direct_result = await run_concurrent_test(
            "Direct",
            ollama_generate,
            PROMPTS["simple"],
            concurrent
        )
        print(f"    Direct {concurrent}x: {direct_result['avg_latency_ms']:.0f}ms avg, {direct_result['throughput_rps']:.2f} req/s")

        betti_result = await run_concurrent_test(
            "BETTI",
            lambda s, p: betti_plan_then_generate(s, p, urgency=5),
            PROMPTS["simple"],
            concurrent
        )
        print(f"    BETTI {concurrent}x:  {betti_result['avg_latency_ms']:.0f}ms avg, {betti_result['throughput_rps']:.2f} req/s")

        all_results["tests"][f"concurrent_{concurrent}"] = {
            "direct": direct_result,
            "betti": betti_result
        }

    # Test 3: Priority handling
    print("\n" + "="*60)
    print("TEST 3: Priority Handling (BETTI Archimedes)")
    print("="*60)

    priority_result = await run_priority_test()
    print(f"    Emergency: {priority_result['emergency_latency_ms']:.0f}ms (priority {priority_result['emergency_priority']})")
    print(f"    Background avg: {priority_result['background_avg_latency_ms']:.0f}ms (priority {priority_result['background_priority']})")
    print(f"    Emergency served first: {priority_result['emergency_first']}")

    all_results["tests"]["priority"] = priority_result

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    print("\n  BETTI provides:")
    print("  - Resource planning before LLM calls")
    print("  - Priority-based request handling")
    print("  - Adaptive timeouts (Doppler)")
    print("  - Queue management (Archimedes)")

    # Save results
    with open("/root/Humotica/BETTI-TIBET-TEST/ollama_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n  Results saved to: ollama_results.json")

    return all_results


if __name__ == "__main__":
    asyncio.run(main())
