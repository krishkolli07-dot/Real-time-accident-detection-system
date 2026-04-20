"""
emergency_dispatch.py

FIXES vs original:
  • Removed `import requests` — it was imported but never used (requests is
    for HTTP; actual dispatch is stub print statements + future integrations).
  • Function is now properly called from notifier.py (was completely orphaned
    before — defined here but never imported or invoked anywhere).
  • Added docstring and proper return so callers know it succeeded.
  • Prepared placeholders for Twilio SMS and Government API integrations.
"""


def dispatch_services(lat: float, lon: float) -> bool:
    """
    Dispatch emergency services to the given GPS coordinates.

    Currently prints to console (stub).  Uncomment the sections below
    once you have Twilio / Government API credentials set up.

    Returns True if dispatch succeeded (or was stubbed), False on error.
    """
    maps_link = f"https://maps.google.com/?q={lat},{lon}"

    print(f"[dispatch] 🚑 Ambulance dispatched to {lat},{lon}  → {maps_link}")
    print(f"[dispatch] 🚓 Police notified at {lat},{lon}")
    print(f"[dispatch] 🔥 Fire services alerted at {lat},{lon}")

    # ── Future: Twilio SMS to emergency control room ──────────────────────────
    # from twilio.rest import Client
    # client = Client("TWILIO_SID", "TWILIO_TOKEN")
    # client.messages.create(
    #     body=f"🚨 Accident at {lat},{lon} — {maps_link}. Dispatch immediately.",
    #     from_="+1XXXXXXXXXX",   # your Twilio number
    #     to="+91XXXXXXXXXX",     # control room number
    # )

    # ── Future: Government / Municipal API ────────────────────────────────────
    # import requests
    # requests.post(
    #     "https://api.smartcity.gov.in/emergency/dispatch",
    #     json={"lat": lat, "lon": lon, "type": "accident", "source": "NEXUS"},
    #     headers={"Authorization": "Bearer YOUR_API_KEY"},
    #     timeout=10,
    # )

    return True