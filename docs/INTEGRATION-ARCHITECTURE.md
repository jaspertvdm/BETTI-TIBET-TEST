# 🏗️ TIBET-BETTI Integration Architecture

**Hoe jouw bestaande app database integreert met TIBET-BETTI**

## 📊 De Complete Architectuur

```
┌─────────────────────────────────────────────────────────────────┐
│                        JOUW APP                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              APP DATABASE (blijft apart!)                 │  │
│  │  • User data                                             │  │
│  │  • Application state                                     │  │
│  │  • Business logic data                                   │  │
│  │  • Preferences, settings, etc.                           │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                          │
│                       │ reads/writes                             │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              KIT API (jouw bestaande API!)               │  │
│  │                                                           │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │  CONTEXT LAYER (POST /context/update)            │   │  │
│  │  │  • Reads from APP DB                             │   │  │
│  │  │  • Aggregates context                            │   │  │
│  │  │  • Provides current state                        │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  │                                                           │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │  SENSE LAYER (POST /sense/rules, /sense/evaluate)│   │  │
│  │  │  • Pattern matching rules                        │   │  │
│  │  │  • Condition evaluation                          │   │  │
│  │  │  • Auto-trigger logic                            │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  │                                                           │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │  INTENT LAYER (internal mapping)                 │   │  │
│  │  │  • Intent definitions                            │   │  │
│  │  │  • Action executors                              │   │  │
│  │  │  • Business logic triggers                       │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  └─────────────────────┬────────────────────────────────────┘  │
└────────────────────────┼───────────────────────────────────────┘
                         │
                         │ via TIBET-BETTI SDK
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              BETTI ROUTER (aparte service!)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            BETTI DATABASE (apart!)                       │  │
│  │  • Trust tokens (FIR/A relationships)                    │  │
│  │  • Intent routing history                                │  │
│  │  • Continuity hashes                                     │  │
│  │  • Conversation depth tracking                           │  │
│  │  • Audit trails (humotica)                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 Sleutelconcept: TWEE DATABASES

### 1️⃣ APP DATABASE (jouw bestaande DB)
**Blijft volledig apart voor ontwikkeling!**

```sql
-- Jouw bestaande tabellen
users
  - id
  - name
  - preferences
  - location
  - ...

devices
  - id
  - user_id
  - type
  - status
  - ...

settings
  - user_id
  - key
  - value
  - ...

-- etc. (al jouw business logic!)
```

### 2️⃣ BETTI DATABASE (nieuwe, aparte DB)
**Alleen voor trust & routing!**

```sql
-- BETTI-specifieke tabellen (in BETTI router)
fira_relationships
  - id (FIR/A token)
  - initiator
  - responder
  - trust_level
  - continuity_hash
  - created_at

intent_history
  - id
  - fira_id
  - intent
  - context
  - timestamp
  - conversation_depth

audit_log
  - id
  - fira_id
  - event_type
  - humotica
  - timestamp
```

## 🔌 Hoe ze Samenwerken

### Stap-voor-Stap Flow

```python
# 1. JOUW APP leest uit APP DATABASE
user = db.query("SELECT * FROM users WHERE id = ?", user_id)
device = db.query("SELECT * FROM devices WHERE user_id = ?", user_id)

# 2. KIT API Context Layer aggregeert
context = {
    "location": user.location,
    "time_of_day": calculate_time_of_day(),
    "devices_home": count_devices_home(user_id),
    "ambient_light": device.light_sensor
}

# 3. KIT API Sense Layer evalueert regels
# (rules kunnen in APP DB of in-memory)
triggered_intents = sense_engine.evaluate(context)
# → Returns: ["turn_on_lights", "set_heating"]

# 4. TIBET-BETTI SDK stuurt naar BETTI ROUTER
for intent in triggered_intents:
    betti_client.send_tibet(
        relationship_id=trust_token,  # From BETTI DB
        intent=intent,
        context=context  # From APP DB!
    )

# 5. BETTI ROUTER (aparte DB!) roept intent audit
# → Opgeslagen in BETTI DATABASE
# → Trust token validated
# → Continuity hash updated
# → Routing to target device

# 6. Target device ontvangt via WebSocket
# → Executes intent
# → Updates eigen APP DATABASE
```

## 📂 Database Strategie

### Voor Ontwikkeling

```yaml
# docker-compose.yml (development)

services:
  # Jouw app database (blijft apart!)
  app-db:
    image: postgres:15
    ports:
      - "5432:5432"
    volumes:
      - app-data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: my_app_db
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: app_pass

  # BETTI router database (apart!)
  betti-db:
    image: postgres:15
    ports:
      - "5433:5432"  # Andere port!
    volumes:
      - betti-data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: betti_router_db
      POSTGRES_USER: betti_user
      POSTGRES_PASSWORD: betti_pass

  # Jouw KIT API
  kit-api:
    build: ./kit-api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://app_user:app_pass@app-db:5432/my_app_db
    depends_on:
      - app-db

  # BETTI Router
  betti-router:
    build: ./tbet-router
    ports:
      - "18081:18081"
    environment:
      DATABASE_URL: postgresql://betti_user:betti_pass@betti-db:5432/betti_router_db
    depends_on:
      - betti-db

volumes:
  app-data:
  betti-data:
```

## 🔧 KIT API Implementatie

### Context Layer (leest uit APP DB)

```python
# kit-api/context.py

from your_app_db import db_session, User, Device

@app.post("/context/update")
async def update_context(user_id: str, context: dict):
    """
    Updates context - reads from APP DB
    """
    # Read from YOUR app database
    user = db_session.query(User).filter_by(id=user_id).first()
    devices = db_session.query(Device).filter_by(user_id=user_id).all()

    # Aggregate context (from YOUR data!)
    aggregated = {
        "location": user.location,
        "preferences": user.preferences,
        "devices": [d.to_dict() for d in devices],
        **context  # Additional context from request
    }

    # Store in memory or cache (NOT in BETTI DB!)
    context_store[user_id] = aggregated

    return {"status": "updated", "context": aggregated}


@app.get("/context/{user_id}")
async def get_context(user_id: str):
    """
    Get current context - from cache + APP DB
    """
    # Get from cache
    cached = context_store.get(user_id, {})

    # Refresh from APP DB if needed
    user = db_session.query(User).filter_by(id=user_id).first()

    return {
        **cached,
        "location": user.location,  # Fresh from APP DB
        "updated_at": datetime.utcnow().isoformat()
    }
```

### Sense Layer (rules kunnen in APP DB of config)

```python
# kit-api/sense.py

# Optie 1: Sense rules in APP DB
class SenseRule(Base):
    __tablename__ = 'sense_rules'
    __bind_key__ = 'app_db'  # YOUR APP DB!

    id = Column(Integer, primary_key=True)
    name = Column(String)
    conditions = Column(JSON)
    intent = Column(String)
    priority = Column(Integer)


# Optie 2: Sense rules in config/code
SENSE_RULES = [
    {
        "name": "evening_lights",
        "conditions": {
            "time_of_day": "evening",
            "location": "home",
            "ambient_light": {"lt": 100}
        },
        "intent": "turn_on_lights",
        "priority": 7
    },
    # ... more rules
]


@app.post("/sense/evaluate")
async def evaluate_sense(user_id: str, context: dict = None):
    """
    Evaluate sense rules - uses APP DB context
    """
    # Get context (from APP DB!)
    if not context:
        context = get_context(user_id)

    # Evaluate rules
    triggered = []

    # Load rules from APP DB or config
    rules = db_session.query(SenseRule).order_by(SenseRule.priority.desc()).all()

    for rule in rules:
        if matches_conditions(context, rule.conditions):
            triggered.append(rule.intent)

    return {
        "user_id": user_id,
        "triggered_intents": triggered,
        "context": context
    }
```

### Intent Layer (execution in YOUR app)

```python
# kit-api/intents.py

@app.post("/intents/execute")
async def execute_intent(intent: str, context: dict, fira_id: str):
    """
    Execute intent - modifies APP DB based on intent
    """
    # This is where YOUR business logic runs
    # And YOUR APP DB gets updated!

    if intent == "turn_on_lights":
        # Update YOUR app database
        device = db_session.query(Device).filter_by(
            user_id=context['user_id'],
            type='lights'
        ).first()

        device.status = 'on'
        device.brightness = context.get('brightness', 100)
        db_session.commit()

        # Log to YOUR app audit
        log_action(
            user_id=context['user_id'],
            action='lights_on',
            source='tibet_betti',
            fira_id=fira_id
        )

    elif intent == "schedule_meeting":
        # Create meeting in YOUR app database
        meeting = Meeting(
            user_id=context['user_id'],
            attendees=context['attendees'],
            time=context['time'],
            created_by='betti_intent'
        )
        db_session.add(meeting)
        db_session.commit()

    # ... more intents

    return {"status": "executed", "intent": intent}
```

## 🚀 Complete Integration Voorbeeld

```python
# your_app/betti_integration.py

from tibet_betti_client import TibetBettiClient
from your_app import db, User, Device
import requests

class AppBettiIntegration:
    def __init__(self):
        # BETTI client (connects to separate BETTI router)
        self.betti = TibetBettiClient(
            betti_url="http://localhost:18081",  # BETTI service
            kit_url="http://localhost:8000",      # YOUR KIT API
            secret="example_secret_123"
        )

        # Your app DB connection
        self.db = db

    def establish_user_trust(self, user_id: str, device_id: str):
        """
        Create trust token (stored in BETTI DB, not yours!)
        """
        # Get user info from YOUR app DB
        user = self.db.query(User).filter_by(id=user_id).first()
        device = self.db.query(Device).filter_by(id=device_id).first()

        # Establish trust in BETTI (goes to BETTI DB!)
        relationship = self.betti.establish_trust(
            initiator=f"user_{user.id}",
            responder=f"device_{device.id}",
            context={
                "user_name": user.name,
                "device_type": device.type,
                "established_from": "app"
            }
        )

        # OPTIONAL: Store FIR/A reference in YOUR app DB
        # (for quick lookup, actual token is in BETTI DB)
        self.db.execute(
            "INSERT INTO user_device_tokens (user_id, device_id, fira_id) VALUES (?, ?, ?)",
            (user_id, device_id, relationship.id)
        )
        self.db.commit()

        return relationship

    def handle_context_change(self, user_id: str, context_update: dict):
        """
        Complete flow: APP DB → Context → Sense → TIBET
        """
        # 1. Get trust token (from YOUR app DB cache)
        fira_id = self.db.execute(
            "SELECT fira_id FROM user_device_tokens WHERE user_id = ? LIMIT 1",
            (user_id,)
        ).fetchone()[0]

        # 2. Update context + evaluate sense + send TIBETs
        # (context from YOUR app DB, routing via BETTI DB!)
        results = self.betti.context_to_tibet(
            relationship_id=fira_id,
            user_id=user_id,
            context_update=context_update
        )

        # 3. Log in YOUR app DB
        for result in results:
            self.db.execute(
                "INSERT INTO betti_intent_log (user_id, fira_id, intent, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (user_id, fira_id, result.get('intent'), datetime.utcnow())
            )
        self.db.commit()

        return results


# Usage in your app
integration = AppBettiIntegration()

# When user arrives home (detected by YOUR app)
@app.on_event("user_location_changed")
def on_location_change(user_id, new_location):
    if new_location == "home":
        # This updates YOUR app DB + triggers BETTI intents
        integration.handle_context_change(
            user_id=user_id,
            context_update={"location": "home", "time": "evening"}
        )
```

## ✅ Samenvatting: Database Scheiding

### APP DATABASE (jouw DB)
✅ Blijft volledig apart
✅ Voor ontwikkeling volledig onder jouw controle
✅ Bevat:
- User data
- Application state
- Business logic
- Settings & preferences
- **Optioneel:** Sense rules (als je wilt)
- **Optioneel:** FIR/A ID cache (voor snelheid)

### BETTI DATABASE (aparte DB)
✅ Volledig onafhankelijk
✅ Beheerd door BETTI router
✅ Bevat:
- Trust tokens (FIR/A)
- Intent routing history
- Continuity hashes
- Conversation depth
- Audit trails

### KIT API (jouw API)
✅ Brug tussen beide!
✅ **Context Layer:** Leest uit APP DB
✅ **Sense Layer:** Evalueert regels (uit APP DB of config)
✅ **Intent Layer:** Schrijft naar APP DB

## 🎉 Voordelen van deze Architectuur

1. **Ontwikkeling onafhankelijk** - APP DB blijft apart
2. **Schaalbaar** - Beide databases kunnen apart schalen
3. **Security** - Trust tokens gescheiden van app data
4. **Flexibel** - Sense rules in APP DB of config
5. **Clean separation** - Duidelijke verantwoordelijkheden

Je app blijft volledig zelfstandig werken, BETTI voegt alleen trust & routing toe! 🚀
