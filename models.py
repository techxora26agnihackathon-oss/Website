from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Domain short-code mapping
DOMAIN_CODES = {
    'Climate & Sustainability Tech': 'CS',
    'HealthTech': 'HT',
    'EdTech': 'ET',
    'Cybersecurity': 'CY',
    'Student Innovation': 'SI',
}


class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    team_number = db.Column(db.Integer, unique=True, nullable=False)  # 1, 2, 3 ...
    team_name = db.Column(db.String(150), nullable=False)
    domain = db.Column(db.String(100), nullable=False)       # Full name
    domain_short = db.Column(db.String(5), nullable=False)   # AI, WD, IoT …
    college = db.Column(db.String(200), nullable=True)
    payment_status = db.Column(db.String(20), default='pending')  # pending / verified
    problem_id = db.Column(db.Integer, db.ForeignKey('problem_statements.id'), nullable=True)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    members = db.relationship('Participant', backref='team_obj', lazy='dynamic',
                              cascade='all, delete-orphan')
    payment = db.relationship('Payment', backref='team_obj', uselist=False,
                              cascade='all, delete-orphan')
    problem_statement = db.relationship('ProblemStatement', backref='teams_selected_obj')

    @property
    def team_id_str(self):
        return f"T{self.team_number}"

    def to_dict(self):
        return {
            'id': self.id,
            'team_number': self.team_number,
            'team_id_str': self.team_id_str,
            'team_name': self.team_name,
            'domain': self.domain,
            'domain_short': self.domain_short,
            'college': self.college or '',
            'payment_status': self.payment_status,
            'problem_id': self.problem_id,
            'problem_title': self.problem_statement.problem_title if self.problem_statement else 'Not Selected',
            'registered_at': self.registered_at.strftime('%Y-%m-%d %H:%M'),
            'member_count': self.members.count(),
        }


class Participant(db.Model):
    __tablename__ = 'participants'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)

    # New structured ID: HF-AI-T1-01
    unique_id = db.Column(db.String(25), unique=True, nullable=False)
    member_number = db.Column(db.Integer, nullable=False)  # position within team: 1, 2 …

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    qr_path = db.Column(db.String(200), nullable=True)

    is_inside = db.Column(db.Boolean, default=False)
    food_issued = db.Column(db.Boolean, default=False)
    food_count = db.Column(db.Integer, default=0)
    password = db.Column(db.String(10), nullable=True)  # 4-digit code
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    logs = db.relationship('Log', backref='participant', lazy='dynamic',
                           cascade='all, delete-orphan')

    def get_time_inside(self):
        """Return total minutes inside."""
        total = 0
        entry_time = None
        for log in self.logs.order_by(Log.timestamp).all():
            if log.action == 'entry':
                entry_time = log.timestamp
            elif log.action == 'exit' and entry_time:
                delta = (log.timestamp - entry_time).total_seconds() / 60
                total += delta
                entry_time = None
        if entry_time and self.is_inside:
            delta = (datetime.utcnow() - entry_time).total_seconds() / 60
            total += delta
        return round(total, 1)

    def get_current_break_minutes(self):
        """If outside, return minutes since last exit."""
        if self.is_inside:
            return 0
        last_exit = self.logs.filter_by(action='exit').order_by(Log.timestamp.desc()).first()
        if last_exit:
            return round((datetime.utcnow() - last_exit.timestamp).total_seconds() / 60, 1)
    @property
    def _qr_abs(self):
        """Returns absolute path to QR code on disk."""
        if not self.qr_path:
            return None
        import os
        from flask import current_app
        return os.path.join(current_app.static_folder, self.qr_path)

    def to_dict(self):
        team = self.team_obj
        return {
            'id': self.id,
            'unique_id': self.unique_id,
            'member_number': self.member_number,
            'team_id': self.team_id,
            'team_name': team.team_name if team else '',
            'team_number': team.team_number if team else '',
            'domain': team.domain if team else '',
            'domain_short': team.domain_short if team else '',
            'college': team.college if team else '',
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'is_inside': self.is_inside,
            'food_issued': self.food_issued,
            'food_count': self.food_count,
            'password': self.password or '',
            'registered_at': self.registered_at.strftime('%Y-%m-%d %H:%M'),
            'qr_path': self.qr_path or '',
            'break_minutes': self.get_current_break_minutes(),
            'time_inside': self.get_time_inside(),
        }


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    transaction_id = db.Column(db.String(100), nullable=False)
    proof_image_path = db.Column(db.String(300), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending / verified
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        team = self.team_obj
        return {
            'id': self.id,
            'team_id': self.team_id,
            'team_name': team.team_name if team else '',
            'transaction_id': self.transaction_id,
            'proof_image_path': self.proof_image_path or '',
            'status': self.status,
            'submitted_at': self.submitted_at.strftime('%Y-%m-%d %H:%M'),
        }


class Log(db.Model):
    __tablename__ = 'logs'

    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=True)
    action = db.Column(db.String(30), nullable=False)  # entry, exit, food, system
    note = db.Column(db.String(300), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'participant_id': self.participant_id,
            'participant_name': self.participant.name if self.participant else 'System',
            'participant_uid': self.participant.unique_id if self.participant else '-',
            'action': self.action,
            'note': self.note or '',
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        }


class Announcement(db.Model):
    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    role_target = db.Column(db.String(20), default='all')  # all, volunteer, participant
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'role_target': self.role_target,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
        }


class ProblemStatement(db.Model):
    __tablename__ = 'problem_statements'

    id = db.Column(db.Integer, primary_key=True)
    problem_title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    max_teams = db.Column(db.Integer, default=7)
    teams_selected = db.Column(db.Integer, default=0)
    domain = db.Column(db.String(100), nullable=True)

    @property
    def remaining_slots(self):
        return max(0, self.max_teams - self.teams_selected)

    def to_dict(self):
        return {
            'id': self.id,
            'problem_title': self.problem_title,
            'description': self.description,
            'max_teams': self.max_teams,
            'teams_selected': self.teams_selected,
            'remaining_slots': self.remaining_slots,
            'domain': self.domain,
        }
