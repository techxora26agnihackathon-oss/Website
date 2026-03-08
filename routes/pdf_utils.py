"""PDF ID Card generator using reportlab - Stylish TECHXORA edition."""
import os
from reportlab.lib.pagesizes import A6
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# TECHXORA brand colours
DARK_BG  = colors.HexColor('#050810')
DARK_BG2 = colors.HexColor('#0a0f1e')
CYAN     = colors.HexColor('#00f5ff')
VIOLET   = colors.HexColor('#a78bfa')
AMBER    = colors.HexColor('#f59e0b')
WHITE    = colors.white
MUTED    = colors.HexColor('#475569')
DEEP_PUR = colors.HexColor('#1e1b4b')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_asset(rel_path):
    """Return absolute path to a static asset, or None if missing."""
    p = os.path.join(BASE_DIR, 'static', *rel_path.split('/'))
    return p if os.path.exists(p) else None


def generate_id_card(participant, output_path: str) -> str:
    """
    Generate a stylish PDF ID card for a participant.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    W, H = A6  # 105 × 148 mm  ≈  297 × 420 pts
    c = canvas.Canvas(output_path, pagesize=A6)

    # ── Full dark gradient background ─────────────────────────────────────────
    c.setFillColor(DARK_BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Side neon accent strips ────────────────────────────────────────────────
    c.setFillColor(CYAN)
    c.rect(0, 0, 2.5*mm, H, fill=1, stroke=0)          # left strip
    c.setFillColor(VIOLET)
    c.rect(W - 2.5*mm, 0, 2.5*mm, H, fill=1, stroke=0) # right strip

    # ── Top header band ───────────────────────────────────────────────────────
    c.setFillColor(DEEP_PUR)
    c.rect(0, H - 24*mm, W, 24*mm, fill=1, stroke=0)

    # Cyan bottom edge on header
    c.setFillColor(CYAN)
    c.rect(0, H - 25*mm, W, 1.2*mm, fill=1, stroke=0)

    # ── Logos: college left, hackathon right — same size ─────────────────────
    clg_logo  = _get_asset('logos/act.png')
    hack_logo = _get_asset('logos/techXora.png')

    logo_size = 19*mm          # bigger and more visible
    logo_pad  = 2*mm           # tight margin from edges
    logo_y    = H - 23*mm      # top of logo box

    if clg_logo:
        try:
            c.drawImage(ImageReader(clg_logo), logo_pad, logo_y,
                        width=logo_size, height=logo_size,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    if hack_logo:
        try:
            c.drawImage(ImageReader(hack_logo),
                        W - logo_pad - logo_size, logo_y,
                        width=logo_size, height=logo_size,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # ── College + event text — centered between two logos ────────────────────
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 8.5)
    c.drawCentredString(W / 2, H - 5.5*mm, 'AGNI COLLEGE OF TECHNOLOGY')

    c.setFillColor(colors.HexColor('#c4b5fd'))
    c.setFont('Helvetica', 6)
    c.drawCentredString(W / 2, H - 11*mm, 'DEPTARTMENT OF COMPUTER SCIENCE AND ENGINEERING')

    c.setFillColor(CYAN)
    c.setFont('Helvetica-Bold', 12)
    c.drawCentredString(W / 2, H - 19*mm, "TECHXORA '26")

    # ── Semi-transparent hackathon watermark (center) ─────────────────────────
    if hack_logo:
        try:
            c.saveState()
            c.setFillAlpha(0.06)
            wm_size = 55*mm
            c.drawImage(ImageReader(hack_logo),
                        (W - wm_size) / 2, (H - wm_size) / 2,
                        width=wm_size, height=wm_size,
                        preserveAspectRatio=True, mask='auto')
            c.restoreState()
        except Exception:
            pass

    # ── PARTICIPANT tag ────────────────────────────────────────────────────────
    c.setFillColor(VIOLET)
    c.setFont('Helvetica-Bold', 6)
    c.drawCentredString(W / 2, H - 23*mm, '— PARTICIPANT —')

    # ── Participant Name ──────────────────────────────────────────────────────
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 15)
    name_y = H - 31*mm
    name = participant.name.upper()
    # Shorten if too long
    if len(name) > 18:
        c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(W / 2, name_y, name)

    # Underline below name (cyan)
    c.setStrokeColor(CYAN)
    c.setLineWidth(0.8)
    c.line(10*mm, name_y - 2*mm, W - 10*mm, name_y - 2*mm)

    # ── QR Code ───────────────────────────────────────────────────────────────
    qr_size = 42*mm
    qr_x = (W - qr_size) / 2
    qr_y = name_y - 9*mm - qr_size

    if participant.qr_path and hasattr(participant, '_qr_abs'):
        abs_qr = participant._qr_abs
        if abs_qr and os.path.exists(abs_qr):
            try:
                c.drawImage(ImageReader(abs_qr), qr_x, qr_y,
                            width=qr_size, height=qr_size,
                            preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

    # QR glow border (double border effect)
    c.setStrokeColor(VIOLET)
    c.setLineWidth(0.4)
    c.rect(qr_x - 2*mm, qr_y - 2*mm, qr_size + 4*mm, qr_size + 4*mm, fill=0, stroke=1)
    c.setStrokeColor(CYAN)
    c.setLineWidth(1)
    c.rect(qr_x - 0.8*mm, qr_y - 0.8*mm, qr_size + 1.6*mm, qr_size + 1.6*mm, fill=0, stroke=1)

    # ── Participant ID ─────────────────────────────────────────────────────────
    id_y = qr_y - 9*mm

    # ID pill background
    pill_w = 60*mm
    pill_h = 7*mm
    pill_x = (W - pill_w) / 2
    c.setFillColor(colors.HexColor('#0d1126'))
    c.roundRect(pill_x, id_y - 1.5*mm, pill_w, pill_h, 3*mm, fill=1, stroke=0)
    c.setStrokeColor(CYAN)
    c.setLineWidth(0.6)
    c.roundRect(pill_x, id_y - 1.5*mm, pill_w, pill_h, 3*mm, fill=0, stroke=1)

    c.setFillColor(CYAN)
    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(W / 2, id_y + 1*mm, participant.unique_id)

    # ── Team & Domain info row ────────────────────────────────────────────────
    info_y = id_y - 9*mm
    team_name = (participant.team_obj.team_name or "TEAM").upper()
    domain = (participant.team_obj.domain or "").upper()

    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 8)
    c.drawCentredString(W / 2, info_y, f"TEAM: {team_name}")

    c.setFillColor(VIOLET)
    c.setFont('Helvetica', 7)
    c.drawCentredString(W / 2, info_y - 5*mm, f"DOMAIN: {domain}")

    # ── Password ──────────────────────────────────────────────────────────────
    pwd_y = info_y - 11*mm
    c.setFillColor(AMBER)
    c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(W / 2, pwd_y, f"PASS: {participant.password or '----'}")

    # ── Bottom bar ────────────────────────────────────────────────────────────
    c.setFillColor(DEEP_PUR)
    c.rect(0, 0, W, 5.5*mm, fill=1, stroke=0)
    c.setFillColor(CYAN)
    c.rect(0, 5.5*mm, W, 0.5*mm, fill=1, stroke=0)

    c.setFillColor(colors.HexColor('#c4b5fd'))
    c.setFont('Helvetica', 5)
    c.drawCentredString(W / 2, 2*mm, "TECHXORA '26  |  Agni College of Technology  |  techxora26.agnihackathon@gmail.com")

    c.save()
    return output_path
