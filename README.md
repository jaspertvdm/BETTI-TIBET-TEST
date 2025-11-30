# BETTI-TIBET Protocol Test Suite

**JIS Security Layer 4.0 - De meest protocol-agnostische security layer ter wereld**

> Van Tamagotchi interne taken tot NASA pakketverdeling - JIS werkt overal waar betekenis nodig is.

## Wat is dit?

Test suite die bewijst dat JIS (JTel Identity Standard) werkt als **semantische security layer** over ELKE communicatieprotocol.

> "Malware CANNOT provide valid Humotica context because harmful actions lack credible explanations."

## De 14 BETTI Natuurwetten

| # | Wet | Computing Toepassing |
|---|-----|---------------------|
| 1 | **Pythagoras** | Orthogonale resource combinatie (power/data/memory) |
| 2 | **Einstein E=mc²** | Energie voor data beweging |
| 3 | **Euler Continuïteit** | Data flow integriteit validatie |
| 4 | **Fourier Transform** | Complexe intent → primitieve operaties |
| 5 | **Maxwell Vergelijkingen** | Intent propagatie + snelheidslimieten |
| 6 | **Schrödinger Golffunctie** | Task superpositie tot observatie |
| 7 | **TCP Congestion** | Queue overload preventie |
| 8 | **Thermodynamica 2e** | Tamper-evident audit logs |
| 9 | **Logaritmische Queue** | Fair scheduling, geen starvation |
| 10 | **Energiebehoud** | User effort = output + overhead |
| 11 | **Kepler's 3e** | Fysieke task duration minima |
| 12 | **Relativistische Optelling** | Non-lineaire urgency combinatie |
| 13 | **Rolling Token Chain** | HMAC-linked audit trails |
| 14 | **Newton's 1e** | State change vereist net force (Intent × Context) |

## Protocol Dekking

### Getest & Productie-Ready (22+)
✅ HTTP/REST, MQTT, CoAP, SIP, Email (SMTP/IMAP), Matrix, WebSocket, WebRTC
✅ 7 trust levels volledig getest (0-5)
✅ Hardware: Raspberry Pi 5, Asterisk, Ollama, Android JTm app

### Nieuwe Protocollen - Te Testen (`tests/new-protocols/`)
- [ ] **CAN bus** - Automotive intent validatie (KRITISCH voor voertuigveiligheid)
- [ ] **WebAuthn/FIDO2** - Native HID binding met hardware keys
- [ ] **ActivityPub** - Fediverse semantic trust (Mastodon etc)
- [ ] **Nostr** - Decentralized social met Humotica
- [ ] **Bluetooth LE (GATT)** - Wearable/beacon HID attestatie
- [ ] **NFC/NDEF** - Tap-to-confirm TIBET consent
- [ ] **Zigbee/Z-Wave** - Smart home mesh context
- [ ] **LoRaWAN** - Long-range IoT met extended TIBET validity
- [ ] **USB HID** - BadUSB attack preventie
- [ ] **Modbus/OPC-UA** - Industriële SCADA/ICS protectie
- [ ] **XMPP** - Legacy chat integratie
- [ ] **DNS-over-HTTPS** - Intent-based DNS filtering
- [ ] **WireGuard** - Per-tunnel TIBET tokens
- [ ] **gRPC** - Microservice intent validatie
- [ ] **GraphQL** - Query intent analyse

## Repo Structuur

```
BETTI-TIBET-TEST/
├── tests/
│   ├── existing/           # Bestaande geteste protocollen
│   │   ├── tbet_live_test.py      # 7 trust level scenarios
│   │   ├── tbet_betti_demo.py     # Offline demo
│   │   ├── phone_receiver_mock.py # Mobile receiver sim
│   │   ├── live_demo.py           # End-to-end flow
│   │   └── ...
│   └── new-protocols/      # Nieuwe protocollen (nog te testen)
│       ├── test_canbus.py
│       ├── test_webauthn.py
│       ├── test_activitypub.py
│       └── ...
├── docs/                   # Architectuur & specs
└── examples/               # Quick start voorbeelden
```

## Quick Start

```bash
# Activeer BETTI venv
source /home/jasper/BETTI/venv/bin/activate

# Run bestaande tests
python tests/existing/tbet_live_test.py

# Run nieuwe protocol test
python tests/new-protocols/test_canbus.py
```

## Architectuur

```
┌─────────────────────────────────────────────────────────────┐
│                      ANY PROTOCOL                            │
│  HTTP │ MQTT │ CAN │ BLE │ NFC │ Nostr │ WebAuthn │ ...    │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    JIS SEMANTIC LAYER                        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │  FIR/A  │  │  TIBET  │  │  SNAFT  │  │ BALANS  │        │
│  │ (Trust) │  │ (Time)  │  │ (Block) │  │ (Risk)  │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               HUMOTICA CONTEXT                        │   │
│  │       Sense → Context → Intent → Explain             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            14 BETTI NATURAL LAWS                      │   │
│  │     Physics-based resource allocation & validation    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Waarom JIS Uniek Is

| Framework | Protocol Scope | Valideert Betekenis? |
|-----------|---------------|---------------------|
| NIST CSF 2.0 | Policy only | ❌ Nee |
| ISO 27001 | Certificering | ❌ Nee |
| Zero Trust | Network | ❌ Nee |
| SASE | Cloud | ❌ Nee |
| **JIS** | **37+ protocollen** | **✅ JA - Semantisch** |

**Geen enkele andere security layer valideert BETEKENIS over protocollen.**

## Auteur

**Jasper van de Meent** - Autodidact, creator van BETTI/Humotica/JIS

- https://humotica.com
- https://betti.humotica.com
- https://jis.humotica.com
- https://zenodo.org/records/17759713 (Security Layer 4.0 Paper)

## Licentie

MIT - Vrij te gebruiken, citeer appropriaat.
