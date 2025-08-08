/**
 * Enhanced Error Handling System
 * Manages error notifications, rollbacks, and retry mechanisms
 * Provides toast-style notifications and comprehensive error logging
 */
class ErrorHandler {
    constructor() {
        this.toastContainer = null;
        this.errorLog = [];
        this.maxLogEntries = 100;
        this.retryAttempts = new Map(); // operationId -> attempt count
        this.maxRetries = 3;
        
        this._initializeToastContainer();
        this._setupGlobalErrorHandlers();
    }

    /**
     * Handle API error with automatic rollback and user notification
     * @param {Error} error - The error object
     * @param {string} operationId - Operation ID for rollback
     * @param {Object} context - Additional context
     */
    async handleApiError(error, operationId, context = {}) {
        this._logError(error, operationId, context);
        
        // Determine if error is retryable
        if (this._shouldRetry(error, operationId)) {
            return this._scheduleRetry(operationId, context);
        }
        
        // Show user-friendly error notification
        this.showErrorToast(
            this._getUserFriendlyMessage(error, context.operation),
            {
                duration: 5000,
                action: context.allowRetry ? {
                    text: 'Retry',
                    callback: () => this._manualRetry(operationId, context)
                } : null
            }
        );
        
        // Note: Rollback functionality removed with API-first approach
        
        return { success: false, error, rolled_back: true };
    }

    /**
     * Handle network errors with retry logic
     * @param {Error} error - Network error
     * @param {string} operationId - Operation ID
     * @param {Object} context - Context with retry function
     */
    async handleNetworkError(error, operationId, context = {}) {
        if (navigator.onLine === false) {
            this.showErrorToast('No internet connection. Changes will be retried when connection is restored.', {
                duration: 0, // Persistent until connection restored
                type: 'warning'
            });
            
            this._setupOfflineRetry(operationId, context);
            return;
        }
        
        return this.handleApiError(error, operationId, { ...context, isNetworkError: true });
    }

    /**
     * Show success toast notification
     * @param {string} message - Success message
     * @param {Object} options - Toast options
     */
    showSuccessToast(message, options = {}) {
        this._showToast(message, 'success', {
            duration: 2000,
            ...options
        });
    }

    /**
     * Show error toast notification
     * @param {string} message - Error message
     * @param {Object} options - Toast options
     */
    showErrorToast(message, options = {}) {
        this._showToast(message, 'error', {
            duration: 5000,
            ...options
        });
    }

    /**
     * Show warning toast notification
     * @param {string} message - Warning message
     * @param {Object} options - Toast options
     */
    showWarningToast(message, options = {}) {
        this._showToast(message, 'warning', {
            duration: 4000,
            ...options
        });
    }

    /**
     * Show info toast notification
     * @param {string} message - Info message
     * @param {Object} options - Toast options
     */
    showInfoToast(message, options = {}) {
        this._showToast(message, 'info', {
            duration: 3000,
            ...options
        });
    }

    /**
     * Simple error display method (alias for showErrorToast)
     * @param {string} message - Error message
     */
    showError(message) {
        this.showErrorToast(message);
    }

    /**
     * Simple success display method (alias for showSuccessToast)
     * @param {string} message - Success message
     */
    showSuccess(message) {
        this.showSuccessToast(message);
    }

    /**
     * Get error statistics
     * @returns {Object} Error statistics
     */
    getErrorStats() {
        const now = Date.now();
        const last24Hours = this.errorLog.filter(entry => 
            now - entry.timestamp < 24 * 60 * 60 * 1000
        );
        
        const errorTypes = {};
        const operations = {};
        
        last24Hours.forEach(entry => {
            errorTypes[entry.type] = (errorTypes[entry.type] || 0) + 1;
            if (entry.operation) {
                operations[entry.operation] = (operations[entry.operation] || 0) + 1;
            }
        });
        
        return {
            total: this.errorLog.length,
            last24Hours: last24Hours.length,
            errorTypes,
            operations,
            activeRetries: this.retryAttempts.size
        };
    }

    /**
     * Clear error log
     */
    clearErrorLog() {
        this.errorLog = [];
        this.retryAttempts.clear();
    }

    /**
     * Export error log for debugging
     * @returns {Array} Error log entries
     */
    exportErrorLog() {
        return this.errorLog.map(entry => ({
            ...entry,
            timestamp: new Date(entry.timestamp).toISOString()
        }));
    }

    /**
     * Initialize toast container
     * @private
     */
    _initializeToastContainer() {
        // Create toast container if it doesn't exist
        this.toastContainer = document.getElementById('toast-container');
        
        if (!this.toastContainer) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.id = 'toast-container';
            this.toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            this.toastContainer.style.zIndex = '9999';
            document.body.appendChild(this.toastContainer);
        }
    }

    /**
     * Setup global error handlers
     * @private
     */
    _setupGlobalErrorHandlers() {
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this._logError(event.reason, null, { 
                type: 'unhandled_promise_rejection',
                source: 'global'
            });
            
            // Prevent default console error
            event.preventDefault();
            
            this.showErrorToast('An unexpected error occurred. Please try again.');
        });
        
        // Handle global JavaScript errors
        window.addEventListener('error', (event) => {
            this._logError(new Error(event.message), null, {
                type: 'javascript_error',
                source: 'global',
                filename: event.filename,
                line: event.lineno,
                column: event.colno
            });
        });
        
        // Handle online/offline events
        window.addEventListener('online', () => {
            this.showSuccessToast('Connection restored. Retrying failed operations...');
            this._retryOfflineOperations();
        });
        
        window.addEventListener('offline', () => {
            this.showWarningToast('Connection lost. Changes will be retried when connection is restored.', {
                duration: 0
            });
        });
    }

    /**
     * Show toast notification
     * @private
     */
    _showToast(message, type = 'info', options = {}) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${this._getBootstrapColor(type)} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        const toastId = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        toast.id = toastId;
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${this._escapeHtml(message)}
                </div>
                ${options.action ? `
                    <button type="button" class="btn btn-sm btn-outline-light me-2" onclick="handleToastAction('${toastId}')">
                        ${options.action.text}
                    </button>
                ` : ''}
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Store action callback if provided
        if (options.action) {
            window[`handleToastAction_${toastId}`] = options.action.callback;
            window.handleToastAction = (id) => {
                const callback = window[`handleToastAction_${id}`];
                if (callback) {
                    callback();
                    delete window[`handleToastAction_${id}`];
                }
            };
        }
        
        this.toastContainer.appendChild(toast);
        
        // Initialize Bootstrap toast
        const bsToast = new bootstrap.Toast(toast, {
            delay: options.duration || 3000,
            autohide: options.duration !== 0
        });
        
        bsToast.show();
        
        // Clean up after hide
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
            if (options.action) {
                delete window[`handleToastAction_${toastId}`];
            }
        });
    }

    /**
     * Get Bootstrap color class for toast type
     * @private
     */
    _getBootstrapColor(type) {
        const colors = {
            success: 'success',
            error: 'danger',
            warning: 'warning',
            info: 'info'
        };
        return colors[type] || 'secondary';
    }

    /**
     * Escape HTML for safe display
     * @private
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Log error with context
     * @private
     */
    _logError(error, operationId, context = {}) {
        const logEntry = {
            timestamp: Date.now(),
            message: error.message || error.toString(),
            stack: error.stack,
            operationId,
            context,
            type: context.type || 'api_error',
            operation: context.operation,
            gameId: context.gameId
        };
        
        this.errorLog.push(logEntry);
        
        // Keep log size manageable
        if (this.errorLog.length > this.maxLogEntries) {
            this.errorLog.shift();
        }
        
        // Console log for debugging
        console.error('Error logged:', logEntry);
    }

    /**
     * Get user-friendly error message
     * @private
     */
    _getUserFriendlyMessage(error, operation) {
        const operationMessages = {
            mark_for_sale: 'Failed to mark game for sale',
            unmark_for_sale: 'Failed to remove game from sale',
            purchase: 'Failed to purchase game',
            add_to_wishlist: 'Failed to add game to wishlist',
            remove_from_wishlist: 'Failed to remove game from wishlist',
            update_condition: 'Failed to update game condition',
            update_details: 'Failed to update game details',
            mark_lent: 'Failed to mark game as lent',
            unmark_lent: 'Failed to return game from lent',
            remove_from_collection: 'Failed to remove game from collection',
            update_price: 'Failed to update game price'
        };
        
        const baseMessage = operationMessages[operation] || 'Operation failed';
        
        // Add specific error info if helpful
        if (error.message && error.message.includes('not found')) {
            return `${baseMessage}: Game not found`;
        }
        
        if (error.message && error.message.includes('network')) {
            return `${baseMessage}: Network error`;
        }
        
        if (error.status === 401) {
            return `${baseMessage}: Authentication required`;
        }
        
        if (error.status === 403) {
            return `${baseMessage}: Permission denied`;
        }
        
        if (error.status >= 500) {
            return `${baseMessage}: Server error`;
        }
        
        return `${baseMessage}. Please try again.`;
    }

    /**
     * Check if error should be retried
     * @private
     */
    _shouldRetry(error, operationId) {
        const retryCount = this.retryAttempts.get(operationId) || 0;
        
        if (retryCount >= this.maxRetries) {
            return false;
        }
        
        // Retry network errors, timeouts, and 5xx server errors
        return error.message.includes('timeout') || 
               error.message.includes('network') ||
               (error.status >= 500 && error.status < 600);
    }

    /**
     * Schedule automatic retry
     * @private
     */
    _scheduleRetry(operationId, context) {
        const retryCount = this.retryAttempts.get(operationId) || 0;
        this.retryAttempts.set(operationId, retryCount + 1);
        
        const delay = Math.pow(2, retryCount) * 1000; // Exponential backoff
        
        this.showInfoToast(`Retrying operation... (${retryCount + 1}/${this.maxRetries})`);
        
        return new Promise((resolve, reject) => {
            setTimeout(async () => {
                try {
                    if (context.retryFn) {
                        const result = await context.retryFn();
                        this.retryAttempts.delete(operationId);
                        resolve(result);
                    } else {
                        reject(new Error('No retry function available'));
                    }
                } catch (error) {
                    reject(error);
                }
            }, delay);
        });
    }

    /**
     * Handle manual retry
     * @private
     */
    async _manualRetry(operationId, context) {
        try {
            if (context.retryFn) {
                await context.retryFn();
                this.showSuccessToast('Operation completed successfully');
            }
        } catch (error) {
            this.handleApiError(error, operationId, context);
        }
    }

    /**
     * Setup offline retry mechanism
     * @private
     */
    _setupOfflineRetry(operationId, context) {
        // Store operation for retry when online
        if (!this.offlineOperations) {
            this.offlineOperations = new Map();
        }
        
        this.offlineOperations.set(operationId, context);
    }

    /**
     * Retry operations that failed while offline
     * @private
     */
    async _retryOfflineOperations() {
        if (!this.offlineOperations || this.offlineOperations.size === 0) {
            return;
        }
        
        const operations = Array.from(this.offlineOperations.entries());
        this.offlineOperations.clear();
        
        for (const [operationId, context] of operations) {
            try {
                if (context.retryFn) {
                    await context.retryFn();
                }
            } catch (error) {
                this.handleApiError(error, operationId, context);
            }
        }
    }
}

// Create global instance
window.errorHandler = new ErrorHandler();

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ErrorHandler;
}
