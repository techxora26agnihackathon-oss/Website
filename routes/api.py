from flask import Blueprint, jsonify, send_file, abort, current_app, make_response
from models import Participant, Log, Announcement, ProblemStatement, DOMAIN_CODES
import io, os

api_bp = Blueprint('api', __name__)


@api_bp.route('/stats')
def stats():
    return jsonify({
        'total': Participant.query.count(),
        'inside': Participant.query.filter_by(is_inside=True).count(),
        'food': Participant.query.filter_by(food_issued=True).count(),
        'events': Log.query.count(),
    })


@api_bp.route('/participants')
def participants():
    ps = Participant.query.order_by(Participant.registered_at.desc()).all()
    return jsonify([p.to_dict() for p in ps])


@api_bp.route('/logs')
def logs():
    ls = Log.query.order_by(Log.timestamp.desc()).limit(100).all()
    return jsonify([l.to_dict() for l in ls])


@api_bp.route('/announcements')
def announcements():
    anns = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return jsonify([a.to_dict() for a in anns])


@api_bp.route('/participants/breaks')
def breaks():
    """Return all participants who are currently outside with their break duration."""
    ps = Participant.query.filter_by(is_inside=False).all()
    result = []
    for p in ps:
        mins = p.get_current_break_minutes() or 0
        result.append({
            **p.to_dict(),
            'break_minutes': mins,
            'alert': mins > 20,
        })
    return jsonify(result)


# ── Problem Statements API ────────────────────────────────────────────────────
@api_bp.route('/problems')
def problems_api():
    """Return all problem statements grouped by domain, with TX-code numbered IDs."""
    all_ps = ProblemStatement.query.order_by(ProblemStatement.domain, ProblemStatement.id).all()
    domains = {}
    counters = {}
    for p in all_ps:
        code = p.domain
        counters[code] = counters.get(code, 0) + 1
        prob_id = f"TX-{code}-{counters[code]:02d}"
        
        # Add a friendly name for the domain if needed, or just use code
        domain_name_map = {
            'CS': 'Climate & Sustainability Tech',
            'HT': 'HealthTech',
            'ET': 'EdTech',
            'CY': 'Cybersecurity',
            'SI': 'Student Innovation'
        }
        
        if code not in domains:
            domains[code] = {'domain': domain_name_map.get(code, code), 'code': code, 'problems': []}
        domains[code]['problems'].append({
            'id': p.id,
            'prob_id': prob_id,
            'title': p.problem_title,
            'description': p.description,
            'remaining_slots': p.remaining_slots,
        })
    return jsonify(list(domains.values()))


# ── Problem Statement PDF Download ────────────────────────────────────────────
@api_bp.route('/problem-pdf/<int:problem_id>')
def download_problem_pdf(problem_id):
    p = ProblemStatement.query.get_or_404(problem_id)
    code = p.domain
    # Count index within domain for the TX-CODE-NN label
    domain_ps = ProblemStatement.query.filter_by(domain=p.domain).order_by(ProblemStatement.id).all()
    idx = next((i + 1 for i, x in enumerate(domain_ps) if x.id == p.id), 1)
    prob_label = f"TX-{code}-{idx:02d}"

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY

        buf = io.BytesIO()
        W, H = A4  # 595.27 x 841.89 pts
        c = rl_canvas.Canvas(buf, pagesize=A4)

        # ── Colors ────────────────────────────────────────────────────────────
        violet  = colors.HexColor('#a78bfa')
        amber   = colors.HexColor('#f59e0b')
        dark_bg = colors.HexColor('#07050f')
        body_c  = colors.HexColor('#1a1a2e')
        muted   = colors.HexColor('#555555')
        light   = colors.HexColor('#999999')
        violet_dark = colors.HexColor('#3b1f6e')

        MARGIN_L = 50
        MARGIN_R = W - 50

        # ── Helper: draw watermark on current page ─────────────────────────────
        hack_logo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'static', 'logos', 'techXora.png'
        )
        def draw_watermark():
            if os.path.exists(hack_logo_path):
                try:
                    wm_size = 400
                    c.saveState()
                    c.setFillAlpha(0.25)
                    c.drawImage(
                        ImageReader(hack_logo_path),
                        (W - wm_size) / 2, (H - wm_size) / 2,
                        width=wm_size, height=wm_size,
                        preserveAspectRatio=True, mask='auto'
                    )
                    c.restoreState()
                except Exception:
                    pass

        draw_watermark()

        # ── College Header Image ───────────────────────────────────────────────
        clg_header_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'static', 'header', 'Clg Header.jpeg'
        )
        header_h = 90
        y = H - 10  # start from near top
        if os.path.exists(clg_header_path):
            try:
                hdr_img = ImageReader(clg_header_path)
                c.drawImage(hdr_img, 0, H - header_h,
                            width=W, height=header_h,
                            preserveAspectRatio=False, mask='auto')
            except Exception:
                # fallback to manual text header
                header_h = 0
        else:
            header_h = 0

        if header_h == 0:
            # ── Fallback manual header ─────────────────────────────────────────
            logo_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'static', 'logos', 'act.png'
            )
            logo_size = 55
            logo_x = (W - logo_size) / 2
            if os.path.exists(logo_path):
                try:
                    c.drawImage(ImageReader(logo_path), logo_x, H - 10 - logo_size,
                                width=logo_size, height=logo_size,
                                preserveAspectRatio=True, mask='auto')
                except Exception:
                    pass
            y_fb = H - 10 - logo_size - 6
            c.setFillColor(body_c); c.setFont('Helvetica-Bold', 14)
            c.drawCentredString(W / 2, y_fb, 'AGNI COLLEGE OF TECHNOLOGY'); y_fb -= 16
            c.setFont('Helvetica', 8); c.setFillColor(muted)
            c.drawCentredString(W / 2, y_fb, '(An Autonomous Institution)'); y_fb -= 14
            c.setFont('Helvetica-Bold', 9); c.setFillColor(muted)
            c.drawCentredString(W / 2, y_fb, 'DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING'); y_fb -= 14
            c.setFont('Helvetica-Bold', 11); c.setFillColor(body_c)
            c.drawCentredString(W / 2, y_fb, "TECHXORA '26"); y_fb -= 6
            y = y_fb
        else:
            y = H - header_h - 5

        # ── Divider ────────────────────────────────────────────────────────────
        c.setStrokeColor(colors.HexColor('#cccccc'))
        c.setLineWidth(0.5)
        c.line(MARGIN_L, y, MARGIN_R, y)
        y -= 40

        # ── TECHXORA header label (small, purple) ──────────────────────────────
        c.setFont('Helvetica-Bold', 26)
        c.setFillColor(violet_dark)
        c.drawString(MARGIN_L, y, "TECHXORA '26 — Problem Statement")
        y -= 35

        # ── Problem ID (big amber) ─────────────────────────────────────────────
        c.setFont('Helvetica-Bold', 22)
        c.setFillColor(amber)
        c.drawString(MARGIN_L, y, prob_label)
        y -= 30

        # ── Problem Title ──────────────────────────────────────────────────────
        c.setFont('Helvetica-Bold', 16)
        c.setFillColor(body_c)
        # Word-wrap title if needed
        title_text = p.problem_title
        c.drawString(MARGIN_L, y, title_text)
        y -= 28

        # ── Domain line ────────────────────────────────────────────────────────
        domain_map = {
            'CS': 'Climate & Sustainability Tech',
            'HT': 'HealthTech',
            'ET': 'EdTech',
            'CY': 'Cybersecurity',
            'SI': 'Student Innovation',
        }
        domain_full = domain_map.get(p.domain, p.domain or '')
        c.setFont('Helvetica', 10)
        c.setFillColor(muted)
        c.drawString(MARGIN_L, y, f"Domain: {domain_full}")
        y -= 32

        # ── "Problem Description" sub-heading (purple) ─────────────────────────
        c.setFont('Helvetica-Bold', 12)
        c.setFillColor(violet_dark)
        c.drawString(MARGIN_L, y, 'Problem Description')
        y -= 22

        # ── Description body (Paragraph for proper wrapping and justification) ──
        style = ParagraphStyle(
            name='Justify',
            fontName='Helvetica',
            fontSize=11,
            leading=19,
            textColor=body_c,
            alignment=TA_JUSTIFY
        )

        texts = (p.description or '').split('\n')
        usable_w = MARGIN_R - MARGIN_L
        
        for text in texts:
            if not text.strip():
                y -= 8
                continue
            
            para = Paragraph(text.strip(), style)
            
            while True:
                w, h = para.wrap(usable_w, y - 60)
                if h <= y - 60:
                    para.drawOn(c, MARGIN_L, y - h)
                    y -= (h + 8)
                    break
                else:
                    split_res = para.split(usable_w, y - 60)
                    if len(split_res) == 2:
                        p1, p2 = split_res
                        w1, h1 = p1.wrap(usable_w, y - 60)
                        p1.drawOn(c, MARGIN_L, y - h1)
                        c.showPage()
                        draw_watermark()
                        y = H - 60
                        para = p2
                    else:
                        c.showPage()
                        draw_watermark()
                        y = H - 60

        y -= 20

        # ── Footer ─────────────────────────────────────────────────────────────
        if y < 60:
            c.showPage()
            y = 60
        c.setStrokeColor(colors.HexColor('#cccccc'))
        c.setLineWidth(0.5)
        c.line(MARGIN_L, y, MARGIN_R, y)
        y -= 14
        c.setFont('Helvetica-Oblique', 8)
        c.setFillColor(light)
        c.drawCentredString(W / 2, y, "TECHXORA '26 | Agni College of Technology")

        c.save()
        buf.seek(0)
        filename = f"{prob_label}_{p.problem_title[:30].replace(' ', '_')}.pdf"
        return send_file(buf, mimetype='application/pdf',
                         as_attachment=True, download_name=filename)

    except ImportError:
        # Fallback: plain text download
        content = f"TECHXORA '26 — Problem Statement\n{'='*50}\n\n"
        content += f"ID: {prob_label}\nTitle: {p.problem_title}\nDomain: {p.domain or ''}\n\n"
        content += f"Description:\n{p.description}\n\n— TECHXORA '26 | Agni College of Technology —"
        buf = io.BytesIO(content.encode('utf-8'))
        buf.seek(0)
        return send_file(buf, mimetype='text/plain',
                         as_attachment=True,
                         download_name=f"{prob_label}.txt")

