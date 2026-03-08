import random
from app import create_app
from models import db, Participant

app = create_app()
with app.app_context():
    participants = Participant.query.filter(Participant.password == None).all()
    print(f"Updating {len(participants)} participants...")
    for p in participants:
        p.password = str(random.randint(1000, 9999))
    db.session.commit()
    print("Done.")
