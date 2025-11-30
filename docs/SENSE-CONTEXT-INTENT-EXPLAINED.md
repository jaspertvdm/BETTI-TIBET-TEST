# 🧠 Sense, Context & Intent - Complete Uitleg

**Hoe de drie layers samenwerken in TIBET-BETTI**

---

## 🎯 De Drie Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    JOUW APP                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 CONTEXT LAYER        "WAT IS DE SITUATIE?"             │
│  ↓                                                          │
│  🧠 SENSE LAYER          "WAT MOET ER GEBEUREN?"           │
│  ↓                                                          │
│  ⚡ INTENT LAYER         "DOE HET!"                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 CONTEXT LAYER - "Wat is de situatie?"

### Wat is Context?

**Context** = alle relevante informatie over de huidige staat van een user/device/systeem

Het is een verzameling van:
- Waar is de user? (locatie)
- Hoe laat is het? (tijd)
- Wat is de status? (device states)
- Wat zijn voorkeuren? (user preferences)
- Wat is de geschiedenis? (recent activities)

### Voorbeeld Context:

```json
{
  "user_id": "user_123",
  "user_name": "Jasper",
  "location": "home",
  "time_of_day": "evening",
  "day_type": "weekday",
  "ambient_light": 50,
  "temperature": 21,
  "devices_active": ["phone", "laptop", "smart_lights"],
  "recent_activity": "working",
  "energy_level": 60,
  "preferences": {
    "lighting_preference": "warm",
    "temperature_preference": 22
  }
}
```

### Waar Komt Context Vandaan?

Context wordt **geaggregeerd** uit meerdere bronnen in **JOUW APP DB**:

```python
def get_user_context(user_id):
    # Lees uit verschillende tabellen
    user = db.query(User).filter_by(id=user_id).first()
    devices = db.query(Device).filter_by(user_id=user_id).all()
    settings = db.query(Settings).filter_by(user_id=user_id).all()
    recent = db.query(Activity).filter_by(user_id=user_id)\
               .order_by(Activity.timestamp.desc()).limit(10).all()

    # Aggregeer tot één context object
    context = {
        "user_id": user.id,
        "user_name": user.name,
        "location": user.location,
        "time_of_day": calculate_time_of_day(),
        "devices_active": [d.name for d in devices if d.status == 'active'],
        "recent_activity": recent[0].type if recent else None,
        # ... meer context
    }

    return context
```

### Context Update Flow:

```
1. Event gebeurt (user komt thuis)
        ↓
2. App detecteert event
        ↓
3. POST /context/update
   {
     "user_id": "user_123",
     "context": {"location": "home"}
   }
        ↓
4. KIT API aggregeert VOLLEDIGE context
   - Leest user uit database
   - Leest devices uit database
   - Leest settings uit database
   - Combineert alles
        ↓
5. Volledig context object klaar!
   {
     "location": "home",
     "time_of_day": "evening",
     "devices_active": [...],
     ...
   }
```

---

## 🧠 SENSE LAYER - "Wat moet er gebeuren?"

### Wat is Sense?

**Sense** = pattern matching engine die automatisch intents triggered op basis van context

Het zijn **regels** die zeggen:
**"ALS context matches deze conditions, DAN trigger deze intent"**

### Anatomie van een Sense Rule:

```python
{
  "name": "Evening Lights",           # Naam van de rule
  "conditions": {                      # WAT moet waar zijn?
    "location": "home",                # User is thuis
    "time_of_day": "evening",          # Het is avond
    "ambient_light": {"lt": 100}       # Licht < 100 lux
  },
  "intent": "turn_on_lights",          # DAN: Deze intent triggeren
  "priority": 7                        # Hogere priority = eerst checken
}
```

### Sense Rule Types:

#### 1. **Exact Match**
```python
conditions: {
  "location": "home"      # location MOET exact "home" zijn
}
```

#### 2. **Comparisons**
```python
conditions: {
  "ambient_light": {"lt": 100},    # < 100
  "temperature": {"gt": 25},        # > 25
  "battery": {"lte": 20},           # <= 20
  "energy": {"gte": 80}             # >= 80
}
```

#### 3. **Multiple Conditions (AND)**
```python
conditions: {
  "location": "home",              # EN
  "time_of_day": "evening",        # EN
  "ambient_light": {"lt": 100}     # EN
}
# Alle conditions moeten waar zijn!
```

#### 4. **List (OR)**
```python
conditions: {
  "location": ["home", "office"]   # home OF office
}
```

### Complete Sense Rule Voorbeelden:

```python
# Rule 1: Avond verlichting
{
  "name": "Evening Lights",
  "conditions": {
    "location": "home",
    "time_of_day": "evening",
    "ambient_light": {"lt": 100}
  },
  "intent": "turn_on_lights",
  "priority": 7
}

# Rule 2: Ochtend routine
{
  "name": "Morning Routine",
  "conditions": {
    "location": "home",
    "time_of_day": "morning",
    "day_type": "weekday"
  },
  "intent": "morning_briefing",
  "priority": 8
}

# Rule 3: Batterij waarschuwing
{
  "name": "Low Battery Alert",
  "conditions": {
    "battery_level": {"lt": 20},
    "location": ["home", "office"]
  },
  "intent": "charge_reminder",
  "priority": 9
}

# Rule 4: Werk focus mode
{
  "name": "Work Focus",
  "conditions": {
    "location": "office",
    "time_of_day": ["morning", "afternoon"],
    "calendar_busy": True
  },
  "intent": "enable_focus_mode",
  "priority": 6
}
```

### Sense Evaluation Flow:

```
1. Context wordt ge-update
   {"location": "home", "time_of_day": "evening", "ambient_light": 50}
        ↓
2. POST /sense/evaluate
        ↓
3. KIT API haalt alle sense rules op
   - Global rules (user_id = NULL)
   - User-specific rules (user_id = "user_123")
        ↓
4. Rules gesorteerd op priority (hoogste eerst)
   [Rule 8 (prio 8), Rule 7 (prio 7), Rule 6 (prio 6), ...]
        ↓
5. Elke rule checken tegen context

   Rule: "Evening Lights"
   Conditions: {location: "home", time_of_day: "evening", ambient_light: {lt: 100}}
   Context:    {location: "home", time_of_day: "evening", ambient_light: 50}

   ✓ location matches (home == home)
   ✓ time_of_day matches (evening == evening)
   ✓ ambient_light matches (50 < 100)

   → TRIGGERED! Intent: "turn_on_lights"
        ↓
6. Return lijst van triggered intents
   ["turn_on_lights", "set_temperature", ...]
```

### Sense Matching Logic:

```python
def matches_conditions(context, conditions):
    """Check if context matches all conditions"""

    for key, expected in conditions.items():
        actual = context.get(key)

        # 1. Key niet in context → NO MATCH
        if actual is None:
            return False

        # 2. Exact match
        if isinstance(expected, str):
            if actual != expected:
                return False

        # 3. Comparison operators
        if isinstance(expected, dict):
            if "lt" in expected and actual >= expected["lt"]:
                return False
            if "gt" in expected and actual <= expected["gt"]:
                return False
            # ... andere operators

        # 4. List (any match)
        if isinstance(expected, list):
            if actual not in expected:
                return False

    # Alle conditions matched!
    return True
```

---

## ⚡ INTENT LAYER - "Doe het!"

### Wat is Intent?

**Intent** = een actie die uitgevoerd moet worden

Het is de **uitvoering** van wat Sense heeft besloten.

### Intent Eigenschappen:

```python
{
  "intent": "turn_on_lights",      # WAT te doen
  "context": {                      # HÓÉE te doen
    "room": "living_room",
    "brightness": 80,
    "color": "warm_white"
  },
  "fira_id": "abc-123",            # WIE stuurt (trust token)
  "user_id": "user_123"            # VOOR WIE
}
```

### Intent Execution:

```python
@app.post("/intents/execute")
async def execute_intent(intent_data):
    intent = intent_data["intent"]
    context = intent_data["context"]
    user_id = intent_data["user_id"]

    # Route naar juiste handler
    if intent == "turn_on_lights":
        # 1. Parse context
        room = context.get("room", "living_room")
        brightness = context.get("brightness", 100)

        # 2. Update JOUW APP DATABASE
        device = db.query(Device).filter_by(
            user_id=user_id,
            type='lights',
            room=room
        ).first()

        device.status = 'on'
        device.brightness = brightness
        db.commit()

        # 3. Return result
        return {
            "status": "completed",
            "message": f"Lights in {room} turned on"
        }
```

### Intent Types (voorbeelden):

#### 1. **Device Control Intents**
```python
"turn_on_lights"
"set_temperature"
"lock_door"
"close_blinds"
```

#### 2. **Information Intents**
```python
"morning_briefing"
"weather_update"
"traffic_report"
"calendar_summary"
```

#### 3. **Action Intents**
```python
"maak_koffie"
"schedule_meeting"
"send_notification"
"create_reminder"
```

#### 4. **State Change Intents**
```python
"enable_focus_mode"
"activate_away_mode"
"start_sleep_mode"
"enable_energy_saving"
```

---

## 🔄 COMPLETE FLOW: Context → Sense → Intent

### Scenario: User komt thuis op avond

```
┌─────────────────────────────────────────────────────────────┐
│ 1. EVENT: User komt thuis om 19:00                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CONTEXT LAYER: Aggregeer context                        │
│                                                             │
│    POST /context/update                                     │
│    {                                                        │
│      "user_id": "user_123",                                │
│      "context": {"location": "home"}                       │
│    }                                                        │
│                                                             │
│    → KIT API leest uit APP DB:                             │
│      - User: location = "home"                             │
│      - Time: calculate → "evening"                         │
│      - Devices: lights, heating, etc.                      │
│      - Sensors: ambient_light = 45                         │
│                                                             │
│    → Volledig context:                                     │
│    {                                                        │
│      "location": "home",                                   │
│      "time_of_day": "evening",                            │
│      "ambient_light": 45,                                  │
│      "temperature": 19,                                    │
│      "devices_active": ["phone"]                           │
│    }                                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. SENSE LAYER: Evaluate rules                             │
│                                                             │
│    POST /sense/evaluate                                     │
│                                                             │
│    → Check Rule 1: "Evening Lights"                        │
│      Conditions: location=home, time=evening, light<100    │
│      Context:    location=home, time=evening, light=45     │
│      ✓ MATCH! → Trigger: "turn_on_lights"                 │
│                                                             │
│    → Check Rule 2: "Evening Heating"                       │
│      Conditions: location=home, time=evening, temp<20      │
│      Context:    location=home, time=evening, temp=19      │
│      ✓ MATCH! → Trigger: "set_temperature"                │
│                                                             │
│    → Check Rule 3: "Morning Routine"                       │
│      Conditions: location=home, time=morning               │
│      Context:    location=home, time=evening               │
│      ✗ NO MATCH (time doesn't match)                       │
│                                                             │
│    → Triggered intents:                                    │
│      ["turn_on_lights", "set_temperature"]                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. BETTI SDK: Send TIBETs                                  │
│                                                             │
│    Voor elke triggered intent:                             │
│                                                             │
│    client.send_tibet(                                       │
│      relationship_id=trust_token,                           │
│      intent="turn_on_lights",                              │
│      context={                                             │
│        "room": "living_room",                              │
│        "brightness": 80                                    │
│      }                                                      │
│    )                                                        │
│                                                             │
│    client.send_tibet(                                       │
│      relationship_id=trust_token,                           │
│      intent="set_temperature",                             │
│      context={                                             │
│        "target": 22,                                       │
│        "mode": "heating"                                   │
│      }                                                      │
│    )                                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. BETTI ROUTER: Routes TIBETs                             │
│                                                             │
│    - Validates trust tokens                                │
│    - Checks conversation depth                             │
│    - Routes to target device/service                       │
│    - Logs to audit trail                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. INTENT LAYER: Execute                                   │
│                                                             │
│    POST /intents/execute                                    │
│    {"intent": "turn_on_lights", ...}                       │
│                                                             │
│    → execute_lights():                                     │
│      - Query device from APP DB                            │
│      - Update device.status = 'on'                         │
│      - Update device.brightness = 80                       │
│      - Commit to APP DB                                    │
│                                                             │
│    POST /intents/execute                                    │
│    {"intent": "set_temperature", ...}                      │
│                                                             │
│    → execute_temperature():                                │
│      - Query thermostat from APP DB                        │
│      - Update thermostat.target = 22                       │
│      - Update thermostat.mode = 'heating'                  │
│      - Commit to APP DB                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. RESULT: Lights on, heating started! 🏠                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 💡 Praktische Voorbeelden

### Voorbeeld 1: Ochtend Routine

**Context:**
```json
{
  "location": "home",
  "time_of_day": "morning",
  "day_type": "weekday",
  "calendar_next_meeting": "09:00"
}
```

**Sense Rules:**
```python
Rule: "Morning Briefing"
  Conditions: {location: "home", time_of_day: "morning", day_type: "weekday"}
  Intent: "morning_briefing"
  ✓ TRIGGERED

Rule: "Morning Coffee"
  Conditions: {location: "home", time_of_day: "morning"}
  Intent: "maak_koffie"
  ✓ TRIGGERED
```

**Intents Executed:**
1. `morning_briefing` → Shows weather, meetings, tasks
2. `maak_koffie` → Starts coffee machine

---

### Voorbeeld 2: Batterij Waarschuwing

**Context:**
```json
{
  "device_type": "phone",
  "battery_level": 15,
  "location": "office",
  "charging": false
}
```

**Sense Rule:**
```python
Rule: "Low Battery Alert"
  Conditions: {
    battery_level: {lt: 20},
    charging: false,
    location: ["office", "home"]
  }
  Intent: "charge_reminder"
  ✓ TRIGGERED
```

**Intent Executed:**
```python
execute_charge_reminder():
  - Send notification to user
  - Log to database
  - Return reminder message
```

---

### Voorbeeld 3: Focus Mode

**Context:**
```json
{
  "location": "office",
  "time_of_day": "afternoon",
  "calendar_busy": true,
  "noise_level": 75
}
```

**Sense Rules:**
```python
Rule: "Work Focus"
  Conditions: {location: "office", calendar_busy: true}
  Intent: "enable_focus_mode"
  ✓ TRIGGERED

Rule: "Noise Control"
  Conditions: {location: "office", noise_level: {gt: 70}}
  Intent: "enable_noise_cancelling"
  ✓ TRIGGERED
```

**Intents Executed:**
1. `enable_focus_mode` → Silence notifications, block distractions
2. `enable_noise_cancelling` → Activate noise cancelling

---

## 🎯 Design Patterns

### Pattern 1: Cascade Rules (Priority)

```python
# High priority: Emergency
Rule 1 (priority 10): {battery: {lt: 5}} → "emergency_shutdown"

# Medium priority: Warning
Rule 2 (priority 7): {battery: {lt: 20}} → "low_battery_warning"

# Low priority: Info
Rule 3 (priority 5): {battery: {lt: 50}} → "battery_info"

# Als battery = 4%, alleen Rule 1 triggered (hoogste priority eerst)
```

### Pattern 2: Composite Context

```python
# Context uit meerdere bronnen
context = {
  **user_location_context,      # GPS, geofencing
  **device_sensor_context,       # Battery, light, temp
  **calendar_context,            # Meetings, events
  **activity_context,            # Recent activities
  **preference_context           # User preferences
}
```

### Pattern 3: Dynamic Sense Rules

```python
# User-specific rules
Rule (user_id="user_123"): {location: "gym"} → "start_workout_tracking"

# Global rules
Rule (user_id=NULL): {location: "office"} → "enable_work_mode"

# Priority: User-specific > Global
```

---

## ✅ Samenvatting

| Layer | Vraag | Input | Output | Database |
|-------|-------|-------|--------|----------|
| **CONTEXT** | Wat is de situatie? | Events, sensors, DB | Aggregated context object | Leest uit APP DB |
| **SENSE** | Wat moet gebeuren? | Context + Rules | List of triggered intents | Leest rules uit APP DB |
| **INTENT** | Doe het! | Intent + Context | Executed action | Schrijft naar APP DB |

**Flow:** Event → Context → Sense → Intent → Action ✅

---

## 📚 Zie Ook

- **kit-api-template/main.py** - Complete KIT API implementatie
- **INTEGRATION-ARCHITECTURE.md** - Architectuur overzicht
- **DATABASE-SCHEMAS.md** - Database design

**Context observeert. Sense beslist. Intent executeert! 🚀**
