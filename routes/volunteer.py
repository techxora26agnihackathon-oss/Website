from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from models import db, Participant, Log, Announcement

volunteer_bp = Blueprint('volunteer', __name__)


def volunteer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') not in ('admin', 'volunteer'):
            flash('Volunteer access required.', 'error')
            return redirect(url_for('auth.login', role='volunteer'))
        return f(*args, **kwargs)
    return decorated


@volunteer_bp.route('/')
@volunteer_required
def dashboard():
    announcements = Announcement.query.filter(
        Announcement.role_target.in_(['all', 'volunteer'])
    ).order_by(Announcement.created_at.desc()).all()
    return render_template('volunteer/dashboard.html', announcements=announcements)


# ─── Smart Entry/Exit Toggle ───────────────────────────────────────────────────
@volunteer_bp.route('/scan', methods=['POST'])
@volunteer_required
def scan():
    """
    Auto-toggle: if participant is outside → mark entry.
                 if participant is inside  → mark exit.
    """
    uid = request.form.get('uid', '').strip().upper()
    p = Participant.query.filter_by(unique_id=uid).first()
    if not p:
        return jsonify({'success': False, 'message': f'ID {uid} not found.'}), 404

    if p.is_inside:
        # Mark exit
        p.is_inside = False
        action = 'exit'
        msg = f'{p.name} ({p.unique_id}) exited the venue.'
    else:
        # Mark entry
        p.is_inside = True
        action = 'entry'
        msg = f'{p.name} ({p.unique_id}) entered the venue.'

    log = Log(participant_id=p.id, action=action, note=msg)
    db.session.add(log)
    db.session.commit()

    team = p.team_obj
    members = []
    if team:
        members = [m.to_dict() for m in team.members.order_by(Participant.member_number).all()]

    return jsonify({
        'success': True,
        'action': action,
        'message': msg,
        'participant': p.to_dict(),
        'team_name': team.team_name if team else 'Individual',
        'domain': team.domain if team else 'N/A',
        'team_members': members
    })


# ─── Food Scan ─────────────────────────────────────────────────────────────────
@volunteer_bp.route('/food-scan', methods=['POST'])
@volunteer_required
def food_scan():
    uid = request.form.get('uid', '').strip().upper()
    p = Participant.query.filter_by(unique_id=uid).first()
    if not p:
        return jsonify({'success': False, 'message': f'ID {uid} not found.'}), 404
    if p.food_issued:
        return jsonify({'success': False,
                        'message': f'{p.name} has already collected food (×{p.food_count}).'}), 400
    p.food_issued = True
    p.food_count += 1
    msg = f'Food token #{p.food_count} issued to {p.name} ({p.unique_id}).'
    log = Log(participant_id=p.id, action='food', note=msg)
    db.session.add(log)
    db.session.commit()
    team = p.team_obj
    members = []
    if team:
        members = [m.to_dict() for m in team.members.order_by(Participant.member_number).all()]

    return jsonify({
        'success': True,
        'action': 'food',
        'message': msg,
        'participant': p.to_dict(),
        'team_name': team.team_name if team else 'Individual',
        'domain': team.domain if team else 'N/A',
        'team_members': members
    })
