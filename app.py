from flask import Flask, render_template, request, redirect, url_for, session
import csv
import os
import base64
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Define the CSV file path
CSV_FILE = 'players_data.csv'
TOURNAMENTS_CSV = 'tournaments.csv'

# Add this if not already present
app.secret_key = 'your_secret_key_here'  # Replace with a secure secret key

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'logo')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_image_base64():
    image_path = os.path.join('static', 'tt_facility.jpg')
    try:
        with open(image_path, 'rb') as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{image_data}"
    except Exception as e:
        print(f"Error reading image: {e}")
        return None

# Create CSV file if it doesn't exist
def initialize_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Player Name', 'DOB', 'Category', 'Academy', 'Seeding'])

# Initialize CSV file at startup
initialize_csv()

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    # Redirect to login page
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        # Add your authentication logic here
        session['logged_in'] = True
        return redirect(url_for('dashboard'))
    
    image_data = get_image_base64()
    return render_template('login.html', image_data=image_data)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/players', methods=['GET', 'POST'])
def player_registration():
    if request.method == 'POST':
        try:
            player_details = {
                'Player Name': request.form['player_name'],
                'DOB': request.form['date_of_birth'],
                'Category': request.form['category'],
                'Academy': request.form['academy']
            }
            
            file_exists = os.path.exists(CSV_FILE)
            file_empty = file_exists and os.path.getsize(CSV_FILE) == 0
            
            with open(CSV_FILE, 'a', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=['Player Name', 'DOB', 'Category', 'Academy'])
                if not file_exists or file_empty:
                    writer.writeheader()
                writer.writerow(player_details)
            
            return render_template('registration_success.html', player_details=player_details)
            
        except Exception as e:
            return render_template('players.html', error=str(e))

    return render_template('players.html')

@app.route('/search-players')
def search_players():
    try:
        # Get search parameters
        player_name = request.args.get('player_name', '').strip().lower()
        category = request.args.get('category', '').strip()
        
        # Debug prints
        print(f"Search parameters received - Name: '{player_name}', Category: '{category}'")
        
        # Check if any search was performed
        search_performed = bool(player_name or category)
        
        # Initialize empty list for players
        players = []
        
        # Only proceed with search if the CSV file exists
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'r', newline='') as file:
                reader = csv.DictReader(file)
                all_players = list(reader)
                
                # Debug print
                print(f"Total players in CSV: {len(all_players)}")
                
                # Filter players based on search criteria
                filtered_players = all_players
                
                if player_name:
                    filtered_players = [
                        p for p in filtered_players 
                        if player_name in p['Player Name'].lower()
                    ]
                    print(f"Players after name filter: {len(filtered_players)}")
                
                if category:
                    filtered_players = [
                        p for p in filtered_players 
                        if p['Category'] == category
                    ]
                    print(f"Players after category filter: {len(filtered_players)}")
                
                # Sort players by seeding (convert seeding to integer for proper sorting)
                players = sorted(filtered_players, key=lambda x: int(x['Seeding']))
                
                # Debug print final results
                print(f"Final number of players to display: {len(players)}")
                if players:
                    print("First few players after sorting:")
                    for p in players[:3]:
                        print(f"Seeding {p['Seeding']}: {p['Player Name']}")
        
        return render_template(
            'search_players.html',
            players=players if search_performed else None,
            search_performed=search_performed
        )
        
    except Exception as e:
        print(f"Error during search: {e}")
        return render_template(
            'search_players.html',
            error=f"An error occurred while searching: {str(e)}",
            players=None,
            search_performed=False
        )

@app.route('/update-seeding', methods=['GET'])
def update_seeding():
    try:
        category = request.args.get('category', '').strip()
        search_performed = bool(category)
        players = []
        message = request.args.get('message')
        success = request.args.get('success', 'false') == 'true'

        print(f"Searching for category: {category}")  # Debug print

        if category and os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'r', newline='') as file:
                reader = csv.DictReader(file)
                # Get all players in the selected category
                players = [player for player in reader if player['Category'] == category]
                
                # Sort players by seeding (unseeded players last)
                players.sort(key=lambda x: (
                    int(x.get('Seeding', '999999')) if x.get('Seeding') and x['Seeding'].strip() else 999999,
                    x['Player Name']
                ))
                
                print(f"Found {len(players)} players in category {category}")  # Debug print
                if players:
                    print("Sample player data:", players[0])  # Debug print

        return render_template('update_seeding.html',
                             players=players,
                             search_performed=search_performed,
                             message=message,
                             success=success)

    except Exception as e:
        print(f"Error in update_seeding: {e}")  # Debug print
        return render_template('update_seeding.html',
                             error=str(e),
                             players=None,
                             search_performed=False)

@app.route('/save-seeding', methods=['POST'])
def save_seeding():
    try:
        category = request.form.get('category')
        print(f"Saving seedings for category: {category}")  # Debug print

        # Read all players
        with open(CSV_FILE, 'r', newline='') as file:
            reader = csv.DictReader(file)
            all_players = list(reader)
            fieldnames = reader.fieldnames
            if 'Seeding' not in fieldnames:
                fieldnames.append('Seeding')

        # Get all form data
        form_data = request.form.to_dict()
        print(f"Received form data: {form_data}")  # Debug print

        # Update seedings
        updated_count = 0
        for key, value in form_data.items():
            if key.startswith('seeding_'):
                index = int(key.split('_')[1])
                player_name = request.form.get(f'player_name_{index}')
                
                if player_name:
                    for player in all_players:
                        if (player['Player Name'] == player_name and 
                            player['Category'] == category):
                            player['Seeding'] = value if value.strip() else ''
                            updated_count += 1

        print(f"Updated seeding for {updated_count} players")  # Debug print

        # Write back to CSV
        with open(CSV_FILE, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_players)

        return redirect(url_for('update_seeding',
                              category=category,
                              success='true',
                              message=f"Successfully updated seeding for {updated_count} players"))

    except Exception as e:
        print(f"Error in save_seeding: {e}")  # Debug print
        return redirect(url_for('update_seeding',
                              category=category,
                              success='false',
                              message=f"Error saving seeding: {str(e)}"))

@app.route('/create-draws')
def create_draws():
    return render_template('create_draws.html')

@app.route('/tournament-creation', methods=['GET', 'POST'])
def tournament_creation():
    if request.method == 'POST':
        tournament_logo = request.files.get('tournament_logo')
        logo_filename = None
        if tournament_logo and tournament_logo.filename:
            logo_filename = secure_filename(tournament_logo.filename)
            logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_filename)
            tournament_logo.save(logo_path)
            print(f"Logo saved to: {logo_path}")  # Debug print

        sponsor_logos = request.files.getlist('sponsor_logos')
        sponsor_logo_filenames = []
        for sponsor_logo in sponsor_logos:
            if sponsor_logo and sponsor_logo.filename:
                sponsor_logo_filename = secure_filename(sponsor_logo.filename)
                sponsor_logo_path = os.path.join(app.config['UPLOAD_FOLDER'], sponsor_logo_filename)
                sponsor_logo.save(sponsor_logo_path)
                sponsor_logo_filenames.append(sponsor_logo_filename)
                print(f"Sponsor logo saved to: {sponsor_logo_path}")  # Debug print

        tournament_name = request.form.get('tournament_name')
        categories = request.form.getlist('categories[]')
        fees = request.form.getlist('fees[]')
        venue = request.form.get('venue')
        date = request.form.get('date')
        last_registration_date = request.form.get('last_registration_date')

        # Save to CSV
        file_exists = os.path.isfile(TOURNAMENTS_CSV)
        with open(TOURNAMENTS_CSV, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Tournament Name', 'Categories', 'Fees', 'Venue', 'Date', 'Last Registration Date']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                'Tournament Name': tournament_name,
                'Categories': ', '.join(categories),
                'Fees': ', '.join(fees),
                'Venue': venue,
                'Date': date,
                'Last Registration Date': last_registration_date
            })

        return render_template(
            'tournament_success.html',
            logo_filename=logo_filename,
            tournament_name=tournament_name,
            categories=categories,
            fees=fees,
            venue=venue,
            date=date,
            last_registration_date=last_registration_date,
            sponsor_logo_filenames=sponsor_logo_filenames
        )

    # Calculate default dates
    today = datetime.today().date()
    tournament_date = today + timedelta(days=10)
    last_reg_date = tournament_date - timedelta(days=2)
    return render_template(
        'tournament_creation.html',
        default_tournament_date=tournament_date.strftime('%Y-%m-%d'),
        default_last_reg_date=last_reg_date.strftime('%Y-%m-%d')
    )

if __name__ == '__main__':
    app.run(debug=True)