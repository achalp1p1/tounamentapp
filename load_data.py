import pandas as pd
import mysql.connector
from mysql.connector import Error
from database.database_init import get_db_connection, init_database
import os
from datetime import datetime

def truncate_tables(connection):
    """Truncate all tables in the correct order to respect foreign key constraints"""
    try:
        cursor = connection.cursor()
        
        print("\nTruncating existing data from tables...")
        
        # Disable foreign key checks temporarily
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        
        # Truncate tables in reverse order of dependencies
        tables = [
            'tournament_draw',
            'tournament_registrations',
            'tournament_categories',
            'tournaments',
            'players'
        ]
        
        for table in tables:
            print(f"Truncating table {table}...")
            cursor.execute(f"TRUNCATE TABLE {table}")
            
        # Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        
        connection.commit()
        print("All tables truncated successfully")
        return True
        
    except Error as e:
        print(f"Error truncating tables: {e}")
        return False
    finally:
        if cursor:
            cursor.close()

def load_players_data():
    """Load data from players_data.csv into players table"""
    try:
        print("\nStarting players data loading process...")
        
        # Initialize database first
        print("Initializing database...")
        if not init_database():
            print("Failed to initialize database")
            return False
            
        # Read CSV file
        print("Reading players_data.csv...")
        df = pd.read_csv('players_data.csv')
        print(f"Found {len(df)} players in CSV file")
        
        # Convert numeric fields to strings and clean up data
        print("Cleaning up data...")
        df = df.fillna('')  # Replace NaN with empty string
        
        # Get database connection
        print("Connecting to database...")
        connection = get_db_connection()
        if connection is None:
            print("Failed to connect to database")
            return False
            
        # Truncate existing data
        if not truncate_tables(connection):
            print("Failed to truncate tables")
            return False
            
        cursor = connection.cursor()
        
        # Check table structure
        print("\nVerifying players table structure...")
        cursor.execute("DESCRIBE players")
        columns = cursor.fetchall()
        print("Current table structure:")
        for col in columns:
            print(f"- {col[0]}: {col[1]}")
            
        # Prepare insert query
        insert_query = """
            INSERT INTO players (
                id, name, date_of_birth, gender, phone_number, email, state,
                district, school_institution, academy, address, ttfi_id,
                official_state_id, photo_path, birth_certificate_path,
                address_proof_path, account_holder_name, account_number,
                bank_name, branch_name, ifsc_code, upi_id,
                payment_snapshot_path, transaction_id, state_registration,
                is_state_transfer, noc_certificate_path
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        # Convert data and insert
        print("\nStarting data insertion...")
        successful_inserts = 0
        failed_inserts = 0
        
        # Try first row to debug
        if len(df) > 0:
            print("\nAttempting to insert first row as test:")
            first_row = df.iloc[0]
            print("First row data:")
            for col in df.columns:
                print(f"- {col}: {first_row[col]}")
            
            # Convert date for first row
            test_dob = None
            if first_row['Date of Birth']:
                try:
                    test_dob = datetime.strptime(str(first_row['Date of Birth']), '%Y-%m-%d').date()
                except ValueError as e:
                    print(f"Date conversion error: {e}")
            
            test_data = (
                first_row['Player ID'],
                first_row['Name'],
                test_dob,
                first_row['Gender'],
                str(first_row['Phone Number']).replace('.0', ''),  # Remove decimal if present
                first_row['Email ID'],
                first_row['State'],
                first_row['District'],
                first_row['School/Institution'],
                first_row['Academy'],
                first_row['Address'],
                str(first_row['TTFI ID']).replace('.0', ''),  # Remove decimal if present
                first_row['Official State ID'],
                first_row['Photo Path'],
                first_row['Birth Certificate Path'],
                first_row['Address Proof Path'],
                first_row['Account Holder Name'],
                first_row['Account Number'],
                first_row['Bank Name'],
                first_row['Branch Name'],
                first_row['IFSC Code'],
                first_row['UPI ID'],
                first_row['Payment Snapshot Path'],
                first_row['Transaction ID'],
                first_row['State Registration'],
                first_row['Is State Transfer'],
                first_row['NOC Certificate Path']
            )
            
            try:
                print("\nExecuting test insert...")
                cursor.execute(insert_query, test_data)
                print("Test insert successful!")
            except Error as e:
                print(f"\nTest insert failed with error: {e}")
                print("Error details:")
                print(f"- Error code: {e.errno}")
                print(f"- Error message: {e.msg}")
                print(f"- SQL state: {e.sqlstate}")
                return False
        
        # If test insert successful, proceed with rest of data
        print("\nProceeding with remaining data...")
        for _, row in df.iterrows():
            # Skip first row as it was already inserted
            if row['Player ID'] == df.iloc[0]['Player ID']:
                continue
                
            # Convert date string to datetime object if not null
            dob = None
            if row['Date of Birth']:
                try:
                    dob = datetime.strptime(str(row['Date of Birth']), '%Y-%m-%d').date()
                except ValueError:
                    print(f"Invalid date format for player {row['Player ID']}: {row['Date of Birth']}")
                    failed_inserts += 1
                    continue
            
            data_tuple = (
                row['Player ID'],
                row['Name'],
                dob,
                row['Gender'],
                str(row['Phone Number']).replace('.0', ''),  # Remove decimal if present
                row['Email ID'],
                row['State'],
                row['District'],
                row['School/Institution'],
                row['Academy'],
                row['Address'],
                str(row['TTFI ID']).replace('.0', ''),  # Remove decimal if present
                row['Official State ID'],
                row['Photo Path'],
                row['Birth Certificate Path'],
                row['Address Proof Path'],
                row['Account Holder Name'],
                row['Account Number'],
                row['Bank Name'],
                row['Branch Name'],
                row['IFSC Code'],
                row['UPI ID'],
                row['Payment Snapshot Path'],
                row['Transaction ID'],
                row['State Registration'],
                row['Is State Transfer'],
                row['NOC Certificate Path']
            )
            
            try:
                cursor.execute(insert_query, data_tuple)
                successful_inserts += 1
                if successful_inserts % 100 == 0:
                    print(f"Inserted {successful_inserts} records...")
            except Error as e:
                print(f"Error inserting player {row['Player ID']}: {e}")
                failed_inserts += 1
                continue
        
        connection.commit()
        print(f"\nData loading completed:")
        print(f"- Total players in CSV: {len(df)}")
        print(f"- Successfully inserted: {successful_inserts}")
        print(f"- Failed to insert: {failed_inserts}")
        
        # Verify data in database
        cursor.execute("SELECT COUNT(*) FROM players")
        count = cursor.fetchone()[0]
        print(f"- Total players in database: {count}")
        
        return True
        
    except Error as e:
        print(f"Database error: {e}")
        print("Error details:")
        print(f"- Error code: {e.errno}")
        print(f"- Error message: {e.msg}")
        print(f"- SQL state: {e.sqlstate}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def load_tournaments_data():
    """Load data from tournaments.csv into tournaments table"""
    try:
        print("\nStarting tournaments data loading process...")
        
        # Read CSV file
        print("Reading tournaments.csv...")
        df = pd.read_csv('tournaments.csv')
        print(f"Found {len(df)} tournaments in CSV file")
        
        # Convert numeric fields to strings and clean up data
        print("Cleaning up data...")
        df = df.fillna('')  # Replace NaN with empty string
        
        # Get database connection
        print("Connecting to database...")
        connection = get_db_connection()
        if connection is None:
            print("Failed to connect to database")
            return False
            
        cursor = connection.cursor()
        
        # Check table structure
        print("\nVerifying tournaments table structure...")
        cursor.execute("DESCRIBE tournaments")
        columns = cursor.fetchall()
        print("Current table structure:")
        for col in columns:
            print(f"- {col[0]}: {col[1]}")
            
        # Prepare insert query
        insert_query = """
            INSERT INTO tournaments (
                tournament_id, name, categories, venue, start_date, end_date,
                last_registration_date, total_prize, general_information,
                tournament_logo_link, status, bank_account, upi_link, payment_qr
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        # Convert data and insert
        successful_inserts = 0
        failed_inserts = 0
        
        for _, row in df.iterrows():
            try:
                # Convert date strings to datetime objects if not empty
                start_date = datetime.strptime(str(row['Start Date']), '%Y-%m-%d').date() if row['Start Date'] else None
                end_date = datetime.strptime(str(row['End Date']), '%Y-%m-%d').date() if row['End Date'] else None
                last_reg_date = datetime.strptime(str(row['Last Registration Date']), '%Y-%m-%d').date() if row['Last Registration Date'] else None
                
                # Convert prize money to float, removing ₹ and commas
                total_prize = float(str(row['Total Prize']).replace('₹', '').replace(',', '')) if row['Total Prize'] else 0
                
                data_tuple = (
                    row['Tournament Id'],  # Note: matches CSV column name
                    row['Tournament Name'],
                    row['Categories'],
                    row['Venue'],
                    start_date,
                    end_date,
                    last_reg_date,
                    total_prize,
                    row['General Information'],
                    row['Tournament Logo Link'],
                    row['Status'],
                    row['Bank Account'],
                    row['UPI Link'],
                    row['Payment QR']
                )
                
                cursor.execute(insert_query, data_tuple)
                successful_inserts += 1
                
            except ValueError as e:
                print(f"Data conversion error for tournament {row['Tournament Id']}: {e}")
                failed_inserts += 1
                continue
            except Error as e:
                print(f"Database error inserting tournament {row['Tournament Id']}: {e}")
                failed_inserts += 1
                continue
        
        connection.commit()
        print(f"\nTournament data loading completed:")
        print(f"- Total tournaments in CSV: {len(df)}")
        print(f"- Successfully inserted: {successful_inserts}")
        print(f"- Failed to insert: {failed_inserts}")
        
        # Verify data in database
        cursor.execute("SELECT COUNT(*) FROM tournaments")
        count = cursor.fetchone()[0]
        print(f"- Total tournaments in database: {count}")
        
        return True
        
    except pd.errors.EmptyDataError:
        print("Error: tournaments.csv is empty")
        return False
    except FileNotFoundError:
        print("Error: tournaments.csv not found")
        return False
    except Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def load_tournament_categories():
    """Load data from tournament_categories.csv into tournament_categories table"""
    try:
        print("\nStarting tournament categories loading process...")
        
        # Read CSV file
        print("Reading tournament_categories.csv...")
        df = pd.read_csv('tournament_categories.csv')
        print(f"Found {len(df)} tournament categories in CSV file")
        
        # Convert numeric fields to strings and clean up data
        print("Cleaning up data...")
        df = df.fillna('')  # Replace NaN with empty string
        
        # Get database connection
        print("Connecting to database...")
        connection = get_db_connection()
        if connection is None:
            print("Failed to connect to database")
            return False
            
        cursor = connection.cursor()
        
        # Check table structure
        print("\nVerifying tournament_categories table structure...")
        cursor.execute("DESCRIBE tournament_categories")
        columns = cursor.fetchall()
        print("Current table structure:")
        for col in columns:
            print(f"- {col[0]}: {col[1]}")
            
        # Prepare insert query
        insert_query = """
            INSERT INTO tournament_categories (
                tournament_id, tournament_name, category, fee,
                first_prize, second_prize, third_prize, format
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        # Convert data and insert
        successful_inserts = 0
        failed_inserts = 0
        
        for _, row in df.iterrows():
            try:
                # Convert prize money to float, removing ₹ and commas
                first_prize = float(str(row['First Prize']).replace('₹', '').replace(',', '')) if row['First Prize'] else 0
                second_prize = float(str(row['Second Prize']).replace('₹', '').replace(',', '')) if row['Second Prize'] else 0
                third_prize = float(str(row['Third Prize']).replace('₹', '').replace(',', '')) if row['Third Prize'] else 0
                fee = float(str(row['Fee']).replace('₹', '').replace(',', '')) if row['Fee'] else 0
                
                data_tuple = (
                    row['Tournament Id'],  # Note: matches CSV column name
                    row['Tournament Name'],
                    row['Category'],
                    fee,
                    first_prize,
                    second_prize,
                    third_prize,
                    row['Format']
                )
                
                cursor.execute(insert_query, data_tuple)
                successful_inserts += 1
                
            except ValueError as e:
                print(f"Data conversion error for tournament {row['Tournament Id']}, category {row['Category']}: {e}")
                failed_inserts += 1
                continue
            except Error as e:
                print(f"Database error inserting category for tournament {row['Tournament Id']}, category {row['Category']}: {e}")
                failed_inserts += 1
                continue
        
        connection.commit()
        print(f"\nTournament categories loading completed:")
        print(f"- Total categories in CSV: {len(df)}")
        print(f"- Successfully inserted: {successful_inserts}")
        print(f"- Failed to insert: {failed_inserts}")
        
        # Verify data in database
        cursor.execute("SELECT COUNT(*) FROM tournament_categories")
        count = cursor.fetchone()[0]
        print(f"- Total categories in database: {count}")
        
        return True
        
    except pd.errors.EmptyDataError:
        print("Error: tournament_categories.csv is empty")
        return False
    except FileNotFoundError:
        print("Error: tournament_categories.csv not found")
        return False
    except Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def load_tournament_registrations():
    """Load data from tournament_registrations.csv into tournament_registrations table"""
    try:
        print("\nStarting tournament registrations loading process...")
        
        # Read CSV file
        print("Reading tournament_registrations.csv...")
        df = pd.read_csv('tournament_registrations.csv')
        print(f"Found {len(df)} tournament registrations in CSV file")
        
        # Convert numeric fields to strings and clean up data
        print("Cleaning up data...")
        df = df.fillna('')  # Replace NaN with empty string
        
        # Get database connection
        print("Connecting to database...")
        connection = get_db_connection()
        if connection is None:
            print("Failed to connect to database")
            return False
            
        cursor = connection.cursor()
        
        # Check table structure
        print("\nVerifying tournament_registrations table structure...")
        cursor.execute("DESCRIBE tournament_registrations")
        columns = cursor.fetchall()
        print("Current table structure:")
        for col in columns:
            print(f"- {col[0]}: {col[1]}")
            
        # Prepare insert query
        insert_query = """
            INSERT INTO tournament_registrations (
                tournament_id, player_id, registration_date,
                category, status, seeding
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )
        """
        
        # Convert data and insert
        successful_inserts = 0
        failed_inserts = 0
        
        for _, row in df.iterrows():
            try:
                # Convert date string to datetime object if not empty
                reg_date = datetime.strptime(str(row['Registration Date']), '%Y-%m-%d').date() if row['Registration Date'] else None
                
                # Convert seeding to int if not empty
                seeding = int(row['Seeding']) if row['Seeding'] else None
                
                data_tuple = (
                    row['Tournament Id'],  # Note: matches CSV column name
                    row['Player ID'],
                    reg_date,
                    row['Category'],
                    row['Status'],
                    seeding
                )
                
                cursor.execute(insert_query, data_tuple)
                successful_inserts += 1
                
            except ValueError as e:
                print(f"Data conversion error for tournament {row['Tournament Id']}, player {row['Player ID']}: {e}")
                failed_inserts += 1
                continue
            except Error as e:
                print(f"Database error inserting registration for tournament {row['Tournament Id']}, player {row['Player ID']}: {e}")
                failed_inserts += 1
                continue
        
        connection.commit()
        print(f"\nTournament registrations loading completed:")
        print(f"- Total registrations in CSV: {len(df)}")
        print(f"- Successfully inserted: {successful_inserts}")
        print(f"- Failed to insert: {failed_inserts}")
        
        # Verify data in database
        cursor.execute("SELECT COUNT(*) FROM tournament_registrations")
        count = cursor.fetchone()[0]
        print(f"- Total registrations in database: {count}")
        
        return True
        
    except pd.errors.EmptyDataError:
        print("Error: tournament_registrations.csv is empty")
        return False
    except FileNotFoundError:
        print("Error: tournament_registrations.csv not found")
        return False
    except Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def load_tournament_draw():
    """Load data from Tournament_draw.csv into tournament_draw table"""
    try:
        print("\nStarting tournament draw loading process...")
        
        # Read CSV file
        print("Reading Tournament_draw.csv...")
        df = pd.read_csv('Tournament_draw.csv')
        print(f"Found {len(df)} tournament draw entries in CSV file")
        
        # Convert numeric fields to strings and clean up data
        print("Cleaning up data...")
        df = df.fillna('')  # Replace NaN with empty string
        
        # Get database connection
        print("Connecting to database...")
        connection = get_db_connection()
        if connection is None:
            print("Failed to connect to database")
            return False
            
        cursor = connection.cursor()
        
        # Check table structure
        print("\nVerifying tournament_draw table structure...")
        cursor.execute("DESCRIBE tournament_draw")
        columns = cursor.fetchall()
        print("Current table structure:")
        for col in columns:
            print(f"- {col[0]}: {col[1]}")
            
        # Prepare insert query
        insert_query = """
            INSERT INTO tournament_draw (
                tournament_id, player_name, school_institution,
                category, player_rank, seeding
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )
        """
        
        # Convert data and insert
        successful_inserts = 0
        failed_inserts = 0
        
        for _, row in df.iterrows():
            try:
                # Convert numeric values if not empty
                player_rank = int(row['Rank']) if row['Rank'] else None
                seeding = int(row['Seeding']) if row['Seeding'] else None
                
                data_tuple = (
                    row['TournamentId'],  # Note: matches CSV column name
                    row['Player Name'],
                    row['School/Institution'],
                    row['Category'],
                    player_rank,
                    seeding
                )
                
                cursor.execute(insert_query, data_tuple)
                successful_inserts += 1
                
            except ValueError as e:
                print(f"Data conversion error for player {row['Player Name']}, category {row['Category']}: {e}")
                failed_inserts += 1
                continue
            except Error as e:
                print(f"Database error inserting draw entry for player {row['Player Name']}, category {row['Category']}: {e}")
                failed_inserts += 1
                continue
        
        connection.commit()
        print(f"\nTournament draw loading completed:")
        print(f"- Total draw entries in CSV: {len(df)}")
        print(f"- Successfully inserted: {successful_inserts}")
        print(f"- Failed to insert: {failed_inserts}")
        
        # Verify data in database
        cursor.execute("SELECT COUNT(*) FROM tournament_draw")
        count = cursor.fetchone()[0]
        print(f"- Total draw entries in database: {count}")
        
        return True
        
    except pd.errors.EmptyDataError:
        print("Error: Tournament_draw.csv is empty")
        return False
    except FileNotFoundError:
        print("Error: Tournament_draw.csv not found")
        return False
    except Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def main():
    """Main function to load all data"""
    print("Starting data loading process...")
    
    # Load data in sequence
    print("\nLoading players data...")
    load_players_data()
    
    print("\nLoading tournaments data...")
    load_tournaments_data()
    
    print("\nLoading tournament categories data...")
    load_tournament_categories()
    
    print("\nLoading tournament registrations data...")
    load_tournament_registrations()
    
    print("\nLoading tournament draw data...")
    load_tournament_draw()
    
    print("\nData loading process completed!")

if __name__ == "__main__":
    main() 