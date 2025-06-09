import pandas as pd
import csv
from datetime import datetime
import os
import requests
from io import StringIO
import re

def clean_phone_number(phone):
    if pd.isna(phone):
        return None
    
    # Convert to string and handle multiple numbers
    phone_str = str(phone).strip()
    
    # If it contains an email, return None
    if '@' in phone_str:
        return None
        
    # Split by common separators and take the first number
    numbers = re.split(r'[,/]', phone_str)
    phone_str = numbers[0].strip()
    
    # Remove all non-digit characters
    cleaned = re.sub(r'[^0-9]', '', phone_str)
    
    # Remove country code if present
    if cleaned.startswith('91') and len(cleaned) > 10:
        cleaned = cleaned[2:]
    
    # Remove leading zero if present
    if cleaned.startswith('0') and len(cleaned) > 10:
        cleaned = cleaned[1:]
    
    # Ensure it's a 10-digit number
    if len(cleaned) == 10:
        return cleaned
    return None

def generate_player_id(date_of_birth):
    # Convert date string to datetime object
    dob = datetime.strptime(date_of_birth, '%d-%m-%Y')
    # Get current year's last 2 digits
    current_year = datetime.now().year % 100
    # Get player's birth year last 2 digits
    birth_year = dob.year % 100
    # Generate a unique number (you might want to make this more sophisticated)
    unique_num = datetime.now().strftime('%H%M%S')
    # Format: YY-YY-XXXX
    return f"{current_year}-{birth_year}-{unique_num}"

def clean_column_name(col_name):
    # Remove metadata after the pipe character
    return col_name.split('|')[0]

def import_players_from_sheet():
    # Read the Google Sheet
    sheet_url = "https://docs.google.com/spreadsheets/d/1sX-zSmpArLYjPFEPRD2Sn5eKmwoPFcw38udUu3Ny2aI/edit?usp=sharing"
    sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        print(f"Attempting to access Google Sheet at: {url}")
        # Read the CSV data
        response = requests.get(url)
        print(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error accessing Google Sheet: {response.status_code}")
            print("Please make sure the sheet is publicly accessible or you have the correct permissions.")
            return False
            
        df = pd.read_csv(StringIO(response.text))
        print(f"Successfully read CSV data. Original columns: {df.columns.tolist()}")
        
        # Clean column names
        df.columns = [clean_column_name(col) for col in df.columns]
        print(f"Cleaned columns: {df.columns.tolist()}")
        
        # Remove empty rows
        df = df.dropna(how='all')
        print(f"Removed empty rows. Remaining entries: {len(df)}")
        
        # Clean phone numbers
        print("\nCleaning Phone Numbers:")
        original_phones = df['Phone'].copy()
        df['Phone'] = df['Phone'].apply(clean_phone_number)
        
        # Report fixed numbers
        fixed_count = 0
        for idx, (original, fixed) in enumerate(zip(original_phones, df['Phone'])):
            if pd.isna(original) or pd.isna(fixed) or str(original).strip() != str(fixed).strip():
                print(f"\nFixed phone number for {df.iloc[idx]['Name']}:")
                print(f"Original: {original}")
                print(f"Fixed: {fixed}")
                fixed_count += 1
        
        # Handle duplicates
        print("\nChecking for Duplicate Entries...")
        duplicates = df[df.duplicated(subset=['Name', 'Date of Birth'], keep=False)]
        if len(duplicates) > 0:
            print(f"\nFound {len(duplicates)} entries with same name and DOB:")
            for (name, dob), group in duplicates.groupby(['Name', 'Date of Birth']):
                print(f"\nPlayer: {name} (DOB: {dob})")
                for _, row in group.iterrows():
                    print(f"- Phone: {row['Phone']}")
                    print(f"  Gender: {row['Gender']}")
                    print(f"  District: {row['TT District']}")
            
            # Remove duplicates keeping the first occurrence
            original_count = len(df)
            df = df.drop_duplicates(subset=['Name', 'Date of Birth'], keep='first')
            removed_count = original_count - len(df)
            print(f"\nRemoved {removed_count} duplicate entries")
        
        # Read existing players to get the last ID
        existing_players = []
        try:
            with open('players_data.csv', 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                existing_players = list(reader)
        except FileNotFoundError:
            pass

        # Prepare new players data
        new_players = []
        for _, row in df.iterrows():
            # Skip empty rows
            if pd.isna(row['Name']) or str(row['Name']).strip() == '':
                continue

            try:
                # Skip invalid entries
                if pd.isna(row['Name']) or str(row['Name']).strip() == '' or str(row['Name']).strip() == '.':
                    continue
                    
                if pd.isna(row['Date of Birth']):
                    print(f"Skipping {row['Name']} - Missing date of birth")
                    continue
                    
                # Generate player ID
                player_id = generate_player_id(row['Date of Birth'])

                # Create player record
                player = {
                    'Player ID': player_id,
                    'Name': str(row['Name']),
                    'Date of Birth': datetime.strptime(row['Date of Birth'], '%d-%m-%Y').strftime('%Y-%m-%d'),
                    'Gender': str(row['Gender']),
                    'Phone Number': str(row['Phone']) if not pd.isna(row['Phone']) else '',
                    'Email ID': str(row['Email Address']) if not pd.isna(row['Email Address']) else '',
                    'State': 'Delhi',  # Setting Delhi as the state for all players
                    'District': str(row['TT District']) if not pd.isna(row['TT District']) else '',
                    'School/Institution': str(row['School/Institution']) if not pd.isna(row['School/Institution']) else '',
                    'Academy': '',  # Not in sheet
                    'Address': str(row['Home Address']) if not pd.isna(row['Home Address']) else '',
                    'TTFI ID': str(row['TTFI ID']) if not pd.isna(row['TTFI ID']) else '',
                    'Official State ID': '',  # Will be generated if state registration is done
                    'Photo Path': str(row['Upload Photo']) if not pd.isna(row['Upload Photo']) else '',
                    'Birth Certificate Path': str(row['Upload Date of Birth Certificate']) if not pd.isna(row['Upload Date of Birth Certificate']) else '',
                    'Address Proof Path': str(row['Upload Address Proof']) if not pd.isna(row['Upload Address Proof']) else '',
                    'Account Holder Name': '',  # Not in sheet
                    'Account Number': '',  # Not in sheet
                    'Bank Name': '',  # Not in sheet
                    'Branch Name': '',  # Not in sheet
                    'IFSC Code': '',  # Not in sheet
                    'UPI ID': '',  # Not in sheet
                    'Payment Snapshot Path': str(row['Upload Payment Snapshot']) if not pd.isna(row['Upload Payment Snapshot']) else '',
                    'Transaction ID': str(row['Payment Transaction ID']) if not pd.isna(row['Payment Transaction ID']) else '',
                    'State Registration': 'Yes',  # Setting to Yes for all entries
                    'Is State Transfer': 'Yes' if str(row['Is Transfer Case']) == 'Yes' else 'No',
                    'NOC Certificate Path': str(row['Upload NOC (For Transfer Cases)']) if not pd.isna(row['Upload NOC (For Transfer Cases)']) else ''
                }
                new_players.append(player)
            except Exception as e:
                print(f"Error processing row for player {row.get('Name', 'Unknown')}: {str(e)}")
                continue

        # Combine existing and new players
        all_players = existing_players + new_players

        # Write to CSV
        fieldnames = [
            'Player ID', 'Name', 'Date of Birth', 'Gender', 'Phone Number', 'Email ID',
            'State', 'District', 'School/Institution', 'Academy', 'Address', 'TTFI ID',
            'Official State ID', 'Photo Path', 'Birth Certificate Path', 'Address Proof Path',
            'Account Holder Name', 'Account Number', 'Bank Name', 'Branch Name', 'IFSC Code',
            'UPI ID', 'Payment Snapshot Path', 'Transaction ID', 'State Registration',
            'Is State Transfer', 'NOC Certificate Path'
        ]

        with open('players_data.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_players)

        print(f"\n=== Final Summary Report ===")
        print(f"1. Total entries imported: {len(new_players)}")
        print(f"2. Phone numbers fixed: {fixed_count}")
        print(f"3. Duplicate entries removed: {removed_count if 'removed_count' in locals() else 0}")
        return True

    except Exception as e:
        print(f"Error importing players: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    import_players_from_sheet() 