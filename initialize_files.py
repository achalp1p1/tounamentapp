import csv
import os

def initialize_csv_files():
    # Define file paths and their headers
    files = {
        'tournaments.csv': [
            'Tournament Id', 'Tournament Name', 'Categories', 'Venue',
            'Start Date', 'End Date', 'Last Registration Date', 'Total Prize',
            'General Information', 'Tournament Logo Link', 'Status'
        ],
        'tournament_categories.csv': [
            'Tournament Id', 'Tournament Name', 'Category', 'Fee',
            'First Prize', 'Second Prize', 'Third Prize', 'Format'
        ],
        'tournament_registrations.csv': [
            'Tournament Id', 'Player ID', 'Registration Date',
            'Category', 'Status', 'Seeding'
        ],
        'players_data.csv': [
            'Player ID', 'Name', 'Date of Birth', 'Gender',
            'Phone Number', 'Email ID', 'State', 'School/Institution',
            'Academy', 'Address', 'DSTTA ID', 'UPI ID'
        ]
    }

    # Create each file if it doesn't exist
    for filename, headers in files.items():
        if not os.path.exists(filename):
            print(f"Creating {filename}...")
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(headers)
            print(f"Created {filename} successfully!")
        else:
            print(f"{filename} already exists.")

if __name__ == '__main__':
    initialize_csv_files() 