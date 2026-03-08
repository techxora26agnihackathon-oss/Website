from app import create_app
from models import db, Participant

app = create_app()
app.config['TESTING'] = True

with app.app_context():
    with app.test_client() as client:
        # Get a participant to test with
        p = Participant.query.first()
        if p:
            print(f"Testing scan with participant: {p.unique_id}")
            # Mock the session to be a volunteer
            with client.session_transaction() as sess:
                sess['role'] = 'volunteer'
            
            res = client.post('/volunteer/scan', data={'uid': p.unique_id})
            print("Status Code:", res.status_code)
            print("JSON Response:", res.json)
        else:
            print("No participants in DB to test.")
