/**
 * Main JavaScript file with optimistic updates for add game functionality
 * This file contains the enhanced add game functionality with optimistic updates
 */

(function() {
    'use strict';
    
    // Ensure required dependencies are available
    if (!window.gameStateManager) {
        console.error('GameStateManager not loaded. Please ensure state-manager.js is loaded first.');
    }
    if (!window.errorHandler) {
        console.error('ErrorHandler not loaded. Please ensure error-handler.js is loaded first.');
    }
    // Continue even if dependencies are missing to allow function definitions

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
        
        // Add click handler to expand details (same as in index.html template)
        tr.addEventListener('click', function(e) {
            const gameId = this.dataset.gameId;
            const detailsDiv = document.querySelector(`.game-details[data-game-id="${gameId}"]`);
            
            if (!detailsDiv) return;
            
            const wasVisible = detailsDiv.classList.contains('show');
            
            // Hide all details and remove selected state
            document.querySelectorAll('.game-details').forEach(div => div.classList.remove('show'));
            document.querySelectorAll('.game-row').forEach(r => r.classList.remove('selected'));
            
            // Toggle this one if it wasn't already visible
            if (!wasVisible) {
                detailsDiv.classList.add('show');
                this.classList.add('selected');
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
        
        try {
            
            // Make API call first
            const response = await fetch('/api/wishlist/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(gameData)
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                console.error(`❌ Add to wishlist failed:`, data);
                throw new Error(data.error || 'Failed to add game to wishlist');
            }
            
            
            // Only add to UI after successful API response
            const realGame = data.game;
            
            // Add to state manager
            window.gameStateManager.addGame(realGame);
            
            // Create and add the game row with fade-in animation
            const row = createGameRow(realGame, true);
            row.classList.add('fade-in');
            addGameRowToTable(row, 'collectionTable', true);
            
            // Update count
            updateResultCount(1, realGame);
            
            // Add to allGames array if it exists
            if (window.allGames) {
                window.allGames.unshift(realGame);
            }
            
            // Show success message
            window.errorHandler.showSuccess(
                `Added ${realGame.name} (${realGame.console}) to your wishlist!`
            );
            
            return data;
            
        } catch (error) {
            console.error('❌ DEBUG: Error in wishlist add:', error);
            window.errorHandler.showError(
                error.message || 'Failed to add game to wishlist'
            );
            throw error;
        }
    };

    /**
     * Enhanced add game to collection with optimistic updates
     */
    window.addToCollectionOptimistic = async function(gameData) {
        
        try {
            
            // 2. Make background API call
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
            
            // 3. Add the game to UI for the first time with real server data
            const realGame = data.game;
            window.gameStateManager.addGame(realGame);
            
            // Add to allGames array and render
            if (window.allGames) {
                window.allGames.unshift(realGame);
                
                // Render with the new game data
                const searchInput = document.getElementById('searchInput');
                const currentSearchTerm = searchInput ? searchInput.value : '';
                
                if (currentSearchTerm && window.filterGames) {
                    // Re-apply current search filter
                    const filtered = window.filterGames(window.allGames, currentSearchTerm);
                    window.renderGames(filtered, false, 1);
                } else {
                    // No active search, show all games
                    window.renderGames(window.allGames, true, 1);
                }
            }
            
            // Show success message
            window.errorHandler.showSuccessToast(`Added "${realGame.name}" to collection`);
            
            // Background refresh removed - API-first approach ensures accuracy
            
            return data;
            
        } catch (error) {
            console.error('❌ DEBUG: Error occurred:', error);
            
            // No rollback needed since we didn't add optimistic UI changes
            // Just show error message
            window.errorHandler.showErrorToast(error.message || 'Failed to add game to collection');
            
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
        
        // Also find and remove the associated details row
        const detailsRow = row.nextElementSibling;
        const hasDetailsRow = detailsRow && detailsRow.classList.contains('details-row');
        
        // Animate removal of main row
        row.style.transition = 'opacity 0.3s ease, transform 0.3s ease, height 0.3s ease';
        row.style.opacity = '0';
        row.style.transform = 'translateX(-20px)';
        
        // If there's an expanded details row, animate it too
        if (hasDetailsRow) {
            detailsRow.style.transition = 'opacity 0.3s ease, height 0.3s ease';
            detailsRow.style.opacity = '0';
            detailsRow.style.height = '0';
        }
        
        setTimeout(() => {
            row.remove();
            if (hasDetailsRow) {
                detailsRow.remove();
            }
            if (onComplete) onComplete();
        }, 300);
    }

    /**
     * Enhanced remove from wishlist with optimistic updates
     */
    window.removeFromWishlistOptimistic = async function(gameId, gameName, gameConsole) {
        
        try {
            
            // Make API call first
            const response = await fetch(`/api/wishlist/${gameId}/remove`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                console.error(`❌ Remove from wishlist failed:`, result);
                throw new Error(result.error || 'Failed to remove game from wishlist');
            }
            
            
            // Only remove from UI after successful API response
            removeGameRowFromTable(gameId);
            
            // Remove from state manager
            window.gameStateManager.removeGame(gameId);
            
            // Remove from allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames.splice(index, 1);
                }
            }
            
            // Update count
            const game = { id: gameId, name: gameName, console: gameConsole, is_wanted: true };
            updateResultCount(-1, game);
            
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
            
            return result;
            
        } catch (error) {
            console.error('❌ DEBUG: Error in wishlist removal:', error);
            window.errorHandler.showError(
                error.message || 'Failed to remove game from wishlist'
            );
            throw error;
        }
    };

    /**
     * Enhanced purchase conversion with optimistic updates
     * Converts wishlist item to purchased collection item
     */
    window.purchaseWishlistGameOptimistic = async function(gameId, gameName, gameConsole, purchaseData) {
        
        try {
            
            // Make API call first
            const response = await fetch(`/api/wishlist/${gameId}/purchase`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(purchaseData)
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                console.error(`❌ Purchase failed:`, data);
                throw new Error(data.error || 'Failed to purchase game');
            }
            
            
            // Only update UI after successful API response
            const serverGame = data.game;
            
            // Remove from wishlist section (with animation)
            removeGameRowFromTable(gameId);
            
            // Update state manager - remove wishlist, add collection
            window.gameStateManager.removeGame(gameId);
            window.gameStateManager.addGame(serverGame);
            
            // Create and add to collection section
            const newRow = createGameRow(serverGame, false); // false = not wishlist
            addGameRowToTable(newRow, 'collectionTable', true);
            
            // Update counts and totals
            updateResultCount(0, serverGame); // Net change is 0 (moved between sections)
            
            // Update in allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames[index] = serverGame;
                } else {
                    window.allGames.unshift(serverGame);
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
            
            return data;
            
        } catch (error) {
            console.error('❌ DEBUG: Error in purchase conversion:', error);
            window.errorHandler.showError(
                error.message || 'Failed to purchase game'
            );
            throw error;
        }
    };

    /**
     * Enhanced remove from collection with optimistic updates
     */
    window.removeFromCollectionOptimistic = async function(purchasedGameId, gameId, gameName, gameConsole) {
        
        try {
            
            // Make API call first
            const response = await fetch(`/api/purchased_game/${purchasedGameId}/remove_from_collection`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                console.error(`❌ Delete failed with status ${response.status}:`, errorData);
                throw new Error(errorData.error || 'Failed to remove game from collection');
            }
            
            const result = await response.json();
            
            // Only remove from UI after successful API response
            removeGameRowFromTable(gameId);
            
            // Remove from state manager
            window.gameStateManager.removeGame(gameId);
            
            // Remove from allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId || g.purchased_game_id == purchasedGameId);
                if (index !== -1) {
                    window.allGames.splice(index, 1);
                    console.log(`🗑️ Removed game from allGames array, new count: ${window.allGames.length}`);
                }
            }
            
            // Update count and totals - get game data for calculation
            const game = { 
                id: gameId, 
                purchased_game_id: purchasedGameId,
                name: gameName, 
                console: gameConsole, 
                is_wanted: false 
            };
            updateResultCount(-1, game);
            
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
            
            return result;
            
        } catch (error) {
            console.error('❌ DEBUG: Error in collection removal:', error);
            window.errorHandler.showError(
                error.message || 'Failed to remove game from collection'
            );
            throw error;
        }
    };

    /**
     * Enhanced mark as lent with optimistic updates
     */
    window.markGameAsLentOptimistic = async function(gameId, gameName, gameConsole, lentData) {
        
        try {
            
            // Make API call first
            const response = await fetch(`/api/game/${gameId}/mark_as_lent`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(lentData)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                console.error(`❌ Mark as lent failed:`, errorData);
                throw new Error(errorData.error || 'Failed to mark game as lent out');
            }
            
            const result = await response.json();
            
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
            
            // Create the lent game object with server data
            const lentGame = {
                ...game,
                is_lent: true,
                lent_date: lentData.lent_date,
                lent_to: lentData.lent_to
            };
            
            // Update state manager
            window.gameStateManager.updateGame(lentGame);
            
            // Update the game row to show lent status
            const row = document.querySelector(`tr[data-game-id="${gameId}"]`);
            if (row) {
                
                // Update status icon (first column) - the icon is directly in the td, not in a badge
                const statusCell = row.querySelector('.status-col');
                if (statusCell) {
                    statusCell.textContent = '📤';  // Lent out emoji
                    statusCell.title = 'Lent Out';
                }
                
                // Try to find name cell with various selectors  
                let nameCell = row.querySelector('.name-col .name-content');
                if (!nameCell) nameCell = row.querySelector('.name-col');
                if (!nameCell) nameCell = row.querySelector('td:nth-child(2)');
                
                if (nameCell) {
                    // Remove existing lent badges
                    const existingBadges = nameCell.querySelectorAll('.badge');
                    existingBadges.forEach(badge => {
                        if (badge.textContent.includes('Lent Out')) {
                            badge.remove();
                        }
                    });
                    
                    // Add lent out badge
                    const lentBadge = document.createElement('span');
                    lentBadge.className = 'badge bg-info text-dark ms-2';
                    lentBadge.textContent = 'Lent Out';
                    nameCell.appendChild(lentBadge);
                }
            } else {
            }
            
            // Update in allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames[index] = lentGame;
                }
            }
            
            // Show success message
            window.errorHandler.showSuccess(
                'Game marked as lent out successfully!'
            );
            
            // Close modal if open
            const modal = document.getElementById('markLentModal');
            if (modal) {
                const bootstrapModal = bootstrap.Modal.getInstance(modal);
                if (bootstrapModal) {
                    bootstrapModal.hide();
                }
            }
            
            return result;
            
        } catch (error) {
            console.error('❌ DEBUG: Error in mark as lent:', error);
            window.errorHandler.showError(
                error.message || 'Failed to mark game as lent out'
            );
            throw error;
        }
    };

    /**
     * Enhanced return from lent with optimistic updates
     */
    window.unmarkGameAsLentOptimistic = async function(gameId, gameName, gameConsole) {
        
        try {
            
            // Make API call first
            const response = await fetch(`/api/game/${gameId}/unmark_as_lent`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                console.error(`❌ Unmark as lent failed:`, errorData);
                throw new Error(errorData.error || 'Failed to mark game as returned');
            }
            
            const result = await response.json();
            
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
            
            // Update state manager
            window.gameStateManager.updateGame(returnedGame);
            
            // Update the game row to remove lent status
            const row = document.querySelector(`tr[data-game-id="${gameId}"]`);
            if (row) {
                // Update status icon back to owned (first column)
                const statusCell = row.querySelector('.status-col');
                if (statusCell) {
                    statusCell.textContent = '✓';  // Back to owned
                    statusCell.title = 'Owned';
                }
                
                // Remove lent out badge
                const nameCell = row.querySelector('.name-col');
                if (nameCell) {
                    const lentBadge = nameCell.querySelector('.badge.bg-info');
                    if (lentBadge && lentBadge.textContent.includes('Lent Out')) {
                        lentBadge.remove();
                    }
                }
            }
            
            // Update in allGames array if it exists
            if (window.allGames) {
                const index = window.allGames.findIndex(g => g.id == gameId);
                if (index !== -1) {
                    window.allGames[index] = returnedGame;
                }
            }
            
            // Show success message
            window.errorHandler.showSuccess(
                'Game marked as returned successfully!'
            );
            
            // Close modal if open
            const modal = document.getElementById('unmarkLentModal');
            if (modal) {
                const bootstrapModal = bootstrap.Modal.getInstance(modal);
                if (bootstrapModal) {
                    bootstrapModal.hide();
                }
            }
            
            return result;
            
        } catch (error) {
            console.error('❌ DEBUG: Error in return from lent:', error);
            window.errorHandler.showError(
                error.message || 'Failed to mark game as returned'
            );
            throw error;
        }
    };

    // Optimistic edit game details function
    window.editGameDetailsOptimistic = async function(gameId, newName, newConsole) {
        
        const originalGame = window.gameStateManager.getGame(gameId);
        
        if (!originalGame) {
            throw new Error(`Game with ID ${gameId} not found in state manager`);
        }
        
        try {
            
            // Make API call first
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
                console.error(`❌ Edit details failed:`, errorData);
                throw new Error(errorData.error || 'Failed to update game details');
            }
            
            const result = await response.json();
            
            // Create updated game object
            const updatedGame = {
                ...originalGame,
                name: newName,
                console: newConsole
            };
            
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
            
            // Show success message
            window.errorHandler.showSuccess('Game details updated successfully!');
            
            return result;
            
        } catch (error) {
            console.error('❌ DEBUG: Error in edit details:', error);
            window.errorHandler.showError(
                'Failed to update game details: ' + 
                (error.message || 'An unexpected error occurred')
            );
            throw error;
        }
    };

    // Background refresh removed - API-first approach ensures data accuracy
    
    // Helper function to detect changes between current and fresh game data
    function detectGameDataChanges(current, fresh) {
        const changes = {};
        
        // Fields to check for changes
        const fieldsToCheck = [
            'name', 'console', 'condition', 'purchase_price', 'current_price',
            'is_wanted', 'is_lent', 'is_for_sale', 'lent_date', 'lent_to', 
            'asking_price', 'sale_notes', 'source_name'
        ];
        
        // Critical fields that may require user input for conflicts
        const criticalFields = ['name', 'console', 'purchase_price', 'is_lent', 'lent_to'];
        
        let hasCriticalConflict = false;
        
        for (const field of fieldsToCheck) {
            if (current[field] !== fresh[field]) {
                changes[field] = {
                    from: current[field],
                    to: fresh[field],
                    isCritical: criticalFields.includes(field)
                };
                
                if (criticalFields.includes(field)) {
                    hasCriticalConflict = true;
                }
            }
        }
        
        // Add metadata about the conflict
        if (Object.keys(changes).length > 0) {
            changes._metadata = {
                hasCriticalConflict,
                conflictCount: Object.keys(changes).length - 1, // -1 for metadata
                timestamp: new Date().toISOString()
            };
        }
        
        return changes;
    }

    /**
     * Show conflict resolution modal to let user choose between versions
     */
    function showConflictModal(gameId, gameName, gameConsole, conflicts, currentData, serverData) {
        const modal = document.getElementById('conflictResolutionModal');
        if (!modal) {
            console.error('Conflict resolution modal not found');
            return;
        }

        // Set game information
        const gameInfo = modal.querySelector('#conflictGameInfo');
        if (gameInfo) {
            gameInfo.textContent = `${gameName} (${gameConsole})`;
        }

        // Populate current version column
        const currentColumn = modal.querySelector('#currentVersion');
        const serverColumn = modal.querySelector('#serverVersion');
        
        if (currentColumn && serverColumn) {
            currentColumn.innerHTML = buildVersionDisplay(currentData, conflicts, 'current');
            serverColumn.innerHTML = buildVersionDisplay(serverData, conflicts, 'server');
        }

        // Store data for button handlers
        modal.dataset.gameId = gameId;
        modal.dataset.gameName = gameName;
        modal.dataset.gameConsole = gameConsole;
        modal._conflictData = { conflicts, currentData, serverData };

        // Show the modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }

    /**
     * Build HTML for version display in conflict modal
     */
    function buildVersionDisplay(data, conflicts, version) {
        let html = '<div class="version-data">';
        
        // Show only fields that have conflicts or are important
        const displayFields = [
            { key: 'name', label: 'Game Name' },
            { key: 'console', label: 'Console' },
            { key: 'purchase_price', label: 'Purchase Price' },
            { key: 'is_lent', label: 'Lent Status', formatter: (val) => val ? 'Yes' : 'No' },
            { key: 'lent_to', label: 'Lent To' },
            { key: 'condition', label: 'Condition' },
            { key: 'current_price', label: 'Current Price' }
        ];

        displayFields.forEach(field => {
            if (data[field.key] !== undefined && data[field.key] !== null && data[field.key] !== '') {
                const value = field.formatter ? field.formatter(data[field.key]) : data[field.key];
                const isConflicted = conflicts[field.key] !== undefined;
                const conflictClass = isConflicted ? (version === 'current' ? 'conflict-current' : 'conflict-server') : '';
                
                html += `<div class="field-row ${conflictClass}">
                    <strong>${field.label}:</strong> ${value}
                    ${isConflicted && conflicts[field.key].isCritical ? ' <span class="badge bg-warning">Critical</span>' : ''}
                </div>`;
            }
        });
        
        html += '</div>';
        return html;
    }

    /**
     * Handle "Keep My Version" button click
     */
    function handleKeepMyVersion() {
        const modal = document.getElementById('conflictResolutionModal');
        if (!modal || !modal._conflictData) return;

        const gameId = modal.dataset.gameId;
        const { conflicts, currentData } = modal._conflictData;

        // Log conflict resolution choice
        logConflictResolution(gameId, 'keep_current', conflicts);

        // Keep current data - no changes needed to UI or state
        console.log(`Conflict resolved for game ${gameId}: kept current version`);
        
        // Close modal
        const bootstrapModal = bootstrap.Modal.getInstance(modal);
        bootstrapModal.hide();

        // Show success message
        window.errorHandler.showSuccessToast('Kept your version of the data');
    }

    /**
     * Handle "Use Server Version" button click  
     */
    function handleUseServerVersion() {
        const modal = document.getElementById('conflictResolutionModal');
        if (!modal || !modal._conflictData) return;

        const gameId = modal.dataset.gameId;
        const { conflicts, currentData, serverData } = modal._conflictData;

        // Log conflict resolution choice
        logConflictResolution(gameId, 'use_server', conflicts);

        // Apply server data to UI and state
        applyServerDataToGame(gameId, serverData);
        
        console.log(`Conflict resolved for game ${gameId}: used server version`);

        // Close modal
        const bootstrapModal = bootstrap.Modal.getInstance(modal);
        bootstrapModal.hide();

        // Show success message
        window.errorHandler.showSuccessToast('Updated to server version');
    }

    /**
     * Apply server data to the game's UI and state
     */
    function applyServerDataToGame(gameId, serverData) {
        // Update game state manager
        if (window.gameStateManager) {
            window.gameStateManager.updateGame(gameId, serverData);
        }

        // Update UI elements
        const gameRow = document.querySelector(`tr[data-game-id="${gameId}"]`);
        if (gameRow) {
            updateGameRowElements(gameRow, serverData);
        }
    }

    /**
     * Update specific elements in a game row with new data
     */
    function updateGameRowElements(gameRow, data) {
        // Update game name
        const nameCell = gameRow.querySelector('.game-name');
        if (nameCell && data.name) {
            nameCell.textContent = data.name;
        }

        // Update console
        const consoleCell = gameRow.querySelector('.console');
        if (consoleCell && data.console) {
            consoleCell.textContent = data.console;
        }

        // Update purchase price
        const priceCell = gameRow.querySelector('.purchase-price');
        if (priceCell && data.purchase_price !== undefined) {
            priceCell.textContent = data.purchase_price ? `$${parseFloat(data.purchase_price).toFixed(2)}` : '';
        }

        // Update lent status
        const lentCell = gameRow.querySelector('.lent-status');
        if (lentCell) {
            lentCell.textContent = data.is_lent ? `Lent to ${data.lent_to || 'Unknown'}` : '';
        }

        // Update condition
        const conditionCell = gameRow.querySelector('.condition');
        if (conditionCell && data.condition) {
            conditionCell.textContent = data.condition;
        }
    }

    /**
     * Update row content with real server data after optimistic update
     * @param {HTMLElement} row - The row element to update
     * @param {Object} gameData - The real game data from server
     */
    function updateRowContent(row, gameData) {
        console.log('🔄 updateRowContent: Updating row with real data:', gameData);
        
        // Update game name
        const nameElement = row.querySelector('.game-name');
        if (nameElement && gameData.name) {
            nameElement.textContent = gameData.name;
        }
        
        // Update console
        const consoleElement = row.querySelector('.console');
        if (consoleElement && gameData.console) {
            consoleElement.textContent = gameData.console;
        }
        
        // Update purchase price
        const priceElement = row.querySelector('.purchase-price');
        if (priceElement && gameData.purchase_price !== undefined) {
            priceElement.textContent = gameData.purchase_price ? 
                `$${parseFloat(gameData.purchase_price).toFixed(2)}` : '';
        }
        
        // Update current price
        const currentPriceElement = row.querySelector('.current-price');
        if (currentPriceElement && gameData.current_price !== undefined) {
            currentPriceElement.textContent = gameData.current_price ? 
                `$${parseFloat(gameData.current_price).toFixed(2)}` : '';
        }
        
        // Update condition
        const conditionElement = row.querySelector('.condition');
        if (conditionElement && gameData.condition) {
            conditionElement.textContent = gameData.condition;
        }
        
        // Update acquisition date
        const dateElement = row.querySelector('.date');
        if (dateElement && gameData.date) {
            const date = new Date(gameData.date);
            dateElement.textContent = date.toLocaleDateString();
        }
        
        // Update source
        const sourceElement = row.querySelector('.source-name');
        if (sourceElement && gameData.source_name) {
            sourceElement.textContent = gameData.source_name;
        }
        
        // Update edit button data attributes
        const editBtn = row.querySelector('.edit-details-btn');
        if (editBtn) {
            editBtn.dataset.gameName = gameData.name || '';
            editBtn.dataset.gameConsole = gameData.console || '';
        }
        
        console.log('✅ updateRowContent: Row updated successfully');
    }

    /**
     * Log conflict resolution for debugging
     */
    function logConflictResolution(gameId, choice, conflicts) {
        const logEntry = {
            gameId,
            choice,
            timestamp: new Date().toISOString(),
            conflictCount: Object.keys(conflicts).filter(k => k !== '_metadata').length,
            hasCriticalConflicts: conflicts._metadata?.hasCriticalConflict || false,
            conflicts: Object.keys(conflicts).filter(k => k !== '_metadata')
        };
        
        console.log('Conflict Resolution:', logEntry);
        
        // Could be extended to send to server for analytics
    }
    
    // Helper function to apply differential changes to DOM
    function applyGameDataChanges(gameId, changes, freshData) {
        console.log('🎯 Applying DOM changes for game:', gameId, changes);
        
        // Update table row if it exists
        const tableRow = document.querySelector(`tr.game-row[data-game-id="${gameId}"]`);
        if (tableRow) {
            // Update name
            if (changes.name) {
                const nameElement = tableRow.querySelector('.game-name');
                if (nameElement) {
                    nameElement.textContent = freshData.name;
                    nameElement.title = freshData.name;
                }
            }
            
            // Update console
            if (changes.console) {
                const consoleElement = tableRow.querySelector('.console-col');
                if (consoleElement) {
                    consoleElement.textContent = freshData.console;
                    consoleElement.title = freshData.console;
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

    // Batch refresh system removed - API-first approach ensures data accuracy

    
    /**
     * Loading State Manager for visual feedback during operations
     */
    const LoadingStateManager = {
        // Basic sync indicator only
        syncIndicator: null,
        syncSpinner: null,
        syncText: null,
        
        // State tracking
        activeSyncOperations: 0,
        syncTimeout: null,
        
        /**
         * Initialize basic loading state manager
         */
        init() {
            this.syncIndicator = document.getElementById('syncIndicator');
            this.syncSpinner = this.syncIndicator?.querySelector('.sync-spinner');
            this.syncText = this.syncIndicator?.querySelector('.sync-text');
            
            console.log('✅ LoadingStateManager (simplified) initialized');
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
         * Add basic loading state to button
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

    // Set up conflict resolution modal button handlers
    document.addEventListener('DOMContentLoaded', function() {
        const keepCurrentBtn = document.getElementById('keepCurrentBtn');
        const useServerBtn = document.getElementById('useServerBtn');
        
        if (keepCurrentBtn) {
            keepCurrentBtn.addEventListener('click', handleKeepMyVersion);
        }
        
        if (useServerBtn) {
            useServerBtn.addEventListener('click', handleUseServerVersion);
        }
    });

    // Export conflict resolution functions
    window.showConflictModal = showConflictModal;
    window.handleKeepMyVersion = handleKeepMyVersion;
    window.handleUseServerVersion = handleUseServerVersion;
    
})();