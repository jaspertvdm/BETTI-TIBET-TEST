#!/usr/bin/env python3
"""
WebAuthn/FIDO2 JIS Protocol Test
================================

Test JIS HID binding met WebAuthn/FIDO2 hardware keys.

Dit is de perfecte integratie:
- WebAuthn heeft al public key cryptografie
- JIS voegt HID (Human Identity) attestation toe
- Samen = bewijs dat een MENS de key fysiek aanraakt

Use case: Passwordless login met JIS trust levels.
          Niet alleen "heb je de key" maar "ben jij de mens die de key mag gebruiken"

NOTE: Dit is een SIMULATIE - geen echte FIDO2 hardware vereist.
      Voor echte FIDO2: pip install fido2
"""

import sys
import json
import hashlib
import base64
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

class AuthenticatorType(Enum):
    """Types FIDO2 authenticators"""
    PLATFORM = "platform"      # TouchID, FaceID, Windows Hello
    CROSS_PLATFORM = "cross-platform"  # YubiKey, hardware tokens

class UserVerification(Enum):
    """User verification methodes"""
    NONE = "none"
    PRESENCE = "presence"      # Knop indrukken
    FINGERPRINT = "fingerprint"
    FACE = "face"
    PIN = "pin"

@dataclass
class FIDOCredential:
    """Gesimuleerde FIDO2 credential"""
    credential_id: bytes
    public_key: bytes
    user_handle: bytes
    rp_id: str  # Relying Party ID (website domain)
    authenticator_type: AuthenticatorType
    created_at: datetime
    last_used: Optional[datetime] = None
    use_count: int = 0

@dataclass
class JISHIDBinding:
    """
    JIS HID binding voor FIDO2 credential

    Dit koppelt een WebAuthn credential aan een JIS Human Identity.
    De HID VERLAAT NOOIT het device - alleen binding hashes worden gedeeld.
    """
    credential_id: bytes
    hid_binding_hash: str  # SHA-256(HID_public + credential_id)
    trust_level: int
    created_at: datetime
    biometric_bound: bool = False
    device_bound: bool = True

    # Humotica context van de binding
    humotica: Dict[str, str] = field(default_factory=dict)

    # TIBET token voor time-bounded access
    tibet_token: Optional[str] = None
    tibet_valid_until: Optional[datetime] = None

@dataclass
class AuthenticationRequest:
    """WebAuthn authentication request met JIS context"""
    rp_id: str
    challenge: bytes
    user_verification: UserVerification

    # JIS uitbreidingen
    required_trust_level: int = 1
    require_hid_attestation: bool = False
    require_tibet: bool = False
    humotica_context: Dict[str, str] = field(default_factory=dict)

@dataclass
class AuthenticationResponse:
    """WebAuthn authentication response met JIS attestation"""
    credential_id: bytes
    authenticator_data: bytes
    signature: bytes
    user_handle: bytes

    # JIS attestation
    hid_attestation: Optional[bytes] = None
    tibet_token: Optional[str] = None
    trust_level: int = 0
    humotica: Dict[str, str] = field(default_factory=dict)

class SimulatedFIDO2Authenticator:
    """
    Gesimuleerde FIDO2 authenticator met JIS integratie

    In productie zou dit een echte YubiKey of platform authenticator zijn.
    """

    def __init__(self, authenticator_type: AuthenticatorType):
        self.type = authenticator_type
        self.credentials: Dict[bytes, FIDOCredential] = {}
        self.hid_bindings: Dict[bytes, JISHIDBinding] = {}

        # Simuleer HID key (in echt zou dit in secure enclave zitten)
        self._hid_private = os.urandom(32)
        self._hid_public = hashlib.sha256(self._hid_private).digest()

    def create_credential(self, rp_id: str, user_handle: bytes) -> FIDOCredential:
        """Maak nieuwe FIDO2 credential"""
        credential_id = os.urandom(32)
        public_key = os.urandom(65)  # Simuleer EC P-256 public key

        credential = FIDOCredential(
            credential_id=credential_id,
            public_key=public_key,
            user_handle=user_handle,
            rp_id=rp_id,
            authenticator_type=self.type,
            created_at=datetime.now()
        )

        self.credentials[credential_id] = credential
        return credential

    def bind_hid(self, credential_id: bytes, trust_level: int,
                 humotica: Dict[str, str], biometric: bool = False) -> JISHIDBinding:
        """
        Bind JIS HID aan FIDO2 credential

        Dit creëert een cryptografische binding tussen de credential
        en de Human Identity, ZONDER de HID te onthullen.
        """
        if credential_id not in self.credentials:
            raise ValueError("Credential niet gevonden")

        # Maak binding hash (HID public + credential ID)
        binding_data = self._hid_public + credential_id
        binding_hash = hashlib.sha256(binding_data).hexdigest()

        binding = JISHIDBinding(
            credential_id=credential_id,
            hid_binding_hash=binding_hash,
            trust_level=trust_level,
            created_at=datetime.now(),
            biometric_bound=biometric,
            humotica=humotica
        )

        self.hid_bindings[credential_id] = binding
        return binding

    def create_tibet_token(self, credential_id: bytes,
                           valid_minutes: int = 5) -> tuple[str, datetime]:
        """Maak TIBET token voor time-bounded authenticatie"""
        if credential_id not in self.hid_bindings:
            raise ValueError("Geen HID binding voor deze credential")

        binding = self.hid_bindings[credential_id]
        valid_until = datetime.now() + timedelta(minutes=valid_minutes)

        # Token = hash van binding + timestamp
        token_data = f"{binding.hid_binding_hash}:{valid_until.isoformat()}"
        token = hashlib.sha256(token_data.encode()).hexdigest()[:32]

        binding.tibet_token = token
        binding.tibet_valid_until = valid_until

        return token, valid_until

    def authenticate(self, request: AuthenticationRequest,
                    credential_id: bytes) -> Optional[AuthenticationResponse]:
        """
        Voer WebAuthn authenticatie uit met JIS validatie
        """
        if credential_id not in self.credentials:
            return None

        credential = self.credentials[credential_id]

        # Check RP ID match
        if credential.rp_id != request.rp_id:
            return None

        # Simuleer authenticator data
        authenticator_data = os.urandom(37)  # Simplified

        # Simuleer signature
        signature = os.urandom(64)

        # Update usage
        credential.last_used = datetime.now()
        credential.use_count += 1

        # Bouw response
        response = AuthenticationResponse(
            credential_id=credential_id,
            authenticator_data=authenticator_data,
            signature=signature,
            user_handle=credential.user_handle
        )

        # Voeg JIS attestation toe als we HID binding hebben
        if credential_id in self.hid_bindings:
            binding = self.hid_bindings[credential_id]
            response.trust_level = binding.trust_level
            response.humotica = binding.humotica

            # HID attestation = signature over challenge met HID private key
            attestation_data = request.challenge + credential_id
            response.hid_attestation = hashlib.sha256(
                self._hid_private + attestation_data
            ).digest()

            # TIBET token als geldig
            if binding.tibet_token and binding.tibet_valid_until:
                if datetime.now() < binding.tibet_valid_until:
                    response.tibet_token = binding.tibet_token

        return response

class JISWebAuthnValidator:
    """
    JIS validator voor WebAuthn responses

    Valideert niet alleen de WebAuthn signature, maar ook:
    - HID binding (is dit dezelfde mens?)
    - Trust level (mag deze mens dit doen?)
    - TIBET token (is dit binnen tijdvenster?)
    - Humotica context (is er een logische reden?)
    """

    def __init__(self):
        self.known_bindings: Dict[str, JISHIDBinding] = {}
        self.audit_log: List[Dict] = []

    def register_binding(self, binding: JISHIDBinding):
        """Registreer bekende HID binding"""
        self.known_bindings[binding.hid_binding_hash] = binding

    def validate(self, request: AuthenticationRequest,
                response: AuthenticationResponse) -> tuple[bool, str, Dict]:
        """
        Volledige JIS validatie van WebAuthn response

        Returns: (valid, reason, details)
        """
        details = {
            "webauthn_valid": False,
            "hid_valid": False,
            "trust_valid": False,
            "tibet_valid": False,
            "humotica_valid": False
        }

        # Stap 1: Basis WebAuthn validatie (simplified)
        if not response.signature or not response.authenticator_data:
            return False, "WebAuthn: Ongeldige signature/data", details
        details["webauthn_valid"] = True

        # Stap 2: HID attestation check
        if request.require_hid_attestation:
            if not response.hid_attestation:
                self._log("BLOCKED", "Geen HID attestation", request, response)
                return False, "JIS: HID attestation vereist maar niet aanwezig", details
        details["hid_valid"] = True

        # Stap 3: Trust level check
        if response.trust_level < request.required_trust_level:
            reason = f"JIS: Trust level {response.trust_level} < vereist {request.required_trust_level}"
            self._log("BLOCKED", reason, request, response)
            return False, reason, details
        details["trust_valid"] = True

        # Stap 4: TIBET token check
        if request.require_tibet:
            if not response.tibet_token:
                self._log("BLOCKED", "TIBET token vereist", request, response)
                return False, "JIS: TIBET token vereist maar niet aanwezig", details
            # In productie: valideer token tegen server
        details["tibet_valid"] = True

        # Stap 5: Humotica context check
        if request.humotica_context:
            if not response.humotica:
                self._log("BLOCKED", "Humotica context vereist", request, response)
                return False, "JIS: Humotica context vereist", details
        details["humotica_valid"] = True

        self._log("ALLOWED", "Alle validaties geslaagd", request, response)
        return True, "JIS: Authenticatie succesvol", details

    def _log(self, action: str, reason: str,
            request: AuthenticationRequest, response: AuthenticationResponse):
        """Audit log entry"""
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "reason": reason,
            "rp_id": request.rp_id,
            "trust_level": response.trust_level,
            "has_hid": response.hid_attestation is not None,
            "has_tibet": response.tibet_token is not None
        })


def test_scenario(name: str, authenticator: SimulatedFIDO2Authenticator,
                 validator: JISWebAuthnValidator,
                 request: AuthenticationRequest,
                 credential_id: bytes,
                 expected_pass: bool) -> bool:
    """Test een scenario"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"RP ID: {request.rp_id}")
    print(f"Required Trust: {request.required_trust_level}")
    print(f"Require HID: {request.require_hid_attestation}")
    print(f"Require TIBET: {request.require_tibet}")

    response = authenticator.authenticate(request, credential_id)

    if not response:
        print("\n❌ Authenticator gaf geen response")
        return not expected_pass

    print(f"\nResponse Trust Level: {response.trust_level}")
    print(f"Has HID Attestation: {response.hid_attestation is not None}")
    print(f"Has TIBET Token: {response.tibet_token is not None}")

    valid, reason, details = validator.validate(request, response)

    status = "✅ ALLOWED" if valid else "❌ BLOCKED"
    print(f"\nResult: {status}")
    print(f"Reason: {reason}")
    print(f"Details: {json.dumps(details, indent=2)}")

    passed = valid == expected_pass
    return passed


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║      JIS WEBAUTHN/FIDO2 PROTOCOL TEST - HID BINDING          ║
║                                                              ║
║  Testing JIS Human Identity binding with hardware keys       ║
║  WebAuthn + HID = Proof of human presence                    ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Setup
    authenticator = SimulatedFIDO2Authenticator(AuthenticatorType.CROSS_PLATFORM)
    validator = JISWebAuthnValidator()

    # Maak credential voor bank website
    user_handle = b"jasper@example.com"
    credential = authenticator.create_credential("bank.example.com", user_handle)

    print(f"Created credential: {credential.credential_id.hex()[:16]}...")

    # Bind HID met hoog trust level (bank = level 3)
    binding = authenticator.bind_hid(
        credential.credential_id,
        trust_level=3,
        humotica={
            "sense": "Gebruiker registreerde YubiKey bij bank account",
            "context": "Online banking setup, 2FA configuratie",
            "intent": "Sterke authenticatie voor financiële transacties",
            "explain": "PSD2 compliant authenticatie methode"
        },
        biometric=False  # YubiKey heeft geen biometrie
    )

    # Registreer binding bij validator
    validator.register_binding(binding)

    print(f"HID Binding: {binding.hid_binding_hash[:16]}...")
    print(f"Trust Level: {binding.trust_level}")

    results = []

    # Test 1: Normale login (MOET SLAGEN)
    print("\n" + "="*60)
    print("SCENARIO 1: Normale bank login")
    print("="*60)

    request1 = AuthenticationRequest(
        rp_id="bank.example.com",
        challenge=os.urandom(32),
        user_verification=UserVerification.PRESENCE,
        required_trust_level=2,
        require_hid_attestation=False,
        require_tibet=False
    )

    result1 = test_scenario(
        "Bank Login - Trust Level 2 (SHOULD PASS)",
        authenticator, validator, request1,
        credential.credential_id,
        expected_pass=True
    )
    results.append(("Normal login allowed", result1))

    # Test 2: Hoge waarde transactie met TIBET (MOET SLAGEN)
    print("\n" + "="*60)
    print("SCENARIO 2: €50.000 overboeking met TIBET token")
    print("="*60)

    # Maak TIBET token voor transactie
    tibet_token, valid_until = authenticator.create_tibet_token(
        credential.credential_id,
        valid_minutes=5
    )
    print(f"TIBET Token: {tibet_token}")
    print(f"Valid until: {valid_until}")

    request2 = AuthenticationRequest(
        rp_id="bank.example.com",
        challenge=os.urandom(32),
        user_verification=UserVerification.PRESENCE,
        required_trust_level=3,
        require_hid_attestation=True,
        require_tibet=True,
        humotica_context={
            "sense": "Grote transactie geïnitieerd",
            "context": "€50.000 naar vastgoed notaris",
            "intent": "Aankoop woning aanbetaling",
            "explain": "Geplande transactie, eerder aangekondigd bij bank"
        }
    )

    result2 = test_scenario(
        "High-value Transfer with TIBET (SHOULD PASS)",
        authenticator, validator, request2,
        credential.credential_id,
        expected_pass=True
    )
    results.append(("High-value with TIBET allowed", result2))

    # Test 3: Credential zonder HID binding probeert high-trust actie
    print("\n" + "="*60)
    print("SCENARIO 3: Credential zonder HID binding")
    print("="*60)

    # Maak credential zonder HID binding
    credential_no_hid = authenticator.create_credential("bank.example.com", b"unknown@example.com")

    request3 = AuthenticationRequest(
        rp_id="bank.example.com",
        challenge=os.urandom(32),
        user_verification=UserVerification.PRESENCE,
        required_trust_level=3,
        require_hid_attestation=True,  # Vereist HID!
        require_tibet=False
    )

    result3 = test_scenario(
        "No HID Binding - Requires HID (SHOULD FAIL)",
        authenticator, validator, request3,
        credential_no_hid.credential_id,
        expected_pass=False
    )
    results.append(("No-HID blocked when required", result3))

    # Test 4: Trust level te laag
    print("\n" + "="*60)
    print("SCENARIO 4: Trust level mismatch")
    print("="*60)

    # Maak credential met laag trust level
    credential_low = authenticator.create_credential("bank.example.com", b"low@example.com")
    authenticator.bind_hid(
        credential_low.credential_id,
        trust_level=1,  # Laag trust level
        humotica={"sense": "Test", "context": "Test", "intent": "Test", "explain": "Test"}
    )

    request4 = AuthenticationRequest(
        rp_id="bank.example.com",
        challenge=os.urandom(32),
        user_verification=UserVerification.PRESENCE,
        required_trust_level=3,  # Vereist hoog trust
        require_hid_attestation=False,
        require_tibet=False
    )

    result4 = test_scenario(
        "Low Trust (1) vs Required (3) (SHOULD FAIL)",
        authenticator, validator, request4,
        credential_low.credential_id,
        expected_pass=False
    )
    results.append(("Low trust blocked", result4))

    # Test 5: Verkeerde RP ID (phishing detectie)
    print("\n" + "="*60)
    print("SCENARIO 5: Phishing site (verkeerde RP ID)")
    print("="*60)

    request5 = AuthenticationRequest(
        rp_id="bank-secure-login.phishing.com",  # NIET bank.example.com!
        challenge=os.urandom(32),
        user_verification=UserVerification.PRESENCE,
        required_trust_level=1,
        require_hid_attestation=False,
        require_tibet=False
    )

    # Dit zou None response moeten geven (authenticator weigert)
    response5 = authenticator.authenticate(request5, credential.credential_id)
    result5 = response5 is None

    print(f"\nRP ID Mismatch: bank.example.com ≠ bank-secure-login.phishing.com")
    print(f"Result: {'✅ BLOCKED (no response)' if result5 else '❌ ALLOWED (BAD!)'}")

    results.append(("Phishing RP blocked", result5))

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
        print("✅ ALLE TESTS GESLAAGD - JIS WEBAUTHN/FIDO2 WERKT!")
    else:
        print("❌ SOMMIGE TESTS GEFAALD")
    print("="*60)

    # Print audit log
    print("\n📋 AUDIT LOG:")
    for entry in validator.audit_log:
        print(f"  [{entry['timestamp'][:19]}] {entry['action']}: {entry['reason'][:40]}...")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
