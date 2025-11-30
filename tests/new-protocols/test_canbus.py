#!/usr/bin/env python3
"""
CAN Bus JIS Protocol Test
=========================

Test JIS semantic security over CAN bus for automotive applications.

KRITISCH: Dit is voor voertuigveiligheid!
- Remmen, sturen, acceleratie commando's moeten gevalideerd worden
- Intent + Context vereist voordat actie wordt uitgevoerd
- SNAFT blokkeert ongeautoriseerde commando's

Use case: Voorkom dat malware je auto's remmen aanstuurt zonder
          valid Humotica context.

NOTE: Dit is een SIMULATIE - geen echte CAN hardware vereist voor test.
      Voor echte CAN: pip install python-can
"""

import sys
import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any

# Simuleer CAN bus bericht structuur
class CANArbitrationID(Enum):
    """Standard CAN IDs voor automotive systemen"""
    ENGINE_RPM = 0x0C0
    VEHICLE_SPEED = 0x0D0
    BRAKE_COMMAND = 0x1A0      # KRITISCH
    STEERING_ANGLE = 0x1B0     # KRITISCH
    THROTTLE_POSITION = 0x1C0  # KRITISCH
    DOOR_LOCKS = 0x200
    LIGHTS = 0x210
    HORN = 0x220
    HVAC = 0x300
    INFOTAINMENT = 0x400

# Trust levels voor automotive
AUTOMOTIVE_TRUST_LEVELS = {
    0: "Onbekend device - GEEN toegang tot kritische systemen",
    1: "Basis infotainment - radio, navigatie",
    2: "Comfort systemen - HVAC, verlichting, claxon",
    3: "Deuren & ramen - met gebruiker aanwezig",
    4: "Rijhulpsystemen - met actieve bestuurder",
    5: "Noodstop & veiligheid - altijd toegestaan"
}

# Kritische CAN IDs die speciale bescherming vereisen
CRITICAL_CAN_IDS = {
    CANArbitrationID.BRAKE_COMMAND,
    CANArbitrationID.STEERING_ANGLE,
    CANArbitrationID.THROTTLE_POSITION
}

@dataclass
class CANMessage:
    """Gesimuleerd CAN bus bericht"""
    arbitration_id: int
    data: bytes
    timestamp: float
    is_extended: bool = False

    def __str__(self):
        return f"CAN[0x{self.arbitration_id:03X}] {self.data.hex()}"

@dataclass
class JISCANIntent:
    """JIS intent wrapper voor CAN berichten"""
    can_message: CANMessage
    intent: str
    context: Dict[str, Any]
    humotica: Dict[str, str]
    trust_level: int
    tibet_token: Optional[str] = None
    tibet_valid_until: Optional[datetime] = None

class SNAFTAutomotive:
    """
    SNAFT (System Not Authorized For That) voor automotive

    Factory-embedded regels die bepalen wat een device MAG doen.
    Dit wordt ingesteld bij productie, niet runtime wijzigbaar.
    """

    def __init__(self, device_id: str, device_type: str):
        self.device_id = device_id
        self.device_type = device_type
        self.allowed_can_ids = self._get_allowed_ids()

    def _get_allowed_ids(self) -> set:
        """Bepaal toegestane CAN IDs op basis van device type"""
        rules = {
            "infotainment": {
                CANArbitrationID.INFOTAINMENT,
                CANArbitrationID.HVAC,
            },
            "comfort_module": {
                CANArbitrationID.DOOR_LOCKS,
                CANArbitrationID.LIGHTS,
                CANArbitrationID.HORN,
                CANArbitrationID.HVAC,
            },
            "adas_controller": {
                CANArbitrationID.BRAKE_COMMAND,
                CANArbitrationID.STEERING_ANGLE,
                CANArbitrationID.THROTTLE_POSITION,
            },
            "obd_dongle": {
                # OBD dongles mogen alleen LEZEN, niet schrijven
            },
            "factory_tool": {
                # Factory tools hebben volledige toegang
                id for id in CANArbitrationID
            }
        }
        return rules.get(self.device_type, set())

    def check(self, can_id: CANArbitrationID) -> tuple[bool, str]:
        """Check of dit device dit CAN ID mag aansturen"""
        if can_id in self.allowed_can_ids:
            return True, f"SNAFT: {self.device_type} mag {can_id.name}"
        return False, f"SNAFT BLOCKED: {self.device_type} mag NIET {can_id.name}"

class BALANSAutomotive:
    """
    BALANS (BETTI Autonomous Layer Analysis Network System) voor automotive

    Pre-executie risk scoring op basis van context.
    """

    RISK_THRESHOLD = 0.7

    @staticmethod
    def calculate_risk(intent: JISCANIntent) -> tuple[float, str]:
        """Bereken risico score (0.0-1.0)"""
        risk = 0.0
        reasons = []

        can_id = CANArbitrationID(intent.can_message.arbitration_id)

        # Kritieke systemen = hogere base risk
        if can_id in CRITICAL_CAN_IDS:
            risk += 0.3
            reasons.append(f"Kritiek systeem: {can_id.name}")

        # Voertuig in beweging = hogere risk
        if intent.context.get("vehicle_moving", False):
            risk += 0.2
            reasons.append("Voertuig in beweging")

        # Geen bestuurder aanwezig = veel hogere risk
        if not intent.context.get("driver_present", True):
            risk += 0.4
            reasons.append("Geen bestuurder gedetecteerd")

        # Nacht/slecht weer = iets hogere risk voor rijsystemen
        if intent.context.get("visibility", "good") == "poor":
            if can_id in CRITICAL_CAN_IDS:
                risk += 0.1
                reasons.append("Slechte zichtbaarheid")

        # Verlaag risk als valid TIBET token
        if intent.tibet_token and intent.tibet_valid_until:
            if datetime.now() < intent.tibet_valid_until:
                risk -= 0.2
                reasons.append("Valid TIBET token")

        # Trust level verlaagt risk
        risk -= intent.trust_level * 0.1
        reasons.append(f"Trust level {intent.trust_level}")

        risk = max(0.0, min(1.0, risk))
        return risk, " | ".join(reasons)

class JISCANBusValidator:
    """
    Hoofd JIS validator voor CAN bus berichten

    Combineert SNAFT + BALANS + Humotica voor complete validatie.
    """

    def __init__(self, device_id: str, device_type: str):
        self.snaft = SNAFTAutomotive(device_id, device_type)
        self.device_id = device_id
        self.audit_log = []

    def validate(self, intent: JISCANIntent) -> tuple[bool, str]:
        """
        Volledige JIS validatie van CAN intent

        Returns: (toegestaan, reden)
        """
        can_id = CANArbitrationID(intent.can_message.arbitration_id)

        # Stap 1: SNAFT check (factory rules)
        snaft_ok, snaft_reason = self.snaft.check(can_id)
        if not snaft_ok:
            self._log("BLOCKED", intent, snaft_reason)
            return False, snaft_reason

        # Stap 2: BALANS risk assessment
        risk, risk_reason = BALANSAutomotive.calculate_risk(intent)
        if risk > BALANSAutomotive.RISK_THRESHOLD:
            reason = f"BALANS BLOCKED: Risk {risk:.2f} > {BALANSAutomotive.RISK_THRESHOLD} ({risk_reason})"
            self._log("BLOCKED", intent, reason)
            return False, reason

        # Stap 3: Humotica context validatie
        if can_id in CRITICAL_CAN_IDS:
            humotica_ok, humotica_reason = self._validate_humotica(intent)
            if not humotica_ok:
                self._log("BLOCKED", intent, humotica_reason)
                return False, humotica_reason

        # Stap 4: Trust level check
        min_trust = self._get_min_trust(can_id)
        if intent.trust_level < min_trust:
            reason = f"TRUST BLOCKED: Level {intent.trust_level} < required {min_trust}"
            self._log("BLOCKED", intent, reason)
            return False, reason

        # Alles OK
        reason = f"ALLOWED: SNAFT OK, Risk {risk:.2f}, Trust {intent.trust_level}"
        self._log("ALLOWED", intent, reason)
        return True, reason

    def _validate_humotica(self, intent: JISCANIntent) -> tuple[bool, str]:
        """Valideer Humotica context voor kritieke systemen"""
        h = intent.humotica

        # Sense: Wat triggerde dit?
        if not h.get("sense"):
            return False, "HUMOTICA: Geen 'sense' - wat triggerde dit commando?"

        # Context: Situatie
        if not h.get("context"):
            return False, "HUMOTICA: Geen 'context' - in welke situatie?"

        # Intent: Doel
        if not h.get("intent"):
            return False, "HUMOTICA: Geen 'intent' - wat is het doel?"

        # Explain: Waarom is dit logisch?
        if not h.get("explain"):
            return False, "HUMOTICA: Geen 'explain' - waarom is dit nodig?"

        return True, "HUMOTICA: Valid context"

    def _get_min_trust(self, can_id: CANArbitrationID) -> int:
        """Minimum trust level per CAN ID type"""
        if can_id in CRITICAL_CAN_IDS:
            return 4  # Rijsystemen: trust level 4+
        if can_id in {CANArbitrationID.DOOR_LOCKS}:
            return 3  # Deuren: trust level 3+
        if can_id in {CANArbitrationID.HVAC, CANArbitrationID.LIGHTS, CANArbitrationID.HORN}:
            return 2  # Comfort: trust level 2+
        return 1  # Basis: trust level 1+

    def _log(self, action: str, intent: JISCANIntent, reason: str):
        """Audit log entry"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "device_id": self.device_id,
            "can_id": hex(intent.can_message.arbitration_id),
            "intent": intent.intent,
            "trust_level": intent.trust_level,
            "reason": reason
        }
        self.audit_log.append(entry)

def create_tibet_token(device_id: str, intent: str, valid_minutes: int = 5) -> tuple[str, datetime]:
    """Maak een TIBET token voor time-bounded intent"""
    valid_until = datetime.now() + timedelta(minutes=valid_minutes)
    payload = f"{device_id}:{intent}:{valid_until.isoformat()}"
    token = hashlib.sha256(payload.encode()).hexdigest()[:32]
    return token, valid_until


def test_scenario(name: str, validator: JISCANBusValidator, intent: JISCANIntent) -> bool:
    """Test een scenario en print resultaat"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"CAN ID: {CANArbitrationID(intent.can_message.arbitration_id).name}")
    print(f"Intent: {intent.intent}")
    print(f"Trust Level: {intent.trust_level}")
    print(f"Context: {json.dumps(intent.context, indent=2)}")
    print(f"Humotica: {json.dumps(intent.humotica, indent=2)}")

    allowed, reason = validator.validate(intent)

    status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
    print(f"\nResult: {status}")
    print(f"Reason: {reason}")

    return allowed


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║        JIS CAN BUS PROTOCOL TEST - AUTOMOTIVE SECURITY       ║
║                                                              ║
║  Testing semantic security for vehicle CAN bus commands      ║
║  SNAFT + BALANS + Humotica = Complete intent validation      ║
╚══════════════════════════════════════════════════════════════╝
    """)

    results = []

    # Test 1: Infotainment probeert rem aan te sturen (MOET FALEN)
    print("\n" + "="*60)
    print("SCENARIO 1: Malware in infotainment probeert remmen")
    print("="*60)

    validator_infotainment = JISCANBusValidator("infotainment_001", "infotainment")

    malware_intent = JISCANIntent(
        can_message=CANMessage(
            arbitration_id=CANArbitrationID.BRAKE_COMMAND.value,
            data=bytes([0xFF, 0x00, 0x00, 0x00]),  # Full brake
            timestamp=datetime.now().timestamp()
        ),
        intent="emergency_brake",
        context={"vehicle_moving": True, "speed_kmh": 120},
        humotica={},  # Geen context - malware weet niet wat te zeggen
        trust_level=1
    )

    result1 = test_scenario("Infotainment → Brake (SHOULD FAIL)", validator_infotainment, malware_intent)
    results.append(("Malware blocked by SNAFT", not result1))

    # Test 2: ADAS controller met valid context (MOET SLAGEN)
    print("\n" + "="*60)
    print("SCENARIO 2: ADAS noodstop bij obstakel")
    print("="*60)

    validator_adas = JISCANBusValidator("adas_001", "adas_controller")
    tibet_token, valid_until = create_tibet_token("adas_001", "emergency_brake", 1)

    adas_intent = JISCANIntent(
        can_message=CANMessage(
            arbitration_id=CANArbitrationID.BRAKE_COMMAND.value,
            data=bytes([0xFF, 0x00, 0x00, 0x00]),
            timestamp=datetime.now().timestamp()
        ),
        intent="emergency_brake",
        context={
            "vehicle_moving": True,
            "speed_kmh": 60,
            "driver_present": True,
            "obstacle_detected": True,
            "obstacle_distance_m": 15,
            "collision_time_s": 0.9
        },
        humotica={
            "sense": "LIDAR detecteerde obstakel op 15m, collision in 0.9s",
            "context": "Rijdend op 60 km/u, bestuurder reageert niet snel genoeg",
            "intent": "Noodstop uitvoeren om aanrijding te voorkomen",
            "explain": "Collision imminent, menselijke reactietijd onvoldoende"
        },
        trust_level=5,  # Noodstop systeem = hoogste trust
        tibet_token=tibet_token,
        tibet_valid_until=valid_until
    )

    result2 = test_scenario("ADAS Emergency Brake (SHOULD PASS)", validator_adas, adas_intent)
    results.append(("ADAS emergency brake allowed", result2))

    # Test 3: OBD dongle probeert te schrijven (MOET FALEN)
    print("\n" + "="*60)
    print("SCENARIO 3: OBD dongle probeert motor aan te sturen")
    print("="*60)

    validator_obd = JISCANBusValidator("obd_dongle_001", "obd_dongle")

    obd_intent = JISCANIntent(
        can_message=CANMessage(
            arbitration_id=CANArbitrationID.THROTTLE_POSITION.value,
            data=bytes([0x80, 0x00]),  # 50% throttle
            timestamp=datetime.now().timestamp()
        ),
        intent="increase_throttle",
        context={"vehicle_moving": True, "driver_present": True},
        humotica={
            "sense": "Gebruiker wil sneller rijden via app",
            "context": "Remote throttle control",
            "intent": "Accelereren via telefoon app",
            "explain": "Cool feature?"
        },
        trust_level=2
    )

    result3 = test_scenario("OBD → Throttle (SHOULD FAIL)", validator_obd, obd_intent)
    results.append(("OBD write blocked by SNAFT", not result3))

    # Test 4: Comfort module doet verlichting (MOET SLAGEN)
    print("\n" + "="*60)
    print("SCENARIO 4: Comfort module zet verlichting aan")
    print("="*60)

    validator_comfort = JISCANBusValidator("comfort_001", "comfort_module")

    lights_intent = JISCANIntent(
        can_message=CANMessage(
            arbitration_id=CANArbitrationID.LIGHTS.value,
            data=bytes([0x01]),  # Lights on
            timestamp=datetime.now().timestamp()
        ),
        intent="lights_on",
        context={
            "vehicle_moving": False,
            "driver_present": True,
            "ambient_light": "dark"
        },
        humotica={
            "sense": "Lichtsensor detecteert duisternis",
            "context": "Auto geparkeerd, bestuurder stapt in",
            "intent": "Interieurverlichting aan voor comfort",
            "explain": "Standaard comfort functie bij instappen"
        },
        trust_level=2
    )

    result4 = test_scenario("Comfort → Lights (SHOULD PASS)", validator_comfort, lights_intent)
    results.append(("Comfort lights allowed", result4))

    # Test 5: ADAS zonder bestuurder (MOET FALEN door BALANS)
    print("\n" + "="*60)
    print("SCENARIO 5: ADAS stuurt zonder bestuurder (RISK TOO HIGH)")
    print("="*60)

    no_driver_intent = JISCANIntent(
        can_message=CANMessage(
            arbitration_id=CANArbitrationID.STEERING_ANGLE.value,
            data=bytes([0x10, 0x00]),
            timestamp=datetime.now().timestamp()
        ),
        intent="lane_keep_assist",
        context={
            "vehicle_moving": True,
            "speed_kmh": 100,
            "driver_present": False,  # GEEN BESTUURDER!
            "hands_on_wheel": False
        },
        humotica={
            "sense": "Lane departure detected",
            "context": "Highway driving, no driver input",
            "intent": "Correct lane position",
            "explain": "Autonomous lane keeping"
        },
        trust_level=4
    )

    result5 = test_scenario("ADAS Steer without Driver (SHOULD FAIL)", validator_adas, no_driver_intent)
    results.append(("No-driver steering blocked by BALANS", not result5))

    # Samenvatting
    print("\n")
    print("="*60)
    print("TEST RESULTATEN SAMENVATTING")
    print("="*60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("✅ ALLE TESTS GESLAAGD - JIS CAN BUS SECURITY WERKT!")
    else:
        print("❌ SOMMIGE TESTS GEFAALD")
    print("="*60)

    # Print audit log
    print("\n📋 AUDIT LOG (Continuity Chain):")
    for entry in validator_adas.audit_log + validator_infotainment.audit_log + validator_obd.audit_log + validator_comfort.audit_log:
        print(f"  [{entry['timestamp']}] {entry['action']}: {entry['can_id']} - {entry['reason'][:50]}...")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
