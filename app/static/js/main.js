/**
 * Main JavaScript file with optimistic updates for add game functionality
 * This file contains the enhanced add game functionality with optimistic updates
 */

(function() {
    'use strict';
    
    // Ensure required dependencies are available
    if (!window.gameStateManager || !window.optimisticUpdater || !window.errorHandler) {
        console.error('Required dependencies not loaded. Please ensure state-manager.js, optimistic-updater.js, and error-handler.js are loaded first.');
        return;
    }

    /**
     * Create a game card HTML element
     * @param {Object} game - Game object
     * @param {boolean} isWishlist - Whether this is a wishlist item
     * @returns {HTMLElement} - The created table row element
     */
    function createGameRow(game, isWishlist = false) {
        const tr = document.createElement('tr');
        tr.className = 'game-row';
        tr.dataset.gameId = game.id;
        tr.dataset.purchasedGameId = game.purchased_game_id || game.id;
        
        // Status column (for collection items)
        if (!isWishlist) {
            const statusTd = document.createElement('td');
            statusTd.className = 'status-col d-none d-md-table-cell text-center';
            
            const statusBadge = document.createElement('span');
            statusBadge.className = 'badge bg-success';
            statusBadge.textContent = game.is_wanted ? '❤️' : '✓';
            statusBadge.title = game.is_wanted ? 'Wanted' : 'Owned';
            
            statusTd.appendChild(statusBadge);
            tr.appendChild(statusTd);
        }
        
        // Name column
        const nameTd = document.createElement('td');
        nameTd.className = 'name-col';
        nameTd.innerHTML = `
            <div class="name-content">
                <span class="game-name">${game.name || 'Unknown'}</span>
                ${game.is_for_sale ? '<span class="badge bg-warning text-dark ms-2">For Sale</span>' : ''}
                ${game.is_lent_out ? '<span class="badge bg-info text-dark ms-2">Lent Out</span>' : ''}
            </div>
        `;
        tr.appendChild(nameTd);
        
        // Console column
        const consoleTd = document.createElement('td');
        consoleTd.className = 'console-col';
        consoleTd.textContent = game.console || 'Unknown';
        tr.appendChild(consoleTd);
        
        // Price column
        const priceTd = document.createElement('td');
        priceTd.className = 'price-col d-none d-md-table-cell';
        priceTd.textContent = game.current_price ? formatCurrency(game.current_price) : '-';
        tr.appendChild(priceTd);
        
        // Value change column (for collection items)
        if (!isWishlist) {
            const changeTd = document.createElement('td');
            changeTd.className = 'change-col d-none d-md-table-cell';
            if (game.current_price && game.purchase_price) {
                const change = ((game.current_price - game.purchase_price) / game.purchase_price * 100).toFixed(1);
                const sign = change >= 0 ? '+' : '';
                const color = change >= 0 ? 'success' : 'danger';
                changeTd.innerHTML = `<span class="text-${color}">${sign}${change}%</span>`;
            } else {
                changeTd.textContent = '-';
            }
            tr.appendChild(changeTd);
        }
        
        // Date column
        const dateTd = document.createElement('td');
        dateTd.className = 'date-col d-none d-md-table-cell';
        if (isWishlist) {
            dateTd.textContent = game.date_added ? new Date(game.date_added).toLocaleDateString() : '-';
        } else {
            dateTd.textContent = game.acquisition_date ? new Date(game.acquisition_date).toLocaleDateString() : '-';
        }
        tr.appendChild(dateTd);
        
        // Add click handler to expand details
        tr.addEventListener('click', function() {
            // This will be handled by the existing expandGameDetails function
            if (window.expandGameDetails) {
                window.expandGameDetails(game.id);
            }
        });
        
        return tr;
    }

    /**
     * Add a game row to the table with animation
     * @param {HTMLElement} row - The row to add
     * @param {string} tableId - The table ID
     * @param {boolean} prepend - Whether to prepend or append
     */
    function addGameRowToTable(row, tableId = 'collectionTable', prepend = true) {
        const tbody = document.querySelector(`#${tableId} tbody`);
        if (!tbody) {
            console.error(`Table body not found for ${tableId}`);
            return;
        }
        
        // Remove "No games found" message if present
        const noGamesRow = tbody.querySelector('tr td[colspan]');
        if (noGamesRow && noGamesRow.textContent.includes('No games found')) {
            noGamesRow.parentElement.remove();
        }
        
        // Add the row with animation
        row.style.opacity = '0';
        row.style.transform = 'translateY(-10px)';
        
        if (prepend) {
            tbody.insertBefore(row, tbody.firstChild);
        } else {
            tbody.appendChild(row);
        }
        
        // Trigger animation
        setTimeout(() => {
            row.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            row.style.opacity = '1';
            row.style.transform = 'translateY(0)';
        }, 10);
    }

    /**
     * Update result count and totals
     * @param {number} delta - Change in count (1 for add, -1 for remove)
     * @param {Object} game - Game object for price calculations
     */
    function updateResultCount(delta, game = null) {
        const resultCount = document.getElementById('resultCount');
        if (!resultCount) return;
        
        // Parse current count
        const currentText = resultCount.innerHTML;
        const countMatch = currentText.match(/Showing (\d+)-(\d+) of (\d+)/);
        
        if (countMatch) {
            let [_, start, end, total] = countMatch.map(Number);
            total += delta;
            
            if (delta > 0) {
                // Adding a game
                end = Math.min(end + delta, total);
            } else {
                // Removing a game
                end = Math.max(start, end + delta);
            }
            
            // Update totals if game object provided
            let totalsText = '';
            if (game && window.collectionTotals) {
                if (game.purchase_price) {
                    window.collectionTotals.totalAcquisition = (window.collectionTotals.totalAcquisition || 0) + 
                        (delta * game.purchase_price);
                }
                if (game.current_price) {
                    window.collectionTotals.totalCurrent = (window.collectionTotals.totalCurrent || 0) + 
                        (delta * game.current_price);
                }
                
                totalsText = `<br><small class="text-muted">Total Acquired: ${formatCurrency(window.collectionTotals.totalAcquisition)} | Current Value: ${formatCurrency(window.collectionTotals.totalCurrent)}</small>`;
            }
            
            resultCount.innerHTML = `Showing ${start}-${end} of ${total} results${totalsText}`;
        }
    }

    /**
     * Format currency helper
     */
    function formatCurrency(value) {
        if (value === null || value === undefined || isNaN(value)) return '-';
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
    }

    /**
     * Enhanced add game to wishlist with optimistic updates
     */
    window.addToWishlistOptimistic = async function(gameData) {
        // Generate a temporary ID for the new game
        const tempId = `temp_${Date.now()}`;
        const optimisticGame = {
            ...gameData,
            id: tempId,
            is_wanted: true,
            date_added: new Date().toISOString()
        };
        
        // UI update function
        const uiUpdateFn = () => {
            // Add to state manager
            window.gameStateManager.addGame(optimisticGame);
            
            // Create and add the game row
            const row = createGameRow(optimisticGame, true);
            addGameRowToTable(row, 'collectionTable', true);
            
            // Update count
            updateResultCount(1, optimisticGame);
            
            // Add to allGames array if it exists
            if (window.allGames) {
                window.allGames.unshift(optimisticGame);
            }
        };
        
        // API call function
        const apiFn = async () => {
            const response = await fetch('/api/wishlist/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(gameData)
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to add game to wishlist');
            }
            
            return data;
        };
        
        // Rollback function
        const rollbackFn = () => {
            // Remove from state manager
            window.gameStateManager.removeGame(tempId);
            
            // Remove from DOM
            const row = document.querySelector(`tr[data-game-id="${tempId}"]`);
            if (row) {
                row.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                row.style.opacity = '0';
                row.style.transform = 'translateY(-10px)';
                setTimeout(() => row.remove(), 300);
            }
            
            // Update count
            updateResultCount(-1, optimisticGame);
            
            // Remove from allGames array
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id === tempId);
                if (index !== -1) {
                    window.allGames.splice(index, 1);
                }
            }
        };
        
        try {
            const result = await window.optimisticUpdater.applyOptimisticUpdate(
                tempId,
                'add_to_wishlist',
                uiUpdateFn,
                apiFn,
                {
                    rollbackFn,
                    onSuccess: (data) => {
                        // Update the temporary ID with the real ID
                        const realGame = data.game;
                        window.gameStateManager.removeGame(tempId);
                        window.gameStateManager.addGame(realGame);
                        
                        // Update the row's data attributes
                        const row = document.querySelector(`tr[data-game-id="${tempId}"]`);
                        if (row) {
                            row.dataset.gameId = realGame.id;
                            row.dataset.purchasedGameId = realGame.purchased_game_id || realGame.id;
                        }
                        
                        // Update in allGames array
                        if (window.allGames) {
                            const index = window.allGames.findIndex(g => g.id === tempId);
                            if (index !== -1) {
                                window.allGames[index] = realGame;
                            }
                        }
                        
                        // Show success message
                        window.errorHandler.showSuccess(
                            `Added ${realGame.name} (${realGame.console}) to your wishlist!`
                        );
                    },
                    onError: (error) => {
                        window.errorHandler.showError(
                            error.message || 'Failed to add game to wishlist'
                        );
                    }
                }
            );
            
            return result;
        } catch (error) {
            console.error('Error in optimistic wishlist add:', error);
            throw error;
        }
    };

    /**
     * Enhanced add game to collection with optimistic updates
     */
    window.addToCollectionOptimistic = async function(gameData) {
        // Generate a temporary ID for the new game
        const tempId = `temp_${Date.now()}`;
        const optimisticGame = {
            ...gameData,
            id: tempId,
            purchased_game_id: tempId,
            is_wanted: false,
            acquisition_date: gameData.purchase_date || new Date().toISOString()
        };
        
        // UI update function
        const uiUpdateFn = () => {
            // Add to state manager
            window.gameStateManager.addGame(optimisticGame);
            
            // Create and add the game row
            const row = createGameRow(optimisticGame, false);
            addGameRowToTable(row, 'collectionTable', true);
            
            // Update count and totals
            updateResultCount(1, optimisticGame);
            
            // Add to allGames array if it exists
            if (window.allGames) {
                window.allGames.unshift(optimisticGame);
            }
        };
        
        // API call function
        const apiFn = async () => {
            const response = await fetch('/api/collection/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(gameData)
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to add game to collection');
            }
            
            return data;
        };
        
        // Rollback function
        const rollbackFn = () => {
            // Remove from state manager
            window.gameStateManager.removeGame(tempId);
            
            // Remove from DOM
            const row = document.querySelector(`tr[data-game-id="${tempId}"]`);
            if (row) {
                row.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                row.style.opacity = '0';
                row.style.transform = 'translateY(-10px)';
                setTimeout(() => row.remove(), 300);
            }
            
            // Update count and totals
            updateResultCount(-1, optimisticGame);
            
            // Remove from allGames array
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id === tempId);
                if (index !== -1) {
                    window.allGames.splice(index, 1);
                }
            }
        };
        
        try {
            const result = await window.optimisticUpdater.applyOptimisticUpdate(
                tempId,
                'add_to_collection',
                uiUpdateFn,
                apiFn,
                {
                    rollbackFn,
                    onSuccess: (data) => {
                        // Update the temporary ID with the real ID
                        const realGame = data.game;
                        window.gameStateManager.removeGame(tempId);
                        window.gameStateManager.addGame(realGame);
                        
                        // Update the row's data attributes
                        const row = document.querySelector(`tr[data-game-id="${tempId}"]`);
                        if (row) {
                            row.dataset.gameId = realGame.id;
                            row.dataset.purchasedGameId = realGame.purchased_game_id || realGame.id;
                        }
                        
                        // Update in allGames array
                        if (window.allGames) {
                            const index = window.allGames.findIndex(g => g.id === tempId);
                            if (index !== -1) {
                                window.allGames[index] = realGame;
                            }
                        }
                        
                        // Show success message
                        window.errorHandler.showSuccess(
                            `Added ${realGame.name} (${realGame.console}) to your collection!`
                        );
                    },
                    onError: (error) => {
                        window.errorHandler.showError(
                            error.message || 'Failed to add game to collection'
                        );
                    }
                }
            );
            
            return result;
        } catch (error) {
            console.error('Error in optimistic collection add:', error);
            throw error;
        }
    };

    /**
     * Remove a game row from the table with animation
     * @param {string|number} gameId - The game ID
     * @param {Function} onComplete - Callback after animation completes
     */
    function removeGameRowFromTable(gameId, onComplete) {
        const row = document.querySelector(`tr[data-game-id="${gameId}"]`);
        if (!row) {
            console.warn(`Row not found for game ID: ${gameId}`);
            if (onComplete) onComplete();
            return;
        }
        
        // Animate removal
        row.style.transition = 'opacity 0.3s ease, transform 0.3s ease, height 0.3s ease';
        row.style.opacity = '0';
        row.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            row.remove();
            if (onComplete) onComplete();
        }, 300);
    }

    /**
     * Enhanced remove from wishlist with optimistic updates
     */
    window.removeFromWishlistOptimistic = async function(gameId, gameName, gameConsole) {
        // Get the game from state or create minimal object
        let game = window.gameStateManager.getGame(gameId);
        if (!game) {
            // Create minimal game object for UI updates
            game = { id: gameId, name: gameName, console: gameConsole, is_wanted: true };
        }
        
        // Store snapshot for rollback
        const snapshot = {
            game: { ...game },
            rowHtml: document.querySelector(`tr[data-game-id="${gameId}"]`)?.outerHTML
        };
        
        // UI update function
        const uiUpdateFn = () => {
            // Remove from DOM with animation
            removeGameRowFromTable(gameId);
            
            // Update count
            updateResultCount(-1, game);
            
            // Remove from state manager
            window.gameStateManager.removeGame(gameId);
            
            // Remove from allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames.splice(index, 1);
                }
            }
        };
        
        // API call function
        const apiFn = async () => {
            const response = await fetch(`/api/wishlist/${gameId}/remove`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || 'Failed to remove game from wishlist');
            }
            
            return result;
        };
        
        // Rollback function
        const rollbackFn = () => {
            // Restore to state manager
            window.gameStateManager.addGame(snapshot.game);
            
            // Restore the row if we have the HTML
            if (snapshot.rowHtml) {
                const tbody = document.querySelector('#collectionTable tbody');
                if (tbody) {
                    // Create temporary container to parse HTML
                    const temp = document.createElement('tbody');
                    temp.innerHTML = snapshot.rowHtml;
                    const restoredRow = temp.firstChild;
                    
                    // Find the right position to insert (maintain sort order)
                    let inserted = false;
                    const rows = tbody.querySelectorAll('tr');
                    for (let row of rows) {
                        if (row.dataset.gameId && parseInt(row.dataset.gameId) > parseInt(gameId)) {
                            tbody.insertBefore(restoredRow, row);
                            inserted = true;
                            break;
                        }
                    }
                    if (!inserted) {
                        tbody.appendChild(restoredRow);
                    }
                    
                    // Animate restoration
                    restoredRow.style.opacity = '0';
                    restoredRow.style.transform = 'translateX(-20px)';
                    setTimeout(() => {
                        restoredRow.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                        restoredRow.style.opacity = '1';
                        restoredRow.style.transform = 'translateX(0)';
                    }, 10);
                }
            }
            
            // Update count
            updateResultCount(1, snapshot.game);
            
            // Restore to allGames array
            if (window.allGames) {
                window.allGames.push(snapshot.game);
            }
        };
        
        try {
            const result = await window.optimisticUpdater.applyOptimisticUpdate(
                gameId,
                'remove_from_wishlist',
                uiUpdateFn,
                apiFn,
                {
                    rollbackFn,
                    onSuccess: () => {
                        // Show success message
                        window.errorHandler.showSuccess(
                            `"${gameName}" has been removed from your wishlist`
                        );
                        
                        // Close modal if open
                        const modal = document.getElementById('removeWishlistModal');
                        if (modal) {
                            const bootstrapModal = bootstrap.Modal.getInstance(modal);
                            if (bootstrapModal) {
                                bootstrapModal.hide();
                            }
                        }
                    },
                    onError: (error) => {
                        window.errorHandler.showError(
                            error.message || 'Failed to remove game from wishlist'
                        );
                    }
                }
            );
            
            return result;
        } catch (error) {
            console.error('Error in optimistic wishlist removal:', error);
            throw error;
        }
    };

    /**
     * Enhanced remove from collection with optimistic updates
     */
    window.removeFromCollectionOptimistic = async function(purchasedGameId, gameId, gameName, gameConsole) {
        // Get the game from state or create minimal object
        let game = window.gameStateManager.getGame(gameId);
        if (!game) {
            // Create minimal game object for UI updates
            game = { 
                id: gameId, 
                purchased_game_id: purchasedGameId,
                name: gameName, 
                console: gameConsole, 
                is_wanted: false 
            };
        }
        
        // Store snapshot for rollback
        const snapshot = {
            game: { ...game },
            rowHtml: document.querySelector(`tr[data-game-id="${gameId}"]`)?.outerHTML
        };
        
        // UI update function
        const uiUpdateFn = () => {
            // Remove from DOM with animation
            removeGameRowFromTable(gameId);
            
            // Update count and totals
            updateResultCount(-1, game);
            
            // Remove from state manager
            window.gameStateManager.removeGame(gameId);
            
            // Remove from allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId || g.purchased_game_id == purchasedGameId);
                if (index !== -1) {
                    window.allGames.splice(index, 1);
                }
            }
        };
        
        // API call function
        const apiFn = async () => {
            const response = await fetch(`/api/purchased_game/${purchasedGameId}/remove_from_collection`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to remove game from collection');
            }
            
            return await response.json();
        };
        
        // Rollback function
        const rollbackFn = () => {
            // Restore to state manager
            window.gameStateManager.addGame(snapshot.game);
            
            // Restore the row if we have the HTML
            if (snapshot.rowHtml) {
                const tbody = document.querySelector('#collectionTable tbody');
                if (tbody) {
                    // Create temporary container to parse HTML
                    const temp = document.createElement('tbody');
                    temp.innerHTML = snapshot.rowHtml;
                    const restoredRow = temp.firstChild;
                    
                    // Find the right position to insert (maintain sort order)
                    let inserted = false;
                    const rows = tbody.querySelectorAll('tr');
                    for (let row of rows) {
                        if (row.dataset.gameId && parseInt(row.dataset.gameId) > parseInt(gameId)) {
                            tbody.insertBefore(restoredRow, row);
                            inserted = true;
                            break;
                        }
                    }
                    if (!inserted) {
                        tbody.appendChild(restoredRow);
                    }
                    
                    // Animate restoration
                    restoredRow.style.opacity = '0';
                    restoredRow.style.transform = 'translateX(-20px)';
                    setTimeout(() => {
                        restoredRow.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                        restoredRow.style.opacity = '1';
                        restoredRow.style.transform = 'translateX(0)';
                    }, 10);
                }
            }
            
            // Update count and totals
            updateResultCount(1, snapshot.game);
            
            // Restore to allGames array
            if (window.allGames) {
                window.allGames.push(snapshot.game);
            }
        };
        
        try {
            const result = await window.optimisticUpdater.applyOptimisticUpdate(
                gameId,
                'remove_from_collection',
                uiUpdateFn,
                apiFn,
                {
                    rollbackFn,
                    onSuccess: () => {
                        // Show success message
                        window.errorHandler.showSuccess(
                            `"${gameName}" has been removed from your collection`
                        );
                        
                        // Close modal if open
                        const modal = document.getElementById('removeFromCollectionModal');
                        if (modal) {
                            const bootstrapModal = bootstrap.Modal.getInstance(modal);
                            if (bootstrapModal) {
                                bootstrapModal.hide();
                            }
                        }
                    },
                    onError: (error) => {
                        window.errorHandler.showError(
                            error.message || 'Failed to remove game from collection'
                        );
                    }
                }
            );
            
            return result;
        } catch (error) {
            console.error('Error in optimistic collection removal:', error);
            throw error;
        }
    };

    // Export functions for use in other scripts
    window.createGameRow = createGameRow;
    window.addGameRowToTable = addGameRowToTable;
    window.updateResultCount = updateResultCount;
    window.removeGameRowFromTable = removeGameRowFromTable;
    
})();