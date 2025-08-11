"""
Photo Service Layer
Handles CRUD operations for game photos and their associations with physical games.
"""
import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import uuid
import time
import re
from datetime import datetime

from flask import current_app


def get_db_path():
    """Get database path from app config or fallback to default"""
    if current_app:
        return current_app.config.get('DATABASE_PATH', 
                                     Path(__file__).parent.parent / "games.db")
    return Path(__file__).parent.parent / "games.db"


@contextmanager
def get_db():
    """Database connection context manager"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
    try:
        yield conn
    finally:
        conn.close()


class PhotoService:
    """Service class for photo-related database operations"""
    
    @staticmethod
    def generate_s3_key(game_id: int, original_filename: str) -> str:
        """
        Generate consistent S3 key for photo storage
        Format: photos/{game_id}/{timestamp}_{uuid}_{sanitized_filename}
        """
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]  # Short UUID for readability
        
        # Clean filename - remove path and keep only basename
        clean_filename = Path(original_filename).name
        
        # Sanitize filename to avoid URL encoding issues
        # Replace spaces and special characters with safe alternatives
        sanitized_filename = re.sub(r'[^\w\-_.]', '_', clean_filename)
        # Remove multiple underscores
        sanitized_filename = re.sub(r'_+', '_', sanitized_filename)
        # Remove leading/trailing underscores
        sanitized_filename = sanitized_filename.strip('_')
        
        # Ensure we have a valid filename
        if not sanitized_filename:
            sanitized_filename = "photo"
        
        return f"photos/{game_id}/{timestamp}_{unique_id}_{sanitized_filename}"
    
    @staticmethod
    def create_photo_record(s3_bucket: str, s3_key: str, original_filename: str, 
                          file_size: int, mime_type: str, uploader_metadata: Optional[str] = None) -> int:
        """
        Create a new photo record in the database
        Returns the photo ID
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO game_photos (
                    s3_bucket, s3_key, original_filename, file_size, 
                    mime_type, uploader_metadata, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (s3_bucket, s3_key, original_filename, file_size, mime_type, uploader_metadata))
            
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def associate_photo_with_game(physical_game_id: int, game_photo_id: int, 
                                photo_order: Optional[int] = None) -> bool:
        """
        Associate a photo with a physical game
        Returns True if successful, False if association already exists
        """
        if photo_order is None:
            # Get next order number for this game
            photo_order = PhotoService.get_next_photo_order(physical_game_id)
        
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO physical_game_photos (physical_game_id, game_photo_id, photo_order)
                    VALUES (?, ?, ?)
                """, (physical_game_id, game_photo_id, photo_order))
                
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Association already exists
                return False
    
    @staticmethod
    def get_next_photo_order(physical_game_id: int) -> int:
        """Get the next photo order number for a game"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(MAX(photo_order), -1) + 1
                FROM physical_game_photos
                WHERE physical_game_id = ?
            """, (physical_game_id,))
            
            result = cursor.fetchone()
            return result[0] if result else 0
    
    @staticmethod
    def get_game_photos(physical_game_id: int, active_only: bool = True) -> List[Dict]:
        """
        Get all photos associated with a physical game
        Returns list of photo records with metadata
        """
        with get_db() as conn:
            cursor = conn.cursor()
            
            active_filter = "AND gp.is_active = 1" if active_only else ""
            
            cursor.execute(f"""
                SELECT 
                    gp.id,
                    gp.s3_bucket,
                    gp.s3_key,
                    gp.original_filename,
                    gp.file_size,
                    gp.mime_type,
                    gp.upload_timestamp,
                    gp.uploader_metadata,
                    pgp.photo_order
                FROM game_photos gp
                JOIN physical_game_photos pgp ON gp.id = pgp.game_photo_id
                WHERE pgp.physical_game_id = ? {active_filter}
                ORDER BY pgp.photo_order ASC, gp.upload_timestamp ASC
            """, (physical_game_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_photo_by_id(photo_id: int) -> Optional[Dict]:
        """Get a single photo record by ID"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    id, s3_bucket, s3_key, original_filename, file_size, 
                    mime_type, upload_timestamp, uploader_metadata, is_active,
                    created_at, updated_at
                FROM game_photos
                WHERE id = ?
            """, (photo_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    @staticmethod
    def get_photo_count(physical_game_id: int, active_only: bool = True) -> int:
        """Get count of photos associated with a physical game"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            active_filter = "AND gp.is_active = 1" if active_only else ""
            
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM game_photos gp
                JOIN physical_game_photos pgp ON gp.id = pgp.game_photo_id
                WHERE pgp.physical_game_id = ? {active_filter}
            """, (physical_game_id,))
            
            result = cursor.fetchone()
            return result[0] if result else 0
    
    @staticmethod
    def soft_delete_photo(photo_id: int) -> bool:
        """
        Soft delete a photo (set is_active = 0)
        Returns True if photo was found and deleted
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE game_photos 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_active = 1
            """, (photo_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    def remove_photo_association(physical_game_id: int, game_photo_id: int) -> bool:
        """
        Remove association between a photo and a physical game
        Returns True if association was found and removed
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM physical_game_photos
                WHERE physical_game_id = ? AND game_photo_id = ?
            """, (physical_game_id, game_photo_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    def verify_game_exists(physical_game_id: int) -> bool:
        """Verify that a physical game exists"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM physical_games WHERE id = ?", (physical_game_id,))
            return cursor.fetchone() is not None
    
    @staticmethod
    def get_photos_by_s3_keys(s3_keys: List[str], s3_bucket: str) -> Dict[str, Dict]:
        """
        Get photo records by S3 keys for verification
        Returns dict mapping s3_key to photo record
        """
        if not s3_keys:
            return {}
        
        placeholders = ','.join(['?'] * len(s3_keys))
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT id, s3_bucket, s3_key, original_filename, file_size, mime_type, upload_timestamp
                FROM game_photos
                WHERE s3_bucket = ? AND s3_key IN ({placeholders}) AND is_active = 1
            """, [s3_bucket] + s3_keys)
            
            results = cursor.fetchall()
            return {row['s3_key']: dict(row) for row in results}
    
    @staticmethod
    def update_photo_order(physical_game_id: int, photo_orders: List[Tuple[int, int]]) -> bool:
        """
        Update photo ordering for a game
        photo_orders: List of (game_photo_id, new_order) tuples
        """
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Begin transaction
            cursor.execute("BEGIN")
            
            try:
                for game_photo_id, new_order in photo_orders:
                    cursor.execute("""
                        UPDATE physical_game_photos 
                        SET photo_order = ?
                        WHERE physical_game_id = ? AND game_photo_id = ?
                    """, (new_order, physical_game_id, game_photo_id))
                
                conn.commit()
                return True
                
            except Exception:
                conn.rollback()
                return False