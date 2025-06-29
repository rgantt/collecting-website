#!/usr/bin/env python3
"""
Fix the games_for_sale table to properly handle multiple copies of the same game.

The current design links to physical_games.id which causes all copies of a game
to show as "for sale" if any copy is marked for sale. This changes the schema
to link to purchased_games.id instead, similar to how lent_games works.
"""

import sqlite3
import os

def fix_games_for_sale_schema():
    # Get the path to the database
    db_path = os.path.join(os.path.dirname(__file__), 'games.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Step 1: Checking current games_for_sale schema...")
        cursor.execute("PRAGMA table_info(games_for_sale)")
        columns = cursor.fetchall()
        print("Current columns:")
        for col in columns:
            print(f"  {col[1]} {col[2]}")
        
        # Check if we already have purchased_game_id column
        has_purchased_game_id = any(col[1] == 'purchased_game_id' for col in columns)
        
        if has_purchased_game_id:
            print("Schema already updated!")
            return
        
        print("\nStep 2: Creating backup of current games_for_sale data...")
        cursor.execute("""
            CREATE TABLE games_for_sale_backup AS 
            SELECT * FROM games_for_sale
        """)
        
        print("Step 3: Getting current for-sale games with their purchase info...")
        cursor.execute("""
            SELECT 
                gfs.*,
                pg.id as purchased_game_id,
                p.name,
                p.console
            FROM games_for_sale gfs
            JOIN physical_games p ON gfs.physical_game_id = p.id
            LEFT JOIN purchased_games pg ON p.id = pg.physical_game
            ORDER BY gfs.id
        """)
        
        current_data = cursor.fetchall()
        print(f"Found {len(current_data)} games currently for sale")
        
        for row in current_data:
            print(f"  {row[-2]} ({row[-1]}) - purchased_game_id: {row[-3]}")
        
        print("\nStep 4: Dropping existing games_for_sale table...")
        cursor.execute("DROP TABLE games_for_sale")
        
        print("Step 5: Creating new games_for_sale table with purchased_game_id...")
        cursor.execute("""
            CREATE TABLE games_for_sale (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchased_game_id INTEGER NOT NULL,
                date_marked DATE NOT NULL DEFAULT (date('now')),
                asking_price DECIMAL,
                notes TEXT,
                
                -- Copied purchase information (denormalized for historical tracking)
                original_acquisition_date DATE,
                original_source TEXT,
                original_purchase_price DECIMAL,
                
                FOREIGN KEY (purchased_game_id) REFERENCES purchased_games (id),
                UNIQUE (purchased_game_id)  -- Prevent duplicate entries for same purchased game
            )
        """)
        
        print("Step 6: Migrating data to new schema...")
        for row in current_data:
            # row structure: [id, physical_game_id, date_marked, asking_price, notes, orig_date, orig_source, orig_price, purchased_game_id, name, console]
            if row[8]:  # If we have a purchased_game_id
                cursor.execute("""
                    INSERT INTO games_for_sale 
                    (purchased_game_id, date_marked, asking_price, notes, 
                     original_acquisition_date, original_source, original_purchase_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (row[8], row[2], row[3], row[4], row[5], row[6], row[7]))
                print(f"  Migrated: {row[9]} ({row[10]})")
            else:
                print(f"  WARNING: No purchased_game_id for {row[9]} ({row[10]}) - skipping")
        
        print("Step 7: Verifying migration...")
        cursor.execute("SELECT COUNT(*) FROM games_for_sale")
        new_count = cursor.fetchone()[0]
        print(f"New table has {new_count} records")
        
        conn.commit()
        print("\n✅ Schema migration completed successfully!")
        print("The games_for_sale table now links to purchased_games.id instead of physical_games.id")
        print("This will properly handle multiple copies of the same game.")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    fix_games_for_sale_schema()
