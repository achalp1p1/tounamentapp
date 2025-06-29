SET FOREIGN_KEY_CHECKS=0;

-- Create tournaments table if it doesn't exist
CREATE TABLE IF NOT EXISTS tournaments (
    id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    categories TEXT,
    venue VARCHAR(255),
    start_date DATE,
    end_date DATE,
    last_registration_date DATE,
    total_prize DECIMAL(10,2),
    general_information TEXT,
    tournament_logo_link TEXT,
    status VARCHAR(20),
    bank_account VARCHAR(50),
    upi_link VARCHAR(255),
    payment_qr TEXT
);

-- Create tournament_categories table if it doesn't exist
CREATE TABLE IF NOT EXISTS tournament_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_id VARCHAR(10),
    tournament_name VARCHAR(255),
    category VARCHAR(50),
    fee DECIMAL(10,2),
    first_prize DECIMAL(10,2),
    second_prize DECIMAL(10,2),
    third_prize DECIMAL(10,2),
    format VARCHAR(50),
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
);

-- Create players table if it doesn't exist
CREATE TABLE IF NOT EXISTS players (
    id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    date_of_birth DATE,
    gender VARCHAR(10),
    phone_number VARCHAR(15),
    email VARCHAR(255),
    state VARCHAR(50),
    district VARCHAR(50),
    school_institution VARCHAR(255),
    academy VARCHAR(255),
    address TEXT,
    ttfi_id VARCHAR(50),
    official_state_id VARCHAR(50),
    photo_path TEXT,
    birth_certificate_path TEXT,
    address_proof_path TEXT,
    account_holder_name VARCHAR(255),
    account_number VARCHAR(50),
    bank_name VARCHAR(100),
    branch_name VARCHAR(100),
    ifsc_code VARCHAR(20),
    upi_id VARCHAR(255),
    payment_snapshot_path TEXT,
    transaction_id VARCHAR(100),
    state_registration VARCHAR(5),
    is_state_transfer VARCHAR(5),
    noc_certificate_path TEXT
);

-- Create tournament_registrations table if it doesn't exist
CREATE TABLE IF NOT EXISTS tournament_registrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_id VARCHAR(10),
    player_id VARCHAR(20),
    registration_date DATE,
    category VARCHAR(50),
    status VARCHAR(20),
    seeding INT,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

-- Create tournament_draw table if it doesn't exist
CREATE TABLE IF NOT EXISTS tournament_draw (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_id VARCHAR(10),
    player_name VARCHAR(255) NOT NULL,
    school_institution VARCHAR(255),
    category VARCHAR(50) NOT NULL,
    player_rank INT,
    seeding INT,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
);

SET FOREIGN_KEY_CHECKS=1; 