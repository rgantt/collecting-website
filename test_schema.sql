-- Test database schema - extracted from production games.db
-- This is the single source of truth for test database structure

CREATE TABLE conditions (
    name TEXT NOT NULL PRIMARY KEY
);

CREATE TABLE sources (
    name TEXT NOT NULL PRIMARY KEY
);

CREATE TABLE physical_consoles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acquire_date TIMESTAMP,
    source TEXT,
    platform TEXT NOT NULL,
    variant TEXT DEFAULT NULL,
    livery TEXT NOT NULL,
    price DECIMAL,
    condition TEXT
);

CREATE TABLE physical_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    console TEXT NOT NULL
);

CREATE TABLE pricecharting_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pricecharting_id INTEGER,
    name TEXT NOT NULL,
    console TEXT NOT NULL,
    url TEXT
);

CREATE TABLE physical_games_pricecharting_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    physical_game INTEGER NOT NULL,
    pricecharting_game INTEGER NOT NULL,
    FOREIGN KEY (physical_game) REFERENCES physical_games (id),
    FOREIGN KEY (pricecharting_game) REFERENCES pricecharting_games (id)
);

CREATE TABLE pricecharting_games_upcs (
    pricecharting_game INTEGER NOT NULL,
    upc INTEGER NOT NULL
);

CREATE TABLE pricecharting_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    retrieve_time TIMESTAMP,
    pricecharting_id INTEGER NOT NULL,
    new DECIMAL, 
    loose DECIMAL,
    complete DECIMAL, 
    condition TEXT, 
    price DECIMAL,
    FOREIGN KEY (pricecharting_id) REFERENCES pricecharting_games (pricecharting_id)
);

CREATE TABLE backup_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL
);

CREATE TABLE physical_games_backup_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    physical_game INTEGER NOT NULL,
    backup_file INTEGER NOT NULL
);

CREATE TABLE wanted_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    physical_game INTEGER NOT NULL, 
    condition TEXT DEFAULT 'complete',
    FOREIGN KEY (physical_game) REFERENCES physical_games (id)
);

CREATE TABLE purchased_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    physical_game INTEGER NOT NULL,
    acquisition_date DATE NOT NULL CHECK (acquisition_date IS strftime('%Y-%m-%d', acquisition_date)),
    source TEXT,
    price DECIMAL,
    condition TEXT,
    FOREIGN KEY (physical_game) REFERENCES physical_games (id)
);

CREATE TABLE lent_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchased_game INTEGER NOT NULL,
    lent_date DATE NOT NULL CHECK (lent_date IS strftime('%Y-%m-%d', lent_date)),
    lent_to TEXT NOT NULL,
    note TEXT,
    returned_date DATE CHECK (returned_date IS NULL OR returned_date IS strftime('%Y-%m-%d', returned_date)),
    FOREIGN KEY (purchased_game) REFERENCES purchased_games (id)
);

CREATE TABLE games_for_sale (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchased_game_id INTEGER NOT NULL,
    date_marked DATE NOT NULL DEFAULT (date('now')),
    asking_price DECIMAL,
    notes TEXT,
    original_acquisition_date DATE,
    original_source TEXT,
    original_purchase_price DECIMAL,
    FOREIGN KEY (purchased_game_id) REFERENCES purchased_games (id),
    UNIQUE (purchased_game_id)
);

-- Legacy tables for backward compatibility
CREATE TABLE wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    console TEXT NOT NULL,
    url TEXT,
    current_price REAL,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    condition TEXT DEFAULT 'CIB'
);

-- Indices
CREATE UNIQUE INDEX distinct_pricecharting_ids ON pricecharting_games(pricecharting_id);