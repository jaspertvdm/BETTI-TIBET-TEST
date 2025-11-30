#!/usr/bin/env python3
"""
BALANS Risk Assessment AGI Script
=================================

BETTI Autonomous Layer Analysis Network System - Real-time risk scoring.

Argumenten:
    1. caller_number
    2. dest_number
    3. intent
    4. trust_level

Output:
    BALANS_RISK=<float 0.0-1.0>
    BALANS_REASON=<string>
"""

import sys
import json
from datetime import datetime


class AGI:
    def __init__(self):
        self.env = {}
        self._read_env()

    def _read_env(self):
        while True:
            line = sys.stdin.readline().strip()
            if not line:
                break
            if ':' in line:
                key, value = line.split(':', 1)
                self.env[key.strip()] = value.strip()

    def set_variable(self, name: str, value: str):
        sys.stdout.write(f'SET VARIABLE {name} "{value}"\n')
        sys.stdout.flush()
        sys.stdin.readline()

    def verbose(self, message: str, level: int = 1):
        sys.stdout.write(f'VERBOSE "{message}" {level}\n')
        sys.stdout.flush()
        sys.stdin.readline()


def calculate_risk(caller: str, dest: str, intent: str, trust: int) -> tuple:
    """
    Bereken risk score op basis van BETTI wetten

    Returns: (risk_score, reasons)
    """
    risk = 0.0
    reasons = []

    # Base risk op basis van trust level (Newton's 1e wet - momentum)
    base_risk = max(0, (5 - trust) * 0.1)
    risk += base_risk
    reasons.append(f"Trust {trust} → base risk {base_risk:.2f}")

    # Intent risk (Kepler - complexity = time)
    intent_risks = {
        "emergency": -0.3,  # Verlaag risk voor noodgevallen
        "personal": 0.0,
        "business": 0.05,
        "urgent": 0.1,
        "unknown": 0.2
    }
    intent_risk = intent_risks.get(intent, 0.15)
    risk += intent_risk
    reasons.append(f"Intent '{intent}' → {intent_risk:.2f}")

    # Tijd-gebaseerde risk (Einstein - relativiteit)
    hour = datetime.now().hour
    if hour < 7 or hour > 22:  # Buiten kantooruren
        if intent not in ["emergency", "urgent"]:
            risk += 0.15
            reasons.append("Buiten kantooruren → +0.15")

    # Caller reputation (Thermodynamica - entropie history)
    # In productie: lookup call history, complaints, etc.
    # Voor nu: simuleer op basis van nummer format
    if caller.startswith("0900") or caller.startswith("+31900"):
        risk += 0.3
        reasons.append("Premium nummer → +0.30")
    elif not caller.startswith("+") and len(caller) < 10:
        risk += 0.2
        reasons.append("Verdacht nummerformaat → +0.20")

    # Destination sensitivity (Maxwell - field strength)
    sensitive_prefixes = ["112", "0800", "0900"]
    for prefix in sensitive_prefixes:
        if dest.startswith(prefix):
            risk += 0.1
            reasons.append(f"Gevoelige bestemming ({prefix}) → +0.10")
            break

    # Cap risk at 1.0
    risk = max(0.0, min(1.0, risk))

    return risk, " | ".join(reasons)


def main():
    agi = AGI()

    args = sys.argv[1:] if len(sys.argv) > 1 else []

    caller = args[0] if len(args) > 0 else ""
    dest = args[1] if len(args) > 1 else ""
    intent = args[2] if len(args) > 2 else "unknown"
    trust = int(args[3]) if len(args) > 3 else 0

    agi.verbose(f"BALANS: Calculating risk for {caller} -> {dest}")

    risk, reasons = calculate_risk(caller, dest, intent, trust)

    agi.set_variable("BALANS_RISK", f"{risk:.2f}")
    agi.set_variable("BALANS_REASON", reasons)

    agi.verbose(f"BALANS Result: risk={risk:.2f}, reasons={reasons}")


if __name__ == "__main__":
    main()
