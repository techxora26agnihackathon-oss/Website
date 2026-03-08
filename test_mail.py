from app import create_app
from models import db, Team, Participant

app = create_app()
app.config['TESTING'] = True

with app.app_context():
    # Get a team to test with
    team = Team.query.first()
    if team:
        participants = team.members.all()
        print(f"Testing emails for team: {team.team_name}")
        
        # 1. Test registration received email
        from routes.mail_utils import send_registration_received_email, send_team_confirmation_email
        print("Sending registration received email...")
        send_registration_received_email(team, participants)
        
        # 2. Test payment verification email (confirmation)
        print("Sending payment confirmation email...")
        from routes.pdf_utils import generate_id_card
        import os
        cards_dir = os.path.join(app.static_folder, 'id_cards')
        os.makedirs(cards_dir, exist_ok=True)
        
        pdf_paths = []
        for p in participants:
            pdf_path = os.path.join(cards_dir, f"{p.unique_id}.pdf")
            print(f"Regenerating ID card for {p.name} at {pdf_path}")
            # Ensure p._qr_abs or similar is accessible if needed, or rely on generate_id_card
            # Note: models.py Participant doesn't have _qr_abs property, but path is in qr_path
            # Let's add a quick helper to participant in models.py if needed, 
            # but generate_id_card uses current_app logic or static folder.
            generate_id_card(p, pdf_path)
            pdf_paths.append(pdf_path)
            
        send_team_confirmation_email(team, participants, pdf_paths)
    else:
        print("No teams in DB to test.")
