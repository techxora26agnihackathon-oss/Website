import os
import random
import csv
import io
from datetime import datetime
from functools import wraps
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, current_app, Response, jsonify)
from models import db, Team, Participant, Payment, Log, Announcement
from qr_utils import generate_qr
from routes.pdf_utils import generate_id_card
from routes.mail_utils import send_team_confirmation_email, send_individual_confirmation_email, test_smtp_connection

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login', role='admin'))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ──────────────────────────────────────────────────────────────────
@admin_bp.route('/')
@admin_required
def dashboard():
    total_participants = Participant.query.count()
    total_teams = Team.query.count()
    
    # Teams Inside (at least one member is_inside=True)
    teams_inside_query = db.session.query(Participant.team_id).filter(Participant.is_inside == True).distinct()
    teams_inside = teams_inside_query.count()
    
    # Teams on Break (total - inside)
    teams_on_break = total_teams - teams_inside
    
    pending_payments = Payment.query.filter_by(status='pending').count()
    participants_list = Participant.query.all()
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                           total=total_participants, 
                           total_teams=total_teams,
                           inside_teams=teams_inside, 
                           break_teams=teams_on_break,
                           pending_payments=pending_payments,
                           participants=participants_list, 
                           announcements=announcements)


# ── Teams View ─────────────────────────────────────────────────────────────────
@admin_bp.route('/teams')
@admin_required
def teams():
    all_teams = Team.query.order_by(Team.team_number).all()
    return render_template('admin/teams.html', teams=all_teams)


@admin_bp.route('/teams/<int:team_id>/delete', methods=['POST'])
@admin_required
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    name = team.team_name
    
    # If payment was not rejected, it was holding a slot. 
    # Return the slot back to the problem statement pool.
    if team.payment_status != 'rejected' and team.problem_statement:
        team.problem_statement.teams_selected = max(0, team.problem_statement.teams_selected - 1)

    db.session.delete(team)
    db.session.commit()
    flash(f'Team "{name}" and all members deleted successfully.', 'success')
    return redirect(url_for('admin.teams'))


# ── Participants ───────────────────────────────────────────────────────────────
@admin_bp.route('/participants')
@admin_required
def participants():
    query = request.args.get('q', '').strip()
    if query:
        ps = Participant.query.join(Team).filter(
            db.or_(
                Participant.name.ilike(f'%{query}%'),
                Participant.unique_id.ilike(f'%{query}%'),
                Participant.email.ilike(f'%{query}%'),
                Team.team_name.ilike(f'%{query}%'),
                Team.domain.ilike(f'%{query}%'),
            )
        ).order_by(Participant.registered_at.desc()).all()
    else:
        ps = Participant.query.order_by(Participant.registered_at.desc()).all()
    return render_template('admin/participants.html', participants=ps, query=query)


@admin_bp.route('/participants/<int:p_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_participant(p_id):
    p = Participant.query.get_or_404(p_id)
    if request.method == 'POST':
        p.name = request.form.get('name', '').strip()
        p.email = request.form.get('email', '').strip().lower()
        p.phone = request.form.get('phone', '').strip()
        
        # Check for email conflict
        conflict = Participant.query.filter(Participant.email == p.email, Participant.id != p.id).first()
        if conflict:
            flash(f'Email {p.email} is already used by another participant.', 'error')
            return render_template('admin/edit_participant.html', p=p)

        db.session.commit()
        flash(f'Participant {p.name} updated successfully.', 'success')
        return redirect(url_for('admin.participants'))

    return render_template('admin/edit_participant.html', p=p)


@admin_bp.route('/participants/<int:p_id>/delete', methods=['POST'])
@admin_required
def delete_participant(p_id):
    p = Participant.query.get_or_404(p_id)
    name = p.name
    uid = p.unique_id
    db.session.delete(p)
    db.session.commit()
    flash(f'Participant {name} ({uid}) deleted.', 'success')
    return redirect(url_for('admin.participants'))


@admin_bp.route('/participants/export')
@admin_required
def export_csv():
    ps = Participant.query.order_by(Participant.registered_at).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Participant ID', 'Name', 'Email', 'Phone',
                     'Team', 'Domain', 'College', 'Inside', 'Food Issued',
                     'Food Count', 'Registered At'])
    for p in ps:
        t = p.team_obj
        writer.writerow([p.unique_id, p.name, p.email, p.phone,
                         t.team_name if t else '', t.domain if t else '',
                         t.college if t else '', p.is_inside, p.food_issued,
                         p.food_count, p.registered_at.strftime('%Y-%m-%d %H:%M')])
    output.seek(0)
    return Response(output, mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=participants.csv'})


# ── Payments ───────────────────────────────────────────────────────────────────
@admin_bp.route('/payments')
@admin_required
def payments():
    all_payments = Payment.query.order_by(Payment.submitted_at.desc()).all()
    return render_template('admin/payments.html', payments=all_payments)


@admin_bp.route('/payments/<int:pay_id>/verify', methods=['POST'])
@admin_required
def verify_payment(pay_id):
    payment = Payment.query.get_or_404(pay_id)
    payment.status = 'verified'
    payment.team_obj.payment_status = 'verified'
    
    # Trigger Email Notification with ID Cards
    team = payment.team_obj
    participants = team.members.all()
    
    qr_dir = os.path.join(current_app.static_folder, 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)
    cards_dir = os.path.join(current_app.static_folder, 'id_cards')
    os.makedirs(cards_dir, exist_ok=True)
    
    pdf_paths = []
    for p in participants:
        # Generate QR code if not exists
        if not p.qr_path:
            p.qr_path = generate_qr(p.unique_id, qr_dir)
            
        pdf_path = os.path.join(cards_dir, f"{p.unique_id}.pdf")
        generate_id_card(p, pdf_path)
        pdf_paths.append(pdf_path)
    
    # ── Send ID-card emails in background threads (with 5-attempt retry)
    send_team_confirmation_email(team, participants, pdf_paths, async_send=True)

    db.session.commit()
    flash(f'Payment for team "{payment.team_obj.team_name}" verified. ID card emails are being sent in the background.', 'success')
    return redirect(url_for('admin.payments'))


@admin_bp.route('/payments/<int:pay_id>/reject', methods=['POST'])
@admin_required
def reject_payment(pay_id):
    payment = Payment.query.get_or_404(pay_id)
    payment.status = 'rejected'
    
    # Optional check: if it was previously not rejected, return the slot
    if payment.team_obj.payment_status != 'rejected':
        payment.team_obj.payment_status = 'rejected'
        if payment.team_obj.problem_statement:
            payment.team_obj.problem_statement.teams_selected = max(0, payment.team_obj.problem_statement.teams_selected - 1)
    
    db.session.commit()
    flash(f'Payment for team "{payment.team_obj.team_name}" marked as rejected. Waitlisted slot released.', 'error')
    return redirect(url_for('admin.payments'))


@admin_bp.route('/payments/<int:pay_id>/resend', methods=['POST'])
@admin_required
def resend_email(pay_id):
    """Manually re-trigger ID-card emails for a verified payment.
    Useful when the background send silently failed due to network issues."""
    payment = Payment.query.get_or_404(pay_id)

    if payment.status != 'verified':
        flash('Can only resend emails for verified payments.', 'error')
        return redirect(url_for('admin.payments'))

    team = payment.team_obj
    participants = team.members.all()

    qr_dir = os.path.join(current_app.static_folder, 'qrcodes')
    cards_dir = os.path.join(current_app.static_folder, 'id_cards')
    os.makedirs(qr_dir, exist_ok=True)
    os.makedirs(cards_dir, exist_ok=True)

    pdf_paths = []
    for p in participants:
        if not p.qr_path:
            p.qr_path = generate_qr(p.unique_id, qr_dir)
        pdf_path = os.path.join(cards_dir, f"{p.unique_id}.pdf")
        generate_id_card(p, pdf_path)
        pdf_paths.append(pdf_path)

    db.session.commit()

    # Re-send in background threads with full retry logic
    send_team_confirmation_email(team, participants, pdf_paths, async_send=True)

    flash(f'Resending ID card emails to all members of "{team.team_name}" in background. Check server logs for delivery status.', 'success')
    return redirect(url_for('admin.payments'))


@admin_bp.route('/test-email')
@admin_required
def test_email():
    """Diagnostic page: checks whether smtp.gmail.com is reachable on ports 465 and 587."""
    from routes.mail_utils import _send_email
    results = test_smtp_connection()

    lines = ['<h2 style="font-family:monospace">SMTP Connectivity Test</h2><pre style="background:#111;color:#0f0;padding:20px;border-radius:8px;font-size:14px">']
    lines.append(f"SMTP User    : {results.get('smtp_user')}")
    lines.append(f"Password Len : {results.get('smtp_pass_len')} chars")
    lines.append(f"Port 465 SSL : {results.get('port_465')}")
    lines.append(f"Port 587 TLS : {results.get('port_587')}")
    lines.append('')
    if 'OK' in results.get('port_465', '') or 'OK' in results.get('port_587', ''):
        lines.append('✅ At least one port is reachable. Emails should work.')
    else:
        lines.append('❌ BOTH ports blocked.')
        lines.append('   → This machine cannot reach smtp.gmail.com')
        lines.append('   → Switch to mobile hotspot OR ask IT to open port 465/587 outbound')
    lines.append('</pre>')
    lines.append('<a href="/admin/payments" style="color:#a78bfa">← Back to Payments</a>')
    return '\n'.join(lines)


@admin_bp.route('/teams/<int:team_id>/add_member', methods=['POST'])
@admin_required
def add_member(team_id):
    team = Team.query.get_or_404(team_id)
    if team.members.count() >= 4:
        flash('Team already has 4 members.', 'error')
        return redirect(url_for('admin.teams'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()

    if not name or not email or not phone:
        flash('All fields are required.', 'error')
        return redirect(url_for('admin.teams'))

    # Check for duplicate email
    existing = Participant.query.filter_by(email=email).first()
    if existing:
        flash(f'Email {email} is already registered.', 'error')
        return redirect(url_for('admin.teams'))

    # Generate UID
    # Pattern: HF-{domain_short}-T{team_number}-{idx:02d}
    next_idx = team.members.count() + 1
    uid = f"TX-{team.domain_short}-T{team.team_number}-{next_idx:02d}"
    
    # Check if this UID exists (edge case if members were deleted/re-indexed)
    while Participant.query.filter_by(unique_id=uid).first():
        next_idx += 1
        uid = f"TX-{team.domain_short}-T{team.team_number}-{next_idx:02d}"

    new_p = Participant(
        team_id=team.id,
        unique_id=uid,
        member_number=next_idx,
        name=name,
        email=email,
        phone=phone,
        password=str(random.randint(1000, 9999))
    )
    db.session.add(new_p)
    
    log = Log(participant_id=None, action='admin', 
              note=f"Admin added {name} ({uid}) to team {team.team_name}")
    db.session.add(log)
    db.session.commit()

    flash(f'Added {name} to team {team.team_name} successfully!', 'success')
    return redirect(url_for('admin.teams'))


# ── Scanner ────────────────────────────────────────────────────────────────────
@admin_bp.route('/scan', methods=['GET', 'POST'])
@admin_required
def scan():
    result = None
    if request.method == 'POST':
        uid = request.form.get('participant_id', '').strip().upper()
        mode = request.form.get('mode', 'entry')
        p = Participant.query.filter_by(unique_id=uid).first()
        if not p:
            flash(f'Participant ID "{uid}" not found.', 'error')
        else:
            if mode == 'entry':
                p.is_inside = True
                action_note = f"{p.name} ({uid}) entered the venue."
            elif mode == 'exit':
                p.is_inside = False
                action_note = f"{p.name} ({uid}) exited the venue."
            elif mode == 'food':
                if p.food_issued:
                    flash(f'{p.name} has already collected their food token.', 'error')
                    result = p
                    return render_template('admin/scanner.html', result=result)
                p.food_issued = True
                p.food_count += 1
                action_note = f"Food token issued to {p.name} ({uid})."
            else:
                action_note = f"Unknown action for {uid}."

            log = Log(participant_id=p.id, action=mode, note=action_note)
            db.session.add(log)
            db.session.commit()
            flash(action_note, 'success')
            result = p

    return render_template('admin/scanner.html', result=result)


# ── Logs ───────────────────────────────────────────────────────────────────────
@admin_bp.route('/logs')
@admin_required
def logs():
    filter_action = request.args.get('filter', 'all')
    q = Log.query.order_by(Log.timestamp.desc())
    if filter_action != 'all':
        q = q.filter_by(action=filter_action)
    all_logs = q.limit(500).all()
    return render_template('admin/logs.html', logs=all_logs, filter_action=filter_action)


@admin_bp.route('/logs/clear', methods=['POST'])
@admin_required
def clear_logs():
    Log.query.filter(Log.action != 'system').delete()
    db.session.add(Log(action='system', note='Logs cleared by admin.'))
    db.session.commit()
    flash('Activity logs cleared.', 'success')
    return redirect(url_for('admin.logs'))


# ── Announcements ──────────────────────────────────────────────────────────────
@admin_bp.route('/announcements', methods=['GET', 'POST'])
@admin_required
def announcements():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        target = request.form.get('role_target', 'all')
        if title and message:
            ann = Announcement(title=title, message=message, role_target=target)
            db.session.add(ann)
            db.session.commit()
            flash('Announcement broadcast!', 'success')
        else:
            flash('Title and message are required.', 'error')
    anns = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('admin/announcements.html', announcements=anns)


@admin_bp.route('/announcements/<int:ann_id>/delete', methods=['POST'])
@admin_required
def delete_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    db.session.delete(ann)
    db.session.commit()
    flash('Announcement deleted.', 'success')
    return redirect(url_for('admin.announcements'))
