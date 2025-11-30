#!/usr/bin/env python3
"""
SNAFT AGI Script voor Asterisk
==============================

System Not Authorized For That - Intent validatie voor telefonie.

Dit script wordt aangeroepen door Asterisk AGI en valideert of
een call intent toegestaan is op basis van JIS SNAFT regels.

Argumenten:
    1. caller_number - Beller nummer
    2. dest_number - Bestemming nummer
    3. intent - Gedeclareerde intent (personal, business, urgent, emergency)
    4. trust_level - JIS trust level (0-5)

Output (Asterisk variabelen):
    SNAFT_ALLOWED=1|0
    SNAFT_BLOCKED=1|0
    SNAFT_REVIEW=1|0
    SNAFT_REASON=<string>
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, Tuple

# AGI helper class
class AGI:
    def __init__(self):
        self.env = {}
        self._read_env()

    def _read_env(self):
        """Lees AGI environment variabelen"""
        while True:
            line = sys.stdin.readline().strip()
            if not line:
                break
            if ':' in line:
                key, value = line.split(':', 1)
                self.env[key.strip()] = value.strip()

    def set_variable(self, name: str, value: str):
        """Set Asterisk channel variable"""
        sys.stdout.write(f'SET VARIABLE {name} "{value}"\n')
        sys.stdout.flush()
        sys.stdin.readline()  # Read response

    def verbose(self, message: str, level: int = 1):
        """Log naar Asterisk CLI"""
        sys.stdout.write(f'VERBOSE "{message}" {level}\n')
        sys.stdout.flush()
        sys.stdin.readline()


# SNAFT Regels Database (in productie: echte database)
SNAFT_RULES = [
    {
        "id": "telemarketing_night",
        "description": "Blokkeer telemarketing na 21:00",
        "condition": lambda ctx: (
            ctx.get("caller_type") == "telemarketing" and
            ctx.get("hour") >= 21 and
            ctx.get("dest_type") == "residential"
        ),
        "action": "block",
        "reason": "Telemarketing niet toegestaan na 21:00"
    },
    {
        "id": "spam_blocklist",
        "description": "Blokkeer bekende spam nummers",
        "condition": lambda ctx: ctx.get("caller_number") in SPAM_BLOCKLIST,
        "action": "block",
        "reason": "Nummer op blocklist"
    },
    {
        "id": "first_contact_tibet",
        "description": "Eerste contact vereist TIBET",
        "condition": lambda ctx: (
            ctx.get("first_contact") and
            not ctx.get("has_tibet") and
            ctx.get("trust_level", 0) < 2
        ),
        "action": "review",
        "reason": "Eerste contact zonder TIBET token"
    },
    {
        "id": "emergency_allow",
        "description": "Noodgevallen altijd doorlaten",
        "condition": lambda ctx: ctx.get("intent") == "emergency",
        "action": "allow",
        "trust_override": 5,
        "reason": "Noodgeval - automatisch goedgekeurd"
    },
    {
        "id": "bank_requires_hid",
        "description": "Bank calls vereisen HID",
        "condition": lambda ctx: (
            ctx.get("dest_type") == "bank" and
            not ctx.get("has_hid_attestation")
        ),
        "action": "review",
        "reason": "Bank vereist mens-verificatie"
    },
    {
        "id": "low_trust_to_high_value",
        "description": "Lage trust naar belangrijke bestemmingen",
        "condition": lambda ctx: (
            ctx.get("trust_level", 0) < 2 and
            ctx.get("dest_type") in ["bank", "government", "healthcare"]
        ),
        "action": "review",
        "reason": "Lage trust naar beveiligde bestemming"
    }
]

# Spam blocklist (in productie: database)
SPAM_BLOCKLIST = {
    "+31900123456",
    "+31909999999",
    "0909123456"
}

# Nummer classificatie (in productie: database lookup)
def classify_number(number: str) -> str:
    """Classificeer nummer type"""
    if not number:
        return "unknown"

    # Nederlandse nummers
    if number.startswith("+3190") or number.startswith("090"):
        return "premium"
    if number.startswith("+31800") or number.startswith("0800"):
        return "tollfree"
    if number.startswith("+316") or number.startswith("06"):
        return "mobile"
    if number.startswith("+3110") or number.startswith("010"):
        return "residential"  # Rotterdam

    # Check tegen bekende business nummers
    business_prefixes = ["+31201234", "+31301234"]  # Voorbeelden
    for prefix in business_prefixes:
        if number.startswith(prefix):
            return "business"

    return "residential"

def get_dest_type(number: str) -> str:
    """Bepaal type bestemming"""
    # In productie: database lookup
    dest_types = {
        "112": "emergency",
        "0900": "premium",
        "0800": "tollfree",
    }

    for prefix, dtype in dest_types.items():
        if number.startswith(prefix):
            return dtype

    return "standard"

def check_first_contact(caller: str, dest: str) -> bool:
    """Check of dit eerste contact is tussen caller en dest"""
    # In productie: check call history database
    # Voor nu: simuleer dat het eerste contact is als trust < 2
    return True  # Simplificatie

def evaluate_snaft(ctx: Dict[str, Any]) -> Tuple[str, str, int]:
    """
    Evalueer SNAFT regels tegen context

    Returns: (action, reason, trust_override)
    """
    for rule in SNAFT_RULES:
        try:
            if rule["condition"](ctx):
                return (
                    rule["action"],
                    rule.get("reason", rule["description"]),
                    rule.get("trust_override", -1)
                )
        except Exception as e:
            # Log error maar ga door met andere regels
            continue

    # Geen regel matched - default allow
    return ("allow", "Geen SNAFT regels van toepassing", -1)


def main():
    agi = AGI()

    # Haal argumenten op
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    caller_number = args[0] if len(args) > 0 else agi.env.get("agi_callerid", "")
    dest_number = args[1] if len(args) > 1 else agi.env.get("agi_extension", "")
    intent = args[2] if len(args) > 2 else "personal"
    trust_level = int(args[3]) if len(args) > 3 else 0

    agi.verbose(f"SNAFT: Validating {caller_number} -> {dest_number}, intent={intent}, trust={trust_level}")

    # Bouw context voor regel evaluatie
    now = datetime.now()
    ctx = {
        "caller_number": caller_number,
        "dest_number": dest_number,
        "intent": intent,
        "trust_level": trust_level,
        "caller_type": classify_number(caller_number),
        "dest_type": get_dest_type(dest_number),
        "first_contact": check_first_contact(caller_number, dest_number),
        "has_tibet": trust_level >= 1,  # Simplificatie
        "has_hid_attestation": trust_level >= 3,  # Simplificatie
        "hour": now.hour,
        "weekday": now.weekday(),  # 0=Monday
    }

    agi.verbose(f"SNAFT Context: {json.dumps(ctx)}")

    # Evalueer regels
    action, reason, trust_override = evaluate_snaft(ctx)

    agi.verbose(f"SNAFT Result: action={action}, reason={reason}")

    # Set output variabelen
    if action == "allow":
        agi.set_variable("SNAFT_ALLOWED", "1")
        agi.set_variable("SNAFT_BLOCKED", "0")
        agi.set_variable("SNAFT_REVIEW", "0")
    elif action == "block":
        agi.set_variable("SNAFT_ALLOWED", "0")
        agi.set_variable("SNAFT_BLOCKED", "1")
        agi.set_variable("SNAFT_REVIEW", "0")
    elif action == "review":
        agi.set_variable("SNAFT_ALLOWED", "0")
        agi.set_variable("SNAFT_BLOCKED", "0")
        agi.set_variable("SNAFT_REVIEW", "1")

    agi.set_variable("SNAFT_REASON", reason)

    if trust_override >= 0:
        agi.set_variable("SNAFT_TRUST_OVERRIDE", str(trust_override))

    # Log naar audit trail
    log_entry = {
        "timestamp": now.isoformat(),
        "caller": caller_number,
        "dest": dest_number,
        "intent": intent,
        "trust": trust_level,
        "action": action,
        "reason": reason
    }

    # In productie: schrijf naar database/logfile
    agi.verbose(f"SNAFT Audit: {json.dumps(log_entry)}")


if __name__ == "__main__":
    main()
