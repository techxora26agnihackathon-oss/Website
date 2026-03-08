import os
import random
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, current_app, send_file)
from models import db, Team, Participant, Payment, Log, DOMAIN_CODES, ProblemStatement
from qr_utils import generate_qr
from routes.mail_utils import send_registration_received_email

auth_bp = Blueprint('auth', __name__)


# ── Homepage ──────────────────────────────────────────────────────────────────
@auth_bp.route('/')
def index():
    problems = ProblemStatement.query.all()
    return render_template('index.html', problems=problems)


# ── Register Page ──────────────────────────────────────────────────────────────
@auth_bp.route('/register')
def register_page():
    problems = ProblemStatement.query.all()
    return render_template('register.html', problems=problems)


# ── Step 1: Accept team+member details, store in session ─────────────────────
@auth_bp.route('/register/step1', methods=['POST'])
def register_step1():
    team_name  = request.form.get('team_name', '').strip()
    domain     = request.form.get('domain', '').strip()
    college    = request.form.get('college', '').strip()
    problem_id = request.form.get('problem_id', '').strip()
    names      = request.form.getlist('name[]')
    emails     = request.form.getlist('email[]')
    phones     = request.form.getlist('phone[]')

    # Basic validation
    if not team_name or not domain or not problem_id:
        flash('Team name, domain, and problem statement are required.', 'error')
        return redirect(url_for('auth.register_page'))

    # Filter out completely blank rows
    members = []
    for i in range(len(names)):
        n = names[i].strip() if i < len(names) else ''
        e = emails[i].strip().lower() if i < len(emails) else ''
        ph = phones[i].strip() if i < len(phones) else ''
        if n and e and ph:
            members.append({'name': n, 'email': e, 'phone': ph})

    if not members:
        flash('At least one complete member entry is required.', 'error')
        return redirect(url_for('auth.register_page'))

    if len(members) > 4:
        flash('Maximum 4 members per team.', 'error')
        return redirect(url_for('auth.register_page'))

    # Check for duplicate emails in DB
    all_emails = [m['email'] for m in members]
    from models import Participant as P
    existing = P.query.filter(P.email.in_(all_emails)).first()
    if existing:
        flash(f'Email {existing.email} is already registered.', 'error')
        return redirect(url_for('auth.register_page'))

    # Store in session and redirect to payment page
    session['reg_pending'] = {
        'team_name': team_name,
        'domain': domain,
        'domain_short': DOMAIN_CODES.get(domain, domain[:2].upper()),
        'college': college,
        'problem_id': int(problem_id),
        'members': members,
    }
    return redirect(url_for('auth.payment_page'))


# ── Payment page ──────────────────────────────────────────────────────────────
@auth_bp.route('/register/payment', methods=['GET'])
def payment_page():
    if 'reg_pending' not in session:
        flash('Please complete Step 1 first.', 'error')
        return redirect(url_for('auth.register_page'))
    reg = session['reg_pending']
    num_members = len(reg['members'])
    fee = 300 * num_members
    return render_template('payment.html', reg=reg, fee=fee, per_person=300)


# ── Step 2: Process payment proof, generate IDs, QRs ─────────────────────────
@auth_bp.route('/register/step2', methods=['POST'])
def register_step2():
    if 'reg_pending' not in session:
        flash('Session expired. Please restart registration.', 'error')
        return redirect(url_for('auth.register_page'))

    reg = session.pop('reg_pending')
    transaction_id = request.form.get('transaction_id', '').strip()

    if not transaction_id:
        flash('Transaction ID is required.', 'error')
        session['reg_pending'] = reg
        return redirect(url_for('auth.payment_page'))

    # Handle file upload
    proof_file = request.files.get('payment_proof')
    if not proof_file or proof_file.filename == '':
        flash('Payment proof screenshot is required.', 'error')
        session['reg_pending'] = reg
        return redirect(url_for('auth.payment_page'))

    upload_dir = os.path.join(current_app.static_folder, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(proof_file.filename)[1].lower() or '.png'
    proof_filename = f"pay_{transaction_id}{ext}"
    proof_path = os.path.join(upload_dir, proof_filename)
    proof_file.save(proof_path)
    proof_rel = f"uploads/{proof_filename}"

    # Create Team record
    problem = ProblemStatement.query.get(reg['problem_id'])
    if not problem or problem.remaining_slots <= 0:
        flash('Selected problem statement is now full. Please choose another.', 'error')
        # We don't restore reg_pending here for simplicity, or we could
        return redirect(url_for('auth.register_page'))

    team_number = (db.session.query(db.func.max(Team.team_number)).scalar() or 0) + 1
    team = Team(
        team_number=team_number,
        team_name=reg['team_name'],
        domain=reg['domain'],
        domain_short=reg['domain_short'],
        college=reg['college'],
        problem_id=problem.id,
        payment_status='pending',
    )
    db.session.add(team)
    
    # Increment problem team count
    problem.teams_selected += 1
    db.session.add(problem)
    
    db.session.flush()

    # Create Payment record
    payment = Payment(
        team_id=team.id,
        transaction_id=transaction_id,
        proof_image_path=proof_rel,
        status='pending',
    )
    db.session.add(payment)

    # Create Participant records + QRs
    qr_dir = os.path.join(current_app.static_folder, 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)

    new_participants = []
    for idx, member in enumerate(reg['members'], start=1):
        uid = f"TX-{reg['domain_short']}-T{team_number}-{idx:02d}"
        p = Participant(
            team_id=team.id,
            unique_id=uid,
            member_number=idx,
            name=member['name'],
            email=member['email'],
            phone=member['phone'],
            password=str(random.randint(1000, 9999))
        )
        db.session.add(p)
        db.session.flush()
        p.qr_path = None

        log = Log(participant_id=p.id, action='system',
                  note=f"Registered as {uid} under team {reg['team_name']}")
        db.session.add(log)
        new_participants.append(p)

    db.session.commit()

    # Send Registration Received Email
    send_registration_received_email(team, new_participants)

    flash(f'Team "{reg["team_name"]}" registered! '
          f'Payment pending admin verification. An email has been sent to the team leader.', 'success')
    return render_template('index.html', registration_success=True, team_name=reg['team_name'])


# ── Download PDF ID Card ──────────────────────────────────────────────────────
@auth_bp.route('/id-card/<uid>.pdf')
def download_id_card(uid):
    p = Participant.query.filter_by(unique_id=uid).first_or_404()
    
    from routes.pdf_utils import generate_id_card
    cards_dir = os.path.join(current_app.static_folder, 'id_cards')
    os.makedirs(cards_dir, exist_ok=True)
    pdf_path = os.path.join(cards_dir, f"{uid}.pdf")
    generate_id_card(p, pdf_path)
    return send_file(pdf_path, as_attachment=True,
                     download_name=f"{uid}_IDCard.pdf",
                     mimetype='application/pdf')


# ── Login ─────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    role = request.args.get('role', 'admin')
    if request.method == 'POST':
        role = request.form.get('role', 'admin')
        password = request.form.get('password', '')
        participant_id = request.form.get('participant_id', '').strip().upper()

        if role == 'admin':
            if password == current_app.config['ADMIN_PASSWORD']:
                session['role'] = 'admin'
                session['user'] = 'Admin'
                return redirect(url_for('admin.dashboard'))
            flash('Invalid admin password.', 'error')

        elif role == 'volunteer':
            if password == current_app.config['VOLUNTEER_PASSWORD']:
                session['role'] = 'volunteer'
                session['user'] = 'Volunteer'
                return redirect(url_for('volunteer.dashboard'))
            flash('Invalid volunteer password.', 'error')

        elif role == 'participant':
            p = Participant.query.filter_by(unique_id=participant_id).first()
            if p and p.password == password:
                session['role'] = 'participant'
                session['user'] = p.name
                session['participant_id'] = p.id
                session['participant_uid'] = p.unique_id
                return redirect(url_for('participant.dashboard'))
            flash('Invalid Participant ID or Password.', 'error')

    return render_template('login.html', role=role)


# ── Logout ────────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))
