from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, flash
from models import Participant, Log, Announcement

participant_bp = Blueprint('participant', __name__)


def participant_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'participant':
            flash('Please log in as a participant.', 'error')
            return redirect(url_for('auth.login', role='participant'))
        return f(*args, **kwargs)
    return decorated


@participant_bp.route('/')
@participant_required
def dashboard():
    p = Participant.query.get(session['participant_id'])
    if not p:
        session.clear()
        return redirect(url_for('auth.index'))

    logs = p.logs.order_by(Log.timestamp).all()
    announcements = Announcement.query.filter(
        Announcement.role_target.in_(['all', 'participant'])
    ).order_by(Announcement.created_at.desc()).all()

    # Build timeline data for Zoho People-style view
    # Group logs by date; each date gets a list of events
    from collections import defaultdict
    from datetime import timezone

    timeline = defaultdict(list)
    for log in logs:
        if log.action not in ['entry', 'exit', 'food']:
            continue
        date_key = log.timestamp.strftime('%Y-%m-%d')
        timeline[date_key].append({
            'action': log.action,
            'time': log.timestamp.strftime('%H:%M'),
            'timestamp': log.timestamp,
            'note': log.note or '',
        })

    # Compute hours per day
    day_summary = {}
    for date_key, events in timeline.items():
        total_min = 0
        entry_time = None
        for ev in sorted(events, key=lambda x: x['timestamp']):
            if ev['action'] == 'entry':
                entry_time = ev['timestamp']
            elif ev['action'] == 'exit' and entry_time:
                total_min += (ev['timestamp'] - entry_time).total_seconds() / 60
                entry_time = None
        hrs = int(total_min // 60)
        mins = int(total_min % 60)
        day_summary[date_key] = f"{hrs:02d}:{mins:02d}"

    timeline = dict(sorted(timeline.items()))

    return render_template('participant/dashboard.html',
                           participant=p,
                           logs=logs,
                           timeline=timeline,
                           day_summary=day_summary,
                           announcements=announcements)


@participant_bp.route('/team')
@participant_required
def team_view():
    p = Participant.query.get(session['participant_id'])
    if not p or not p.team_obj:
        return redirect(url_for('participant.dashboard'))
    return render_template('participant/team.html', team=p.team_obj)
