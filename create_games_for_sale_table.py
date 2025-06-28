#!/usr/bin/env python3
"""
Database migration script to create the games_for_sale table.
This script creates a new table to track games that are marked for sale,
preserving the original purchase information.
"""

import sqlite3
import sys
from pathlib import Path

def create_games_for_sale_table(db_path):
    """Create the games_for_sale table with purchase history preservation."""
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create the games_for_sale table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games_for_sale (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                physical_game_id INTEGER NOT NULL,
                date_marked DATE NOT NULL DEFAULT (date('now')),
                asking_price DECIMAL,
                notes TEXT,
                
                -- Copied purchase information (denormalized for historical tracking)
                original_acquisition_date DATE,
                original_source TEXT,
                original_purchase_price DECIMAL,
                
                FOREIGN KEY (physical_game_id) REFERENCES physical_games (id),
                UNIQUE (physical_game_id)  -- Prevent duplicate entries for same game
            )
        """)
        
        print("✅ Created games_for_sale table successfully")
        conn.commit()
        conn.close()
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function to run the migration."""
    
    # Get database path
    script_dir = Path(__file__).parent
    db_path = script_dir / "games.db"
    
    if not db_path.exists():
        print(f"❌ Database file not found: {db_path}")
        sys.exit(1)
    
    print(f"🔄 Running migration on database: {db_path}")
    
    if create_games_for_sale_table(db_path):
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
