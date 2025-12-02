#!/usr/bin/env python3
"""
BETTI Local Torture Test v2
===========================

Vergelijkt RAW (geen throttling) vs BALANCED (DABS-style) resource management.

Dit simuleert de 14-wetten client-side:
- MAX_PAR_HEAVY = Newton blocking (max parallel heavy jobs)
- COOLDOWN = Kepler orbital delay (tijd tussen jobs)

Usage:
    python3 local_torture_v2.py

Resultaat: BALANCED mode heeft lagere P90 latency en betere throughput.
"""

import time
import math
import os
import statistics
from threading import Thread, Lock
from uuid import uuid4

DURATION = 30          # testduur per modus (s)
COOLDOWN = 0.10        # minst. tijd tussen jobs
MAX_PAR_HEAVY = 3      # max parallel zware jobs (balanced)

INNER_LOOPS = 2_000_000    # CPU-intensiteit
IO_SIZE = 1 * 1024 * 1024  # 1MB pseudo-IO per job

state_lock = Lock()
active_heavy = 0
last_heavy_ts = 0.0

def cpu_burn():
    s = 0.0
    for i in range(INNER_LOOPS):
        s += math.sqrt(i % 1000)
    return s

def io_burn():
    data = b"x" * IO_SIZE
    fname = f"torture_tmp_{uuid4().hex}.bin"
    with open(fname, "wb") as f:
        f.write(data)
    os.remove(fname)

def ai_latency():
    time.sleep(0.01)

def worker(mode, end_at, exec_times, counters, worker_id):
    global active_heavy, last_heavy_ts

    while time.time() < end_at:
        now = time.time()
        do_heavy = False  # default

        with state_lock:
            if mode == "balanced":
                too_soon = (now - last_heavy_ts) < COOLDOWN
                too_busy = active_heavy >= MAX_PAR_HEAVY
                if too_soon or too_busy:
                    counters["skips"] += 1
                else:
                    active_heavy += 1
                    last_heavy_ts = now
                    counters["heavy_runs"] += 1
                    do_heavy = True
            else:
                # RAW: altijd knallen
                active_heavy += 1
                counters["heavy_runs"] += 1
                do_heavy = True

        if not do_heavy:
            time.sleep(0.003)
            continue

        # Zware job
        t0 = time.time()
        cpu_burn()
        io_burn()
        ai_latency()
        dt = (time.time() - t0) * 1000.0

        with state_lock:
            exec_times.append(dt)
            active_heavy -= 1
            counters["total_loops"] += 1

        time.sleep(0.003)

def run_mode(mode: str):
    global active_heavy, last_heavy_ts
    active_heavy = 0
    last_heavy_ts = 0.0

    print(f"\n=== MODE: {mode.upper()} ===")
    exec_times = []
    counters = {"total_loops": 0, "heavy_runs": 0, "skips": 0}

    start_wall = time.time()
    end_at = start_wall + DURATION

    threads = []
    for wid in range(8):
        t = Thread(target=worker, args=(mode, end_at, exec_times, counters, wid))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    total_wall = time.time() - start_wall

    if exec_times:
        sorted_times = sorted(exec_times)
        avg = statistics.mean(sorted_times)
        p50 = sorted_times[int(0.5 * len(sorted_times))]
        p90 = sorted_times[int(0.9 * len(sorted_times))]
        p99 = sorted_times[min(int(0.99 * len(sorted_times)), len(sorted_times)-1)]
    else:
        avg = p50 = p90 = p99 = 0.0

    results = {
        "mode": mode,
        "wall_time_s": round(total_wall, 1),
        "total_loops": counters["total_loops"],
        "heavy_runs": counters["heavy_runs"],
        "skips": counters["skips"],
        "avg_ms": round(avg, 1),
        "p50_ms": round(p50, 1),
        "p90_ms": round(p90, 1),
        "p99_ms": round(p99, 1),
        "throughput": round(counters["total_loops"] / total_wall, 1)
    }

    print(f"Totale looptijd (wall) : {results['wall_time_s']} s")
    print(f"Total loops (alles)    : {results['total_loops']}")
    print(f"Zware jobs uitgevoerd  : {results['heavy_runs']}")
    print(f"Skips (Newton block)   : {results['skips']}")
    print(f"Gem. jobtijd           : {results['avg_ms']} ms")
    print(f"P50 jobtijd            : {results['p50_ms']} ms")
    print(f"P90 jobtijd            : {results['p90_ms']} ms")
    print(f"P99 jobtijd            : {results['p99_ms']} ms")
    print(f"Throughput             : {results['throughput']} jobs/s")

    return results

if __name__ == "__main__":
    print("=" * 60)
    print("  BETTI Local Torture Test v2")
    print("  Comparing RAW vs BALANCED (14-wetten) resource management")
    print("=" * 60)

    raw_results = run_mode("raw")
    balanced_results = run_mode("balanced")

    print("\n" + "=" * 60)
    print("  COMPARISON")
    print("=" * 60)

    latency_improvement = ((raw_results["p90_ms"] - balanced_results["p90_ms"]) / raw_results["p90_ms"]) * 100
    throughput_ratio = balanced_results["throughput"] / raw_results["throughput"] if raw_results["throughput"] > 0 else 0

    print(f"\nP90 Latency: RAW {raw_results['p90_ms']}ms vs BALANCED {balanced_results['p90_ms']}ms")
    print(f"Improvement: {latency_improvement:.1f}%")
    print(f"\nThroughput: RAW {raw_results['throughput']} vs BALANCED {balanced_results['throughput']} jobs/s")
    print(f"Ratio: {throughput_ratio:.2f}x")
    print(f"\nNewton blocks (skips): {balanced_results['skips']}")
