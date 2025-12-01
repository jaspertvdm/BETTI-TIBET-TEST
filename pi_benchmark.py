#!/usr/bin/env python3
"""
BETTI Raspberry Pi 5 Benchmark
==============================

Tests BETTI performance on edge hardware.

Tests:
1. API Throughput (requests/sec)
2. IoT Sensor Data Processing
3. Archimedes Priority (emergency vs background)
4. Qwen LLM Inference

Author: Jasper van de Meent
License: JOSL
"""

import asyncio
import aiohttp
import time
import json
import statistics
from dataclasses import dataclass
from typing import Dict, List, Any

# Configuration - adjust based on where BETTI API runs
BETTI_URL = "http://localhost:8010"  # Pi local or server
OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:1.5b"

@dataclass
class BenchmarkResult:
    name: str
    success: bool
    latency_ms: float
    throughput: float = 0
    details: Dict = None


async def test_api_throughput(session: aiohttp.ClientSession, duration: int = 10) -> Dict:
    """Test 1: API Throughput - how many requests/sec can the Pi handle"""
    print("\n" + "="*50)
    print("TEST 1: API Throughput")
    print("="*50)

    payload = {
        "task_type": "query",
        "urgency": 5,
        "participants": ["sensor"],
        "devices": ["pi"],
        "data_size_kb": 1,
        "operations": ["process"]
    }

    results = []
    errors = 0
    start_time = time.perf_counter()
    end_time = start_time + duration

    async def single_request():
        nonlocal errors
        try:
            req_start = time.perf_counter()
            async with session.post(
                f"{BETTI_URL}/planner/plan/quick",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                await resp.json()
                return (time.perf_counter() - req_start) * 1000
        except Exception as e:
            errors += 1
            return None

    # Run requests for duration seconds
    while time.perf_counter() < end_time:
        batch = [single_request() for _ in range(10)]
        batch_results = await asyncio.gather(*batch)
        results.extend([r for r in batch_results if r is not None])

    elapsed = time.perf_counter() - start_time
    successful = len(results)

    result = {
        "duration_sec": elapsed,
        "total_requests": successful + errors,
        "successful": successful,
        "errors": errors,
        "requests_per_sec": successful / elapsed if elapsed > 0 else 0,
        "avg_latency_ms": statistics.mean(results) if results else 0,
        "p95_latency_ms": sorted(results)[int(len(results) * 0.95)] if len(results) > 1 else 0,
        "p99_latency_ms": sorted(results)[int(len(results) * 0.99)] if len(results) > 1 else 0
    }

    print(f"  Throughput: {result['requests_per_sec']:.1f} req/sec")
    print(f"  Avg Latency: {result['avg_latency_ms']:.2f}ms")
    print(f"  P99 Latency: {result['p99_latency_ms']:.2f}ms")
    print(f"  Errors: {errors}")

    return result


async def test_iot_sensor_processing(session: aiohttp.ClientSession) -> Dict:
    """Test 2: IoT Sensor Data Processing - simulated sensor bursts"""
    print("\n" + "="*50)
    print("TEST 2: IoT Sensor Data Processing")
    print("="*50)

    # Simulate different sensor types
    sensors = [
        {"type": "temperature", "urgency": 3, "data_kb": 0.1},
        {"type": "motion", "urgency": 8, "data_kb": 0.5},
        {"type": "camera", "urgency": 5, "data_kb": 50},
        {"type": "audio", "urgency": 6, "data_kb": 10},
        {"type": "heartbeat", "urgency": 2, "data_kb": 0.01},
    ]

    results = {}

    for sensor in sensors:
        payload = {
            "task_type": "sensor",
            "urgency": sensor["urgency"],
            "participants": [sensor["type"]],
            "devices": ["pi", "sensor"],
            "data_size_kb": sensor["data_kb"],
            "operations": ["collect", "process", "store"]
        }

        latencies = []
        for _ in range(20):
            start = time.perf_counter()
            try:
                async with session.post(
                    f"{BETTI_URL}/planner/plan",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    data = await resp.json()
                    latencies.append((time.perf_counter() - start) * 1000)
            except:
                pass

        if latencies:
            results[sensor["type"]] = {
                "avg_latency_ms": statistics.mean(latencies),
                "urgency": sensor["urgency"],
                "data_kb": sensor["data_kb"],
                "priority": data.get("allocation", {}).get("queue_priority", "N/A")
            }
            print(f"  {sensor['type']:12} | {statistics.mean(latencies):6.2f}ms | priority: {results[sensor['type']]['priority']}")

    return results


async def test_archimedes_priority(session: aiohttp.ClientSession) -> Dict:
    """Test 3: Archimedes Priority - emergency vs background tasks"""
    print("\n" + "="*50)
    print("TEST 3: Archimedes Priority (Emergency vs Background)")
    print("="*50)

    # Launch emergency and background tasks simultaneously
    emergency_payload = {
        "task_type": "call",
        "urgency": 10,
        "participants": ["user", "emergency"],
        "devices": ["pi"],
        "data_size_kb": 1,
        "operations": ["alert", "notify"]
    }

    background_payloads = [
        {"task_type": "sync", "urgency": 1, "participants": ["system"], "devices": ["pi"], "data_size_kb": 100, "operations": ["backup"]},
        {"task_type": "update", "urgency": 2, "participants": ["system"], "devices": ["pi"], "data_size_kb": 50, "operations": ["download"]},
        {"task_type": "log", "urgency": 1, "participants": ["system"], "devices": ["pi"], "data_size_kb": 10, "operations": ["write"]},
    ]

    async def make_request(payload, name):
        start = time.perf_counter()
        try:
            async with session.post(
                f"{BETTI_URL}/planner/plan",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                latency = (time.perf_counter() - start) * 1000
                return {
                    "name": name,
                    "latency_ms": latency,
                    "priority": data.get("allocation", {}).get("queue_priority", 10),
                    "success": True
                }
        except Exception as e:
            return {"name": name, "latency_ms": 0, "priority": 10, "success": False, "error": str(e)}

    # Launch all at once
    tasks = [
        make_request(emergency_payload, "EMERGENCY"),
        *[make_request(p, f"background_{i+1}") for i, p in enumerate(background_payloads)]
    ]

    results = await asyncio.gather(*tasks)

    # Sort by completion time
    emergency = [r for r in results if r["name"] == "EMERGENCY"][0]
    backgrounds = [r for r in results if r["name"] != "EMERGENCY"]
    bg_avg = statistics.mean([r["latency_ms"] for r in backgrounds if r["success"]])

    print(f"  EMERGENCY:     {emergency['latency_ms']:6.2f}ms | priority: {emergency['priority']}")
    print(f"  Background avg: {bg_avg:6.2f}ms | priority: {backgrounds[0]['priority']}")
    print(f"  Emergency first: {emergency['latency_ms'] < min([r['latency_ms'] for r in backgrounds])}")

    return {
        "emergency_latency_ms": emergency["latency_ms"],
        "emergency_priority": emergency["priority"],
        "background_avg_latency_ms": bg_avg,
        "background_priority": backgrounds[0]["priority"],
        "emergency_served_first": emergency["latency_ms"] < min([r["latency_ms"] for r in backgrounds])
    }


async def test_qwen_llm(session: aiohttp.ClientSession) -> Dict:
    """Test 4: Qwen LLM Inference on Pi"""
    print("\n" + "="*50)
    print("TEST 4: Qwen LLM Inference (qwen2.5:1.5b)")
    print("="*50)

    prompts = {
        "simple": "What is 2+2?",
        "medium": "Explain IoT in 2 sentences.",
        "complex": "Write a Python function to read a temperature sensor."
    }

    results = {}

    for prompt_type, prompt in prompts.items():
        print(f"  Testing {prompt_type}...", end=" ", flush=True)

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
                data = await resp.json()
                latency = (time.perf_counter() - start) * 1000
                tokens = data.get("eval_count", 0)

                results[prompt_type] = {
                    "latency_ms": latency,
                    "tokens": tokens,
                    "tokens_per_sec": tokens / (latency / 1000) if latency > 0 else 0,
                    "success": True
                }
                print(f"{latency/1000:.1f}s | {results[prompt_type]['tokens_per_sec']:.1f} tok/s")
        except Exception as e:
            results[prompt_type] = {"success": False, "error": str(e)}
            print(f"FAILED: {e}")

    return results


async def main():
    """Run all Pi benchmarks"""
    print("\n" + "="*60)
    print("BETTI RASPBERRY PI 5 BENCHMARK")
    print("="*60)
    print(f"Hardware: Raspberry Pi 5 (4 cores, 8GB RAM)")
    print(f"BETTI API: {BETTI_URL}")
    print(f"Ollama: {OLLAMA_URL}")
    print(f"LLM Model: {MODEL}")
    print("="*60)

    all_results = {
        "hardware": "Raspberry Pi 5 8GB",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tests": {}
    }

    async with aiohttp.ClientSession() as session:
        # Check BETTI API
        try:
            async with session.get(f"{BETTI_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    print(f"\nWARNING: BETTI API not healthy at {BETTI_URL}")
        except:
            print(f"\nERROR: Cannot reach BETTI API at {BETTI_URL}")
            print("Skipping API tests, running only LLM test...")
            all_results["tests"]["llm"] = await test_qwen_llm(session)
            return all_results

        # Run all tests
        all_results["tests"]["throughput"] = await test_api_throughput(session, duration=10)
        all_results["tests"]["iot_sensors"] = await test_iot_sensor_processing(session)
        all_results["tests"]["archimedes"] = await test_archimedes_priority(session)
        all_results["tests"]["llm"] = await test_qwen_llm(session)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    tp = all_results["tests"].get("throughput", {})
    print(f"\n  API Throughput: {tp.get('requests_per_sec', 0):.1f} req/sec")
    print(f"  P99 Latency: {tp.get('p99_latency_ms', 0):.2f}ms")

    arch = all_results["tests"].get("archimedes", {})
    print(f"\n  Emergency Priority: {arch.get('emergency_priority', 'N/A')}")
    print(f"  Emergency First: {arch.get('emergency_served_first', 'N/A')}")

    llm = all_results["tests"].get("llm", {})
    if "simple" in llm:
        print(f"\n  LLM Simple: {llm['simple'].get('latency_ms', 0)/1000:.1f}s")
        print(f"  LLM Tokens/sec: {llm['simple'].get('tokens_per_sec', 0):.1f}")

    # Save results
    with open("pi_benchmark_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n  Results saved to: pi_benchmark_results.json")

    return all_results


if __name__ == "__main__":
    asyncio.run(main())
