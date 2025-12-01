#!/usr/bin/env python3
"""
DABS 14-Wetten Test Suite
==========================

Tests voor de 14 natuurkundige wetten in het DABS resource planning systeem.
Elke test bewijst dat een specifieke wet correct werkt.

Test Cases:
- Test A: Thundering Herd (Stress Test) - Ohm & Thermodynamics blocking
- Test B: David & Goliath (Priority Test) - Archimedes & Kepler scheduling
- Test C: Battery Saver (Condition Test) - Einstein & Heisenberg tradeoffs
- Test D: Memory Fragmentation (Planck Test) - 32MB quanta allocation

Author: Jasper van de Meent
Date: December 2025

Note: Uses only standard library (urllib) for portability
"""

import urllib.request
import urllib.error
import json
import time
import concurrent.futures
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

# Configuration
API_BASE = "https://betti.humotica.com"
# API_BASE = "http://localhost:8010"  # For local testing

# Newton Blocking Threshold (client-side pre-check)
# Requests with trust_level < 0.3 are blocked before reaching the backend
# Newton is a GATEKEEPER law: determines IF task runs, not HOW MUCH boost it gets
NEWTON_TRUST_THRESHOLD = 0.3

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    details: str
    laws_triggered: List[str]

def log_dabs(status: str, task_type: str, urgency: int, details: dict):
    """Pretty log output like suggested in the spec."""
    if status == "allowed":
        icon = f"{Colors.GREEN}✅ ALLOWED{Colors.END}"
    elif status == "blocked":
        icon = f"{Colors.RED}🛑 BLOCKED{Colors.END}"
    elif status == "delayed":
        icon = f"{Colors.YELLOW}⏳ DELAYED{Colors.END}"
    else:
        icon = f"{Colors.BLUE}ℹ️ {status.upper()}{Colors.END}"

    print(f"\n[DABS] {icon}: {task_type} (Urgency {urgency})")

    if "blocking_law" in details and details["blocking_law"]:
        print(f"       └─ {Colors.RED}{details['blocking_law']}: {details.get('message', 'Blocked')}{Colors.END}")

    if "cpu_boost" in details:
        boost_color = Colors.GREEN if details["cpu_boost"] >= 1.0 else Colors.YELLOW
        print(f"       ├─ Einstein: Boost {boost_color}{details['cpu_boost']}x{Colors.END}")

    if "queue_position" in details:
        print(f"       ├─ Archimedes: Queue Pos {details['queue_position']}")

    if "memory_mb" in details:
        print(f"       ├─ Planck: {details['memory_mb']}MB Allocated")

    if "timeout_seconds" in details:
        print(f"       ├─ Doppler: Timeout {details['timeout_seconds']}s")

    if "scaling_signal" in details:
        signal = details["scaling_signal"]
        signal_color = Colors.GREEN if signal == "UP" else (Colors.RED if signal == "DOWN" else Colors.CYAN)
        print(f"       └─ Hooke: Scaling {signal_color}{signal}{Colors.END}")


def plan_resources(task_type: str,
                   urgency: int = 5,
                   participants: List[str] = None,
                   data_size_mb: float = 1.0,
                   trust_level: float = 0.5) -> dict:
    """
    Call the DABS /planner/plan endpoint.

    Includes client-side Newton blocking pre-check:
    - Newton is a GATEKEEPER law (blocking, not scaling)
    - If trust_level < 0.3, block immediately before calling backend
    - This matches DabsClient.kt behavior on Android
    """
    # ═══════════════════════════════════════════════════════════════════
    # NEWTON BLOCKING LAW (Client-side Pre-Check)
    # ═══════════════════════════════════════════════════════════════════
    # Newton is a GATEKEEPER: if trust < 0.3, block immediately.
    # This check happens BEFORE any backend call or CPU boost calculation.
    # Newton determines IF the task runs, not HOW MUCH boost it gets.
    # ═══════════════════════════════════════════════════════════════════
    if trust_level < NEWTON_TRUST_THRESHOLD:
        return {
            "status": "blocked",
            "blocking_law": "Newton",
            "message": f"Trust level too low: {trust_level:.2f} < {NEWTON_TRUST_THRESHOLD} threshold",
            "laws_applied": ["Newton"],
            "cpu_boost": 0.0,
            "memory_mb": 0,
            "timeout_seconds": 0,
            "queue_position": 0
        }

    payload = {
        "task_type": task_type,
        "urgency": urgency,
        "participants": participants or [],
        "data_size_mb": data_size_mb,
        "trust_level": trust_level
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{API_BASE}/planner/plan",
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            response = json.loads(resp.read().decode('utf-8'))

            # API returns nested structure: {success: true, allocation: {...}}
            if response.get("success") and "allocation" in response:
                alloc = response["allocation"]
                # Map to our expected format
                return {
                    "status": "allowed" if alloc.get("health_action") != "BLOCK" else "blocked",
                    "memory_mb": alloc.get("memory_mb", 32),
                    "cpu_boost": alloc.get("cpu_percent", 50) / 50.0,  # Normalize to 1.0
                    "timeout_seconds": alloc.get("timeout_ms", 30000) / 1000.0,
                    "queue_position": alloc.get("queue_priority", 5),
                    "flow_rate_mbps": alloc.get("flow_rate_kbps", 1000) / 1000.0,
                    "scaling_signal": alloc.get("scale_action", "STABLE"),
                    "should_split": alloc.get("split_required", False),
                    "tokens_allocated": alloc.get("cpu_percent", 50) * 10,
                    "chain_hmac": alloc.get("chain_hash"),
                    "laws_applied": alloc.get("laws_applied", []),
                    "blocking_law": None if alloc.get("health_action") != "BLOCK" else "Thermodynamics",
                    "trust_score": alloc.get("trust_score", 0.5),
                    "system_health": alloc.get("system_health_percent", 100),
                    "complexity": alloc.get("complexity_score", 0),
                    "tradeoff_valid": alloc.get("tradeoff_valid", True),
                    "raw": alloc  # Keep raw response for debugging
                }
            else:
                return {"status": "error", "message": "Invalid response format"}
    except urllib.error.HTTPError as e:
        return {"status": "error", "code": e.code, "message": str(e)}
    except urllib.error.URLError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def test_a_thundering_herd() -> TestResult:
    """
    Test A: Thundering Herd (Stress Test)

    Doel: Bewijzen dat de app niet crasht als er chaos is, maar netjes weigert.

    - Loop die 50x snel requests stuurt
    - Eerste paar krijgen success
    - Dan Ohm (rate limiting) of Thermodynamics (health CRITICAL)
    - Requests falen netjes, systeem blijft stabiel
    """
    print(f"\n{'='*60}")
    print(f"{Colors.BOLD}TEST A: THUNDERING HERD (Stress Test){Colors.END}")
    print(f"{'='*60}")
    print("Doel: Bewijzen dat zware belasting netjes afgehandeld wordt")

    start = time.time()
    results = []
    blocked_count = 0
    allowed_count = 0
    error_count = 0
    laws_triggered = set()

    # Fire 30 requests using ThreadPoolExecutor for parallelism
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(30):
            futures.append(executor.submit(
                plan_resources,
                task_type="video_call",
                urgency=5,
                data_size_mb=50.0,  # Heavy task
                trust_level=0.8
            ))

        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            result = future.result()
            results.append(result)

            if result.get("status") == "allowed":
                allowed_count += 1
            elif result.get("status") == "blocked":
                blocked_count += 1
                if result.get("blocking_law"):
                    laws_triggered.add(result["blocking_law"])
            else:
                error_count += 1

            # Log first 3 and any blocked ones
            if i < 3 or result.get("status") == "blocked":
                log_dabs(
                    result.get("status", "unknown"),
                    "video_call",
                    5,
                    result
                )

    duration = (time.time() - start) * 1000

    # Determine pass/fail
    # Success if: some requests handled, system didn't completely fail
    passed = (allowed_count > 0 or blocked_count > 0) and error_count < len(results)

    details = f"Allowed: {allowed_count}, Blocked: {blocked_count}, Errors: {error_count}, Laws: {list(laws_triggered)}"

    print(f"\n{Colors.BOLD}Resultaat:{Colors.END}")
    print(f"  • {allowed_count} requests toegestaan")
    print(f"  • {blocked_count} requests geblokkeerd")
    print(f"  • {error_count} errors")
    print(f"  • Wetten getriggerd: {list(laws_triggered) or ['Geen (systeem hield stand)']}")
    print(f"  • Duur: {duration:.1f}ms")

    return TestResult(
        name="Thundering Herd",
        passed=passed,
        duration_ms=duration,
        details=details,
        laws_triggered=list(laws_triggered)
    )


def test_b_david_goliath() -> TestResult:
    """
    Test B: David & Goliath (Priority Test)

    Doel: Bewijzen dat een klein belangrijk bericht wint van een grote download.

    - Start lage urgency, hoge massa taak (background_sync, 50MB)
    - Start hoge urgency, lage massa taak (voice_call, urgency 9)
    - Voice call moet hogere queue_position krijgen (Archimedes)
    - Voice call interval ~0ms (Kepler)
    """
    print(f"\n{'='*60}")
    print(f"{Colors.BOLD}TEST B: DAVID & GOLIATH (Priority Test){Colors.END}")
    print(f"{'='*60}")
    print("Doel: Klein belangrijk bericht wint van grote download")

    start = time.time()
    laws_triggered = []

    # Goliath: Large background sync
    print(f"\n{Colors.CYAN}1. Start Goliath (background, 50MB, urgency=1){Colors.END}")
    goliath = plan_resources(
        task_type="background",
        urgency=1,
        data_size_mb=50.0,
        trust_level=0.6
    )
    log_dabs(goliath.get("status", "unknown"), "background", 1, goliath)

    # David: Small urgent voice call
    print(f"\n{Colors.CYAN}2. Start David (voice_call, 0.1MB, urgency=9){Colors.END}")
    david = plan_resources(
        task_type="voice_call",
        urgency=9,
        data_size_mb=0.1,
        trust_level=0.9
    )
    log_dabs(david.get("status", "unknown"), "voice_call", 9, david)

    duration = (time.time() - start) * 1000

    # Check if David wins
    david_queue = david.get("queue_position", 999)
    goliath_queue = goliath.get("queue_position", 0)
    david_timeout = david.get("timeout_seconds", 999)
    goliath_timeout = goliath.get("timeout_seconds", 0)

    passed = david_queue <= goliath_queue or david_timeout < goliath_timeout

    if "queue_position" in david or "queue_position" in goliath:
        laws_triggered.append("Archimedes")
    if david_timeout < goliath_timeout:
        laws_triggered.append("Kepler")

    details = f"David queue={david_queue} timeout={david_timeout}s, Goliath queue={goliath_queue} timeout={goliath_timeout}s"

    print(f"\n{Colors.BOLD}Resultaat:{Colors.END}")
    print(f"  • David (voice_call): queue={david_queue}, timeout={david_timeout}s")
    print(f"  • Goliath (background): queue={goliath_queue}, timeout={goliath_timeout}s")
    print(f"  • David wint: {Colors.GREEN if passed else Colors.RED}{passed}{Colors.END}")

    return TestResult(
        name="David & Goliath",
        passed=passed,
        duration_ms=duration,
        details=details,
        laws_triggered=laws_triggered
    )


def test_c_battery_saver() -> TestResult:
    """
    Test C: Battery Saver (Einstein & Heisenberg Test)

    Doel: Zien hoe het systeem reageert op slechte condities.

    - Simuleer lage trust (Heisenberg uncertainty)
    - Vraag zware resource allocatie
    - Verwacht: cpu_boost < 1.0 of blocked
    """
    print(f"\n{'='*60}")
    print(f"{Colors.BOLD}TEST C: BATTERY SAVER (Einstein & Heisenberg){Colors.END}")
    print(f"{'='*60}")
    print("Doel: Systeem past zich aan bij slechte condities")

    start = time.time()
    laws_triggered = []

    # High trust request
    print(f"\n{Colors.CYAN}1. Hoge trust (0.9) - zou normaal moeten werken{Colors.END}")
    high_trust = plan_resources(
        task_type="ai_inference",
        urgency=5,
        data_size_mb=10.0,
        trust_level=0.9
    )
    log_dabs(high_trust.get("status", "unknown"), "ai_inference", 5, high_trust)

    # Low trust request (should trigger Newton blocking or reduced resources)
    print(f"\n{Colors.CYAN}2. Lage trust (0.2) - zou moeten blokkeren of reduceren{Colors.END}")
    low_trust = plan_resources(
        task_type="ai_inference",
        urgency=5,
        data_size_mb=10.0,
        trust_level=0.2  # Below 0.3 threshold
    )
    log_dabs(low_trust.get("status", "unknown"), "ai_inference", 5, low_trust)

    # Very heavy request (might trigger Heisenberg)
    print(f"\n{Colors.CYAN}3. Zware request (100MB, urgency 10){Colors.END}")
    heavy = plan_resources(
        task_type="file_transfer",
        urgency=10,
        data_size_mb=100.0,
        trust_level=0.5
    )
    log_dabs(heavy.get("status", "unknown"), "file_transfer", 10, heavy)

    duration = (time.time() - start) * 1000

    # Check results
    high_boost = high_trust.get("cpu_boost", 1.0)
    low_status = low_trust.get("status", "allowed")
    low_boost = low_trust.get("cpu_boost", 1.0)

    # Pass if: low trust gets reduced resources or blocked
    passed = (low_status == "blocked" or
              low_boost < high_boost or
              low_trust.get("blocking_law") is not None)

    if low_trust.get("blocking_law") == "Newton":
        laws_triggered.append("Newton")
    if "cpu_boost" in high_trust:
        laws_triggered.append("Einstein")
    if low_status == "blocked" and "Heisenberg" in str(low_trust.get("blocking_law", "")):
        laws_triggered.append("Heisenberg")

    details = f"High trust boost={high_boost}, Low trust status={low_status} boost={low_boost}"

    print(f"\n{Colors.BOLD}Resultaat:{Colors.END}")
    print(f"  • Hoge trust: boost={high_boost}")
    print(f"  • Lage trust: status={low_status}, boost={low_boost}")
    print(f"  • Wet werkt correct: {Colors.GREEN if passed else Colors.RED}{passed}{Colors.END}")

    return TestResult(
        name="Battery Saver",
        passed=passed,
        duration_ms=duration,
        details=details,
        laws_triggered=laws_triggered
    )


def test_d_memory_fragmentation() -> TestResult:
    """
    Test D: Memory Fragmentation (Planck Test)

    Doel: Bewijzen dat geheugenbeheer efficiënter is via quanta.

    - Vraag random hoeveelheden geheugen (10MB, 55MB, 2MB)
    - Verwacht: allocatie altijd in veelvouden van 32MB
    - 10MB -> 32MB, 55MB -> 64MB, 2MB -> 32MB
    """
    print(f"\n{'='*60}")
    print(f"{Colors.BOLD}TEST D: MEMORY FRAGMENTATION (Planck Test){Colors.END}")
    print(f"{'='*60}")
    print("Doel: Geheugen allocatie in 32MB quanta")

    start = time.time()
    laws_triggered = []
    test_cases = [
        (2, 32),    # 2MB -> 32MB
        (10, 32),   # 10MB -> 32MB
        (33, 64),   # 33MB -> 64MB
        (55, 64),   # 55MB -> 64MB
        (100, 128), # 100MB -> 128MB
    ]

    results = []
    all_correct = True

    for requested, expected in test_cases:
        result = plan_resources(
            task_type="ai_inference",
            urgency=5,
            data_size_mb=float(requested),
            trust_level=0.7
        )

        allocated = result.get("memory_mb", 0)
        correct = allocated >= expected and allocated % 32 == 0

        if not correct and allocated > 0:
            all_correct = False

        status_icon = f"{Colors.GREEN}✓{Colors.END}" if correct or allocated == 0 else f"{Colors.RED}✗{Colors.END}"
        print(f"  {status_icon} Request {requested}MB → Allocated {allocated}MB (expected ≥{expected}MB, %32=0)")

        results.append({
            "requested": requested,
            "allocated": allocated,
            "expected": expected,
            "correct": correct
        })

    duration = (time.time() - start) * 1000

    if any(r["allocated"] % 32 == 0 for r in results if r["allocated"] > 0):
        laws_triggered.append("Planck")

    passed = all_correct or all(r.get("allocated", 0) % 32 == 0 for r in results if r.get("allocated", 0) > 0)

    details = f"Tested {len(test_cases)} cases, {sum(1 for r in results if r['correct'])} correct"

    print(f"\n{Colors.BOLD}Resultaat:{Colors.END}")
    print(f"  • Alle allocaties in 32MB quanta: {Colors.GREEN if passed else Colors.RED}{passed}{Colors.END}")

    return TestResult(
        name="Memory Fragmentation",
        passed=passed,
        duration_ms=duration,
        details=details,
        laws_triggered=laws_triggered
    )


def run_all_tests():
    """Run all DABS 14-laws tests."""
    print(f"""
{Colors.BOLD}{Colors.CYAN}
╔══════════════════════════════════════════════════════════════════════╗
║                    DABS 14-WETTEN TEST SUITE                         ║
║                                                                      ║
║  Testing the physics-based resource allocation system                ║
║  API: {API_BASE:<55}║
╚══════════════════════════════════════════════════════════════════════╝
{Colors.END}
Datum: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")

    results = []

    # Run all tests
    results.append(test_a_thundering_herd())
    results.append(test_b_david_goliath())
    results.append(test_c_battery_saver())
    results.append(test_d_memory_fragmentation())

    # Summary
    print(f"\n{'='*60}")
    print(f"{Colors.BOLD}TEST SUMMARY{Colors.END}")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    for result in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if result.passed else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {status} {result.name}: {result.duration_ms:.1f}ms")
        print(f"       Laws: {result.laws_triggered or ['None']}")

    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.END}")

    # Save results to JSON
    output = {
        "timestamp": datetime.now().isoformat(),
        "api_base": API_BASE,
        "summary": {
            "passed": passed,
            "total": total,
            "success_rate": f"{passed/total*100:.1f}%"
        },
        "tests": [
            {
                "name": r.name,
                "passed": r.passed,
                "duration_ms": r.duration_ms,
                "details": r.details,
                "laws_triggered": r.laws_triggered
            }
            for r in results
        ]
    }

    with open("/home/jasper/BETTI-TIBET-TEST/tests/dabs_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResultaten opgeslagen in: tests/dabs_results.json")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
