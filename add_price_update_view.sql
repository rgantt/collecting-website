-- Migration: Add eligible_price_updates view for daily price update system
-- Date: 2025-09-06
-- Purpose: Identifies games that need price updates based on last update time
-- 
-- This view selects games that:
-- 1. Have never had a price update (NULL last_update)
-- 2. Haven't been updated in more than 7 days
-- 
-- Ported from collecting-tools repository to enable batch price updates

-- Drop the view if it exists (for idempotent migrations)
DROP VIEW IF EXISTS eligible_price_updates;

-- Create the view for identifying games needing price updates
CREATE VIEW eligible_price_updates AS
WITH latest_updates AS (
    SELECT 
        pricecharting_id,
        MAX(retrieve_time) as last_update
    FROM pricecharting_prices
    GROUP BY pricecharting_id
)
SELECT DISTINCT
    g.id as game_id,  -- Added game_id for easier updates
    g.name,
    g.console,
    z.pricecharting_id,
    lu.last_update
FROM physical_games g
-- Include both purchased and wanted games
LEFT JOIN purchased_games pg
    ON g.id = pg.physical_game
LEFT JOIN wanted_games wg
    ON g.id = wg.physical_game
-- Join to get pricecharting associations
JOIN physical_games_pricecharting_games j
    ON g.id = j.physical_game
JOIN pricecharting_games z
    ON j.pricecharting_game = z.id
-- Get latest price update info
LEFT JOIN latest_updates lu
    ON z.pricecharting_id = lu.pricecharting_id
WHERE 
    -- Game must be in collection or wishlist
    (pg.id IS NOT NULL OR wg.id IS NOT NULL)
    AND (
        -- Never attempted a price update
        lu.last_update IS NULL  
        -- Or last update was more than 7 days ago
        OR datetime(lu.last_update) < datetime('now', '-7 days')
    )
ORDER BY 
    -- Prioritize games never updated
    lu.last_update ASC NULLS FIRST,
    -- Then by name for consistent ordering
    g.name ASC;

-- Create an index to improve performance of the view
CREATE INDEX IF NOT EXISTS idx_pricecharting_prices_retrieve 
ON pricecharting_prices(pricecharting_id, retrieve_time);

-- Verify the view was created successfully
SELECT 'View created successfully. Found ' || COUNT(*) || ' games eligible for price updates.' as status
FROM eligible_price_updates;