from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import os
import logging

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ------------------- Configuration -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYER_CSV = os.path.join(BASE_DIR, 'data', 'ipl_players.csv')
FIXTURE_CSV = os.path.join(BASE_DIR, 'data', 'match_fixtures.csv')
TEAM_PLAYERS_CSV = os.path.join(BASE_DIR, 'data', 'players_by_team.csv')

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'ticket_booking.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Set up logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


# ------------------- Database Models -------------------
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, nullable=False)
    seat_no = db.Column(db.String(10), nullable=False)
    customer_name = db.Column(db.String(100))
    customer_email = db.Column(db.String(100))
    status = db.Column(db.String(10), default='booked')

    __table_args__ = (
        db.UniqueConstraint('match_id', 'seat_no', name='unique_match_seat'),
    )


# ------------------- Helper Functions -------------------
def load_player_data():
    """Load player data from CSV file"""
    df = pd.read_csv(PLAYER_CSV)
    df.dropna(subset=['player_name', 'team'], inplace=True)
    df.fillna('', inplace=True)
    players = df.to_dict('records')
    for player in players:
        image_path = os.path.join(BASE_DIR, 'static', 'images', player.get('image_url', ''))
        player['image_exists'] = os.path.exists(image_path)
    return players


def load_match_fixtures():
    """Load match fixtures from CSV file"""
    df = pd.read_csv(FIXTURE_CSV)
    return df.to_dict('records')


def load_players_by_team():
    """Load players grouped by team from CSV file"""
    df = pd.read_csv(TEAM_PLAYERS_CSV)
    df.dropna(subset=['team', 'player'], inplace=True)
    players_by_team = {}
    for _, row in df.iterrows():
        team = row['team']
        player = row['player']
        if team not in players_by_team:
            players_by_team[team] = []
        players_by_team[team].append(player)
    return players_by_team


def get_zoned_layout(seat_count):
    """Generate seat layout with different zones"""
    premium_seats = [f"P-{i}" for i in range(1, 101)]
    standard_seats = [f"S-{i}" for i in range(1, 201)]
    economy_seats = [f"E-{i}" for i in range(1, 251)]
    return {
        'premium': premium_seats,
        'standard': standard_seats,
        'economy': economy_seats
    }


# ------------------- Routes -------------------
@app.route('/')
def index():
    """Home page showing players and fixtures"""
    players = load_player_data()
    fixtures = load_match_fixtures()
    return render_template('home.html', players=players, fixtures=fixtures)


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@app.route('/team/<team_name>')
def team_players(team_name):
    """Show players for a specific team"""
    players = [p for p in load_player_data() if
               isinstance(p.get('team'), str) and p['team'].lower() == team_name.lower()]
    return render_template('team.html', players=players, selected_team=team_name.upper())


@app.route('/match_fixtures')
def match_fixtures():
    """Show all match fixtures"""
    fixtures = load_match_fixtures()
    return render_template('match_fixture.html', fixtures=fixtures)


@app.route('/match/<int:match_id>')
def match_details(match_id):
    """Show details for a specific match"""
    fixtures = load_match_fixtures()
    match = next((m for m in fixtures if m['match_id'] == match_id), None)
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('match_fixtures'))

    players_by_team = load_players_by_team()
    team_1_players = players_by_team.get(match['team_1'], [])[:11]
    team_2_players = players_by_team.get(match['team_2'], [])[:11]

    return render_template('match_details.html', match=match,
                           team_1_players=team_1_players,
                           team_2_players=team_2_players)


@app.route('/match/<int:match_id>/book', methods=['GET', 'POST'])
def book_tickets(match_id):
    """Handle ticket booking for a match"""
    try:
        fixtures = load_match_fixtures()
        match = next((m for m in fixtures if m['match_id'] == match_id), None)
        if not match:
            flash('Match not found', 'error')
            return redirect(url_for('match_fixtures'))

        seat_layout = get_zoned_layout(0)  # We're using predefined zones
        booked_seats = [t.seat_no for t in Ticket.query.filter_by(match_id=match_id).all()]

        if request.method == 'POST':
            selected_seats = request.form.getlist('seats')
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            selected_stand = request.form.get('selected_stand', '')

            # Validate input
            if not selected_seats:
                flash('Please select at least one seat', 'error')
                return redirect(url_for('book_tickets', match_id=match_id))

            if not name or not email:
                flash('Please provide your name and email', 'error')
                return redirect(url_for('book_tickets', match_id=match_id))

            # Validate seats belong to selected stand
            valid_seats = []
            for seat in selected_seats:
                if (selected_stand == 'premium' and seat.startswith('P-')) or \
                        (selected_stand == 'standard' and seat.startswith('S-')) or \
                        (selected_stand == 'economy' and seat.startswith('E-')):
                    if seat not in booked_seats:
                        valid_seats.append(seat)
                else:
                    flash(f'Invalid seat selection: {seat}', 'error')
                    return redirect(url_for('book_tickets', match_id=match_id))

            # Book valid seats
            for seat in valid_seats:
                ticket = Ticket(
                    match_id=match_id,
                    seat_no=seat,
                    customer_name=name,
                    customer_email=email
                )
                db.session.add(ticket)

            db.session.commit()
            flash(f'Successfully booked {len(valid_seats)} seat(s)!', 'success')
            return redirect(url_for('book_tickets', match_id=match_id))

        return render_template('ticket_booking.html',
                               match=match,
                               premium_seats=seat_layout['premium'],
                               standard_seats=seat_layout['standard'],
                               economy_seats=seat_layout['economy'],
                               booked=booked_seats)

    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error booking tickets: {str(e)}')
        flash('An error occurred while processing your booking. Please try again.', 'error')
        return redirect(url_for('book_tickets', match_id=match_id))


@app.route('/privacy_policy')
def privacy_policy():
    """Privacy policy page"""
    return render_template('privacy_policy.html')


@app.route('/terms_of_service')
def terms_of_service():
    """Terms of service page"""
    return render_template('terms_of_service.html')


@app.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')


@app.route('/send-message', methods=['POST'])
def send_message():
    """Handle contact form submission"""
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    message = request.form.get('message', '').strip()

    if not name or not email or not message:
        flash('Please fill all fields', 'error')
        return redirect(url_for('contact'))

    # In a real application, you would send an email here
    app.logger.info(f'New message from {name} ({email}): {message}')
    flash('Thank you for your message. We will get back to you shortly.', 'success')
    return redirect(url_for('contact'))


# ------------------- Application Startup -------------------
if __name__ == '__main__':
    with app.app_context():
        # Create database tables
        db.create_all()

        # Check if database file was created
        db_path = os.path.join(BASE_DIR, 'ticket_booking.db')
        if os.path.exists(db_path):
            app.logger.info(f"Database created at {db_path}")
        else:
            app.logger.error(f"Failed to create database at {db_path}")

    app.run(debug=True)