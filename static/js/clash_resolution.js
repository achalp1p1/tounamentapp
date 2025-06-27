// Clash Resolution Functions - Centralized Module
// This file contains all clash resolution logic to avoid duplication

let clashResolutionMode = 'auto'; // 'auto' or 'manual'

// Helper functions to get current tournament and category
function getCurrentTournamentId() {
    // Extract tournament ID from the current URL
    const url = window.location.pathname;
    const match = url.match(/\/tournament\/(\d+)/);
    return match ? match[1] : null;
}

function getCurrentCategory() {
    // Get the currently selected category from the clash category select
    const clashCategorySelect = document.getElementById('clashCategorySelect');
    return clashCategorySelect ? clashCategorySelect.value : '';
}

// Common batch update function to reduce code duplication
async function batchUpdateSeedings(playerIds, seedings, category, tournamentId) {
    try {
        if (playerIds.length === 0) {
            console.log('No seed inputs found to save');
            return { success: false, message: 'No seed inputs found to save' };
        }

        console.log(`Saving for Tournament ID: "${tournamentId}", Category: "${category}"`);
        console.log(`Player IDs being sent: ${JSON.stringify(playerIds)}`);
        console.log(`Seedings being sent: ${JSON.stringify(seedings)}`);

        // Create form data
        const formData = new FormData();
        formData.append('category', category);

        // Add each player ID and seeding as separate form fields
        playerIds.forEach(playerId => {
            formData.append('player_ids[]', playerId);
        });

        seedings.forEach(seeding => {
            formData.append('seedings[]', seeding);
        });

        console.log('Form data created, sending to backend...');

        // Send to backend
        const response = await fetch(`/tournament/${tournamentId}/update_seeding`, {
            method: 'POST',
            body: formData
        });

        console.log('Backend response received:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        console.log('Backend result:', result);

        return result;
    } catch (error) {
        console.error('Error in batch update:', error);
        return { success: false, message: error.message };
    }
}

function setClashMode(mode) {
    clashResolutionMode = mode;
    // Update button styles
    const autoModeBtn = document.getElementById('autoModeBtn');
    const manualModeBtn = document.getElementById('manualModeBtn');
    
    if (autoModeBtn) {
        autoModeBtn.style.backgroundColor = (mode === 'auto') ? '#2196f3' : '#bdbdbd';
    }
    if (manualModeBtn) {
        manualModeBtn.style.backgroundColor = (mode === 'manual') ? '#9c27b0' : '#bdbdbd';
    }
    
    // Re-render the clash summary with the current mode
    if (window.currentClashes) {
        showClashSummary(window.currentClashes);
    }
    
    // Re-render the table if players are loaded
    const category = document.getElementById('clashCategorySelect').value;
    if (category) {
        loadClashPlayers();
    }
}

// Function to show clash summary
function showClashSummary(clashes) {
    window.currentClashes = clashes; // Save for mode switching
    const clashSummary = document.getElementById('clashSummary');
    const clashItems = document.getElementById('clashItems');
    
    if (!clashSummary || !clashItems) {
        console.error('Clash summary elements not found');
        return;
    }
    
    clashItems.innerHTML = '';
    
    // Show only relevant options based on mode
    if (clashResolutionMode === 'auto') {
        // Add overall clash resolution options (auto/shuffle)
        const overallResolutionDiv = document.createElement('div');
        overallResolutionDiv.className = 'clash-item';
        overallResolutionDiv.style.backgroundColor = '#e8f5e8';
        overallResolutionDiv.innerHTML = `
            <div style="margin-bottom: 15px;">
                <strong style="color: #2e7d32;">🎯 Automatic Clash Resolution Options:</strong>
            </div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <button class="resolve-clash-btn" style="background-color: #2196f3;" onclick="autoResolveAllClashes()">
                    🔄 Auto-Resolve All Clashes
                </button>
                <button class="resolve-clash-btn" style="background-color: #ff9800;" onclick="shuffleClashPlayers()">
                    🎲 Shuffle Clash Players
                </button>
            </div>
        `;
        clashItems.appendChild(overallResolutionDiv);
    } else if (clashResolutionMode === 'manual') {
        // Add manual (paper chit) option
        const manualDiv = document.createElement('div');
        manualDiv.className = 'clash-item';
        manualDiv.style.backgroundColor = '#ede7f6';
        manualDiv.innerHTML = `
            <div style="margin-bottom: 15px;">
                <strong style="color: #6a1b9a;">📄 Manual Clash Resolution:</strong>
            </div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <button class="resolve-clash-btn" style="background-color: #9c27b0;" onclick="showPaperChitResolution()">
                    📄 Paper Chit Resolution
                </button>
            </div>
        `;
        clashItems.appendChild(manualDiv);
    }
    
    // Show clash details (common to both modes)
    clashes.forEach(clash => {
        const clashItem = document.createElement('div');
        clashItem.className = 'clash-item';
        
        const playerNames = clash.players.map(p => p.player.name).join(', ');
        const ranges = clash.ranges.join(' and ');
        
        clashItem.innerHTML = `
            <div>
                <strong>Seed ${clash.seed}</strong> is used by <strong>${playerNames}</strong> 
                across different ranges: <strong>${ranges}</strong>
            </div>
            <div style="margin-top: 8px;">
                <strong>Suggested resolutions:</strong> 
                ${clash.suggestedSeeds.map(seed => 
                    `<button class="resolve-clash-btn" onclick="resolveClash('${clash.seed}', ${seed})">Use Seed ${seed}</button>`
                ).join(' ')}
            </div>
        `;
        if (clashResolutionMode === 'auto') {
            clashItems.appendChild(clashItem);
        } else if (clashResolutionMode === 'manual') {
            // In manual mode, only show the details, not the individual auto buttons
            const lastDiv = clashItem.querySelector('div:last-child');
            if (lastDiv) {
                lastDiv.style.display = 'none';
            }
            clashItems.appendChild(clashItem);
        }
    });
    
    clashSummary.style.display = 'block';
}

// Function to auto-resolve all clashes
async function autoResolveAllClashes() {
    const category = document.getElementById('clashCategorySelect').value;
    const tournamentId = getCurrentTournamentId();
    
    try {
        // Get current players and clashes
        const response = await fetch(`/tournament/${tournamentId}/get_category_players/${category}?fields=full`);
        const data = await response.json();
        
        if (!data.success) {
            alert('Failed to load players');
            return;
        }
        
        const players = data.players;
        const seedRangesResponse = await fetch('/get_seeding_ranges');
        const seedRangesData = await seedRangesResponse.json();
        const seedRanges = seedRangesData.seeding_ranges;
        
        // Detect clashes
        const clashes = detectSeedingClashes(players, seedRanges);
        
        if (clashes.length === 0) {
            alert('No clashes detected to resolve');
            return;
        }
        
        // Collect all updates for batch processing
        const playerIds = [];
        const seedings = [];
        
        // Auto-resolve each clash
        let resolvedCount = 0;
        for (const clash of clashes) {
            const availableSeeds = generateSuggestedSeeds(clash.seed, players);
            if (availableSeeds.length > 0) {
                // Assign new seeds to clash players
                for (let i = 0; i < clash.players.length; i++) {
                    const player = clash.players[i].player;
                    const newSeed = availableSeeds[i % availableSeeds.length];
                    
                    // Collect for batch update
                    playerIds.push(player.player_id);
                    seedings.push(newSeed.toString());
                    resolvedCount++;
                }
            }
        }
        
        // Perform batch update using common function
        const result = await batchUpdateSeedings(playerIds, seedings, category, tournamentId);
        if (result.success) {
            showSuccessMessage(`Auto-resolved ${resolvedCount} clash players`);
            loadClashPlayers(); // Reload to show updated state
        } else {
            showErrorMessage('Failed to save auto-resolved changes: ' + result.message);
        }
        
    } catch (error) {
        console.error('Error auto-resolving clashes:', error);
        showErrorMessage('Error auto-resolving clashes. Please try again.');
    }
}

// Function to shuffle clash players
async function shuffleClashPlayers() {
    const category = document.getElementById('clashCategorySelect').value;
    const tournamentId = getCurrentTournamentId();
    
    try {
        // Get current players and clashes
        const response = await fetch(`/tournament/${tournamentId}/get_category_players/${category}?fields=full`);
        const data = await response.json();
        
        if (!data.success) {
            alert('Failed to load players');
            return;
        }
        
        const players = data.players;
        const seedRangesResponse = await fetch('/get_seeding_ranges');
        const seedRangesData = await seedRangesResponse.json();
        const seedRanges = seedRangesData.seeding_ranges;
        
        // Detect clashes
        const clashes = detectSeedingClashes(players, seedRanges);
        
        if (clashes.length === 0) {
            alert('No clashes detected to shuffle');
            return;
        }
        
        // Collect all clash players
        const clashPlayers = [];
        clashes.forEach(clash => {
            clash.players.forEach(playerInfo => {
                clashPlayers.push(playerInfo.player);
            });
        });
        
        // Shuffle the clash players
        for (let i = clashPlayers.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [clashPlayers[i], clashPlayers[j]] = [clashPlayers[j], clashPlayers[i]];
        }
        
        // Collect all updates for batch processing
        const playerIds = [];
        const seedings = [];
        
        // Assign new seeds to shuffled players
        let resolvedCount = 0;
        for (let i = 0; i < clashPlayers.length; i++) {
            const player = clashPlayers[i];
            const newSeed = i + 1; // Assign sequential seeds
            
            // Collect for batch update
            playerIds.push(player.player_id);
            seedings.push(newSeed.toString());
            resolvedCount++;
        }
        
        // Perform batch update using common function
        const result = await batchUpdateSeedings(playerIds, seedings, category, tournamentId);
        if (result.success) {
            showSuccessMessage(`Shuffled and resolved ${resolvedCount} clash players`);
            loadClashPlayers(); // Reload to show updated state
        } else {
            showErrorMessage('Failed to save shuffled changes: ' + result.message);
        }
        
    } catch (error) {
        console.error('Error shuffling clash players:', error);
        showErrorMessage('Error shuffling clash players. Please try again.');
    }
}

// Function to show paper chit resolution
function showPaperChitResolution() {
    const category = document.getElementById('clashCategorySelect').value;
    const tournamentId = getCurrentTournamentId();
    
    // Create paper chit resolution modal
    const modal = document.createElement('div');
    modal.id = 'paperChitModal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    `;
    
    modal.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 10px; max-width: 600px; max-height: 80vh; overflow-y: auto;">
            <h3 style="color: #9c27b0; margin-bottom: 20px;">📄 Paper Chit Resolution</h3>
            <div id="paperChitContent">
                <p>This feature allows you to manually resolve seeding clashes using paper chits.</p>
                <div style="margin: 20px 0;">
                    <strong>Instructions:</strong>
                    <ol style="margin-top: 10px;">
                        <li>Write player names on separate paper chits</li>
                        <li>Shuffle the chits thoroughly</li>
                        <li>Draw chits one by one and assign seeds</li>
                        <li>Click "Apply Paper Chit Results" when done</li>
                    </ol>
                </div>
                <div id="paperChitPlayers" style="margin: 20px 0;">
                    <!-- Clash players will be listed here -->
                </div>
                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button onclick="closePaperChitModal()" style="padding: 10px 20px; background: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        Cancel
                    </button>
                    <button onclick="applyPaperChitResults()" style="padding: 10px 20px; background: #4caf50; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        Apply Paper Chit Results
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Load clash players for paper chit
    loadPaperChitPlayers();
}

// Function to load players for paper chit resolution
async function loadPaperChitPlayers() {
    const category = document.getElementById('clashCategorySelect').value;
    const tournamentId = getCurrentTournamentId();
    
    try {
        const response = await fetch(`/tournament/${tournamentId}/get_category_players/${category}?fields=full`);
        const data = await response.json();
        
        if (!data.success) {
            alert('Failed to load players');
            return;
        }
        
        const players = data.players;
        const seedRangesResponse = await fetch('/get_seeding_ranges');
        const seedRangesData = await seedRangesResponse.json();
        const seedRanges = seedRangesData.seeding_ranges;
        
        // Detect clashes
        const clashes = detectSeedingClashes(players, seedRanges);
        
        const paperChitPlayers = document.getElementById('paperChitPlayers');
        if (!paperChitPlayers) {
            console.error('Paper chit players container not found');
            return;
        }
        
        paperChitPlayers.innerHTML = '';
        
        if (clashes.length === 0) {
            paperChitPlayers.innerHTML = '<p style="color: #f44336;">No clashes detected for paper chit resolution.</p>';
            return;
        }
        
        // Collect all clash players
        const clashPlayers = [];
        clashes.forEach(clash => {
            clash.players.forEach(playerInfo => {
                clashPlayers.push(playerInfo.player);
            });
        });
        
        // Display clash players
        paperChitPlayers.innerHTML = `
            <h4>Players with Seeding Clashes (${clashPlayers.length} players):</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 15px 0;">
                ${clashPlayers.map((player, index) => `
                    <div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px; background: #f9f9f9;">
                        <strong>${index + 1}.</strong> ${player.name}<br>
                        <small>Current Seed: ${player.seeding}</small><br>
                        <input type="number" id="paperChitSeed_${player.player_id}" 
                               placeholder="New Seed" min="1" 
                               style="width: 80px; margin-top: 5px;">
                    </div>
                `).join('')}
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading paper chit players:', error);
        alert('Error loading players for paper chit resolution.');
    }
}

// Function to apply paper chit results
async function applyPaperChitResults() {
    const category = document.getElementById('clashCategorySelect').value;
    const tournamentId = getCurrentTournamentId();
    
    try {
        // Get all paper chit seed inputs
        const seedInputs = document.querySelectorAll('[id^="paperChitSeed_"]');
        const playerIds = [];
        const seedings = [];
        
        for (const input of seedInputs) {
            const playerId = input.id.replace('paperChitSeed_', '');
            const newSeed = input.value.trim();
            
            if (newSeed && !isNaN(newSeed)) {
                playerIds.push(playerId);
                seedings.push(newSeed);
            }
        }
        
        if (playerIds.length > 0) {
            // Perform batch update using common function
            const result = await batchUpdateSeedings(playerIds, seedings, category, tournamentId);
            if (result.success) {
                showSuccessMessage(`Applied paper chit results for ${playerIds.length} players`);
                closePaperChitModal();
                loadClashPlayers(); // Reload to show updated state
            } else {
                showErrorMessage('Failed to save paper chit results: ' + result.message);
            }
        } else {
            showErrorMessage('No valid seed values found. Please enter new seeds for the players.');
        }
        
    } catch (error) {
        console.error('Error applying paper chit results:', error);
        showErrorMessage('Error applying paper chit results. Please try again.');
    }
}

// Function to close paper chit modal
function closePaperChitModal() {
    const modal = document.getElementById('paperChitModal');
    if (modal) {
        modal.remove();
    }
}

// Helper function to update player seeding
async function updatePlayerSeeding(tournamentId, category, playerId, newSeed) {
    try {
        console.log(`updatePlayerSeeding called: tournamentId=${tournamentId}, category=${category}, playerId=${playerId}, newSeed=${newSeed}`);
        
        const result = await batchUpdateSeedings([playerId], [newSeed.toString()], category, tournamentId);
        
        if (result.success) {
            console.log('Successfully updated player seeding');
            return result;
        } else {
            console.error('Failed to update player seeding:', result.message);
            throw new Error(result.message);
        }
    } catch (error) {
        console.error('Error updating player seeding:', error);
        throw error;
    }
}

// Function to resolve a clash by updating seed values
function resolveClash(oldSeed, newSeed) {
    const tbody = document.getElementById('clashTableBody');
    if (!tbody) {
        console.error('Clash table body not found');
        return;
    }
    
    const rows = tbody.getElementsByTagName('tr');
    
    // Find all rows with the old seed and update them
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const seedCell = row.cells[2]; // Seed column
        if (seedCell && seedCell.textContent.trim() === oldSeed) {
            seedCell.textContent = newSeed;
            row.classList.remove('seeding-clash');
            row.title = '';
        }
    }
    
    // Re-detect clashes after resolution
    const category = document.getElementById('clashCategorySelect').value;
    if (category) {
        loadClashPlayers(); // Reload to re-detect clashes
    }
}

// Helper functions that need to be available globally
function detectSeedingClashes(players, seedRanges) {
    const clashes = [];
    const seedGroups = {};
    
    // Group players by seed value
    players.forEach((player, index) => {
        const seed = player.seeding;
        if (seed && seed !== '') {
            if (!seedGroups[seed]) {
                seedGroups[seed] = [];
            }
            seedGroups[seed].push({
                player: player,
                index: index,
                range: getSeedRangeForSNo(index + 1, seedRanges)
            });
        }
    });
    
    // Check for clashes (same seed across different unique min-max ranges)
    Object.keys(seedGroups).forEach(seed => {
        const playersWithSeed = seedGroups[seed];
        if (playersWithSeed.length > 1) {
            // Use min-max as unique range identifier
            const rangeIdentifiers = playersWithSeed.map(p => {
                const range = p.range;
                return range ? `${range.min}-${range.max}` : 'unknown';
            });
            const uniqueRanges = [...new Set(rangeIdentifiers)];
            if (uniqueRanges.length > 1) {
                // This is a clash - same seed across different unique ranges
                const rangeDescriptions = uniqueRanges.map(rangeId => {
                    const [min, max] = rangeId.split('-').map(Number);
                    const range = seedRanges.find(r => r.min === min && r.max === max);
                    return range ? `${range.description} (${min}-${max})` : rangeId;
                });
                
                clashes.push({
                    seed: seed,
                    players: playersWithSeed,
                    ranges: rangeDescriptions,
                    rangeIdentifiers: uniqueRanges,
                    suggestedSeeds: generateSuggestedSeeds(seed, players)
                });
            }
        }
    });
    
    console.log('Detected clashes:', clashes);
    return clashes;
}

function getSeedRangeForSNo(serialNumber, seedRanges) {
    const seedNumber = parseInt(serialNumber);
    for (const range of seedRanges) {
        if (seedNumber >= range.min && seedNumber <= range.max) {
            return range;
        }
    }
    return null;
}

function generateSuggestedSeeds(clashSeed, allPlayers) {
    const usedSeeds = new Set(allPlayers.map(p => parseInt(p.seeding)).filter(s => !isNaN(s)));
    const clashSeedNum = parseInt(clashSeed);
    const suggestions = [];
    
    // Try next available seeds
    for (let i = 1; i <= 10; i++) {
        const suggestedSeed = clashSeedNum + i;
        if (!usedSeeds.has(suggestedSeed)) {
            suggestions.push(suggestedSeed);
            if (suggestions.length >= 3) break; // Limit to 3 suggestions
        }
    }
    
    // If we don't have enough suggestions, try lower seeds
    if (suggestions.length < 3) {
        for (let i = 1; i <= 10; i++) {
            const suggestedSeed = clashSeedNum - i;
            if (suggestedSeed > 0 && !usedSeeds.has(suggestedSeed)) {
                suggestions.unshift(suggestedSeed);
                if (suggestions.length >= 3) break;
            }
        }
    }
    
    return suggestions;
}

// Function to highlight clashes in the table
function highlightClashes(clashes) {
    const tbody = document.getElementById('clashTableBody');
    if (!tbody) {
        console.error('Clash table body not found');
        return;
    }
    
    const rows = tbody.getElementsByTagName('tr');
    
    clashes.forEach(clash => {
        clash.players.forEach(playerInfo => {
            const row = rows[playerInfo.index];
            if (row) {
                row.classList.add('seeding-clash');
                // Add tooltip with clash information
                row.title = `Seeding clash detected! Seed ${clash.seed} appears in multiple ranges: ${clash.ranges.join(', ')}`;
            }
        });
    });
}

async function saveAllSeedChanges() {
    try {
        console.log('Starting saveAllSeedChanges...');
        
        // Get all editable seed inputs
        const seedInputs = document.querySelectorAll('.seed-input[data-player-id]');
        console.log(`Found ${seedInputs.length} seed inputs to save`);
        
        const playerIds = [];
        const seedings = [];
        
        // Collect all player IDs and their new seedings
        seedInputs.forEach(input => {
            const playerId = input.getAttribute('data-player-id');
            const newSeeding = input.value.trim();
            
            playerIds.push(playerId);
            seedings.push(newSeeding);
            
            console.log(`Will save: Player ID "${playerId}" -> Seeding "${newSeeding}"`);
        });
        
        // Get current tournament and category
        const tournamentId = getCurrentTournamentId();
        const category = getCurrentCategory();
        
        // Use common batch update function
        const result = await batchUpdateSeedings(playerIds, seedings, category, tournamentId);
        
        if (result.success) {
            console.log('Save successful!');
            showSuccessMessage('Changes are saved!');
            
            // Refresh the data to show updated values
            await loadClashPlayers();
        } else {
            console.error('Save failed:', result.message);
            showErrorMessage('Failed to save seed changes: ' + result.message);
        }
    } catch (error) {
        console.error('Error saving seed changes:', error);
        showErrorMessage('Error saving seed changes: ' + error.message);
    }
}

// Function to show a simple success message
function showSuccessMessage(message) {
    // Create or get existing message element
    let messageElement = document.getElementById('clashMessage');
    if (!messageElement) {
        messageElement = document.createElement('div');
        messageElement.id = 'clashMessage';
        messageElement.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #4caf50;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            font-weight: bold;
            z-index: 10000;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transition: opacity 0.3s ease;
        `;
        document.body.appendChild(messageElement);
    }
    
    messageElement.textContent = message;
    messageElement.style.opacity = '1';
    messageElement.style.display = 'block';
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        messageElement.style.opacity = '0';
        setTimeout(() => {
            messageElement.style.display = 'none';
        }, 300);
    }, 3000);
}

// Function to show a simple error message
function showErrorMessage(message) {
    // Create or get existing message element
    let messageElement = document.getElementById('clashMessage');
    if (!messageElement) {
        messageElement = document.createElement('div');
        messageElement.id = 'clashMessage';
        messageElement.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #f44336;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            font-weight: bold;
            z-index: 10000;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transition: opacity 0.3s ease;
        `;
        document.body.appendChild(messageElement);
    }
    
    messageElement.textContent = message;
    messageElement.style.backgroundColor = '#f44336';
    messageElement.style.opacity = '1';
    messageElement.style.display = 'block';
    
    // Auto-hide after 5 seconds for errors
    setTimeout(() => {
        messageElement.style.opacity = '0';
        setTimeout(() => {
            messageElement.style.display = 'none';
        }, 300);
    }, 5000);
}

// Set default mode on page load
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function() {
        setClashMode('auto');
    });
} 