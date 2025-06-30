import pandas as pd
from mysql.connector import Error
from database.database_init import get_db_connection

def get_csv_counts():
    """Get record counts from CSV files"""
    try:
        csv_counts = {
            'players': len(pd.read_csv('players_data.csv')),
            'tournaments': len(pd.read_csv('tournaments.csv')),
            'tournament_categories': len(pd.read_csv('tournament_categories.csv')),
            'tournament_registrations': len(pd.read_csv('tournament_registrations.csv')),
            'tournament_draw': len(pd.read_csv('Tournament_draw.csv'))
        }
        return csv_counts
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        return None

def get_db_counts():
    """Get record counts from database tables"""
    try:
        connection = get_db_connection()
        if connection is None:
            print("Failed to connect to database")
            return None
            
        cursor = connection.cursor()
        
        # Get counts for each table
        tables = ['players', 'tournaments', 'tournament_categories', 
                 'tournament_registrations', 'tournament_draw']
        
        db_counts = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            db_counts[table] = count
            
        return db_counts
        
    except Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def main():
    """Compare record counts between CSV files and database tables"""
    print("\nComparing record counts between CSV files and database tables...")
    print("-" * 70)
    
    # Get counts
    csv_counts = get_csv_counts()
    db_counts = get_db_counts()
    
    if csv_counts is None or db_counts is None:
        print("Failed to get counts")
        return
    
    # Print comparison
    print(f"{'Table':<25} {'CSV Records':<15} {'DB Records':<15} {'Match?':<10}")
    print("-" * 70)
    
    for table in csv_counts.keys():
        csv_count = csv_counts[table]
        db_count = db_counts[table]
        match = "✓" if csv_count == db_count else "✗"
        
        print(f"{table:<25} {csv_count:<15} {db_count:<15} {match:<10}")
        
        # If counts don't match, show the difference
        if csv_count != db_count:
            diff = abs(csv_count - db_count)
            source = "CSV" if csv_count > db_count else "DB"
            print(f"  → {source} has {diff} more record(s)")
    
    print("-" * 70)

if __name__ == "__main__":
    main() 