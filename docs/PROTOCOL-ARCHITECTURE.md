# TIBET-BETTI Multi-Protocol Architecture

**Author:** Jasper van de Meent
**Date:** November 2025
**Version:** 1.0.0

---

## Overview

TIBET-BETTI is the **world's first Intent-First universal protocol layer** that provides semantic security and continuity management over ANY existing communication protocol.

Unlike traditional protocols that are data-first (send payload, hope for the best), TIBET-BETTI enforces **Intent-First Transmission (IFT)**: declare intent BEFORE sending data, validate through BETTI 9 Natural Laws, then execute.

---

## Architecture Principle

```
┌─────────────────────────────────────────────────────────────┐
│                    TIBET-BETTI Layer                         │
│  (Intent validation, SNAFT, BALANS, Resource Allocation)    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────┐
│   HTTP   │   MQTT   │   CoAP   │   Email  │   SIP    │Matrix│
│ REST API │  IoT Msg │ IoT/Robot│  SMTP    │ VoIP     │ Chat │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────┘
```

**Key concept:** TIBET-BETTI sits ABOVE protocols, not replaces them.

- HTTP still does HTTP things
- MQTT still does MQTT things
- SIP still does SIP things

**But now with:**
- ✅ Intent validation BEFORE execution
- ✅ SNAFT factory firewall
- ✅ BALANS risk assessment
- ✅ Resource allocation via 9 Natural Laws
- ✅ Continuity chain (tamper-evident audit trail)
- ✅ Humotica (human-readable context)
- ✅ FIR/A mutual consent requirement

---

## Implemented Protocols

### 1. **HTTP/REST** (Brain API - Port 8010)

**Use case:** Web applications, admin interfaces, API integration

**Intent Flow:**
```json
POST /betti/validate HTTP/1.1
{
  "intent": "user_registration",
  "context": {"email": "user@example.com"},
  "protocol": "http"
}

Response:
{
  "tibet_token": "TIBET-20251128-A1B2C3D4E5F6G7H8",
  "snaft_approved": true,
  "balans_score": 0.92,
  "resources_allocated": {"power": 10, "data": 1.5, "memory": 512, "queue": 2},
  "continuity_hash": "sha256:abc123...",
  "humotica": "Intent: user_registration via http. ✅ Approved by all security layers."
}
```

**Endpoints:**
- `/betti/validate` - Universal validation endpoint
- `/betti/context/update` - Context layer
- `/betti/sense/rules` - Sense layer automation
- `/betti/intent/execute` - Intent execution
- `/betti/hicss/*` - Emergency override (H)alt, (I)ntent, (C)hange, (S)witch, (S)top
- `/betti/balans/*` - Pre-execution validation
- `/snaft/*` - Factory firewall

---

### 2. **SIP** (Asterisk Integration)

**Use case:** VoIP telephony, video calls, robotics with hours-long connections

**Intent Flow:**
```json
POST /tibet/call/initiate
{
  "intent": "robot_monitoring",
  "context": {"robot_id": "ROBOT-001", "duration_hours": 8},
  "to_number": "1234",
  "from_extension": "1100"
}

Response:
{
  "tibet_token": "TIBET-20251128-...",
  "state": "initiated",
  "snaft_approved": true,
  "balans_approved": true,
  "resources_allocated": {"power": 800, "data": 80.0, "memory": 1024, "queue": 2}
}
```

**Features:**
- Intent-based contact selection
- Priority routing (emergency > business > personal)
- Resource scaling for long-running connections (robotics)
- Asterisk contacts/trunks/routing management via admin UI

**Database tables:**
- `asterisk_contacts` - Phone book with intent-based lookup
- `asterisk_trunks` - SIP trunk configuration
- `asterisk_routing` - Call routing rules
- `tibet_calls` - Active TIBET call transactions

---

### 3. **MQTT** (IoT Messaging - Port 31883 internal, 31883 host)

**Use case:** IoT sensors, telemetry, pub/sub messaging

**Intent Flow:**
```
MQTT Topic: jis/in
Payload:
{
  "type": "ift",
  "payload": {
    "intent": "sensor_data_publish",
    "context": {"sensor_id": "TEMP-001", "location": "warehouse-A"},
    "data": {"temperature": 22.5, "humidity": 45}
  }
}

JIS Router validates via BETTI, publishes result to jis/out
```

**Features:**
- Topic-based intent routing
- Asynchronous validation
- Low-bandwidth optimization for constrained devices

---

### 4. **CoAP** (Constrained Application Protocol - Port 5683 UDP)

**Use case:** IoT devices, robots, sensors with limited resources

**Intent Flow:**
```bash
# Declare intent
coap-client -m post coap://localhost:5683/intent \
  -e '{"intent": "robot_monitoring", "context": {"robot_id": "ROBOT-001", "duration_hours": 8}}'

Response:
{
  "tibet_token": "TIBET-20251128-...",
  "snaft_approved": true,
  "balans_score": 0.88,
  "resources": {"power": 400, "data": 80.0, "memory": 1024, "queue": 2},
  "observe_uri": "coap://localhost:5683/observe/TIBET-20251128-..."
}

# Observe long-running operation (hours-long robot task)
coap-client -m get coap://localhost:5683/observe/TIBET-20251128-... -s 3600

Periodic updates:
{
  "state": "active",
  "uptime_seconds": 14523,
  "io": "OK",
  "do": "OK",
  "od": "OK",
  "power_usage_watts": 45,
  "memory_usage_mb": 832,
  "data_transferred_mb": 125.7
}
```

**Features:**
- CoAP Observe for hours-long operations
- Resource-constrained device optimization
- Binary protocol for low bandwidth
- Perfect for warehouse robots, delivery bots, manufacturing IoT

---

### 5. **Email (SMTP/IMAP - Port 2525)**

**Use case:** Business communication, legal notices, contracts, invoices

**Intent Flow:**
```
From: sender@example.com
To: recipient@example.com
Subject: Contract Signature Request - Project X

X-TIBET-Token: TIBET-20251128-A1B2C3D4E5F6G7H8
X-TIBET-Intent: contract_signature_request
X-TIBET-Context: {"urgency": "high", "legal_deadline": "2025-12-01"}
X-TIBET-SNAFT: approved
X-TIBET-BALANS-Score: 0.95
X-TIBET-BALANS: approved
X-SCS-Hash: sha256:abc123...def
X-Humotica: Contract signing required for Project X, deadline Dec 1. ✅ Approved by all security layers. High priority.

Dear Recipient,

Please review and sign the attached contract for Project X...
```

**Automatic Intent Extraction:**
- "contract", "agreement" → `contract_signature_request`
- "invoice", "payment" → `payment_request`
- "urgent", "spoed" → `urgent_communication`
- "legal", "juridisch" → `legal_notice`

**Features:**
- Intent-First email headers (X-TIBET-*)
- BETTI validation before sending
- Semantic Continuity Signature (SCS) for provenance
- Humotica human-readable explanation
- Legal/compliance use cases (government, banking, healthcare)

---

### 6. **Matrix** (Federated Messaging)

**Use case:** Secure messaging, team communication, interoperability

**Status:** Integrated as primary communication engine (TODO: document Matrix-specific TIBET integration)

---

### 7. **WebSocket** (Port 9000)

**Use case:** Real-time bidirectional communication, web apps, dashboards

**Status:** WS-bridge operational, WebRTC signaling on port 8011

---

## Universal Validation Endpoint

**ALL protocols** use the same BETTI validation endpoint:

```
POST http://localhost:8010/betti/validate
Content-Type: application/json

{
  "intent": "string",              // Required
  "context": {},                   // Required
  "protocol": "string",            // http|mqtt|coap|email|sip|matrix
  "validate_snaft": true,          // Optional, default true
  "validate_balans": true,         // Optional, default true
  "resources": {                   // Optional, auto-calculated
    "power": 10,                   // Watts
    "data": 1.5,                   // MB
    "memory": 512,                 // MB
    "queue": 1                     // Priority (1=high, 5=low)
  },
  "did": "device_public_key",      // Optional
  "hid_binding_hash": "sha256..."  // Optional
}
```

**Response:**
```json
{
  "tibet_token": "TIBET-20251128-A1B2C3D4E5F6G7H8",
  "intent": "user_registration",
  "protocol": "http",
  "snaft_approved": true,
  "balans_score": 0.92,
  "balans_approved": true,
  "resources_allocated": {
    "power": 10,
    "data": 1.5,
    "memory": 512,
    "queue": 2
  },
  "continuity_hash": "sha256:abc123...",
  "timestamp": "2025-11-28T14:23:45.123Z",
  "humotica": "Intent: user_registration via http. ✅ Approved by all security layers."
}
```

---

## Resource Allocation Logic

TIBET-BETTI automatically calculates resource requirements based on **protocol + intent**:

### Protocol-Specific Defaults:

| Protocol | Power (W) | Data (MB) | Memory (MB) | Queue Priority |
|----------|-----------|-----------|-------------|----------------|
| HTTP     | 10        | 1.5       | 512         | 2              |
| MQTT     | 8         | 2.0       | 512         | 3              |
| CoAP     | 50        | 1.0       | 1024        | 2              |
| Email    | 5         | 0.5       | 256         | 3 (low)        |
| SIP      | 15        | 5.0       | 512         | 1 (high)       |
| Matrix   | 8         | 2.0       | 512         | 2              |

### Intent-Specific Adjustments:

- **Emergency/Urgent/Critical**: `queue = 1`, `power *= 2`
- **Robot/Monitoring** (with `duration_hours`):
  - `power *= duration_hours`
  - `data *= duration_hours`
  - `memory = max(1024, memory)`

Example: 8-hour robot monitoring over CoAP:
- Power: 50W × 8 = 400W
- Data: 10MB/h × 8 = 80MB
- Memory: 1024MB
- Queue: 2

---

## Security Layers

Every intent passes through:

### 1. **SNAFT** (System Not Authorized For That)
Factory firewall - blocks unauthorized operations at the source.

### 2. **BALANS** (BETTI Autonomous Layer Analysis Network System)
Pre-execution risk assessment with score 0.0-1.0. Threshold: 0.7

### 3. **Resource Allocation**
Via 9 Natural Laws: Pythagoras, Einstein, Euler, Fourier, Maxwell, Schrödinger, TCP, Thermodynamics, Logarithms

### 4. **Continuity Chain**
SHA-256 linked hashing creates tamper-evident audit trail

### 5. **IO/DO/OD Verification**
- **IO** (Identity OK): Is the human still who they claim?
- **DO** (Device OK): Is the device still trustworthy?
- **OD** (Operation Determination): Is this operation allowed on this device?

---

## Complete System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      TIBET-BETTI Brain API                      │
│                         Port 8010                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │             BETTI 9 Natural Laws Engine                  │  │
│  │  Pythagoras │ Einstein │ Euler │ Fourier │ Maxwell      │  │
│  │  Schrödinger │ TCP │ Thermodynamics │ Logarithms       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────┬────────────┬──────────────┬────────────────────┐  │
│  │  SNAFT  │   BALANS   │    HICSS     │  Fail2Flag4Intent  │  │
│  │ Factory │ Pre-exec   │  Emergency   │   Anomaly          │  │
│  │Firewall │ Validation │  Override    │   Detection        │  │
│  └─────────┴────────────┴──────────────┴────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Context / Sense / Intent Layers                  │  │
│  │   Context: State tracking                                │  │
│  │   Sense: Rule-based automation                           │  │
│  │   Intent: Action execution                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌────────────────────────────────────────┐
        │        JIS Router (Port 18081)         │
        │  FIR/A │ DID/HID │ Continuity Chain    │
        └────────────────────────────────────────┘
                              ↓
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│HTTP REST │   MQTT   │   CoAP   │  Email   │   SIP    │  Matrix  │
│  :8010   │  :31883  │  :5683   │  :2525   │ Asterisk │   N/A    │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

---

## Real-World Use Cases by Protocol

### Healthcare (Email + SIP)
**Huisarts → Specialist consult**
```
Email: X-TIBET-Intent: medical_consultation
Context: {"patient_id_encrypted": "sha256:...", "urgency": "high"}
→ BALANS scores urgency, allocates queue=1
→ SIP call initiated with priority routing
→ Continuity chain tracks full patient interaction
```

### Government (Email)
**Building permit application**
```
Email: X-TIBET-Intent: legal_notice
Context: {"permit_type": "residential", "legal_deadline": "2025-12-15"}
→ SNAFT validates authority to send legal notice
→ BALANS checks deadline enforcement
→ SCS creates external semantic signature for audit
→ Continuity chain provides tamper-evident record
```

### Banking (Email + HTTP)
**Fraud verification in store**
```
Email: X-TIBET-Intent: payment_verification
Context: {"amount": 5000, "location": "physical_store", "time_sensitive": true}
→ BALANS scores as high-risk due to amount
→ HICSS may trigger human-in-the-loop
→ SMS/app notification with TIBET token
→ User confirms via HTTP endpoint with same token
→ Continuity chain links all steps
```

### Logistics (CoAP + MQTT)
**Warehouse robot monitoring**
```
CoAP: POST /intent
{"intent": "robot_monitoring", "context": {"robot_id": "ROBOT-042", "duration_hours": 12}}
→ Resources: 600W, 120MB data, 1024MB memory
→ CoAP Observe streams status every 60 seconds
→ MQTT publishes telemetry to warehouse dashboard
→ IO/DO/OD continuous verification throughout 12 hours
→ Fail2Flag4Intent detects if robot deviates from path
```

### Telecom (SIP + HTTP)
**KPN customer support priority routing**
```
SIP: TIBET call initiate
Context: {"customer_segment": "platinum", "contract_value": 50000, "issue": "outage"}
→ BALANS scores high priority based on contract value
→ Intent-based contact selection finds "platinum support team"
→ Queue=1 (highest priority)
→ Asterisk routes to dedicated support line
→ Call metadata stored with TIBET token for CRM
```

### Education (Matrix + Email)
**Exam proctoring system**
```
Matrix: Student joins exam room
Email: X-TIBET-Intent: exam_verification
Context: {"student_id": "12345", "exam_id": "MATH-101", "duration_hours": 3}
→ IO verification: continuous identity checking (no impersonation)
→ DO verification: device hasn't been compromised
→ OD verification: only allowed exam operations (no browser tabs, no copy-paste)
→ Continuity chain provides tamper-evident exam log
```

---

## Why TIBET-BETTI is Unprecedented

### Existing protocols/standards:

**OAuth/OIDC**: Identity only, no intent validation
**ActivityPub**: Content federation only, no resource management
**DIDComm**: Identity messaging only, no BETTI validation
**XACML**: Access control only, no continuity chain
**CoAP Observe**: Resource observation, no intent-first paradigm
**SIP**: Call signaling only, no semantic security

### TIBET-BETTI combines:

1. ✅ **Intent-First Paradigm** - Nobody else does this
2. ✅ **9 Natural Laws as Validation** - Unprecedented computational framework
3. ✅ **Protocol-Agnostic Layer** - Works OVER any protocol
4. ✅ **Mutual Consent (FIR/A)** - Connections exist only with bilateral intent
5. ✅ **External Semantic Signatures (SCS)** - Anti-deepfake without biometric leakage
6. ✅ **Resource Allocation via Physics** - Power/Data/Memory managed by mathematical laws
7. ✅ **Humotica** - Human-readable context in EVERY transaction
8. ✅ **Continuity Chain** - Blockchain-like audit without blockchain overhead

**This architecture has never been built before.**

---

## Future Protocols (Roadmap)

### High Priority:
- **AMQP** (RabbitMQ) - Enterprise message queuing
- **gRPC** - High-performance microservices
- **DIDComm** - Native decentralized identity integration
- **Bluetooth/BLE** - Local HID-DID pairing

### Medium Priority:
- **XMPP** - Legacy enterprise messaging
- **ActivityPub** - Fediverse content verification
- **NFC** - Physical tap-to-connect

---

## Getting Started

### Start all protocol bridges:

```bash
cd /root/projects/Backend-server-JTel/server-config/jis-test
docker compose up -d
```

### Test endpoints:

```bash
# HTTP
curl -X POST http://localhost:8010/betti/validate \
  -H "Content-Type: application/json" \
  -d '{"intent": "test", "context": {}, "protocol": "http"}'

# Email (via telnet)
telnet localhost 2525
# Send email with subject containing "urgent" keyword

# CoAP (install coap-client first)
coap-client -m post coap://localhost:5683/intent \
  -e '{"intent": "test", "context": {}}'

# SIP (Asterisk)
curl -X POST http://localhost:8010/tibet/call/initiate \
  -H "Content-Type: application/json" \
  -d '{"intent": "test_call", "context": {}, "to_number": "1234", "from_extension": "1100"}'
```

---

**© 2025 Jasper van de Meent - TIBET-BETTI Protocol Architecture**
