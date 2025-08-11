-- Photo Capture Feature: Database Migration Script
-- Add tables for storing game photo references with S3 integration
-- Run this script against your production database

-- Table: game_photos
-- Stores references to photos uploaded to S3 with metadata
CREATE TABLE IF NOT EXISTS game_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    s3_bucket VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    upload_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    uploader_metadata TEXT, -- JSON for additional metadata (reserved for future use)
    is_active BOOLEAN NOT NULL DEFAULT 1, -- Soft delete capability
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_s3_reference UNIQUE(s3_bucket, s3_key) -- Prevent duplicate S3 references
);

-- Table: physical_game_photos  
-- Junction table associating photos with physical games
CREATE TABLE IF NOT EXISTS physical_game_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    physical_game_id INTEGER NOT NULL,
    game_photo_id INTEGER NOT NULL,
    photo_order INTEGER NOT NULL DEFAULT 0, -- Allow user-defined ordering
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (physical_game_id) REFERENCES physical_games(id) ON DELETE CASCADE,
    FOREIGN KEY (game_photo_id) REFERENCES game_photos(id) ON DELETE CASCADE,
    CONSTRAINT unique_game_photo UNIQUE(physical_game_id, game_photo_id) -- Prevent duplicate associations
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_game_photos_s3_lookup ON game_photos(s3_bucket, s3_key);
CREATE INDEX IF NOT EXISTS idx_game_photos_active ON game_photos(is_active, upload_timestamp);
CREATE INDEX IF NOT EXISTS idx_physical_game_photos_lookup ON physical_game_photos(physical_game_id, photo_order);
CREATE INDEX IF NOT EXISTS idx_physical_game_photos_photo ON physical_game_photos(game_photo_id);

-- Update trigger for game_photos.updated_at
CREATE TRIGGER IF NOT EXISTS update_game_photos_timestamp 
    AFTER UPDATE ON game_photos
    FOR EACH ROW
    BEGIN
        UPDATE game_photos SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Verification queries (run these to confirm tables were created correctly)
-- SELECT name FROM sqlite_master WHERE type='table' AND name IN ('game_photos', 'physical_game_photos');
-- SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%photo%';