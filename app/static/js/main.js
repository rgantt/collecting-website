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
            
            // Create and add the game row with fade-in animation
            const row = createGameRow(optimisticGame, true);
            row.classList.add('fade-in');
            addGameRowToTable(row, 'collectionTable', true);
            
            // Set pending state
            window.LoadingStateManager?.setRowState(tempId, 'pending');
            
            // Update count
            updateResultCount(1, optimisticGame);
            
            // Add to allGames array if it exists
            if (window.allGames) {
                window.allGames.unshift(optimisticGame);
            }
        };
        
        // API call function with loading state
        const apiFn = async () => {
            window.LoadingStateManager?.showSyncIndicator('Adding to wishlist...');
            
            try {
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
                
                // Set success state
                window.LoadingStateManager?.setRowState(tempId, 'success');
                window.LoadingStateManager?.hideSyncIndicator('success');
                
                return data;
            } catch (error) {
                window.LoadingStateManager?.setRowState(tempId, 'error');
                window.LoadingStateManager?.hideSyncIndicator('error');
                throw error;
            }
        };
        
        // Rollback function with fade-out animation
        const rollbackFn = () => {
            // Remove from state manager
            window.gameStateManager.removeGame(tempId);
            
            // Remove from DOM with fade-out animation
            const row = document.querySelector(`tr[data-game-id="${tempId}"]`);
            if (row) {
                window.LoadingStateManager?.setRowState(tempId, 'fade-out');
                setTimeout(() => row.remove(), 400);
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
     * Enhanced purchase conversion with optimistic updates
     * Converts wishlist item to purchased collection item
     */
    window.purchaseWishlistGameOptimistic = async function(gameId, gameName, gameConsole, purchaseData) {
        // Get the game from state or create enhanced object
        let wishlistGame = window.gameStateManager.getGame(gameId);
        if (!wishlistGame) {
            wishlistGame = { 
                id: gameId, 
                name: gameName, 
                console: gameConsole, 
                is_wanted: true 
            };
        }
        
        // Create the purchased game object with purchase data
        const purchasedGame = {
            ...wishlistGame,
            id: gameId,
            purchased_game_id: gameId, // Will be updated with real ID from API
            is_wanted: false,
            purchase_date: purchaseData.purchase_date,
            purchase_source: purchaseData.purchase_source,
            purchase_price: parseFloat(purchaseData.purchase_price) || null,
            acquisition_date: purchaseData.purchase_date,
            current_price: wishlistGame.current_price || null
        };
        
        // Store snapshot for rollback
        const snapshot = {
            wishlistGame: { ...wishlistGame },
            wishlistRowHtml: document.querySelector(`tr[data-game-id="${gameId}"]`)?.outerHTML
        };
        
        // UI update function
        const uiUpdateFn = () => {
            // Remove from wishlist section (with animation)
            removeGameRowFromTable(gameId);
            
            // Update state manager - remove wishlist, add collection
            window.gameStateManager.removeGame(gameId);
            window.gameStateManager.addGame(purchasedGame);
            
            // Create and add to collection section
            const newRow = createGameRow(purchasedGame, false); // false = not wishlist
            addGameRowToTable(newRow, 'collectionTable', true);
            
            // Update counts and totals
            updateResultCount(0, purchasedGame); // Net change is 0 (moved between sections)
            
            // Update in allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames[index] = purchasedGame;
                } else {
                    window.allGames.unshift(purchasedGame);
                }
            }
        };
        
        // API call function
        const apiFn = async () => {
            const response = await fetch(`/api/wishlist/${gameId}/purchase`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(purchaseData)
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to purchase game');
            }
            
            return data;
        };
        
        // Rollback function
        const rollbackFn = () => {
            // Remove from collection state
            window.gameStateManager.removeGame(gameId);
            
            // Restore to wishlist state
            window.gameStateManager.addGame(snapshot.wishlistGame);
            
            // Remove from collection DOM
            const collectionRow = document.querySelector(`tr[data-game-id="${gameId}"]`);
            if (collectionRow) {
                collectionRow.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                collectionRow.style.opacity = '0';
                collectionRow.style.transform = 'translateX(-20px)';
                setTimeout(() => collectionRow.remove(), 300);
            }
            
            // Restore wishlist row if we have the HTML
            if (snapshot.wishlistRowHtml) {
                const tbody = document.querySelector('#collectionTable tbody');
                if (tbody) {
                    // Create temporary container to parse HTML
                    const temp = document.createElement('tbody');
                    temp.innerHTML = snapshot.wishlistRowHtml;
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
            
            // Update counts
            updateResultCount(0, snapshot.wishlistGame); // Restore original state
            
            // Restore in allGames array
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames[index] = snapshot.wishlistGame;
                }
            }
        };
        
        try {
            const result = await window.optimisticUpdater.applyOptimisticUpdate(
                gameId,
                'purchase_conversion',
                uiUpdateFn,
                apiFn,
                {
                    rollbackFn,
                    onSuccess: (data) => {
                        // Update with real purchased game ID and data from server
                        const serverGame = data.game;
                        
                        // Update state with server response
                        window.gameStateManager.removeGame(gameId);
                        window.gameStateManager.addGame({
                            ...purchasedGame,
                            ...serverGame,
                            purchased_game_id: serverGame.purchased_game_id || serverGame.id
                        });
                        
                        // Update the row's data attributes with real IDs
                        const row = document.querySelector(`tr[data-game-id="${gameId}"]`);
                        if (row && serverGame.purchased_game_id) {
                            row.dataset.purchasedGameId = serverGame.purchased_game_id;
                        }
                        
                        // Update in allGames array
                        if (window.allGames) {
                            const index = window.allGames.findIndex(g => g.id == gameId);
                            if (index !== -1) {
                                window.allGames[index] = { ...purchasedGame, ...serverGame };
                            }
                        }
                        
                        // Show success message
                        window.errorHandler.showSuccess(
                            data.message || `Successfully purchased ${gameName}!`
                        );
                        
                        // Close purchase modal if open
                        const modal = document.getElementById('purchaseModal');
                        if (modal) {
                            const bootstrapModal = bootstrap.Modal.getInstance(modal);
                            if (bootstrapModal) {
                                bootstrapModal.hide();
                            }
                        }
                    },
                    onError: (error) => {
                        window.errorHandler.showError(
                            error.message || 'Failed to purchase game'
                        );
                    }
                }
            );
            
            return result;
        } catch (error) {
            console.error('Error in optimistic purchase conversion:', error);
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

    /**
     * Enhanced mark as lent with optimistic updates
     */
    window.markGameAsLentOptimistic = async function(gameId, gameName, gameConsole, lentData) {
        // Get the game from state or create minimal object
        let game = window.gameStateManager.getGame(gameId);
        if (!game) {
            game = { 
                id: gameId, 
                name: gameName, 
                console: gameConsole, 
                is_wanted: false,
                is_lent: false
            };
        }
        
        // Create the lent game object
        const lentGame = {
            ...game,
            is_lent: true,
            lent_date: lentData.lent_date,
            lent_to: lentData.lent_to
        };
        
        // Store snapshot for rollback
        const snapshot = {
            originalGame: { ...game },
            rowHtml: document.querySelector(`tr[data-game-id="${gameId}"]`)?.outerHTML
        };
        
        // UI update function
        const uiUpdateFn = () => {
            // Update state manager
            window.gameStateManager.updateGame(lentGame);
            
            // Update the game row to show lent status
            const row = document.querySelector(`tr[data-game-id="${gameId}"]`);
            if (row) {
                // Update status badge and actions
                const statusCell = row.querySelector('.name-col .name-content');
                if (statusCell) {
                    // Remove existing status badges
                    const existingBadges = statusCell.querySelectorAll('.badge');
                    existingBadges.forEach(badge => {
                        if (!badge.textContent.includes('For Sale')) {
                            badge.remove();
                        }
                    });
                    
                    // Add lent out badge
                    const lentBadge = document.createElement('span');
                    lentBadge.className = 'badge bg-info text-dark ms-2';
                    lentBadge.textContent = 'Lent Out';
                    statusCell.appendChild(lentBadge);
                }
                
                // Update expanded detail view if it exists and is open for this game
                const expandedRow = row.nextElementSibling;
                if (expandedRow && expandedRow.classList.contains('details-row')) {
                    // Re-render the expanded content with new lent status
                    // This will be handled by the existing game detail rendering logic
                }
            }
            
            // Update in allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames[index] = lentGame;
                }
            }
        };
        
        // API call function
        const apiFn = async () => {
            const response = await fetch(`/api/game/${gameId}/mark_as_lent`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(lentData)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to mark game as lent out');
            }
            
            return await response.json();
        };
        
        // Rollback function
        const rollbackFn = () => {
            // Restore original state
            window.gameStateManager.updateGame(snapshot.originalGame);
            
            // Restore the row HTML if available
            if (snapshot.rowHtml) {
                const currentRow = document.querySelector(`tr[data-game-id="${gameId}"]`);
                if (currentRow) {
                    // Create temporary container to parse HTML
                    const temp = document.createElement('tbody');
                    temp.innerHTML = snapshot.rowHtml;
                    const restoredRow = temp.firstChild;
                    
                    // Replace current row with original
                    currentRow.parentNode.replaceChild(restoredRow, currentRow);
                }
            }
            
            // Restore in allGames array
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames[index] = snapshot.originalGame;
                }
            }
        };
        
        try {
            const result = await window.optimisticUpdater.applyOptimisticUpdate(
                gameId,
                'mark_as_lent',
                uiUpdateFn,
                apiFn,
                {
                    rollbackFn,
                    onSuccess: (data) => {
                        // Show success message
                        window.errorHandler.showSuccess(
                            'Game marked as lent out successfully!'
                        );
                        
                        // Phase 3: Background refresh to ensure data accuracy
                        setTimeout(() => {
                            window.refreshGame(gameId).catch(err => 
                                console.log('Background refresh failed (non-critical):', err)
                            );
                        }, 1000);
                        
                        // Close modal if open
                        const modal = document.getElementById('markLentModal');
                        if (modal) {
                            const bootstrapModal = bootstrap.Modal.getInstance(modal);
                            if (bootstrapModal) {
                                bootstrapModal.hide();
                            }
                        }
                    },
                    onError: (error) => {
                        window.errorHandler.showError(
                            error.message || 'Failed to mark game as lent out'
                        );
                    }
                }
            );
            
            return result;
        } catch (error) {
            console.error('Error in optimistic mark as lent:', error);
            throw error;
        }
    };

    /**
     * Enhanced return from lent with optimistic updates
     */
    window.unmarkGameAsLentOptimistic = async function(gameId, gameName, gameConsole) {
        // Get the game from state or create minimal object
        let game = window.gameStateManager.getGame(gameId);
        if (!game) {
            game = { 
                id: gameId, 
                name: gameName, 
                console: gameConsole, 
                is_wanted: false,
                is_lent: true
            };
        }
        
        // Create the returned game object
        const returnedGame = {
            ...game,
            is_lent: false,
            lent_date: null,
            lent_to: null
        };
        
        // Store snapshot for rollback
        const snapshot = {
            originalGame: { ...game },
            rowHtml: document.querySelector(`tr[data-game-id="${gameId}"]`)?.outerHTML
        };
        
        // UI update function
        const uiUpdateFn = () => {
            // Update state manager
            window.gameStateManager.updateGame(returnedGame);
            
            // Update the game row to remove lent status
            const row = document.querySelector(`tr[data-game-id="${gameId}"]`);
            if (row) {
                // Remove lent out badge
                const statusCell = row.querySelector('.name-col .name-content');
                if (statusCell) {
                    const lentBadge = statusCell.querySelector('.badge.bg-info');
                    if (lentBadge && lentBadge.textContent.includes('Lent Out')) {
                        lentBadge.remove();
                    }
                }
                
                // Update expanded detail view if it exists and is open for this game
                const expandedRow = row.nextElementSibling;
                if (expandedRow && expandedRow.classList.contains('details-row')) {
                    // Re-render the expanded content without lent status
                    // This will be handled by the existing game detail rendering logic
                }
            }
            
            // Update in allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames[index] = returnedGame;
                }
            }
        };
        
        // API call function
        const apiFn = async () => {
            const response = await fetch(`/api/game/${gameId}/unmark_as_lent`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to mark game as returned');
            }
            
            return await response.json();
        };
        
        // Rollback function
        const rollbackFn = () => {
            // Restore original state
            window.gameStateManager.updateGame(snapshot.originalGame);
            
            // Restore the row HTML if available
            if (snapshot.rowHtml) {
                const currentRow = document.querySelector(`tr[data-game-id="${gameId}"]`);
                if (currentRow) {
                    // Create temporary container to parse HTML
                    const temp = document.createElement('tbody');
                    temp.innerHTML = snapshot.rowHtml;
                    const restoredRow = temp.firstChild;
                    
                    // Replace current row with original
                    currentRow.parentNode.replaceChild(restoredRow, currentRow);
                }
            }
            
            // Restore in allGames array
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames[index] = snapshot.originalGame;
                }
            }
        };
        
        try {
            const result = await window.optimisticUpdater.applyOptimisticUpdate(
                gameId,
                'unmark_as_lent',
                uiUpdateFn,
                apiFn,
                {
                    rollbackFn,
                    onSuccess: (data) => {
                        // Show success message
                        window.errorHandler.showSuccess(
                            'Game marked as returned successfully!'
                        );
                        
                        // Phase 3: Background refresh to ensure data accuracy
                        setTimeout(() => {
                            window.refreshGame(gameId).catch(err => 
                                console.log('Background refresh failed (non-critical):', err)
                            );
                        }, 1000);
                        
                        // Close modal if open
                        const modal = document.getElementById('unmarkLentModal');
                        if (modal) {
                            const bootstrapModal = bootstrap.Modal.getInstance(modal);
                            if (bootstrapModal) {
                                bootstrapModal.hide();
                            }
                        }
                    },
                    onError: (error) => {
                        window.errorHandler.showError(
                            error.message || 'Failed to mark game as returned'
                        );
                    }
                }
            );
            
            return result;
        } catch (error) {
            console.error('Error in optimistic return from lent:', error);
            throw error;
        }
    };

    // Optimistic edit game details function
    window.editGameDetailsOptimistic = async function(gameId, newName, newConsole) {
        const tempId = `edit_${gameId}_${Date.now()}`;
        const originalGame = window.gameStateManager.getGame(gameId);
        
        if (!originalGame) {
            throw new Error(`Game with ID ${gameId} not found in state manager`);
        }
        
        console.log('🎯 Starting optimistic edit details for:', gameId, newName, newConsole);
        
        // Create updated game object
        const updatedGame = {
            ...originalGame,
            name: newName,
            console: newConsole
        };
        
        // UI update function - immediately update all locations where game details appear
        const uiUpdateFn = () => {
            console.log('📝 Applying optimistic edit details UI updates');
            
            // Update in state manager
            window.gameStateManager.updateGame(updatedGame);
            
            // Update table row
            const tableRow = document.querySelector(`tr.game-row[data-game-id="${gameId}"]`);
            if (tableRow) {
                const nameCell = tableRow.querySelector('.name-col');
                const consoleCell = tableRow.querySelector('.console-col');
                if (nameCell) {
                    nameCell.textContent = newName;
                    nameCell.title = newName;
                }
                if (consoleCell) {
                    consoleCell.textContent = newConsole;
                    consoleCell.title = newConsole;
                }
            }
            
            // Update expanded details view
            const nameDisplay = document.querySelector(`[data-game-id="${gameId}"] .full-name`);
            const consoleDisplay = document.getElementById(`console-display-${gameId}`);
            
            if (nameDisplay) {
                nameDisplay.textContent = newName;
            }
            if (consoleDisplay) {
                consoleDisplay.textContent = newConsole;
            }
            
            // Update edit button data attributes
            const editBtn = document.querySelector(`[data-game-id="${gameId}"].edit-details-btn`);
            if (editBtn) {
                editBtn.dataset.gameName = newName;
                editBtn.dataset.gameConsole = newConsole;
            }
            
            // Update modal data attributes if open
            const modal = document.getElementById('editDetailsModal');
            if (modal && modal.dataset.gameId === gameId.toString()) {
                modal.dataset.gameName = newName;
                modal.dataset.gameConsole = newConsole;
            }
            
            // Update in allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames[index] = updatedGame;
                }
            }
        };
        
        // API call function
        const apiFn = async () => {
            console.log('📡 Making edit details API call for:', gameId);
            const response = await fetch(`/api/game/${gameId}/details`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: newName,
                    console: newConsole
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to update game details');
            }
            
            return response.json();
        };
        
        // Rollback function - restore original values
        const rollbackFn = () => {
            console.log('⏪ Rolling back edit details for:', gameId);
            
            // Restore in state manager
            window.gameStateManager.updateGame(originalGame);
            
            // Restore table row
            const tableRow = document.querySelector(`tr.game-row[data-game-id="${gameId}"]`);
            if (tableRow) {
                const nameCell = tableRow.querySelector('.name-col');
                const consoleCell = tableRow.querySelector('.console-col');
                if (nameCell) {
                    nameCell.textContent = originalGame.name;
                    nameCell.title = originalGame.name;
                }
                if (consoleCell) {
                    consoleCell.textContent = originalGame.console;
                    consoleCell.title = originalGame.console;
                }
            }
            
            // Restore expanded details view
            const nameDisplay = document.querySelector(`[data-game-id="${gameId}"] .full-name`);
            const consoleDisplay = document.getElementById(`console-display-${gameId}`);
            
            if (nameDisplay) {
                nameDisplay.textContent = originalGame.name;
            }
            if (consoleDisplay) {
                consoleDisplay.textContent = originalGame.console;
            }
            
            // Restore edit button data attributes
            const editBtn = document.querySelector(`[data-game-id="${gameId}"].edit-details-btn`);
            if (editBtn) {
                editBtn.dataset.gameName = originalGame.name;
                editBtn.dataset.gameConsole = originalGame.console;
            }
            
            // Restore in allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames[index] = originalGame;
                }
            }
        };
        
        try {
            const result = await window.optimisticUpdater.applyOptimisticUpdate(
                tempId,
                'edit_details',
                uiUpdateFn,
                apiFn,
                {
                    rollbackFn,
                    onSuccess: (result) => {
                        console.log('✅ Edit details completed successfully:', result);
                        window.errorHandler.showSuccess('Game details updated successfully!');
                        
                        // Phase 3: Background refresh to ensure data accuracy
                        setTimeout(() => {
                            window.refreshGame(gameId).catch(err => 
                                console.log('Background refresh failed (non-critical):', err)
                            );
                        }, 1000); // 1 second delay to let server process complete
                    },
                    onError: (error) => {
                        console.error('❌ Edit details failed:', error);
                        window.errorHandler.showError(
                            'Failed to update game details: ' + 
                            (error.message || 'An unexpected error occurred')
                        );
                    }
                }
            );
            
            return result;
        } catch (error) {
            console.error('Error in optimistic edit details:', error);
            throw error;
        }
    };

    // Selective game data refresh function (Phase 3)
    window.refreshGame = async function(gameId) {
        console.log('🔄 Starting selective refresh for game:', gameId);
        
        try {
            // Fetch fresh game data from server
            const response = await fetch(`/api/game/${gameId}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    console.log('⚠️ Game not found during refresh, may have been deleted:', gameId);
                    // Handle deleted game - remove from client state
                    handleDeletedGameRefresh(gameId);
                    return null;
                }
                throw new Error(`Failed to refresh game data: ${response.status}`);
            }
            
            const result = await response.json();
            const freshGameData = result.game;
            
            console.log('📥 Received fresh game data:', freshGameData);
            
            // Get current client state
            const currentGameData = window.gameStateManager.getGame(gameId);
            
            if (!currentGameData) {
                console.log('⚠️ Game not in client state, adding:', gameId);
                // Game exists on server but not in client state - add it
                window.gameStateManager.addGame(freshGameData);
                // Game was added elsewhere - simply add to client state
                // The optimistic UI system handles all game additions via optimistic operations
                console.log('ℹ️ New game detected and added to client state');
                return freshGameData;
            }
            
            // Perform differential update - only change what's different
            const changes = detectGameDataChanges(currentGameData, freshGameData);
            
            if (Object.keys(changes).length === 0) {
                console.log('✅ No changes detected for game:', gameId);
                return currentGameData;
            }
            
            console.log('🔄 Applying differential update with changes:', changes);
            
            // Update client state
            window.gameStateManager.updateGame(freshGameData);
            
            // Apply differential DOM updates
            applyGameDataChanges(gameId, changes, freshGameData);
            
            // Update allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames[index] = freshGameData;
                } else {
                    window.allGames.unshift(freshGameData);
                }
            }
            
            console.log('✅ Successfully refreshed game:', gameId);
            return freshGameData;
            
        } catch (error) {
            console.error('❌ Error refreshing game data:', error);
            // Don't show error to user for background refresh failures
            // Just log and continue - optimistic state remains unchanged
            return null;
        }
    };
    
    // Helper function to detect changes between current and fresh game data
    function detectGameDataChanges(current, fresh) {
        const changes = {};
        
        // Fields to check for changes
        const fieldsToCheck = [
            'name', 'console', 'condition', 'purchase_price', 'current_price',
            'is_wanted', 'is_lent', 'is_for_sale', 'lent_date', 'lent_to', 
            'asking_price', 'sale_notes', 'source_name'
        ];
        
        for (const field of fieldsToCheck) {
            if (current[field] !== fresh[field]) {
                changes[field] = {
                    from: current[field],
                    to: fresh[field]
                };
            }
        }
        
        return changes;
    }
    
    // Helper function to apply differential changes to DOM
    function applyGameDataChanges(gameId, changes, freshData) {
        console.log('🎯 Applying DOM changes for game:', gameId, changes);
        
        // Update table row if it exists
        const tableRow = document.querySelector(`tr.game-row[data-game-id="${gameId}"]`);
        if (tableRow) {
            // Update name
            if (changes.name) {
                const nameCell = tableRow.querySelector('.name-col');
                if (nameCell) {
                    nameCell.textContent = freshData.name;
                    nameCell.title = freshData.name;
                }
            }
            
            // Update console
            if (changes.console) {
                const consoleCell = tableRow.querySelector('.console-col');
                if (consoleCell) {
                    consoleCell.textContent = freshData.console;
                    consoleCell.title = freshData.console;
                }
            }
            
            // Update condition
            if (changes.condition) {
                const conditionCell = tableRow.querySelector('.condition-col');
                if (conditionCell) {
                    conditionCell.textContent = freshData.condition;
                }
            }
            
            // Update prices
            if (changes.purchase_price || changes.current_price) {
                // Re-render price columns if they exist
                const priceCell = tableRow.querySelector('.price-col');
                if (priceCell && freshData.purchase_price) {
                    priceCell.textContent = `$${freshData.purchase_price}`;
                }
                
                const currentPriceCell = tableRow.querySelector('.current-price-col');
                if (currentPriceCell && freshData.current_price) {
                    currentPriceCell.textContent = `$${freshData.current_price}`;
                }
            }
        }
        
        // Update expanded details view if open
        const gameDetails = document.querySelector(`div.game-details[data-game-id="${gameId}"]`);
        if (gameDetails && gameDetails.style.display !== 'none') {
            
            // Update name in details
            if (changes.name) {
                const nameDisplay = gameDetails.querySelector('.full-name');
                if (nameDisplay) {
                    nameDisplay.textContent = freshData.name;
                }
            }
            
            // Update console in details
            if (changes.console) {
                const consoleDisplay = document.getElementById(`console-display-${gameId}`);
                if (consoleDisplay) {
                    consoleDisplay.textContent = freshData.console;
                }
            }
            
            // Update status badges and action buttons
            if (changes.is_lent || changes.is_for_sale) {
                updateGameStatusDisplay(gameId, freshData);
            }
        }
        
        // Update edit button data attributes
        const editBtn = document.querySelector(`[data-game-id="${gameId}"].edit-details-btn`);
        if (editBtn) {
            if (changes.name) editBtn.dataset.gameName = freshData.name;
            if (changes.console) editBtn.dataset.gameConsole = freshData.console;
        }
    }
    
    // Helper function to handle deleted games during refresh
    function handleDeletedGameRefresh(gameId) {
        console.log('🗑️ Handling deleted game during refresh:', gameId);
        
        // Remove from client state
        window.gameStateManager.removeGame(gameId);
        
        // Remove from DOM
        const tableRow = document.querySelector(`tr.game-row[data-game-id="${gameId}"]`);
        if (tableRow) {
            tableRow.remove();
        }
        
        // Remove from allGames array if it exists
        if (window.allGames) {
            const index = window.allGames.findIndex(g => g.id == gameId);
            if (index !== -1) {
                window.allGames.splice(index, 1);
            }
        }
        
        // Close any open details for this game
        const gameDetails = document.querySelector(`div.game-details[data-game-id="${gameId}"]`);
        if (gameDetails) {
            gameDetails.style.display = 'none';
        }
        
        // Update result count
        updateResultCount(-1);
    }
    
    // Helper function to update game status display (badges, buttons)
    function updateGameStatusDisplay(gameId, gameData) {
        // This would update status badges, action buttons based on fresh data
        // Implementation depends on existing UI structure
        console.log('🎨 Updating status display for game:', gameId, gameData);
        
        // Find actions section and update buttons based on fresh status
        const gameCard = document.querySelector(`[data-game-id="${gameId}"]`);
        if (!gameCard) return;
        
        // Update status indicators
        const statusElements = gameCard.querySelectorAll('.status-badge');
        statusElements.forEach(el => el.remove()); // Remove existing badges
        
        // Add fresh status badges based on gameData
        if (gameData.is_lent) {
            // Add "Lent Out" badge
        }
        if (gameData.is_for_sale) {
            // Add "For Sale" badge  
        }
    }

    // Batch refresh functionality with debouncing (Phase 3.2)
    let batchRefreshQueue = new Set();
    let batchRefreshTimeout = null;
    const BATCH_REFRESH_DELAY = 2000; // 2 second delay for debouncing
    const MAX_BATCH_SIZE = 50; // Maximum games per batch request
    
    window.refreshMultipleGames = async function(gameIds, options = {}) {
        console.log('🔄 Starting batch refresh for games:', gameIds);
        
        if (!Array.isArray(gameIds) || gameIds.length === 0) {
            console.warn('Invalid gameIds provided to refreshMultipleGames');
            return [];
        }
        
        // Remove duplicates and ensure valid IDs
        const validGameIds = [...new Set(gameIds.filter(id => id && !isNaN(id)))];
        
        if (validGameIds.length === 0) {
            console.warn('No valid game IDs provided');
            return [];
        }
        
        // If immediate option is set, skip debouncing
        if (options.immediate) {
            return await executeBatchRefresh(validGameIds);
        }
        
        // Add to debounced queue
        validGameIds.forEach(id => batchRefreshQueue.add(id));
        
        // Clear existing timeout and set new one
        if (batchRefreshTimeout) {
            clearTimeout(batchRefreshTimeout);
        }
        
        return new Promise((resolve) => {
            batchRefreshTimeout = setTimeout(async () => {
                const queuedIds = Array.from(batchRefreshQueue);
                batchRefreshQueue.clear();
                batchRefreshTimeout = null;
                
                const results = await executeBatchRefresh(queuedIds);
                resolve(results);
            }, BATCH_REFRESH_DELAY);
        });
    };
    
    // Execute the actual batch refresh API call
    async function executeBatchRefresh(gameIds) {
        console.log(`📡 Executing batch refresh for ${gameIds.length} games:`, gameIds);
        
        // Show batch progress indicator
        window.LoadingStateManager?.showBatchProgress('Refreshing games...', 0, gameIds.length);
        
        try {
            // Split large batches into smaller chunks
            const chunks = [];
            for (let i = 0; i < gameIds.length; i += MAX_BATCH_SIZE) {
                chunks.push(gameIds.slice(i, i + MAX_BATCH_SIZE));
            }
            
            const allResults = [];
            let processedCount = 0;
            
            // Process each chunk
            for (let chunkIndex = 0; chunkIndex < chunks.length; chunkIndex++) {
                const chunk = chunks[chunkIndex];
                console.log(`📦 Processing batch chunk ${chunkIndex + 1}/${chunks.length} (${chunk.length} games)`);
                
                // Update progress
                window.LoadingStateManager?.updateBatchProgress(processedCount, gameIds.length, `Processing chunk ${chunkIndex + 1}/${chunks.length}...`);
                
                const response = await fetch('/api/games/batch-refresh', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        game_ids: chunk
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Batch refresh failed: ${response.status}`);
                }
                
                const result = await response.json();
                console.log(`📥 Received batch data: ${result.found_count} found, ${result.missing_count} missing`);
                
                // Process found games with progress updates
                for (const freshGameData of result.games) {
                    const gameId = freshGameData.id;
                    const currentGameData = window.gameStateManager.getGame(gameId);
                    
                    // Update progress for each game processed
                    processedCount++;
                    window.LoadingStateManager?.updateBatchProgress(processedCount, gameIds.length);
                    
                    if (!currentGameData) {
                        console.log('⚠️ Game not in client state, adding:', gameId);
                        window.gameStateManager.addGame(freshGameData);
                        allResults.push({ gameId, status: 'added', data: freshGameData });
                        continue;
                    }
                    
                    // Perform differential update
                    const changes = detectGameDataChanges(currentGameData, freshGameData);
                    
                    if (Object.keys(changes).length === 0) {
                        console.log('✅ No changes for game:', gameId);
                        allResults.push({ gameId, status: 'unchanged', data: currentGameData });
                        continue;
                    }
                    
                    console.log('🔄 Applying batch changes for game:', gameId, changes);
                    
                    // Update client state
                    window.gameStateManager.updateGame(freshGameData);
                    
                    // Apply differential DOM updates with subtle visual feedback
                    window.LoadingStateManager?.setRowState(gameId, 'updating');
                    applyGameDataChanges(gameId, changes, freshGameData);
                    setTimeout(() => window.LoadingStateManager?.setRowState(gameId, 'success'), 100);
                    
                    // Update allGames array if it exists
                    if (window.allGames) {
                        const index = window.allGames.findIndex(g => g.id == gameId);
                        if (index !== -1) {
                            window.allGames[index] = freshGameData;
                        }
                    }
                    
                    allResults.push({ gameId, status: 'updated', data: freshGameData, changes });
                }
                
                // Handle missing (deleted) games
                for (const missingGameId of result.missing_game_ids) {
                    console.log('🗑️ Handling deleted game in batch:', missingGameId);
                    handleDeletedGameRefresh(missingGameId);
                    allResults.push({ gameId: missingGameId, status: 'deleted' });
                }
            }
            
            // Hide batch progress indicator
            window.LoadingStateManager?.hideBatchProgress();
            console.log(`✅ Batch refresh completed: ${allResults.length} games processed`);
            return allResults;
            
        } catch (error) {
            console.error('❌ Error in batch refresh:', error);
            // Hide batch progress and show error
            window.LoadingStateManager?.hideBatchProgress();
            window.LoadingStateManager?.showSyncIndicator('Batch refresh failed', 'error');
            window.LoadingStateManager?.hideSyncIndicator('error');
            // Return partial results or empty array - don't break UI
            return [];
        }
    }
    
    // Convenience function to queue single game for batch refresh
    window.queueGameRefresh = function(gameId) {
        console.log('📋 Queuing game for batch refresh:', gameId);
        return window.refreshMultipleGames([gameId]);
    };
    
    // Function to flush the batch refresh queue immediately
    window.flushBatchRefresh = function() {
        console.log('⚡ Flushing batch refresh queue immediately');
        
        if (batchRefreshTimeout) {
            clearTimeout(batchRefreshTimeout);
            batchRefreshTimeout = null;
        }
        
        if (batchRefreshQueue.size > 0) {
            const queuedIds = Array.from(batchRefreshQueue);
            batchRefreshQueue.clear();
            return executeBatchRefresh(queuedIds);
        }
        
        return Promise.resolve([]);
    };

    // ===== PHASE 4.1: LOADING STATE IMPROVEMENTS =====
    
    /**
     * Loading State Manager for visual feedback during operations
     */
    const LoadingStateManager = {
        // Sync indicator elements
        syncIndicator: null,
        syncSpinner: null,
        syncText: null,
        
        // Batch progress elements
        batchProgress: null,
        batchProgressText: null,
        batchProgressCount: null,
        batchProgressFill: null,
        
        // State tracking
        activeSyncOperations: 0,
        syncTimeout: null,
        
        /**
         * Initialize loading state manager
         */
        init() {
            this.syncIndicator = document.getElementById('syncIndicator');
            this.syncSpinner = this.syncIndicator?.querySelector('.sync-spinner');
            this.syncText = this.syncIndicator?.querySelector('.sync-text');
            
            this.batchProgress = document.getElementById('batchProgress');
            this.batchProgressText = this.batchProgress?.querySelector('.batch-progress-text');
            this.batchProgressCount = this.batchProgress?.querySelector('.batch-progress-count');
            this.batchProgressFill = this.batchProgress?.querySelector('.batch-progress-fill');
            
            console.log('✅ LoadingStateManager initialized');
        },
        
        /**
         * Show sync indicator with custom message
         */
        showSyncIndicator(message = 'Syncing...', type = 'info') {
            if (!this.syncIndicator) return;
            
            this.activeSyncOperations++;
            
            // Update content
            if (this.syncText) {
                this.syncText.textContent = message;
            }
            
            // Update styling based on type
            this.syncIndicator.className = `sync-indicator show ${type === 'error' ? 'error' : type === 'success' ? 'success' : ''}`;
            
            // Clear any existing timeout
            if (this.syncTimeout) {
                clearTimeout(this.syncTimeout);
                this.syncTimeout = null;
            }
        },
        
        /**
         * Hide sync indicator after brief delay
         */
        hideSyncIndicator(type = 'success', delay = 1000) {
            this.activeSyncOperations = Math.max(0, this.activeSyncOperations - 1);
            
            if (this.activeSyncOperations > 0) {
                return; // Still have active operations
            }
            
            if (!this.syncIndicator) return;
            
            // Show success/error state briefly before hiding
            if (type !== 'info') {
                this.syncIndicator.className = `sync-indicator show ${type}`;
                if (this.syncText) {
                    this.syncText.textContent = type === 'success' ? 'Synced!' : 'Sync failed';
                }
            }
            
            // Hide after delay
            this.syncTimeout = setTimeout(() => {
                if (this.syncIndicator && this.activeSyncOperations === 0) {
                    this.syncIndicator.classList.remove('show', 'success', 'error');
                }
            }, delay);
        },
        
        /**
         * Show batch progress indicator
         */
        showBatchProgress(message = 'Refreshing games...', current = 0, total = 0) {
            if (!this.batchProgress) return;
            
            // Update text and count
            if (this.batchProgressText) {
                this.batchProgressText.textContent = message;
            }
            if (this.batchProgressCount) {
                this.batchProgressCount.textContent = `${current}/${total}`;
            }
            
            // Update progress bar
            const percentage = total > 0 ? (current / total) * 100 : 0;
            if (this.batchProgressFill) {
                this.batchProgressFill.style.width = `${percentage}%`;
            }
            
            // Show the progress indicator
            this.batchProgress.classList.add('show');
        },
        
        /**
         * Update batch progress
         */
        updateBatchProgress(current, total, message = null) {
            if (!this.batchProgress) return;
            
            if (message && this.batchProgressText) {
                this.batchProgressText.textContent = message;
            }
            
            if (this.batchProgressCount) {
                this.batchProgressCount.textContent = `${current}/${total}`;
            }
            
            const percentage = total > 0 ? (current / total) * 100 : 0;
            if (this.batchProgressFill) {
                this.batchProgressFill.style.width = `${percentage}%`;
            }
        },
        
        /**
         * Hide batch progress indicator
         */
        hideBatchProgress(delay = 500) {
            if (!this.batchProgress) return;
            
            setTimeout(() => {
                this.batchProgress.classList.remove('show');
                // Reset progress bar
                if (this.batchProgressFill) {
                    this.batchProgressFill.style.width = '0%';
                }
            }, delay);
        },
        
        /**
         * Add loading state to button
         */
        setButtonLoading(button, loading = true) {
            if (!button) return;
            
            if (loading) {
                button.classList.add('btn-loading');
                button.disabled = true;
            } else {
                button.classList.remove('btn-loading');
                button.disabled = false;
            }
        },
        
        /**
         * Add visual feedback to game row
         */
        setRowState(gameId, state) {
            const row = document.querySelector(`tr[data-game-id="${gameId}"]`);
            if (!row) return;
            
            // Remove existing state classes
            row.classList.remove('optimistic-pending', 'optimistic-success', 'optimistic-error', 'updating', 'fade-out', 'fade-in');
            
            // Add new state class
            switch (state) {
                case 'pending':
                    row.classList.add('optimistic-pending');
                    break;
                case 'updating':
                    row.classList.add('updating');
                    break;
                case 'success':
                    row.classList.add('optimistic-success');
                    setTimeout(() => row.classList.remove('optimistic-success'), 2000);
                    break;
                case 'error':
                    row.classList.add('optimistic-error');
                    setTimeout(() => row.classList.remove('optimistic-error'), 3000);
                    break;
                case 'fade-out':
                    row.classList.add('fade-out');
                    break;
                case 'fade-in':
                    row.classList.add('fade-in');
                    break;
            }
        },
        
        /**
         * Trigger success micro-animation on element
         */
        showSuccessAnimation(element) {
            if (!element) return;
            element.classList.add('operation-success');
            setTimeout(() => element.classList.remove('operation-success'), 600);
        },
        
        /**
         * Trigger error micro-animation on element
         */
        showErrorAnimation(element) {
            if (!element) return;
            element.classList.add('operation-error');
            setTimeout(() => element.classList.remove('operation-error'), 600);
        }
    };
    
    // Initialize loading state manager when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => LoadingStateManager.init());
    } else {
        LoadingStateManager.init();
    }
    
    /**
     * Enhanced API call wrapper with loading state management
     */
    async function apiCallWithLoadingState(url, options = {}, loadingMessage = 'Processing...') {
        LoadingStateManager.showSyncIndicator(loadingMessage);
        
        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            LoadingStateManager.hideSyncIndicator('success');
            return data;
        } catch (error) {
            console.error('API call failed:', error);
            LoadingStateManager.hideSyncIndicator('error');
            throw error;
        }
    }
    
    // Export loading state manager and functions
    window.LoadingStateManager = LoadingStateManager;
    window.apiCallWithLoadingState = apiCallWithLoadingState;

    // Export functions for use in other scripts
    window.createGameRow = createGameRow;
    window.addGameRowToTable = addGameRowToTable;
    window.updateResultCount = updateResultCount;
    window.removeGameRowFromTable = removeGameRowFromTable;
    
})();