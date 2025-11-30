#!/usr/bin/env python3
"""
TIBET Token Validation AGI Script
=================================

Valideert TIBET (Time Intent Based Event Token) tokens voor Asterisk.

Argumenten:
    1. tibet_token - De TIBET token string
    2. valid_until - ISO timestamp wanneer token verloopt

Output:
    TIBET_VALID=1|0
    TIBET_REASON=<string>
"""

import sys
import hashlib
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


# Bekende valid tokens (in productie: database/Redis)
VALID_TOKENS = {}


def validate_token(token: str, valid_until: str) -> tuple:
    """
    Valideer TIBET token

    Returns: (is_valid, reason)
    """
    if not token:
        return False, "Geen token aanwezig"

    if not valid_until:
        return False, "Geen valid_until timestamp"

    try:
        expiry = datetime.fromisoformat(valid_until.replace('Z', '+00:00'))
        now = datetime.now(expiry.tzinfo) if expiry.tzinfo else datetime.now()

        if now > expiry:
            return False, f"Token verlopen op {valid_until}"
    except Exception as e:
        return False, f"Ongeldige timestamp: {e}"

    # In productie: verificeer token signature tegen database
    # Voor nu: accepteer alle tokens met valid timestamp
    if len(token) >= 16:  # Minimale token lengte
        return True, "Token valid"

    return False, "Ongeldig token formaat"


def main():
    agi = AGI()

    args = sys.argv[1:] if len(sys.argv) > 1 else []

    token = args[0] if len(args) > 0 else ""
    valid_until = args[1] if len(args) > 1 else ""

    agi.verbose(f"TIBET: Validating token={token[:8]}... valid_until={valid_until}")

    is_valid, reason = validate_token(token, valid_until)

    agi.set_variable("TIBET_VALID", "1" if is_valid else "0")
    agi.set_variable("TIBET_REASON", reason)

    agi.verbose(f"TIBET Result: valid={is_valid}, reason={reason}")


if __name__ == "__main__":
    main()
