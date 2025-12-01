import time
import math
import os
import statistics
from threading import Thread, Lock

# fase tijd in seconden
PHASE_DURATION = 60

# BALANS configuratie
COOLDOWN = 0.02          # min. tijd tussen heavy jobs (balanced)
MAX_PAR_HEAVY = 6        # max parallel op jouw server (pas aan naar cores)

# zwaarte instellingen
VEC_SIZE = 300_000       # vector RAM pressure
RENDER_W = 128           # pseudo-render width
RENDER_H = 128           # pseudo-render height
CPU_LOOPS = 150_000      # raw CPU load

state_lock = Lock()
active_heavy = 0
last_heavy_ts = 0.0

def heavy_job():
    """
    Een zware taak: RAM alloc + render + CPU ALU stress.
    Ideaal voor test van jitter, scheduler en BALANS.
    """

    # RAM / cache load
    buf = [math.sin(i * 0.0001) for i in range(VEC_SIZE)]

    # "render" simulatie
    acc = 0.0
    for y in range(RENDER_H):
        base = y * RENDER_W
        for x in range(RENDER_W):
            idx = (base + x) % VEC_SIZE
            acc += buf[idx] * 0.27

    # CPU stress
    for i in range(CPU_LOOPS):
        acc += math.cos(i * 0.00007)

    return acc


def worker(mode, end_at, exec_times, counters):
    global active_heavy, last_heavy_ts

    while time.time() < end_at:
        now = time.time()
        do_heavy = False

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

            else:  # RAW
                active_heavy += 1
                counters["heavy_runs"] += 1
                do_heavy = True

        if not do_heavy:
            time.sleep(0.001)
            continue

        t0 = time.time()
        heavy_job()
        dt = (time.time() - t0) * 1000.0  # in ms

        with state_lock:
            exec_times.append(dt)
            active_heavy -= 1
            counters["total_jobs"] += 1

        time.sleep(0.001)


def run_phase(mode: str):
    print(f"\n=== PHASE: {mode.upper()} ({PHASE_DURATION}s) ===")
    exec_times = []
    counters = {"total_jobs": 0, "heavy_runs": 0, "skips": 0}

    start = time.time()
    end = start + PHASE_DURATION

    thread_count = os.cpu_count() or 8
    print(f"Workers: {thread_count}")

    threads = []
    for _ in range(thread_count):
        t = Thread(target=worker, args=(mode, end, exec_times, counters))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    total_wall = time.time() - start

    if exec_times:
        ts = sorted(exec_times)
        avg = statistics.mean(ts)
        p50 = ts[int(0.5 * len(ts))]
        p90 = ts[int(0.9 * len(ts))]
    else:
        avg = p50 = p90 = 0.0

    print(f"Totale looptijd (wall) : {total_wall:.1f} s")
    print(f"Jobs uitgevoerd        : {counters['total_jobs']}")
    print(f"Heavy-runs             : {counters['heavy_runs']}")
    print(f"Skips (BALANS)         : {counters['skips']}")
    print(f"Gem. jobtijd           : {avg:.1f} ms")
    print(f"P50 jobtijd            : {p50:.1f} ms")
    print(f"P90 jobtijd            : {p90:.1f} ms")


if __name__ == "__main__":
    # RAW fase
    run_phase("raw")

    # Idle fase (telefoon/CPU mag cooldown)
    print("\n=== PHASE: idle (60s) ===")
    time.sleep(60)

    # BALANCED fase
    run_phase("balanced")
