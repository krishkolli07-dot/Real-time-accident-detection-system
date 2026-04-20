"""
notifier.py  —  Multi-channel alert system

Channels supported:
  1. SMS       — Twilio SMS to your mobile + all neighbours
  2. Call      — Twilio voice call with TwiML message to your mobile
  3. Email     — SMTP email (Gmail / any SMTP) to all contacts
  4. WhatsApp  — Twilio WhatsApp sandbox to registered numbers
  5. Dispatch  — Calls emergency_dispatch.dispatch_services(lat, lon)

FIXES vs original:
  • ENABLE_CALL  was False  → set to True  (you were never getting calls!)
  • ENABLE_SMS   was False  → set to True  (you were never getting SMS!)
  • dispatch_services() is now called on every accident (was orphaned before)
  • _twilio_client() guard fixed — checked "YOUR_TWILIO" but real SID starts
    with "AC", so the guard never fired; now also validates token length
  • Neighbour loop now safely skips missing keys without KeyError
"""

import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# ── Twilio ────────────────────────────────────────────────────────────────────
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("[notifier] ⚠ twilio not installed — run: pip install twilio")

# ── Emergency dispatch (fixed: was orphaned, now called on every accident) ────
try:
    from .emergency_dispatch import dispatch_services
    DISPATCH_AVAILABLE = True
except ImportError:
    try:
        from emergency_dispatch import dispatch_services
        DISPATCH_AVAILABLE = True
    except ImportError:
        DISPATCH_AVAILABLE = False
        print("[notifier] ⚠ emergency_dispatch not found — dispatch skipped")


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG  — edit here or use environment variables
# ══════════════════════════════════════════════════════════════════════════════

class AlertConfig:
    # ── Twilio credentials ────────────────────────────────────────────────────
    TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID",  "AC68cf06de30321387b32c5fae4f0a822d")
    TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN",   "ccc4cf4a54a2d341015b09b4778abae7")
    TWILIO_FROM  = os.getenv("TWILIO_FROM_PHONE",   "+16592504680")
    TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"

    # ── Your mobile (primary alert recipient) ─────────────────────────────────
    MY_PHONE     = os.getenv("MY_PHONE",  "+917075582488")
    MY_EMAIL     = os.getenv("MY_EMAIL",  "vuyyurueswar363@gmail.com")

    # ── Email SMTP ────────────────────────────────────────────────────────────
    EMAIL_FROM   = os.getenv("ALERT_EMAIL_FROM", "vuyyurueswar363@gmail.com")
    EMAIL_PASS   = os.getenv("ALERT_EMAIL_PASS", "rykkxzrudbkarbpy")
    SMTP_HOST    = "smtp.gmail.com"
    SMTP_PORT    = 587

    # ── Neighbourhood members ─────────────────────────────────────────────────
    NEIGHBOURS = [
        {"name": "Neighbour 1", "phone": "+917013959306", "email": "krishkolli07@gmail.com",    "whatsapp": True},
        {"name": "Neighbour 2", "phone": "+917207887279", "email": "susanthgaddam28@gmail.com", "whatsapp": True},
        {"name": "Neighbour 3", "phone": "+919398676207",                                        "whatsapp": True},
    ]

    # ── Which channels to use ─────────────────────────────────────────────────
    # FIX: ENABLE_SMS and ENABLE_CALL were both False — you were getting zero
    #      calls and no SMS even though Twilio was fully configured!
    ENABLE_SMS        = True   # was False ← BUG FIXED
    ENABLE_CALL       = True   # was False ← BUG FIXED (this is why no calls!)
    ENABLE_EMAIL      = True
    ENABLE_WHATSAPP   = True
    ENABLE_NEIGHBOURS = True
    ENABLE_DISPATCH   = True   # NEW: call emergency_dispatch.dispatch_services()


cfg = AlertConfig()


# ══════════════════════════════════════════════════════════════════════════════
# TWILIO CLIENT
# ══════════════════════════════════════════════════════════════════════════════

def _twilio_client():
    if not TWILIO_AVAILABLE:
        print("[notifier] ⚠ Twilio library not installed")
        return None
    # FIX: old guard checked for literal string "YOUR_TWILIO" which was never
    # present — real SIDs start with "AC". Now we validate both SID and token
    # are non-empty and look real.
    if not cfg.TWILIO_SID or not cfg.TWILIO_TOKEN:
        print("[notifier] ⚠ Twilio credentials missing — skipping SMS/Call")
        return None
    if len(cfg.TWILIO_TOKEN) < 20:
        print("[notifier] ⚠ Twilio token looks invalid — skipping SMS/Call")
        return None
    try:
        return TwilioClient(cfg.TWILIO_SID, cfg.TWILIO_TOKEN)
    except Exception as e:
        print(f"[notifier] Twilio init error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# SMS
# ══════════════════════════════════════════════════════════════════════════════

def send_sms(to: str, message: str, client=None):
    """Send SMS to a single number."""
    cl = client or _twilio_client()
    if not cl:
        return
    try:
        msg = cl.messages.create(body=message, from_=cfg.TWILIO_FROM, to=to)
        print(f"[SMS] ✓ Sent to {to} — SID: {msg.sid}")
    except Exception as e:
        print(f"[SMS] ✗ Failed to {to}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# VOICE CALL
# ══════════════════════════════════════════════════════════════════════════════

def make_call(to: str, message: str, client=None):
    """Make a voice call that reads the accident message aloud."""
    cl = client or _twilio_client()
    if not cl:
        return
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice" language="en-IN">
    Alert! {message}. I repeat. {message}. Please take immediate action.
  </Say>
  <Pause length="1"/>
  <Say voice="alice" language="en-IN">This is an automated message from your Smart City Traffic AI system.</Say>
</Response>"""
    try:
        call = cl.calls.create(twiml=twiml, from_=cfg.TWILIO_FROM, to=to)
        print(f"[CALL] ✓ Calling {to} — SID: {call.sid}")
    except Exception as e:
        print(f"[CALL] ✗ Failed to {to}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# WHATSAPP
# ══════════════════════════════════════════════════════════════════════════════

def send_whatsapp(to: str, message: str, client=None):
    """Send WhatsApp message via Twilio sandbox."""
    cl = client or _twilio_client()
    if not cl:
        return
    wa_to = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
    try:
        msg = cl.messages.create(
            body=message,
            from_=cfg.TWILIO_WHATSAPP_FROM,
            to=wa_to,
        )
        print(f"[WHATSAPP] ✓ Sent to {to} — SID: {msg.sid}")
    except Exception as e:
        print(f"[WHATSAPP] ✗ Failed to {to}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL
# ══════════════════════════════════════════════════════════════════════════════

def send_email(to: str, subject: str, body: str, snapshot_path: str = None):
    """Send HTML email with optional accident snapshot attachment."""
    if not cfg.EMAIL_FROM or not cfg.EMAIL_PASS:
        print("[EMAIL] ⚠ Email not configured — skipping")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = cfg.EMAIL_FROM
        msg["To"]      = to

        html = f"""
        <html><body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:20px">
        <div style="max-width:600px;margin:auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.1)">
          <div style="background:#dc2626;padding:24px;text-align:center">
            <h1 style="color:white;margin:0;font-size:24px">🚨 ACCIDENT DETECTED</h1>
            <p style="color:#fecaca;margin:8px 0 0;font-size:14px">Smart City Traffic AI — NEXUS System</p>
          </div>
          <div style="padding:24px">
            <div style="background:#fef2f2;border-left:4px solid #dc2626;padding:16px;border-radius:0 8px 8px 0;margin-bottom:20px">
              <pre style="margin:0;font-family:monospace;font-size:13px;white-space:pre-wrap;color:#7f1d1d">{body}</pre>
            </div>
            <p style="color:#6b7280;font-size:12px;margin-top:20px">
              This is an automated alert from the NEXUS Smart City Traffic AI system.<br>
              Please contact emergency services if required: <strong>112</strong>
            </p>
          </div>
        </div>
        </body></html>"""

        msg.attach(MIMEText(html, "html"))

        if snapshot_path and os.path.exists(snapshot_path):
            with open(snapshot_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            fname = os.path.basename(snapshot_path)
            part.add_header("Content-Disposition", f"attachment; filename={fname}")
            msg.attach(part)

        with smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg.EMAIL_FROM, cfg.EMAIL_PASS)
            server.sendmail(cfg.EMAIL_FROM, to, msg.as_string())
        print(f"[EMAIL] ✓ Sent to {to}")

    except Exception as e:
        print(f"[EMAIL] ✗ Failed to {to}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ALERT DISPATCHER
# ══════════════════════════════════════════════════════════════════════════════

def send_accident_alert(camera_id: int, camera_name: str,
                        location: str, lat: float, lon: float,
                        snapshot_path: str = None):
    """
    Send alerts via ALL configured channels + dispatch emergency services.
    Runs in a background thread so it never blocks the camera worker.
    """
    def _dispatch():
        now       = datetime.now().strftime("%d %b %Y at %H:%M:%S")
        maps_link = f"https://maps.google.com/?q={lat},{lon}"

        sms_msg = (
            f"🚨 ACCIDENT DETECTED\n"
            f"Camera: {camera_name} (CAM-{camera_id})\n"
            f"Location: {location}\n"
            f"Time: {now}\n"
            f"Map: {maps_link}\n"
            f"— NEXUS Traffic AI"
        )

        email_subject = f"🚨 Accident Alert — {camera_name} — {location}"
        email_body = (
            f"ACCIDENT DETECTED\n\n"
            f"Camera     : {camera_name} (CAM-{camera_id})\n"
            f"Location   : {location}\n"
            f"Time       : {now}\n"
            f"Coordinates: {lat:.5f}°, {lon:.5f}°\n"
            f"Map Link   : {maps_link}\n\n"
            f"Please take immediate action.\n"
            f"Emergency: 112 | Police: 100 | Ambulance: 108"
        )

        call_msg = (
            f"Accident detected at {location} from camera {camera_id}. "
            f"Time: {now}. "
            f"Please check the NEXUS dashboard immediately."
        )

        # FIX: initialise Twilio client once and reuse — avoids repeated auth
        cl = _twilio_client()

        # ── 0. Emergency dispatch (was completely orphaned — now called!) ──────
        if cfg.ENABLE_DISPATCH and DISPATCH_AVAILABLE:
            try:
                dispatch_services(lat, lon)
                print(f"[notifier] 🚑 Emergency services dispatched to {lat},{lon}")
            except Exception as e:
                print(f"[notifier] ⚠ dispatch_services error: {e}")

        # ── 1. SMS to your mobile ─────────────────────────────────────────────
        if cfg.ENABLE_SMS:
            send_sms(cfg.MY_PHONE, sms_msg, cl)

        # ── 2. Voice call to your mobile ──────────────────────────────────────
        if cfg.ENABLE_CALL:
            make_call(cfg.MY_PHONE, call_msg, cl)

        # ── 3. Email to your address ──────────────────────────────────────────
        if cfg.ENABLE_EMAIL:
            send_email(cfg.MY_EMAIL, email_subject, email_body, snapshot_path)

        # ── 4. WhatsApp to your mobile ────────────────────────────────────────
        if cfg.ENABLE_WHATSAPP:
            send_whatsapp(cfg.MY_PHONE, sms_msg, cl)

        # ── 5. Alert all neighbours ───────────────────────────────────────────
        if cfg.ENABLE_NEIGHBOURS:
            neighbour_sms = (
                f"⚠ NEIGHBOURHOOD ALERT\n"
                f"Accident detected near {location}.\n"
                f"Time: {now}\n"
                f"Map: {maps_link}\n"
                f"Please be cautious.\n— Smart City NEXUS"
            )
            for nb in cfg.NEIGHBOURS:
                # SMS
                if cfg.ENABLE_SMS and nb.get("phone"):
                    send_sms(nb["phone"], neighbour_sms, cl)
                # Email
                if cfg.ENABLE_EMAIL and nb.get("email"):
                    send_email(
                        nb["email"],
                        f"⚠ Neighbourhood Accident Alert — {location}",
                        f"An accident was detected near {location} at {now}.\n"
                        f"Map: {maps_link}\nPlease be cautious.",
                        None,  # no snapshot sent to neighbours for privacy
                    )
                # WhatsApp
                if cfg.ENABLE_WHATSAPP and nb.get("whatsapp") and nb.get("phone"):
                    send_whatsapp(nb["phone"], neighbour_sms, cl)

        print(f"[notifier] ✓ All alerts dispatched for CAM-{camera_id}")

    # Run in background thread — never block the camera worker
    threading.Thread(target=_dispatch, daemon=True).start()