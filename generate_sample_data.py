import csv
import random
from datetime import datetime, timedelta

# List of sample academies
academies = [
    "Champions TT Academy", "Elite Table Tennis", "Pro Ping Academy",
    "Master Spin Club", "Power Smash Institute", "Table Tennis Hub",
    "Premier TT Center", "Golden Paddle Academy", "Victory TT Club",
    "Star Sports Academy"
]

# List of common Indian names
first_names = [
    "Aarav", "Arjun", "Advait", "Vihaan", "Reyansh", "Aditya", "Kabir", "Vivaan",
    "Ishaan", "Rudra", "Aanya", "Aadhya", "Saanvi", "Ananya", "Pari", "Myra",
    "Aaradhya", "Avni", "Diya", "Prisha", "Riya", "Sara", "Divya", "Anita",
    "Rahul", "Rohit", "Amit", "Priya", "Neha", "Pooja", "Raj", "Sanjay",
    "Karan", "Rohan", "Vikram", "Nisha", "Meera", "Kavya", "Arun", "Deepak"
]

last_names = [
    "Sharma", "Verma", "Singh", "Patel", "Kumar", "Shah", "Mehta", "Gupta",
    "Chopra", "Malhotra", "Reddy", "Kapoor", "Joshi", "Rao", "Chauhan", "Yadav",
    "Tiwari", "Bhat", "Nair", "Menon", "Khanna", "Saxena", "Basu", "Das",
    "Iyer", "Pillai", "Desai", "Bansal", "Agarwal", "Soni", "Dalal", "Malik"
]

# Categories and their target counts
category_targets = {
    # Age-based categories
    "u9": 15,
    "u11 Girls": 15,
    "u11 Boys": 15,
    "u13 Girls": 18,
    "u13 Boys": 18,
    "u15 Girls": 20,
    "u17 Boys": 22,
    "u19 Girls": 22,
    "u19 Boys": 22,
    
    # Open categories
    "Women": 25,
    "Men": 25,
    
    # Veterans categories
    "Veterans 39+ Women": 20,
    "Veterans 39+ Men": 20
}

def generate_dob(category):
    today = datetime.now()
    
    if "Veterans 39+" in category:
        # Generate age between 39-55 years
        days = random.randint(39*365, 55*365)
    elif category.startswith('u'):
        # Extract age from category (e.g., "u11" -> 11)
        age = int(category[1:].split()[0])
        # Generate age appropriate for the category (1-2 years younger)
        min_age = age - 2
        max_age = age - 1
        days = random.randint(min_age*365, max_age*365)
    else:
        # For open categories (Women/Men), generate age between 19-38
        days = random.randint(19*365, 38*365)
    
    dob = today - timedelta(days=days)
    return dob.strftime("%Y-%m-%d")

def main():
    # Create the CSV file
    with open('players_data.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Player Name', 'DOB', 'Category', 'Academy', 'Seeding'])
        
        # Generate players for each category
        for category, target_count in category_targets.items():
            print(f"\nGenerating data for {category}")
            
            # Create a list of players for this category
            category_players = []
            for _ in range(target_count):
                name = f"{random.choice(first_names)} {random.choice(last_names)}"
                dob = generate_dob(category)
                academy = random.choice(academies)
                category_players.append([name, dob, category, academy])
            
            # Randomly shuffle the players to assign random seedings
            random.shuffle(category_players)
            
            # Assign seeding numbers from 1 to total number of players
            for i, player in enumerate(category_players, 1):
                player.append(str(i))  # Add seeding number
                writer.writerow(player)
                print(f"Added player with seeding {i}: {player[0]}")

    # Print summary of generated data
    with open('players_data.csv', 'r', newline='') as file:
        reader = csv.DictReader(file)
        players = list(reader)
        
        print("\nData Generation Summary:")
        print("-" * 50)
        
        # Count by category
        print("\nPlayers by Category:")
        category_counts = {}
        for player in players:
            cat = player['Category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        for category in sorted(category_counts.keys()):
            total = category_counts[category]
            print(f"\n{category}:")
            print(f"  Total Players: {total}")
            print(f"  Seeding Range: 1-{total}")
            
            # Print sample players with their seedings
            category_players = [p for p in players if p['Category'] == category]
            print("\n  Sample Players:")
            for player in sorted(category_players, key=lambda x: int(x['Seeding']))[:5]:
                print(f"    Seeding {player['Seeding']}: {player['Player Name']}")
        
        print(f"\nTotal players across all categories: {len(players)}")
        print("\nData has been successfully written to 'players_data.csv'")

if __name__ == "__main__":
    main()