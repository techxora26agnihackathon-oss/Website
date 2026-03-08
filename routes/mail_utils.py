import os
import time
import smtplib
import ssl
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


def _get_smtp_creds():
    """Read SMTP credentials from environment, stripping spaces from App Password."""
    return {
        'server':   os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'user':     os.getenv('SMTP_USER', ''),
        'password': os.getenv('SMTP_PASS', '').replace(' ', ''),   # strip App Password spaces
        'sender':   os.getenv('SENDER_EMAIL', os.getenv('SMTP_USER', '')),
    }


def _build_message(sender, to_email, subject, body, pdf_paths=None):
    msg = MIMEMultipart()
    msg['From']    = f"TECHXORA '26 <{sender}>"
    msg['To']      = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    if pdf_paths:
        for path in pdf_paths:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    part = MIMEApplication(f.read())
                part.add_header('Content-Disposition', 'attachment',
                                filename=os.path.basename(path))
                msg.attach(part)
    return msg


def _try_port_465(creds, msg, to_email, timeout=15):
    """Send via SSL on port 465. Returns True on success."""
    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(creds['server'], 465, context=ctx, timeout=timeout) as s:
            s.login(creds['user'], creds['password'])
            s.send_message(msg)
        print(f"[MAIL] ✓ Sent to {to_email} via port 465 (SSL)")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[MAIL] ✗ AUTH FAILED port 465: {e}")
        print("[MAIL] → Check SMTP_USER and SMTP_PASS in .env")
        return False
    except Exception as e:
        print(f"[MAIL] ✗ Port 465 failed: {e}")
        return False


def _try_port_587(creds, msg, to_email, timeout=10):
    """Send via STARTTLS on port 587. Returns True on success."""
    try:
        with smtplib.SMTP(creds['server'], 587, timeout=timeout) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(creds['user'], creds['password'])
            s.send_message(msg)
        print(f"[MAIL] ✓ Sent to {to_email} via port 587 (STARTTLS)")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[MAIL] ✗ AUTH FAILED port 587: {e}")
        return False
    except Exception as e:
        print(f"[MAIL] ✗ Port 587 failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────
#  Public send function — tries 465 first, then 587, then retry
# ─────────────────────────────────────────────────────────────
def _send_email(to_email, subject, body, pdf_paths=None, max_retries=2):
    creds = _get_smtp_creds()

    if not creds['user'] or not creds['password']:
        print("[MAIL] ✗ SMTP_USER or SMTP_PASS missing in .env")
        return False

    msg = _build_message(creds['sender'], to_email, subject, body, pdf_paths)

    for attempt in range(1, max_retries + 1):
        print(f"[MAIL] → Sending to {to_email} (attempt {attempt}/{max_retries})")

        # Try port 465 (SSL) first — less often blocked by firewalls
        if _try_port_465(creds, msg, to_email):
            return True

        # Try port 587 (STARTTLS) as fallback
        if _try_port_587(creds, msg, to_email):
            return True

        if attempt < max_retries:
            wait = 4 * attempt   # 4s then 8s
            print(f"[MAIL] Both ports failed. Retrying in {wait}s …")
            time.sleep(wait)

    print(f"[MAIL] ✗ ALL ATTEMPTS FAILED for {to_email}.")
    print("[MAIL] → This machine cannot reach smtp.gmail.com.")
    print("[MAIL] → Use a mobile hotspot or ask admin to open port 465/587 outbound.")
    return False


# ─────────────────────────────────────────────────────────────
#  Background thread sender (admin page won't freeze)
# ─────────────────────────────────────────────────────────────
def _send_email_async(to_email, subject, body, pdf_paths=None, max_retries=2):
    t = threading.Thread(
        target=_send_email,
        args=(to_email, subject, body, pdf_paths),
        kwargs={'max_retries': max_retries},
        daemon=False   # survive Flask auto-reload
    )
    t.start()
    return t


# ─────────────────────────────────────────────────────────────
#  Test connectivity — used by /admin/test-email
# ─────────────────────────────────────────────────────────────
def test_smtp_connection():
    """
    Quick probe: can this machine reach smtp.gmail.com on port 465 and 587?
    Returns dict with results. No email is actually sent.
    """
    results = {}
    creds = _get_smtp_creds()

    # Test 465
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(creds['server'], 465, context=ctx, timeout=8) as s:
            results['port_465'] = 'OK – connected'
    except Exception as e:
        results['port_465'] = f'FAIL – {e}'

    # Test 587
    try:
        with smtplib.SMTP(creds['server'], 587, timeout=8) as s:
            s.ehlo()
            results['port_587'] = 'OK – connected'
    except Exception as e:
        results['port_587'] = f'FAIL – {e}'

    results['smtp_user'] = creds['user'] or '(not set)'
    results['smtp_pass_len'] = len(creds['password'])
    return results


# ─────────────────────────────────────────────────────────────
#  1. Registration received (payment pending)
# ─────────────────────────────────────────────────────────────
def send_registration_received_email(team, participants, async_send=True):
    leader_email = participants[0].email if participants else None
    if not leader_email:
        return False

    subject = f"Registration Received – TECHXORA '26: {team.team_name}"
    body = f"""Dear Team Leader,

Thank you for registering "{team.team_name}" for TECHXORA '26.

We have received your registration and payment proof.
Our team is currently verifying your payment.

Domain: {team.domain}

Participants:
"""
    for p in participants:
        body += f"  - {p.name}\n"

    body += """
ID cards will be emailed to each participant once payment is verified.

Best regards,
Organizing Committee – TECHXORA '26
techxora26.agnihackathon@gmail.com
"""
    if async_send:
        _send_email_async(leader_email, subject, body)
        return True
    return _send_email(leader_email, subject, body)


# ─────────────────────────────────────────────────────────────
#  2. Per-participant ID card (payment verified)
# ─────────────────────────────────────────────────────────────
def send_individual_confirmation_email(team, participant, pdf_path,
                                       async_send=True):
    if not participant.email:
        return False

    subject = f"Payment Verified & Your ID Card – TECHXORA '26"
    body = f"""Dear {participant.name},

Your payment for team "{team.team_name}" has been verified.
Your registration for TECHXORA '26 is confirmed!

Login Credentials
  Participant ID : {participant.unique_id}
  Password       : {participant.password}

Your PDF ID card is attached. Please carry it to the venue.

Event Details
  Date  : April 15-16, 2026
  Venue : Agni College of Technology, OMR, Chennai
  Domain: {team.domain}

Best regards,
Organizing Committee – TECHXORA '26
techxora26.agnihackathon@gmail.com
"""
    pdfs = [pdf_path] if pdf_path and os.path.exists(pdf_path) else []

    if async_send:
        _send_email_async(participant.email, subject, body, pdf_paths=pdfs)
        return True
    return _send_email(participant.email, subject, body, pdf_paths=pdfs)


# ─────────────────────────────────────────────────────────────
#  3. Send to whole team
# ─────────────────────────────────────────────────────────────
def send_team_confirmation_email(team, participants, pdf_paths,
                                 async_send=True):
    for i, participant in enumerate(participants):
        pdf = pdf_paths[i] if i < len(pdf_paths) else None
        send_individual_confirmation_email(team, participant, pdf,
                                           async_send=async_send)
        time.sleep(0.1)
    return True
