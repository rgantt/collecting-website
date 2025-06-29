/**
 * Optimistic Update Framework
 * Handles immediate UI updates with rollback capability
 * Manages operation queueing and visual feedback states
 */
class OptimisticUpdater {
    constructor(stateManager) {
        this.stateManager = stateManager;
        this.operationQueue = new Map(); // gameId -> queue of operations
        this.rollbackSnapshots = new Map(); // operationId -> rollback state
        this.activeOperations = new Map(); // operationId -> operation details
        this.operationCounter = 0;
    }

    /**
     * Apply an optimistic update immediately
     * @param {string|number} gameId - Game ID
     * @param {string} operation - Operation type
     * @param {Function} uiUpdateFn - Function to update UI immediately
     * @param {Function} apiFn - Function to call API
     * @param {Object} options - Additional options
     * @returns {Promise} Operation promise
     */
    async applyOptimisticUpdate(gameId, operation, uiUpdateFn, apiFn, options = {}) {
        const operationId = this._generateOperationId();
        const gameIdStr = gameId.toString();
        
        try {
            // Take snapshot for potential rollback
            const snapshot = this._takeSnapshot(gameId);
            this.rollbackSnapshots.set(operationId, snapshot);
            
            // Track active operation
            this.activeOperations.set(operationId, {
                gameId: gameIdStr,
                operation,
                timestamp: Date.now(),
                options
            });
            
            // Mark pending in state manager
            this.stateManager.setPendingOperation(gameId, operation, { operationId });
            
            // Apply immediate UI updates
            this._setLoadingState(gameId, operation, true);
            await this._safeExecute(uiUpdateFn, `UI update for ${operation}`);
            
            // Queue the operation if rapid succession
            if (this._shouldQueue(gameId, operation)) {
                return this._queueOperation(gameId, operation, apiFn, operationId);
            }
            
            // Execute API call
            const result = await this._executeApiCall(apiFn, operation);
            
            // Confirm successful update
            await this.confirmUpdate(operationId, result);
            
            return result;
            
        } catch (error) {
            console.error(`Optimistic update failed for ${operation}:`, error);
            await this.rollbackUpdate(operationId, error);
            throw error;
        }
    }

    /**
     * Confirm a successful update
     * @param {string} operationId - Operation ID
     * @param {*} result - API result
     */
    async confirmUpdate(operationId, result) {
        const operation = this.activeOperations.get(operationId);
        
        if (!operation) {
            console.warn(`Cannot confirm unknown operation ${operationId}`);
            return;
        }
        
        try {
            // Clear pending state
            this.stateManager.clearPendingOperation(operation.gameId);
            
            // Update state with server response if provided
            if (result && result.game) {
                this.stateManager.updateGame(result.game);
            }
            
            // Set success state
            this._setLoadingState(operation.gameId, operation.operation, false, 'success');
            
            // Clean up
            this._cleanup(operationId);
            
            // Trigger success callback if provided
            if (operation.options?.onSuccess) {
                await this._safeExecute(
                    () => operation.options.onSuccess(result),
                    'success callback'
                );
            }
            
        } catch (error) {
            console.error('Error confirming update:', error);
            // Still clean up even if callback fails
            this._cleanup(operationId);
        }
    }

    /**
     * Rollback an update due to failure
     * @param {string} operationId - Operation ID
     * @param {Error} error - Error that caused rollback
     */
    async rollbackUpdate(operationId, error) {
        const operation = this.activeOperations.get(operationId);
        const snapshot = this.rollbackSnapshots.get(operationId);
        
        if (!operation) {
            console.warn(`Cannot rollback unknown operation ${operationId}`);
            return;
        }
        
        try {
            // Restore state from snapshot
            if (snapshot) {
                this.stateManager.updateGame(snapshot.game);
            }
            
            // Clear pending state
            this.stateManager.clearPendingOperation(operation.gameId);
            
            // Set error state
            this._setLoadingState(operation.gameId, operation.operation, false, 'error');
            
            // Trigger rollback UI updates if provided
            if (operation.options?.rollbackFn) {
                await this._safeExecute(
                    () => operation.options.rollbackFn(snapshot),
                    'rollback UI update'
                );
            }
            
            // Trigger error callback if provided
            if (operation.options?.onError) {
                await this._safeExecute(
                    () => operation.options.onError(error),
                    'error callback'
                );
            }
            
        } catch (rollbackError) {
            console.error('Error during rollback:', rollbackError);
        } finally {
            // Always clean up
            this._cleanup(operationId);
        }
    }

    /**
     * Check if there are pending operations for a game
     * @param {string|number} gameId - Game ID
     * @returns {boolean}
     */
    hasPendingOperations(gameId) {
        return this.stateManager.hasPendingOperation(gameId) || 
               this.operationQueue.has(gameId.toString());
    }

    /**
     * Get pending operations for a game
     * @param {string|number} gameId - Game ID
     * @returns {Array} Array of pending operations
     */
    getPendingOperations(gameId) {
        const gameIdStr = gameId.toString();
        const current = this.stateManager.getPendingOperation(gameId);
        const queued = this.operationQueue.get(gameIdStr) || [];
        
        return [current, ...queued].filter(Boolean);
    }

    /**
     * Cancel all pending operations for a game
     * @param {string|number} gameId - Game ID
     */
    cancelPendingOperations(gameId) {
        const gameIdStr = gameId.toString();
        
        // Cancel queued operations
        this.operationQueue.delete(gameIdStr);
        
        // Find and cancel active operations
        for (const [operationId, operation] of this.activeOperations) {
            if (operation.gameId === gameIdStr) {
                this.rollbackUpdate(operationId, new Error('Operation canceled'));
            }
        }
    }

    /**
     * Generate unique operation ID
     * @private
     */
    _generateOperationId() {
        return `op_${Date.now()}_${++this.operationCounter}`;
    }

    /**
     * Take snapshot of current game state for rollback
     * @private
     */
    _takeSnapshot(gameId) {
        const game = this.stateManager.getGame(gameId);
        return {
            game: game ? { ...game } : null,
            timestamp: Date.now()
        };
    }

    /**
     * Set loading state for UI feedback
     * @private
     */
    _setLoadingState(gameId, operation, isLoading, state = null) {
        const event = new CustomEvent('optimistic-update-state', {
            detail: {
                gameId: gameId.toString(),
                operation,
                isLoading,
                state // 'success', 'error', or null
            }
        });
        
        document.dispatchEvent(event);
    }

    /**
     * Safely execute a function with error handling
     * @private
     */
    async _safeExecute(fn, description) {
        try {
            const result = await fn();
            return result;
        } catch (error) {
            console.error(`Error in ${description}:`, error);
            throw error;
        }
    }

    /**
     * Execute API call with timeout and retry logic
     * @private
     */
    async _executeApiCall(apiFn, operation) {
        const maxRetries = 2;
        const timeout = 10000; // 10 seconds
        
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                // Create timeout promise
                const timeoutPromise = new Promise((_, reject) => {
                    setTimeout(() => reject(new Error('API call timeout')), timeout);
                });
                
                // Race API call against timeout
                const result = await Promise.race([apiFn(), timeoutPromise]);
                return result;
                
            } catch (error) {
                if (attempt === maxRetries || !this._isRetryableError(error)) {
                    throw error;
                }
                
                // Wait before retry with exponential backoff
                const delay = Math.pow(2, attempt) * 1000;
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }

    /**
     * Check if error is retryable
     * @private
     */
    _isRetryableError(error) {
        // Network errors, timeouts, and 5xx server errors are retryable
        return error.message.includes('timeout') || 
               error.message.includes('network') ||
               (error.status >= 500 && error.status < 600);
    }

    /**
     * Check if operation should be queued (for rapid succession)
     * @private
     */
    _shouldQueue(gameId, operation) {
        const gameIdStr = gameId.toString();
        const currentPending = this.stateManager.getPendingOperation(gameId);
        
        // Queue if there's already a pending operation of the same type
        return currentPending && currentPending.operation === operation;
    }

    /**
     * Queue an operation for later execution
     * @private
     */
    async _queueOperation(gameId, operation, apiFn, operationId) {
        const gameIdStr = gameId.toString();
        
        if (!this.operationQueue.has(gameIdStr)) {
            this.operationQueue.set(gameIdStr, []);
        }
        
        const queue = this.operationQueue.get(gameIdStr);
        queue.push({ operation, apiFn, operationId });
        
        // Process queue when current operation completes
        return new Promise((resolve, reject) => {
            const checkQueue = () => {
                if (!this.stateManager.hasPendingOperation(gameId)) {
                    this._processQueue(gameId).then(resolve).catch(reject);
                } else {
                    setTimeout(checkQueue, 100);
                }
            };
            checkQueue();
        });
    }

    /**
     * Process queued operations
     * @private
     */
    async _processQueue(gameId) {
        const gameIdStr = gameId.toString();
        const queue = this.operationQueue.get(gameIdStr);
        
        if (!queue || queue.length === 0) {
            return;
        }
        
        const { operation, apiFn, operationId } = queue.shift();
        
        try {
            const result = await this._executeApiCall(apiFn, operation);
            await this.confirmUpdate(operationId, result);
            
            // Process remaining queue items
            if (queue.length > 0) {
                setTimeout(() => this._processQueue(gameId), 50);
            } else {
                this.operationQueue.delete(gameIdStr);
            }
            
            return result;
            
        } catch (error) {
            await this.rollbackUpdate(operationId, error);
            throw error;
        }
    }

    /**
     * Clean up operation data
     * @private
     */
    _cleanup(operationId) {
        this.activeOperations.delete(operationId);
        this.rollbackSnapshots.delete(operationId);
    }

    /**
     * Get statistics about active operations
     * @returns {Object} Operation statistics
     */
    getStats() {
        return {
            activeOperations: this.activeOperations.size,
            queuedOperations: Array.from(this.operationQueue.values())
                .reduce((sum, queue) => sum + queue.length, 0),
            rollbackSnapshots: this.rollbackSnapshots.size
        };
    }
}

// Create global instance
window.optimisticUpdater = new OptimisticUpdater(window.gameStateManager);

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
    module.exports = OptimisticUpdater;
}
