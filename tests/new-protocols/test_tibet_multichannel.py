#!/usr/bin/env python3
"""
TIBET Multi-Channel Session Test
================================

Test scenario: TIBET sessie op SIP opent automatisch beveiligd
secundair kanaal (Matrix/WebRTC/Document signing) voor tijdens het gesprek.

USE CASES:
1. Bank belt klant → automatisch secure doc sharing voor handtekening
2. Notaris belt → automatisch e-signing portal geopend
3. Arts belt patiënt → automatisch secure bestandsdeling voor lab resultaten
4. Support call → automatisch screen share channel
5. Juridisch gesprek → automatisch versleuteld chat kanaal voor notities

Dit is BAANBREKEND:
- Traditioneel: je belt, dan zeg je "check je email"
- JIS: TIBET sessie opent automatisch alle benodigde kanalen
- Alles onder dezelfde trust token, zelfde tijdvenster, zelfde audit trail

NOTE: Dit is een SIMULATIE van de flow.
"""

import sys
import json
import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

class ChannelType(Enum):
    """Beschikbare secondary channel types"""
    SIP_VOICE = "sip_voice"           # Primair voice kanaal
    MATRIX_CHAT = "matrix_chat"        # Encrypted chat room
    WEBRTC_VIDEO = "webrtc_video"      # Video conferencing
    DOC_SIGNING = "doc_signing"        # Document ondertekening
    FILE_SHARE = "file_share"          # Secure file sharing
    SCREEN_SHARE = "screen_share"      # Screen sharing
    WHITEBOARD = "whiteboard"          # Collaborative whiteboard

class SessionState(Enum):
    """TIBET session states"""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    REJECTED = "rejected"

@dataclass
class TIBETChannel:
    """Een kanaal binnen een TIBET sessie"""
    channel_type: ChannelType
    channel_id: str
    endpoint: str
    created_at: datetime
    encryption_key: bytes  # Per-channel encryption key
    state: str = "pending"

    # Channel-specific config
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TIBETSession:
    """
    Multi-channel TIBET sessie

    Een TIBET token kan meerdere kanalen omvatten, allemaal
    onder dezelfde trust relatie en tijdvenster.
    """
    session_id: str
    token: str
    valid_until: datetime

    # Partijen
    initiator: str      # bijv. "bank_ing"
    responder: str      # bijv. "jasper_client"

    # Trust info
    trust_level: int
    humotica: Dict[str, str]

    # Kanalen
    primary_channel: TIBETChannel
    secondary_channels: List[TIBETChannel] = field(default_factory=list)

    # State
    state: SessionState = SessionState.PROPOSED
    created_at: datetime = field(default_factory=datetime.now)

    # Audit trail
    audit_log: List[Dict] = field(default_factory=list)

    def add_channel(self, channel_type: ChannelType, config: Dict = None) -> TIBETChannel:
        """Voeg secondary channel toe aan sessie"""
        channel_id = hashlib.sha256(
            f"{self.session_id}:{channel_type.value}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Derive per-channel encryption key van session token
        channel_key = hashlib.sha256(
            f"{self.token}:{channel_id}".encode()
        ).digest()

        channel = TIBETChannel(
            channel_type=channel_type,
            channel_id=channel_id,
            endpoint=self._generate_endpoint(channel_type, channel_id),
            created_at=datetime.now(),
            encryption_key=channel_key,
            config=config or {}
        )

        self.secondary_channels.append(channel)

        self._log("CHANNEL_ADDED", {
            "type": channel_type.value,
            "id": channel_id
        })

        return channel

    def _generate_endpoint(self, channel_type: ChannelType, channel_id: str) -> str:
        """Genereer endpoint URL voor channel"""
        base = "https://jis.example.com"

        endpoints = {
            ChannelType.MATRIX_CHAT: f"matrix://#tibet-{channel_id}:jis.example.com",
            ChannelType.WEBRTC_VIDEO: f"{base}/webrtc/room/{channel_id}",
            ChannelType.DOC_SIGNING: f"{base}/docs/sign/{channel_id}",
            ChannelType.FILE_SHARE: f"{base}/files/share/{channel_id}",
            ChannelType.SCREEN_SHARE: f"{base}/screen/{channel_id}",
            ChannelType.WHITEBOARD: f"{base}/board/{channel_id}"
        }

        return endpoints.get(channel_type, f"{base}/channel/{channel_id}")

    def _log(self, action: str, details: Dict):
        """Audit log entry"""
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        })

@dataclass
class Document:
    """Document voor ondertekening tijdens TIBET sessie"""
    doc_id: str
    title: str
    content_hash: str
    signers: List[str]
    signatures: Dict[str, bytes] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

class TIBETSessionManager:
    """
    Manager voor TIBET multi-channel sessies

    Handelt het opzetten, valideren en afsluiten van
    multi-channel TIBET sessies af.
    """

    def __init__(self):
        self.sessions: Dict[str, TIBETSession] = {}
        self.documents: Dict[str, Document] = {}

    def create_session(self, initiator: str, responder: str,
                       trust_level: int, humotica: Dict[str, str],
                       primary_type: ChannelType = ChannelType.SIP_VOICE,
                       valid_minutes: int = 30) -> TIBETSession:
        """
        Maak nieuwe TIBET sessie met primary channel
        """
        session_id = hashlib.sha256(
            f"{initiator}:{responder}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:24]

        valid_until = datetime.now() + timedelta(minutes=valid_minutes)

        token = hashlib.sha256(
            f"{session_id}:{valid_until.isoformat()}:{os.urandom(16).hex()}".encode()
        ).hexdigest()[:32]

        # Primary channel
        primary_channel = TIBETChannel(
            channel_type=primary_type,
            channel_id=f"primary-{session_id[:8]}",
            endpoint=f"sip:{responder}@jis.example.com",
            created_at=datetime.now(),
            encryption_key=hashlib.sha256(f"{token}:primary".encode()).digest()
        )

        session = TIBETSession(
            session_id=session_id,
            token=token,
            valid_until=valid_until,
            initiator=initiator,
            responder=responder,
            trust_level=trust_level,
            humotica=humotica,
            primary_channel=primary_channel
        )

        session._log("SESSION_CREATED", {
            "initiator": initiator,
            "responder": responder,
            "trust_level": trust_level,
            "valid_until": valid_until.isoformat()
        })

        self.sessions[session_id] = session
        return session

    def accept_session(self, session_id: str, responder_token: str) -> bool:
        """Responder accepteert de sessie"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        # Valideer tijdvenster
        if datetime.now() > session.valid_until:
            session.state = SessionState.REJECTED
            session._log("SESSION_EXPIRED", {})
            return False

        session.state = SessionState.ACCEPTED
        session.primary_channel.state = "active"
        session._log("SESSION_ACCEPTED", {"responder_token": responder_token[:8]})

        return True

    def open_doc_signing(self, session_id: str, doc_title: str,
                        doc_content: str, signers: List[str]) -> Optional[tuple]:
        """
        Open document signing channel binnen TIBET sessie

        Returns: (channel, document) tuple
        """
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        if session.state != SessionState.ACCEPTED:
            return None

        # Valideer tijdvenster
        if datetime.now() > session.valid_until:
            return None

        # Maak document
        doc_id = hashlib.sha256(
            f"{session_id}:{doc_title}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        content_hash = hashlib.sha256(doc_content.encode()).hexdigest()

        document = Document(
            doc_id=doc_id,
            title=doc_title,
            content_hash=content_hash,
            signers=signers
        )

        self.documents[doc_id] = document

        # Voeg signing channel toe
        channel = session.add_channel(
            ChannelType.DOC_SIGNING,
            config={
                "doc_id": doc_id,
                "title": doc_title,
                "content_hash": content_hash,
                "signers": signers
            }
        )

        session._log("DOC_CHANNEL_OPENED", {
            "doc_id": doc_id,
            "title": doc_title,
            "signers": signers
        })

        return channel, document

    def sign_document(self, session_id: str, doc_id: str,
                     signer: str, signature_data: bytes) -> bool:
        """
        Onderteken document binnen TIBET sessie

        De handtekening is gebonden aan:
        - De sessie (token)
        - Het document (content hash)
        - De tijd (binnen TIBET window)
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        if datetime.now() > session.valid_until:
            session._log("SIGN_FAILED", {"reason": "Session expired"})
            return False

        if doc_id not in self.documents:
            return False

        doc = self.documents[doc_id]

        if signer not in doc.signers:
            session._log("SIGN_FAILED", {"reason": "Not authorized signer"})
            return False

        # Maak gebonden signature
        # Signature = hash(doc_content_hash + session_token + signer + timestamp)
        bound_signature = hashlib.sha256(
            doc.content_hash.encode() +
            session.token.encode() +
            signer.encode() +
            datetime.now().isoformat().encode() +
            signature_data
        ).digest()

        doc.signatures[signer] = bound_signature

        session._log("DOCUMENT_SIGNED", {
            "doc_id": doc_id,
            "signer": signer,
            "signature_hash": bound_signature.hex()[:16]
        })

        return True

    def is_document_complete(self, doc_id: str) -> bool:
        """Check of alle handtekeningen binnen zijn"""
        if doc_id not in self.documents:
            return False

        doc = self.documents[doc_id]
        return all(signer in doc.signatures for signer in doc.signers)


def test_scenario(name: str, description: str, test_func) -> bool:
    """Run een test scenario"""
    print(f"\n{'='*70}")
    print(f"SCENARIO: {name}")
    print(f"{'='*70}")
    print(f"Beschrijving: {description}")
    print()

    try:
        result = test_func()
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"\nResultaat: {status}")
        return result
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║     TIBET MULTI-CHANNEL SESSION TEST                                  ║
║                                                                        ║
║  Test: SIP gesprek opent automatisch secundaire kanalen               ║
║  Use case: Document ondertekening tijdens telefoongesprek             ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    manager = TIBETSessionManager()
    results = []

    # Test 1: Bank belt klant voor hypotheek handtekening
    def test_bank_doc_signing():
        print("Scenario: ING bank belt klant voor hypotheek ondertekening")
        print()

        # Bank initieert TIBET sessie
        session = manager.create_session(
            initiator="ing_bank_hypotheken",
            responder="jasper_client",
            trust_level=3,
            humotica={
                "sense": "Hypotheek aanvraag goedgekeurd, wacht op handtekening",
                "context": "Klant heeft hypotheek aangevraagd voor woning Utrecht",
                "intent": "Mondeling bespreken condities en digitaal ondertekenen",
                "explain": "Klant verwacht dit gesprek, afspraak gemaakt via app"
            },
            valid_minutes=60
        )

        print(f"✓ TIBET Sessie aangemaakt: {session.session_id[:16]}...")
        print(f"  Token: {session.token[:16]}...")
        print(f"  Geldig tot: {session.valid_until}")
        print(f"  Primary channel: {session.primary_channel.channel_type.value}")

        # Klant accepteert (na TIBET consent flow)
        client_token = hashlib.sha256(b"jasper_accepts").hexdigest()[:32]
        accepted = manager.accept_session(session.session_id, client_token)

        if not accepted:
            print("✗ Sessie niet geaccepteerd")
            return False

        print(f"✓ Klant accepteert TIBET sessie")
        print(f"  State: {session.state.value}")

        # Nu gesprek loopt, bank opent document signing
        channel, document = manager.open_doc_signing(
            session.session_id,
            doc_title="Hypotheekakte Utrecht 2025-001",
            doc_content="""
            HYPOTHEEKAKTE

            Ondergetekenden:
            1. ING Bank N.V. (geldverstrekker)
            2. Jasper van de Meent (geldnemer)

            Komen overeen:
            - Hypotheekbedrag: €350.000
            - Looptijd: 30 jaar
            - Rente: 3.5% vast 10 jaar

            [Volledige juridische tekst hier...]
            """,
            signers=["ing_bank_hypotheken", "jasper_client"]
        )

        print(f"\n✓ Document signing channel geopend")
        print(f"  Document ID: {document.doc_id}")
        print(f"  Titel: {document.title}")
        print(f"  Content hash: {document.content_hash[:32]}...")
        print(f"  Endpoint: {channel.endpoint}")

        # Bank tekent eerst
        bank_signed = manager.sign_document(
            session.session_id,
            document.doc_id,
            "ing_bank_hypotheken",
            b"BANK_DIGITAL_SIGNATURE_DATA"
        )

        print(f"\n✓ Bank heeft getekend: {bank_signed}")

        # Klant tekent (via hun app/portal)
        client_signed = manager.sign_document(
            session.session_id,
            document.doc_id,
            "jasper_client",
            b"CLIENT_DIGITAL_SIGNATURE_DATA"
        )

        print(f"✓ Klant heeft getekend: {client_signed}")

        # Check of document compleet is
        complete = manager.is_document_complete(document.doc_id)
        print(f"\n✓ Document volledig ondertekend: {complete}")

        # Print audit trail
        print(f"\n📋 AUDIT TRAIL ({len(session.audit_log)} entries):")
        for entry in session.audit_log:
            print(f"  [{entry['timestamp'][:19]}] {entry['action']}")

        return accepted and bank_signed and client_signed and complete

    result1 = test_scenario(
        "Bank Hypotheek Ondertekening",
        "ING belt klant, opent automatisch doc signing portal",
        test_bank_doc_signing
    )
    results.append(("Bank doc signing flow", result1))

    # Test 2: Arts belt met lab resultaten (file share)
    def test_doctor_file_share():
        print("Scenario: Arts belt patiënt met lab resultaten")
        print()

        session = manager.create_session(
            initiator="dr_jansen_huisarts",
            responder="patient_jasper",
            trust_level=4,  # Medisch = hoog trust
            humotica={
                "sense": "Lab resultaten bloedonderzoek binnen",
                "context": "Routinecontrole diabetes, glucose en HbA1c",
                "intent": "Resultaten bespreken en PDF delen",
                "explain": "Periodieke controle, afspraak 3 maanden geleden gemaakt"
            },
            valid_minutes=30
        )

        print(f"✓ Medische TIBET sessie: {session.session_id[:16]}...")

        # Patient accepteert
        manager.accept_session(session.session_id, "patient_accepts")
        print("✓ Patiënt accepteert")

        # Arts opent file share channel voor PDF
        file_channel = session.add_channel(
            ChannelType.FILE_SHARE,
            config={
                "file_name": "lab_resultaten_2025_01.pdf",
                "file_size": 245000,
                "mime_type": "application/pdf",
                "encrypted": True,
                "expires_with_session": True  # File verdwijnt na sessie
            }
        )

        print(f"\n✓ File share channel geopend")
        print(f"  Endpoint: {file_channel.endpoint}")
        print(f"  Bestand: {file_channel.config['file_name']}")
        print(f"  Versleuteld: {file_channel.config['encrypted']}")
        print(f"  Verloopt met sessie: {file_channel.config['expires_with_session']}")

        # Arts kan ook chat toevoegen voor notities
        chat_channel = session.add_channel(
            ChannelType.MATRIX_CHAT,
            config={
                "room_name": "Consult Dr. Jansen - Jasper",
                "encrypted": True,
                "history_visible": "members_only"
            }
        )

        print(f"\n✓ Encrypted chat channel toegevoegd")
        print(f"  Endpoint: {chat_channel.endpoint}")

        print(f"\n📊 Sessie overzicht:")
        print(f"  Primary: {session.primary_channel.channel_type.value}")
        print(f"  Secondary channels: {len(session.secondary_channels)}")
        for ch in session.secondary_channels:
            print(f"    - {ch.channel_type.value}: {ch.channel_id}")

        return len(session.secondary_channels) == 2

    result2 = test_scenario(
        "Arts Lab Resultaten",
        "Arts belt, deelt automatisch versleutelde PDF + chat",
        test_doctor_file_share
    )
    results.append(("Doctor file share flow", result2))

    # Test 3: Expired session mag geen channels openen
    def test_expired_session():
        print("Scenario: Verlopen TIBET sessie mag geen channels openen")
        print()

        session = manager.create_session(
            initiator="test_initiator",
            responder="test_responder",
            trust_level=2,
            humotica={
                "sense": "Test",
                "context": "Test",
                "intent": "Test expired session",
                "explain": "Test"
            },
            valid_minutes=0  # Verloopt meteen!
        )

        print(f"✓ Sessie aangemaakt met 0 minuten validity")
        print(f"  Valid until: {session.valid_until}")
        print(f"  Current time: {datetime.now()}")

        # Probeer te accepteren na timeout (wacht even)
        import time
        time.sleep(0.1)

        accepted = manager.accept_session(session.session_id, "late_accept")
        print(f"\n✓ Accept poging na expiry: {accepted} (verwacht: False)")

        return not accepted

    result3 = test_scenario(
        "Expired Session Blocked",
        "Verlopen TIBET sessie wordt correct geweigerd",
        test_expired_session
    )
    results.append(("Expired session blocked", result3))

    # Test 4: Notaris met e-signing + video
    def test_notaris_full_session():
        print("Scenario: Notaris - volledige multi-channel sessie")
        print()

        session = manager.create_session(
            initiator="notaris_van_der_berg",
            responder="koper_jasper",
            trust_level=4,
            humotica={
                "sense": "Koopakte woning klaar voor ondertekening",
                "context": "Woning aankoop Maliebaan 123 Utrecht",
                "intent": "Akte doorlopen, vragen beantwoorden, ondertekenen",
                "explain": "Passeerafspraak, verkoper al getekend"
            },
            valid_minutes=120  # 2 uur voor volledige sessie
        )

        manager.accept_session(session.session_id, "koper_accepts")

        # Notaris opent alle benodigde channels
        channels_opened = []

        # 1. Video call voor face-to-face
        video = session.add_channel(ChannelType.WEBRTC_VIDEO, {
            "quality": "HD",
            "recording": True,  # Verplicht voor notariële akte
            "recording_consent": ["notaris_van_der_berg", "koper_jasper"]
        })
        channels_opened.append(video)
        print(f"✓ Video channel: {video.channel_id}")

        # 2. Document sharing voor koopakte
        doc_channel, doc = manager.open_doc_signing(
            session.session_id,
            "Koopakte Maliebaan 123 Utrecht",
            "[Volledige koopakte tekst...]",
            ["notaris_van_der_berg", "koper_jasper", "verkoper_pietersen"]
        )
        channels_opened.append(doc_channel)
        print(f"✓ Doc signing: {doc_channel.channel_id}")

        # 3. Screen share voor doorlopen akte
        screen = session.add_channel(ChannelType.SCREEN_SHARE, {
            "presenter": "notaris_van_der_berg",
            "viewers": ["koper_jasper"]
        })
        channels_opened.append(screen)
        print(f"✓ Screen share: {screen.channel_id}")

        # 4. Chat voor notities/vragen
        chat = session.add_channel(ChannelType.MATRIX_CHAT, {
            "purpose": "Vragen en notities tijdens passeren"
        })
        channels_opened.append(chat)
        print(f"✓ Chat channel: {chat.channel_id}")

        print(f"\n📊 Complete notaris sessie:")
        print(f"  Primary (voice): {session.primary_channel.channel_type.value}")
        print(f"  Secondary channels: {len(session.secondary_channels)}")

        # Alle channels onder 1 TIBET token!
        print(f"\n🔐 Security:")
        print(f"  Single TIBET token: {session.token[:16]}...")
        print(f"  Alle kanalen versleuteld met sessie-afgeleide keys")
        print(f"  Alle activiteit in unified audit trail")

        return len(channels_opened) == 4

    result4 = test_scenario(
        "Notaris Full Multi-Channel",
        "Notaris opent video + doc signing + screen share + chat",
        test_notaris_full_session
    )
    results.append(("Notaris multi-channel", result4))

    # Samenvatting
    print("\n")
    print("="*70)
    print("TEST RESULTATEN SAMENVATTING")
    print("="*70)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "="*70)
    if all_passed:
        print("✅ ALLE TESTS GESLAAGD - TIBET MULTI-CHANNEL WERKT!")
    else:
        print("❌ SOMMIGE TESTS GEFAALD")
    print("="*70)

    print("""
💡 KEY INSIGHTS:

1. TIBET sessie = umbrella voor meerdere kanalen
   - 1 token, 1 tijdvenster, 1 audit trail
   - Channels erven trust level van sessie

2. Document ondertekening is GEBONDEN aan sessie
   - Signature bevat session token
   - Niet geldig buiten TIBET window
   - Continuity chain bewijst wanneer getekend

3. Kanalen kunnen dynamisch toegevoegd worden
   - Start met voice, voeg video toe als nodig
   - File share opent pas wanneer relevant
   - Alles onder dezelfde security context

4. Na sessie einde verdwijnen tijdelijke kanalen
   - Files kunnen "expires_with_session" hebben
   - Geen losse eindjes
   - Privacy by design
    """)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
