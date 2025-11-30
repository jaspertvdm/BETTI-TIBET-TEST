#!/usr/bin/env python3
"""
Live Demo - Test tegen draaiende JIS Router
Dit script maakt een FIR/A, stuurt intents, en toont resultaten
Die je LIVE kunt zien in de Admin UI!
"""

import time
import sys
from jis_client import JISClient, DIDKey, HIDKey

# Configuratie
ROUTER_URL = "http://localhost:18081"  # Pas aan naar je server IP
SECRET = "example_secret_123"              # Pas aan naar je secret

def print_banner(text):
    """Print mooie banner"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def main():
    print_banner("🚀 JIS Live Demo - Test je Draaiende Router!")

    # 1. Connect
    print(f"\n📡 Connecting to router: {ROUTER_URL}")
    client = JISClient(ROUTER_URL, secret=SECRET)

    try:
        health = client.health_check()
        print(f"✓ Router status: {health['status']}")
    except Exception as e:
        print(f"✗ Cannot connect to router: {e}")
        print(f"\nMake sure router is running on {ROUTER_URL}")
        sys.exit(1)

    # 2. Generate Keys
    print_banner("🔑 Generating DID/HID Keys")
    did = DIDKey.generate()
    hid = HIDKey.generate()

    print(f"✓ DID public key (first 40 chars):")
    print(f"  {did.export_public()[:40]}...")

    binding = hid.derive_did_binding(did)
    print(f"✓ HID-DID binding hash:")
    print(f"  {binding[:32]}...")
    print(f"\n⚠️  HID key stays LOCAL - never transmitted!")

    # 3. Create FIR/A
    print_banner("🤝 Creating FIR/A Relationship")

    fir_a = client.init_relationship(
        initiator="live-demo-client",
        responder="jis-router",
        roles=["demo", "client"],
        context={
            "test": "live_demo",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        humotica="Live demo session testing JIS",
        did_key=did,
        hid_key=hid
    )

    print(f"✓ FIR/A created!")
    print(f"  ID: {fir_a.id}")
    print(f"  Hash: {fir_a.continuity_hash[:16]}...")
    print(f"  Events: {fir_a.events}")

    print(f"\n👀 Check Admin UI now - you should see this relationship!")
    print(f"   URL: {ROUTER_URL}/")
    time.sleep(3)

    # 4. Send Intents
    print_banner("🎯 Sending Intents")

    intents = [
        ("test_action_1", {"step": 1, "action": "initialize"}),
        ("test_action_2", {"step": 2, "action": "process"}),
        ("test_action_3", {"step": 3, "action": "complete"}),
    ]

    for intent, context in intents:
        print(f"\n→ Sending: {intent}")
        result = client.send_intent(fir_a.id, intent, context)
        print(f"  ✓ Accepted. New hash: {result.continuity_hash[:16]}...")
        print(f"  ✓ Total events: {result.events}")
        time.sleep(1)

    print(f"\n👀 Refresh Admin UI - see the new events!")
    time.sleep(2)

    # 5. NIR Demo
    print_banner("🚨 Testing NIR (Notification)")

    print("→ Triggering NIR notification...")
    nir = client.notify_nir(
        fir_a.id,
        reason="demo_flag_unusual_activity",
        suggested_method="demo_confirmation"
    )
    print(f"  ✓ NIR notification sent")
    print(f"  ✓ Reason: {nir.reason}")
    time.sleep(2)

    print("\n→ Confirming NIR resolution...")
    confirmed = client.confirm_nir(
        fir_a.id,
        method="demo_method",
        result="confirmed"
    )
    print(f"  ✓ NIR resolved")
    print(f"  ✓ New hash: {confirmed.continuity_hash[:16]}...")

    # 6. Get Event History
    print_banner("📜 Fetching Event History")

    events = client.get_events(fir_a.id, limit=20)
    print(f"\nTotal events in chain: {len(events)}")
    print("\nEvent Timeline (newest first):")

    for event in events:
        event_type = event.payload.get('type', 'unknown')
        print(f"  #{event.seq:2d} | {event_type:20s} | {event.timestamp or 'N/A'}")

    # 7. Get DID Keys
    print_banner("🔐 Fetching DID Keys")

    keys = client.get_did_keys(fir_a.id)
    for entity, key_info in keys.items():
        print(f"\n{entity}:")
        print(f"  DID (first 40): {key_info.did_public_key[:40]}...")
        if key_info.hid_did_binding:
            print(f"  HID binding:    {key_info.hid_did_binding[:32]}...")
        print(f"  Created:        {key_info.created_at or 'N/A'}")

    # 8. Metrics
    print_banner("📊 Router Metrics")

    metrics = client.get_metrics()
    print(f"\nTotal Relationships: {metrics.get('total_relationships', 'N/A')}")
    print(f"Total Events:        {metrics.get('total_events', 'N/A')}")
    print(f"Redis Commands:      {metrics.get('redis_total_commands', 'N/A')}")

    # Done!
    print_banner("✅ Demo Complete!")

    print(f"""
Your JIS Router is working perfectly! 🎉

Next steps:
1. Open Admin UI: {ROUTER_URL}/
2. Go to "Relationships" tab
3. Find FIR/A: {fir_a.id}
4. Click "View Events" to see the full chain

You now have:
✓ Working JIS Router (server + Pi)
✓ Admin UI for monitoring
✓ Python SDK for development
✓ Complete event history
✓ DID/HID key management

Ready to build your first app! 🚀
""")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Bye! 👋")
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
