# 🚀 Getting Started met JTel Identity Standard

**Complete setup guide - van nul tot werkend systeem in 10 minuten**

## 📋 Overzicht

Dit project bevat:
- **JIS Router** - Production-ready server (FastAPI + PostgreSQL + Redis)
- **Admin UI** - Web dashboard voor monitoring
- **Python SDK** - Client library voor apps
- **Protocol Bridges** - WebSocket, MQTT, SIP, WebRTC

## 🎯 Wat Je Gaat Doen

1. ✅ Git repo clonen/pullen
2. ✅ Docker containers starten (router + database + UI)
3. ✅ Admin UI openen en testen
4. ✅ Python SDK installeren
5. ✅ Live demo draaien

**Tijd:** ~10 minuten
**Vereisten:** Docker, Python 3.9+, Git

---

## 📥 Stap 1: Repository Setup

### Eerste keer (nieuwe clone)

```bash
# Clone repo
git clone https://github.com/jaspertvdm/JTel-identity-standard.git
cd JTel-identity-standard

# Checkout de werkende branch
git checkout claude/security-layer-integration-014bYZy9HuEysgqUVDaJhUqM
```

### Updates pullen (bestaande repo)

```bash
# Ga naar repo root
cd /pad/naar/JTel-identity-standard

# Pull laatste updates
git fetch origin
git checkout claude/security-layer-integration-014bYZy9HuEysgqUVDaJhUqM
git pull origin claude/security-layer-integration-014bYZy9HuEysgqUVDaJhUqM
```

**✓ Check:** Je zou nu deze directories moeten zien:
```
JTel-identity-standard/
├── client-sdk/
│   └── python/          ← SDK is hier
├── server-config/
│   └── jis-test/        ← Docker setup is hier
└── ...
```

---

## 🐳 Stap 2: Start de JIS Router

### Navigeer naar server directory

```bash
cd server-config/jis-test
```

### Configureer secrets (eerste keer)

```bash
# Kopieer example config
cp .env.example .env

# Pas aan (optioneel maar aangeraden voor productie)
nano .env
```

**Minimaal aanpassen:**
```bash
JIS_SHARED_SECRET=jouw_sterke_secret_hier
POSTGRES_PASSWORD=jouw_sterke_password_hier
```

### Start de stack

```bash
# Stop oude containers (indien aanwezig)
docker compose down -v

# Start alles
docker compose up -d --build
```

**Wat dit start:**
- `router` - JIS Router (poort 18081)
- `db` - PostgreSQL database
- `redis` - Redis cache
- `ws-bridge` - WebSocket bridge (poort 9000)
- `mqtt` - MQTT broker (poort 31883)
- `mqtt-bridge` - MQTT bridge

### Controleer of alles draait

```bash
# Check container status
docker compose ps

# Alles moet "Up" en "healthy" zijn
# NAME                COMMAND                  SERVICE      STATUS        PORTS
# jis-test-router-1   "python main.py"        router       Up (healthy)  0.0.0.0:18081->8081/tcp
# jis-test-db-1       "docker-entrypoint.s…"   db           Up (healthy)  0.0.0.0:55433->5432/tcp
# jis-test-redis-1    "docker-entrypoint.s…"   redis        Up (healthy)  0.0.0.0:36381->6379/tcp
# ...

# Check logs
docker compose logs -f router

# Je zou moeten zien:
# ✓ Running database migrations...
# ✓ Migration 1 applied successfully
# ✓ Migration 2 applied successfully
# ✓ All migrations completed successfully
# INFO:     Uvicorn running on http://0.0.0.0:8081
```

**✓ Check:** Curl de health endpoint:
```bash
curl http://localhost:18081/health
# Verwacht: {"status":"ok","version":"0.4.0"}
```

---

## 🎨 Stap 3: Open Admin UI

### In je browser

**Lokaal:**
```
http://localhost:18081/
```

**Op server (remote toegang):**
```
http://YOUR_SERVER_IP:18081/
```

**Op Raspberry Pi:**
```
http://YOUR_PI_IP:18081/
```

### Login

Je wordt gevraagd om de **JIS_SHARED_SECRET**:
- Standaard: `example_secret_123`
- Of wat je in `.env` hebt gezet

### Wat je zou moeten zien

**Tab 1: Overview**
- Total Relationships: 0
- Total Events: 0
- Router Status: ✓ Ready

**Tab 2: Relationships**
- Lege tabel (nog geen FIR/A's)

**Tab 3: Health**
- PostgreSQL: ✓ Connected
- Redis: ✓ Connected

**✓ Check:** Alle indicators groen? Dan werkt alles! 🎉

---

## 🐍 Stap 4: Installeer Python SDK

### Navigeer naar SDK directory

```bash
# BELANGRIJK: Ga terug naar repo root eerst!
cd /pad/naar/JTel-identity-standard

# Dan naar SDK
cd client-sdk/python
```

**⚠️ Veelgemaakte fout:**
```bash
# FOUT - als je in server-config/jis-test zit:
cd client-sdk/python  # ✗ Deze directory bestaat hier niet!

# GOED - ga eerst naar repo root:
cd ../..  # Vanuit server-config/jis-test
cd client-sdk/python  # ✓ Nu wel!
```

### Installeer SDK

```bash
# Maak virtual environment (optioneel maar aangeraden)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# of
venv\Scripts\activate  # Windows

# Installeer SDK
pip install -e .
```

**✓ Check:** Test de import:
```bash
python -c "from jis_client import JISClient, DIDKey, HIDKey; print('✓ SDK imported successfully!')"
```

---

## 🧪 Stap 5: Run Live Demo

### Simpele test (5 regels)

```bash
python examples/simple_app.py
```

**Verwachte output:**
```
✓ Relationship created: <uuid>
✓ Intent sent. Events: 2
```

### Volledige demo

```bash
python examples/live_demo.py
```

**Wat dit doet:**
1. Connect naar router
2. Generate DID/HID keys
3. Maak FIR/A relationship
4. Stuur 3 test intents
5. Trigger NIR notification
6. Resolve NIR
7. Haal event history op
8. Toon DID keys
9. Laat metrics zien

**Terwijl dit draait:**
- Open Admin UI in je browser
- Ga naar "Relationships" tab
- Zie je nieuwe FIR/A verschijnen! 🎯
- Klik "View Events" voor de timeline

**✓ Check:** Zie je events in de Admin UI? SUCCESS! 🎉

---

## 📊 Wat Nu Werkt

Je hebt nu een **volledig werkend JIS systeem**:

✅ **Server Infrastructure**
- Production-ready router
- Health checks
- Metrics endpoint
- Admin dashboard

✅ **Security Layer**
- DID/HID key management
- FIR/A relationships
- Continuity chains
- Intent validation

✅ **Developer Tools**
- Python SDK
- Code examples
- Live testing

✅ **Schaalbaarheid**
- Draait op Raspberry Pi
- Draait op server
- Zelfde code = config is schaling

---

## 🎯 Volgende Stappen

### 1. Maak je eigen app

```python
from jis_client import JISClient, DIDKey, HIDKey

# Connect naar je router
client = JISClient("http://localhost:18081", secret="your-secret")

# Generate keys
did = DIDKey.generate()
hid = HIDKey.generate()

# Create relationship
fir_a = client.init_relationship(
    "my-app",
    "server",
    ["client"],
    did_key=did,
    hid_key=hid
)

# Send intents
client.send_intent(fir_a.id, "your_custom_intent", {"data": "test"})
```

### 2. Bekijk de documentatie

- **Server deployment:** `server-config/jis-test/DEPLOYMENT.md`
- **SDK docs:** `client-sdk/python/README.md`
- **Examples:** `client-sdk/python/examples/`

### 3. Configureer whitelists

Edit `.env`:
```bash
# Alleen deze intents toestaan
ALLOWED_INTENTS=unlock_door,verify_identity,send_message

# Alleen deze rollen toestaan
ALLOWED_ROLES=client,server,device
```

Restart router:
```bash
docker compose restart router
```

### 4. Monitor je systeem

**Metrics endpoint:**
```bash
curl http://localhost:18081/metrics
```

**Health check:**
```bash
curl http://localhost:18081/health/ready
```

**Logs:**
```bash
docker compose logs -f router
```

---

## 🆘 Troubleshooting

### Router start niet

```bash
# Check logs
docker compose logs router

# Vaak: DB niet ready
# Oplossing: wacht 10 seconden, health checks handelen dit af
```

### SDK import error

```bash
# Zorg dat je in de juiste directory zit
cd /pad/naar/JTel-identity-standard/client-sdk/python
pip install -e .

# Check Python version
python --version  # Moet >= 3.9 zijn
```

### Admin UI 401 Unauthorized

- Check of je de juiste **JIS_SHARED_SECRET** gebruikt
- Kijk in `.env` of `docker-compose.yml` voor de secret
- Standaard is: `example_secret_123`

### "Cannot connect to router"

```bash
# Check of router draait
docker compose ps

# Check health
curl http://localhost:18081/health

# Check firewall (voor remote access)
sudo ufw status
sudo ufw allow 18081/tcp
```

### Continuity hash mismatch (409 error)

- Normaal als je chain "achterloopt"
- SDK tracked hashes automatisch
- Bij twijfel: haal laatste hash op met `client.get_relationship(fir_a_id)`

---

## 📁 Directory Structuur

```
JTel-identity-standard/
│
├── client-sdk/
│   └── python/                    ← Python SDK
│       ├── jis_client/            ← SDK code
│       ├── examples/              ← Voorbeelden
│       ├── README.md              ← SDK documentatie
│       └── setup.py               ← Installatie
│
├── server-config/
│   └── jis-test/                  ← Server setup
│       ├── router/                ← Router code
│       │   ├── main.py
│       │   ├── migrations/        ← DB migraties
│       │   └── static/            ← Admin UI
│       ├── docker-compose.yml     ← Docker setup
│       ├── .env.example           ← Config template
│       ├── DEPLOYMENT.md          ← Productie guide
│       └── README.md              ← Server docs
│
├── GETTING-STARTED.md             ← Dit bestand!
├── ROADMAP-standardization.md     ← Toekomst plannen
└── JIS2025.md                     ← Spec documentatie
```

---

## 📞 Support

**Problemen of vragen?**

1. Check logs: `docker compose logs -f router`
2. Check health: `curl http://localhost:18081/health/ready`
3. Bekijk voorbeelden: `client-sdk/python/examples/`
4. Lees docs: `server-config/jis-test/DEPLOYMENT.md`

**Veelvoorkomende commando's:**

```bash
# Router logs
docker compose logs -f router

# Herstart alles
docker compose restart

# Stop alles
docker compose down

# Clean restart
docker compose down -v && docker compose up -d --build

# Check status
docker compose ps

# SDK testen
python -c "from jis_client import JISClient; print('OK')"
```

---

## ✅ Success Checklist

- [ ] Docker containers draaien (`docker compose ps`)
- [ ] Health check OK (`curl http://localhost:18081/health`)
- [ ] Admin UI toegankelijk (browser)
- [ ] SDK geïnstalleerd (`pip list | grep jis-client`)
- [ ] Simple app werkt (`python examples/simple_app.py`)
- [ ] Live demo werkt (`python examples/live_demo.py`)
- [ ] FIR/A zichtbaar in Admin UI

**Alles gelukt? 🎉 Je hebt nu een werkend JIS systeem!**

---

**Versie:** 0.4.0
**Laatste update:** 2025-01-26
**Status:** Production Ready

Voor geavanceerde configuratie, zie `server-config/jis-test/DEPLOYMENT.md`
