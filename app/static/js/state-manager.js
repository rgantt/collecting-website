/**
 * Game State Management System
 * Manages client-side game state independently from DOM
 * Supports optimistic updates with rollback capability
 */
class GameStateManager {
    constructor() {
        this.games = new Map(); // gameId -> game data
        this.pendingOperations = new Map(); // gameId -> operation details
        this.listeners = new Set(); // state change listeners
    }

    /**
     * Add or update a game in the state
     * @param {Object} game - Game object with id property
     */
    updateGame(game) {
        if (!game || !game.id) {
            throw new Error('Game must have an id property');
        }
        
        const gameId = game.id.toString();
        const previousState = this.games.get(gameId);
        
        this.games.set(gameId, { ...game });
        this._notifyListeners('update', gameId, game, previousState);
        
        return this.games.get(gameId);
    }

    /**
     * Get a specific game by id
     * @param {string|number} gameId - Game ID
     * @returns {Object|null} Game object or null if not found
     */
    getGame(gameId) {
        return this.games.get(gameId.toString()) || null;
    }

    /**
     * Get all games as an array
     * @returns {Array} Array of all game objects
     */
    getAllGames() {
        return Array.from(this.games.values());
    }

    /**
     * Add a new game to the state
     * @param {Object} game - Game object with id property
     */
    addGame(game) {
        if (!game || !game.id) {
            throw new Error('Game must have an id property');
        }
        
        const gameId = game.id.toString();
        if (this.games.has(gameId)) {
            console.warn(`Game with ID ${gameId} already exists, updating instead`);
            return this.updateGame(game);
        }
        
        this.games.set(gameId, { ...game });
        this._notifyListeners('add', gameId, game);
        
        return this.games.get(gameId);
    }

    /**
     * Remove a game from the state
     * @param {string|number} gameId - Game ID
     * @returns {boolean} True if game was removed, false if not found
     */
    removeGame(gameId) {
        const gameIdStr = gameId.toString();
        const game = this.games.get(gameIdStr);
        
        if (!game) {
            return false;
        }
        
        this.games.delete(gameIdStr);
        this.pendingOperations.delete(gameIdStr);
        this._notifyListeners('remove', gameIdStr, game);
        
        return true;
    }

    /**
     * Mark a pending operation for a game
     * @param {string|number} gameId - Game ID
     * @param {string} operation - Operation type (e.g., 'mark_for_sale', 'purchase')
     * @param {Object} details - Operation details
     */
    setPendingOperation(gameId, operation, details = {}) {
        const gameIdStr = gameId.toString();
        
        this.pendingOperations.set(gameIdStr, {
            operation,
            details,
            timestamp: Date.now()
        });
        
        this._notifyListeners('pending', gameIdStr, operation, details);
    }

    /**
     * Get pending operation for a game
     * @param {string|number} gameId - Game ID
     * @returns {Object|null} Pending operation or null
     */
    getPendingOperation(gameId) {
        return this.pendingOperations.get(gameId.toString()) || null;
    }

    /**
     * Clear pending operation for a game
     * @param {string|number} gameId - Game ID
     */
    clearPendingOperation(gameId) {
        const gameIdStr = gameId.toString();
        const operation = this.pendingOperations.get(gameIdStr);
        
        this.pendingOperations.delete(gameIdStr);
        
        if (operation) {
            this._notifyListeners('operation_complete', gameIdStr, operation);
        }
    }

    /**
     * Check if a game has a pending operation
     * @param {string|number} gameId - Game ID
     * @returns {boolean}
     */
    hasPendingOperation(gameId) {
        return this.pendingOperations.has(gameId.toString());
    }

    /**
     * Get all games with pending operations
     * @returns {Array} Array of {gameId, game, operation} objects
     */
    getPendingGames() {
        const pending = [];
        
        for (const [gameId, operation] of this.pendingOperations) {
            const game = this.games.get(gameId);
            if (game) {
                pending.push({ gameId, game, operation });
            }
        }
        
        return pending;
    }

    /**
     * Validate game state consistency
     * @returns {Object} Validation result with errors array
     */
    validateState() {
        const errors = [];
        
        // Check for games without required fields
        for (const [gameId, game] of this.games) {
            if (!game.name) {
                errors.push(`Game ${gameId} missing name`);
            }
            if (!game.console) {
                errors.push(`Game ${gameId} missing console`);
            }
        }
        
        // Check for orphaned pending operations
        for (const gameId of this.pendingOperations.keys()) {
            if (!this.games.has(gameId)) {
                errors.push(`Pending operation for non-existent game ${gameId}`);
            }
        }
        
        return {
            isValid: errors.length === 0,
            errors
        };
    }

    /**
     * Add state change listener
     * @param {Function} callback - Callback function
     */
    addListener(callback) {
        if (typeof callback === 'function') {
            this.listeners.add(callback);
        }
    }

    /**
     * Remove state change listener
     * @param {Function} callback - Callback function
     */
    removeListener(callback) {
        this.listeners.delete(callback);
    }

    /**
     * Clear all state
     */
    clear() {
        this.games.clear();
        this.pendingOperations.clear();
        this._notifyListeners('clear');
    }

    /**
     * Get state statistics
     * @returns {Object} State statistics
     */
    getStats() {
        return {
            totalGames: this.games.size,
            pendingOperations: this.pendingOperations.size,
            listeners: this.listeners.size
        };
    }

    /**
     * Notify all listeners of state changes
     * @private
     */
    _notifyListeners(type, gameId, ...args) {
        for (const listener of this.listeners) {
            try {
                listener(type, gameId, ...args);
            } catch (error) {
                console.error('Error in state change listener:', error);
            }
        }
    }

    /**
     * Export state for debugging
     * @returns {Object} Complete state object
     */
    exportState() {
        return {
            games: Object.fromEntries(this.games),
            pendingOperations: Object.fromEntries(this.pendingOperations),
            stats: this.getStats()
        };
    }
}

// Create global instance
window.gameStateManager = new GameStateManager();

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GameStateManager;
}
