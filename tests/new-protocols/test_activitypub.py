#!/usr/bin/env python3
"""
ActivityPub/Nostr JIS Protocol Test
===================================

Test JIS semantic security voor federated social media.

Dit lost een ENORM probleem op:
- Mastodon/Fediverse heeft geen spam/bot bescherming
- Nostr heeft keys maar geen intent validatie
- JIS voegt "waarom post je dit?" toe

Use case: Alleen berichten met valid Humotica context worden geaccepteerd.
          Bots kunnen geen legitieme context genereren.

NOTE: Dit is een SIMULATIE - geen echte ActivityPub server vereist.
"""

import sys
import json
import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

class ActivityType(Enum):
    """ActivityPub activity types"""
    CREATE = "Create"
    ANNOUNCE = "Announce"  # Boost/repost
    LIKE = "Like"
    FOLLOW = "Follow"
    DELETE = "Delete"
    UPDATE = "Update"

class ObjectType(Enum):
    """ActivityPub object types"""
    NOTE = "Note"          # Regular post
    ARTICLE = "Article"    # Long-form
    IMAGE = "Image"
    VIDEO = "Video"
    QUESTION = "Question"  # Poll

class JISTrustLevel(Enum):
    """Trust levels voor social media"""
    UNVERIFIED = 0      # Nieuw account, geen verificatie
    VERIFIED_EMAIL = 1  # Email geverifieerd
    VERIFIED_PHONE = 2  # Telefoon geverifieerd
    VERIFIED_ID = 3     # ID document geverifieerd
    VERIFIED_ORG = 4    # Organisatie geverifieerd (bijv. bedrijf, overheid)
    VERIFIED_PRESS = 5  # Pers/journalist met perskaart

@dataclass
class Actor:
    """ActivityPub Actor (gebruiker/account)"""
    id: str              # URI, bijv. https://mastodon.social/users/jasper
    username: str
    display_name: str
    public_key: bytes
    inbox: str
    outbox: str
    followers: str
    following: str

    # JIS extensies
    jis_did: Optional[str] = None  # Device Identity
    jis_trust_level: JISTrustLevel = JISTrustLevel.UNVERIFIED
    jis_hid_binding: Optional[str] = None  # HID binding hash

@dataclass
class JISActivity:
    """ActivityPub Activity met JIS semantic layer"""
    id: str
    type: ActivityType
    actor: Actor
    object: Dict[str, Any]
    published: datetime

    # JIS extensies
    humotica: Dict[str, str] = field(default_factory=dict)
    tibet_token: Optional[str] = None
    tibet_valid_until: Optional[datetime] = None
    trust_level: int = 0
    content_hash: Optional[str] = None  # SCS - Semantic Continuity Signature

@dataclass
class JISFederationPolicy:
    """
    Federatie policy voor een instance

    Bepaalt welke activiteiten worden geaccepteerd op basis van JIS.
    """
    instance_domain: str

    # Minimum trust levels per activity type
    min_trust_create: int = 1
    min_trust_announce: int = 1
    min_trust_follow: int = 0
    min_trust_dm: int = 2  # Direct messages vereisen hogere trust

    # Humotica vereisten
    require_humotica_for_create: bool = True
    require_humotica_for_dm: bool = True

    # TIBET vereisten
    require_tibet_for_first_contact: bool = True

    # Blocklist
    blocked_instances: List[str] = field(default_factory=list)

    # Rate limiting per trust level
    rate_limits: Dict[int, int] = field(default_factory=lambda: {
        0: 5,    # Unverified: 5 posts/hour
        1: 20,   # Email verified: 20/hour
        2: 50,   # Phone verified: 50/hour
        3: 100,  # ID verified: 100/hour
        4: 500,  # Org verified: 500/hour
        5: 1000  # Press: 1000/hour
    })

class SNAFTSocial:
    """
    SNAFT voor social media

    Blokkeert activiteiten die niet passen bij het account type.
    """

    ACCOUNT_TYPE_RULES = {
        "personal": {
            "allowed_activities": [ActivityType.CREATE, ActivityType.ANNOUNCE,
                                  ActivityType.LIKE, ActivityType.FOLLOW],
            "max_posts_per_hour": 20,
            "can_create_polls": True,
            "can_dm_strangers": False
        },
        "business": {
            "allowed_activities": [ActivityType.CREATE, ActivityType.ANNOUNCE,
                                  ActivityType.LIKE, ActivityType.FOLLOW],
            "max_posts_per_hour": 50,
            "can_create_polls": True,
            "can_dm_strangers": True  # Voor klantenservice
        },
        "bot": {
            "allowed_activities": [ActivityType.CREATE, ActivityType.ANNOUNCE],
            "max_posts_per_hour": 100,
            "can_create_polls": False,
            "can_dm_strangers": False,
            "must_label_as_bot": True
        },
        "press": {
            "allowed_activities": [ActivityType.CREATE, ActivityType.ANNOUNCE,
                                  ActivityType.LIKE, ActivityType.FOLLOW],
            "max_posts_per_hour": 200,
            "can_create_polls": True,
            "can_dm_strangers": True,
            "breaking_news_priority": True
        }
    }

    @classmethod
    def check(cls, account_type: str, activity: ActivityType,
              context: Dict[str, Any]) -> tuple[bool, str]:
        """Check of account type deze activity mag doen"""
        rules = cls.ACCOUNT_TYPE_RULES.get(account_type, cls.ACCOUNT_TYPE_RULES["personal"])

        if activity not in rules["allowed_activities"]:
            return False, f"SNAFT: {account_type} mag geen {activity.value}"

        # Check rate limit
        posts_this_hour = context.get("posts_this_hour", 0)
        if posts_this_hour >= rules["max_posts_per_hour"]:
            return False, f"SNAFT: Rate limit bereikt ({rules['max_posts_per_hour']}/hour)"

        # Bot labeling check
        if account_type == "bot" and rules.get("must_label_as_bot"):
            if not context.get("labeled_as_bot", False):
                return False, "SNAFT: Bot accounts moeten gelabeld zijn"

        return True, "SNAFT: OK"

class BALANSSocial:
    """
    BALANS voor social media

    Risk assessment voor activiteiten.
    """

    RISK_THRESHOLD = 0.7

    @classmethod
    def calculate_risk(cls, activity: JISActivity) -> tuple[float, str]:
        """Bereken risico score"""
        risk = 0.0
        reasons = []

        # Nieuw account = hogere risk (simulatie: trust level * 30 dagen)
        account_age_days = activity.actor.jis_trust_level.value * 30
        if account_age_days < 7:
            risk += 0.3
            reasons.append("Account < 7 dagen oud")

        # Geen Humotica context = verdacht
        if not activity.humotica:
            risk += 0.3
            reasons.append("Geen Humotica context")

        # Links in eerste post = spam indicator
        content = activity.object.get("content", "")
        if "http" in content and account_age_days < 30:
            risk += 0.2
            reasons.append("Links in post van nieuw account")

        # Veel mentions = mogelijk spam
        mentions = content.count("@")
        if mentions > 5:
            risk += 0.2
            reasons.append(f"Veel mentions ({mentions})")

        # Trust level verlaagt risk
        risk -= activity.trust_level * 0.1
        reasons.append(f"Trust level {activity.trust_level}")

        # TIBET token verlaagt risk
        if activity.tibet_token:
            risk -= 0.15
            reasons.append("Valid TIBET token")

        risk = max(0.0, min(1.0, risk))
        return risk, " | ".join(reasons)

class JISActivityPubValidator:
    """
    Hoofd JIS validator voor ActivityPub activiteiten
    """

    def __init__(self, policy: JISFederationPolicy):
        self.policy = policy
        self.audit_log: List[Dict] = []
        self.rate_counters: Dict[str, int] = {}  # actor_id -> posts this hour

    def validate(self, activity: JISActivity,
                 account_type: str = "personal",
                 is_first_contact: bool = False,
                 is_dm: bool = False) -> tuple[bool, str]:
        """
        Volledige JIS validatie van ActivityPub activity
        """
        actor_id = activity.actor.id

        # Check blocked instances
        instance = actor_id.split("/")[2]  # Extract domain from URI
        if instance in self.policy.blocked_instances:
            self._log("BLOCKED", activity, f"Instance {instance} is geblokkeerd")
            return False, f"Instance {instance} is geblokkeerd"

        # Stap 1: SNAFT check
        context = {
            "posts_this_hour": self.rate_counters.get(actor_id, 0),
            "labeled_as_bot": account_type == "bot"
        }
        snaft_ok, snaft_reason = SNAFTSocial.check(account_type, activity.type, context)
        if not snaft_ok:
            self._log("BLOCKED", activity, snaft_reason)
            return False, snaft_reason

        # Stap 2: Trust level check
        min_trust = self._get_min_trust(activity.type, is_dm)
        if activity.trust_level < min_trust:
            reason = f"Trust level {activity.trust_level} < vereist {min_trust}"
            self._log("BLOCKED", activity, reason)
            return False, reason

        # Stap 3: BALANS risk assessment
        risk, risk_reason = BALANSSocial.calculate_risk(activity)
        if risk > BALANSSocial.RISK_THRESHOLD:
            reason = f"BALANS: Risk {risk:.2f} > {BALANSSocial.RISK_THRESHOLD} ({risk_reason})"
            self._log("BLOCKED", activity, reason)
            return False, reason

        # Stap 4: Humotica check
        if self._requires_humotica(activity.type, is_dm):
            if not self._validate_humotica(activity.humotica):
                self._log("BLOCKED", activity, "Ongeldige Humotica context")
                return False, "Humotica context vereist"

        # Stap 5: TIBET check voor first contact
        if is_first_contact and self.policy.require_tibet_for_first_contact:
            if not activity.tibet_token:
                self._log("BLOCKED", activity, "TIBET vereist voor eerste contact")
                return False, "TIBET token vereist voor eerste contact"
            if activity.tibet_valid_until and datetime.now() > activity.tibet_valid_until:
                self._log("BLOCKED", activity, "TIBET token verlopen")
                return False, "TIBET token is verlopen"

        # Update rate counter
        self.rate_counters[actor_id] = self.rate_counters.get(actor_id, 0) + 1

        self._log("ALLOWED", activity, f"Risk {risk:.2f}, Trust {activity.trust_level}")
        return True, f"Geaccepteerd (risk={risk:.2f}, trust={activity.trust_level})"

    def _get_min_trust(self, activity_type: ActivityType, is_dm: bool) -> int:
        """Bepaal minimum trust level"""
        if is_dm:
            return self.policy.min_trust_dm
        if activity_type == ActivityType.CREATE:
            return self.policy.min_trust_create
        if activity_type == ActivityType.ANNOUNCE:
            return self.policy.min_trust_announce
        if activity_type == ActivityType.FOLLOW:
            return self.policy.min_trust_follow
        return 1

    def _requires_humotica(self, activity_type: ActivityType, is_dm: bool) -> bool:
        """Check of Humotica vereist is"""
        if is_dm:
            return self.policy.require_humotica_for_dm
        if activity_type == ActivityType.CREATE:
            return self.policy.require_humotica_for_create
        return False

    def _validate_humotica(self, humotica: Dict[str, str]) -> bool:
        """Valideer Humotica context"""
        required = ["sense", "context", "intent", "explain"]
        return all(humotica.get(k) for k in required)

    def _log(self, action: str, activity: JISActivity, reason: str):
        """Audit log entry"""
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "actor": activity.actor.username,
            "activity_type": activity.type.value,
            "trust_level": activity.trust_level,
            "reason": reason
        })


def create_test_actor(username: str, trust_level: JISTrustLevel) -> Actor:
    """Maak test actor"""
    domain = "mastodon.example.com"
    return Actor(
        id=f"https://{domain}/users/{username}",
        username=username,
        display_name=username.title(),
        public_key=os.urandom(32),
        inbox=f"https://{domain}/users/{username}/inbox",
        outbox=f"https://{domain}/users/{username}/outbox",
        followers=f"https://{domain}/users/{username}/followers",
        following=f"https://{domain}/users/{username}/following",
        jis_trust_level=trust_level
    )


def create_tibet_token(actor_id: str, valid_minutes: int = 5) -> tuple[str, datetime]:
    """Maak TIBET token"""
    valid_until = datetime.now() + timedelta(minutes=valid_minutes)
    payload = f"{actor_id}:{valid_until.isoformat()}"
    token = hashlib.sha256(payload.encode()).hexdigest()[:32]
    return token, valid_until


def test_scenario(name: str, validator: JISActivityPubValidator,
                 activity: JISActivity, account_type: str,
                 is_first_contact: bool, is_dm: bool,
                 expected_pass: bool) -> bool:
    """Test een scenario"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"Actor: {activity.actor.username}")
    print(f"Activity: {activity.type.value}")
    print(f"Trust Level: {activity.trust_level}")
    print(f"Account Type: {account_type}")
    print(f"First Contact: {is_first_contact}")
    print(f"DM: {is_dm}")
    print(f"Has Humotica: {bool(activity.humotica)}")
    print(f"Has TIBET: {bool(activity.tibet_token)}")

    allowed, reason = validator.validate(activity, account_type, is_first_contact, is_dm)

    status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
    print(f"\nResult: {status}")
    print(f"Reason: {reason}")

    return allowed == expected_pass


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║     JIS ACTIVITYPUB/NOSTR PROTOCOL TEST - FEDIVERSE          ║
║                                                              ║
║  Testing semantic security for federated social media        ║
║  Stop spam & bots with intent validation                     ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Setup policy
    policy = JISFederationPolicy(
        instance_domain="mastodon.example.com",
        min_trust_create=1,
        min_trust_dm=2,
        require_humotica_for_create=True,
        require_tibet_for_first_contact=True,
        blocked_instances=["spam.instance.xyz"]
    )

    validator = JISActivityPubValidator(policy)
    results = []

    # Test 1: Legitieme post met Humotica (MOET SLAGEN)
    print("\n" + "="*60)
    print("SCENARIO 1: Normale post met Humotica context")
    print("="*60)

    actor1 = create_test_actor("jasper", JISTrustLevel.VERIFIED_EMAIL)
    activity1 = JISActivity(
        id="https://mastodon.example.com/activities/1",
        type=ActivityType.CREATE,
        actor=actor1,
        object={
            "type": "Note",
            "content": "Net mijn nieuwe JIS protocol test suite afgemaakt! 🎉"
        },
        published=datetime.now(),
        humotica={
            "sense": "Afronding van development project",
            "context": "Open source security framework ontwikkeling",
            "intent": "Delen van mijlpaal met community",
            "explain": "Transparantie over voortgang, feedback welkom"
        },
        trust_level=1
    )

    result1 = test_scenario(
        "Normal Post with Humotica (SHOULD PASS)",
        validator, activity1, "personal",
        is_first_contact=False, is_dm=False,
        expected_pass=True
    )
    results.append(("Normal post allowed", result1))

    # Test 2: Spam bot zonder Humotica (MOET FALEN)
    print("\n" + "="*60)
    print("SCENARIO 2: Spam bot zonder context")
    print("="*60)

    actor2 = create_test_actor("buy_crypto_now", JISTrustLevel.UNVERIFIED)
    activity2 = JISActivity(
        id="https://mastodon.example.com/activities/2",
        type=ActivityType.CREATE,
        actor=actor2,
        object={
            "type": "Note",
            "content": "🚀 BUY NOW! http://scam.link @user1 @user2 @user3 @user4 @user5 @user6"
        },
        published=datetime.now(),
        humotica={},  # Geen context - spam!
        trust_level=0
    )

    result2 = test_scenario(
        "Spam Bot - No Humotica (SHOULD FAIL)",
        validator, activity2, "bot",
        is_first_contact=False, is_dm=False,
        expected_pass=False
    )
    results.append(("Spam bot blocked", result2))

    # Test 3: First contact DM zonder TIBET (MOET FALEN)
    print("\n" + "="*60)
    print("SCENARIO 3: Eerste DM zonder TIBET token")
    print("="*60)

    actor3 = create_test_actor("stranger", JISTrustLevel.VERIFIED_PHONE)
    activity3 = JISActivity(
        id="https://mastodon.example.com/activities/3",
        type=ActivityType.CREATE,
        actor=actor3,
        object={
            "type": "Note",
            "content": "Hey, ik ben een recruiter...",
            "to": ["https://mastodon.example.com/users/jasper"]
        },
        published=datetime.now(),
        humotica={
            "sense": "Talent scouting",
            "context": "LinkedIn alternatief",
            "intent": "Job opportunity delen",
            "explain": "Professional networking"
        },
        trust_level=2,
        tibet_token=None  # Geen TIBET!
    )

    result3 = test_scenario(
        "First Contact DM without TIBET (SHOULD FAIL)",
        validator, activity3, "business",
        is_first_contact=True, is_dm=True,
        expected_pass=False
    )
    results.append(("First contact without TIBET blocked", result3))

    # Test 4: First contact DM MET TIBET (MOET SLAGEN)
    print("\n" + "="*60)
    print("SCENARIO 4: Eerste DM met TIBET token")
    print("="*60)

    tibet_token, valid_until = create_tibet_token(actor3.id, 5)
    activity4 = JISActivity(
        id="https://mastodon.example.com/activities/4",
        type=ActivityType.CREATE,
        actor=actor3,
        object={
            "type": "Note",
            "content": "Hey, ik ben een recruiter bij TechCorp...",
            "to": ["https://mastodon.example.com/users/jasper"]
        },
        published=datetime.now(),
        humotica={
            "sense": "Talent scouting na zien van JIS project",
            "context": "Open source developer outreach",
            "intent": "Gesprek over mogelijke samenwerking",
            "explain": "JIS past bij onze security roadmap"
        },
        trust_level=2,
        tibet_token=tibet_token,
        tibet_valid_until=valid_until
    )

    result4 = test_scenario(
        "First Contact DM with TIBET (SHOULD PASS)",
        validator, activity4, "business",
        is_first_contact=True, is_dm=True,
        expected_pass=True
    )
    results.append(("First contact with TIBET allowed", result4))

    # Test 5: Post van geblokkeerde instance (MOET FALEN)
    print("\n" + "="*60)
    print("SCENARIO 5: Post van geblokkeerde instance")
    print("="*60)

    actor5 = Actor(
        id="https://spam.instance.xyz/users/spammer",
        username="spammer",
        display_name="Totally Legit",
        public_key=os.urandom(32),
        inbox="https://spam.instance.xyz/users/spammer/inbox",
        outbox="https://spam.instance.xyz/users/spammer/outbox",
        followers="https://spam.instance.xyz/users/spammer/followers",
        following="https://spam.instance.xyz/users/spammer/following",
        jis_trust_level=JISTrustLevel.VERIFIED_ID  # Zelfs met hoge trust
    )

    activity5 = JISActivity(
        id="https://spam.instance.xyz/activities/1",
        type=ActivityType.CREATE,
        actor=actor5,
        object={"type": "Note", "content": "Hello!"},
        published=datetime.now(),
        humotica={
            "sense": "Friendly hello",
            "context": "Making friends",
            "intent": "Social connection",
            "explain": "Being nice"
        },
        trust_level=3
    )

    result5 = test_scenario(
        "Blocked Instance (SHOULD FAIL)",
        validator, activity5, "personal",
        is_first_contact=False, is_dm=False,
        expected_pass=False
    )
    results.append(("Blocked instance rejected", result5))

    # Test 6: Verified press met breaking news (MOET SLAGEN)
    print("\n" + "="*60)
    print("SCENARIO 6: Geverifieerde journalist - breaking news")
    print("="*60)

    actor6 = create_test_actor("journalist_nos", JISTrustLevel.VERIFIED_PRESS)
    activity6 = JISActivity(
        id="https://mastodon.example.com/activities/6",
        type=ActivityType.CREATE,
        actor=actor6,
        object={
            "type": "Note",
            "content": "BREAKING: Grote security lek ontdekt in veel gebruikte software. Meer info volgt. #security #breaking"
        },
        published=datetime.now(),
        humotica={
            "sense": "Security incident bij tech bedrijf bevestigd",
            "context": "Verantwoorde disclosure na coordinatie met vendor",
            "intent": "Publiek waarschuwen voor kwetsbaarheid",
            "explain": "CVE toegewezen, patches beschikbaar, tijd voor publicatie"
        },
        trust_level=5
    )

    result6 = test_scenario(
        "Verified Press Breaking News (SHOULD PASS)",
        validator, activity6, "press",
        is_first_contact=False, is_dm=False,
        expected_pass=True
    )
    results.append(("Press breaking news allowed", result6))

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
        print("✅ ALLE TESTS GESLAAGD - JIS ACTIVITYPUB WERKT!")
    else:
        print("❌ SOMMIGE TESTS GEFAALD")
    print("="*60)

    # Print audit log
    print("\n📋 AUDIT LOG:")
    for entry in validator.audit_log:
        print(f"  [{entry['timestamp'][:19]}] {entry['action']}: @{entry['actor']} - {entry['reason'][:35]}...")

    print("\n💡 KEY INSIGHT:")
    print("   Bots kunnen technisch gezien wel Humotica velden invullen,")
    print("   maar ze kunnen geen COHERENTE context genereren die past")
    print("   bij hun gedrag over tijd. De continuity chain onthult dit.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
