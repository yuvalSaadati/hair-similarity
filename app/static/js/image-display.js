/**
 * Image Display Management
 * 
 * Handles different image display modes for creator cards:
 * 1. Default: Show first/newest image
 * 2. Similarity search: Show most similar image to query
 */

const API_BASE = 'http://localhost:8000';

// Global state for current display mode
let currentDisplayMode = 'default';
let currentQueryImage = null;
// Store similarity data globally so it persists through other filters
let similarityDataMap = new Map(); // username -> {similar_image_data, similarity_score, etc.}

/**
 * Load creators with their display images
 */
export async function loadCreatorsWithDisplayImages() {
    try {
        const response = await fetch(`${API_BASE}/api/creators/with-display-images`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        return data.creators;
    } catch (error) {
        console.error('Failed to load creators with display images:', error);
        throw error;
    }
}

/**
 * Set display mode and update all creator cards
 */
export async function setDisplayMode(mode, queryImageFile = null) {
    currentDisplayMode = mode;
    currentQueryImage = queryImageFile;
    
    if (mode === 'similarity' && queryImageFile) {
        await updateAllCreatorCardsForSimilarity(queryImageFile);
    } else {
        await updateAllCreatorCardsForDefault();
    }
}

/**
 * Update all creator cards for default display mode
 */
async function updateAllCreatorCardsForDefault() {
    try {
        const creators = await loadCreatorsWithDisplayImages();
        // Update window.allCreators to remove similarity data
        window.allCreators = creators;
        await updateCreatorCardsDisplay(creators);
    } catch (error) {
        console.error('Failed to update creator cards for default mode:', error);
    }
}

/**
 * Show preloader
 */
function showPreloader(text = 'טוען את המסרקות והמאפרות המובילות...') {
    let preloader = document.getElementById('preloader');
    if (!preloader) {
        // Use the preloader from HTML if it exists, otherwise create it
        preloader = document.getElementById('preloader');
        if (!preloader) {
            // Create preloader if it doesn't exist in HTML
            preloader = document.createElement('div');
            preloader.id = 'preloader';
            preloader.className = 'preloader';
            preloader.innerHTML = document.querySelector('#preloader')?.innerHTML || `
                <div class="preloader-content">
                    <div class="preloader-animation">
                        <svg viewBox="0 0 300 350" xmlns="http://www.w3.org/2000/svg" class="bride-preloader">
                            <circle cx="50" cy="50" r="3" fill="#ffd700" opacity="0.6" class="sparkle sparkle-1"/>
                            <circle cx="250" cy="80" r="2.5" fill="#ffd700" opacity="0.6" class="sparkle sparkle-2"/>
                            <circle cx="80" cy="300" r="2" fill="#ffd700" opacity="0.6" class="sparkle sparkle-3"/>
                            <circle cx="220" cy="320" r="2.5" fill="#ffd700" opacity="0.6" class="sparkle sparkle-4"/>
                            <g class="hair-updo">
                                <path d="M 80 100 Q 70 50 90 40 Q 110 30 150 35 Q 190 30 210 40 Q 230 50 220 100 Q 215 120 210 130 L 200 140 L 100 140 Z" fill="#d4a574" class="hair-base"/>
                                <ellipse cx="150" cy="60" rx="35" ry="25" fill="#c9a574" class="hair-bun"/>
                                <ellipse cx="150" cy="60" rx="30" ry="20" fill="#d4a574" class="hair-bun-inner"/>
                                <path d="M 100 90 Q 95 85 100 80 Q 105 75 110 80" stroke="#c9a574" stroke-width="3" fill="none" stroke-linecap="round" class="hair-curl"/>
                                <path d="M 200 90 Q 205 85 200 80 Q 195 75 190 80" stroke="#c9a574" stroke-width="3" fill="none" stroke-linecap="round" class="hair-curl"/>
                                <path d="M 120 70 Q 150 65 180 70" stroke="#f0e68c" stroke-width="2" fill="none" opacity="0.7" class="hair-shine"/>
                            </g>
                            <g class="veil-tiara">
                                <path d="M 120 50 Q 150 45 180 50" stroke="#ffd700" stroke-width="2" fill="none" class="tiara"/>
                                <circle cx="150" cy="45" r="2" fill="#ffd700" class="tiara-gem"/>
                                <circle cx="130" cy="48" r="1.5" fill="#ffd700" class="tiara-gem"/>
                                <circle cx="170" cy="48" r="1.5" fill="#ffd700" class="tiara-gem"/>
                                <path d="M 100 100 Q 150 120 200 100 L 200 200 Q 150 180 100 200 Z" fill="rgba(255,255,255,0.3)" class="veil"/>
                            </g>
                            <ellipse cx="150" cy="160" rx="50" ry="55" fill="#fdbcb4" class="face"/>
                            <ellipse cx="150" cy="220" rx="25" ry="30" fill="#fdbcb4"/>
                            <path d="M 100 250 Q 150 240 200 250 L 200 280 Q 150 270 100 280 Z" fill="#fff5f5" class="dress-top"/>
                            <g class="eyes">
                                <ellipse cx="130" cy="150" rx="12" ry="10" fill="#fff" class="eye"/>
                                <circle cx="132" cy="150" r="7" fill="#4a4a4a" class="pupil"/>
                                <circle cx="133" cy="149" r="3" fill="#000" class="iris"/>
                                <circle cx="134" cy="148" r="1.5" fill="#fff" class="highlight"/>
                                <path d="M 118 145 Q 120 143 122 145" stroke="#333" stroke-width="1.5" fill="none" class="eyelash"/>
                                <path d="M 120 147 Q 122 145 124 147" stroke="#333" stroke-width="1.5" fill="none" class="eyelash"/>
                                <path d="M 122 149 Q 124 147 126 149" stroke="#333" stroke-width="1.5" fill="none" class="eyelash"/>
                                <ellipse cx="170" cy="150" rx="12" ry="10" fill="#fff" class="eye"/>
                                <circle cx="168" cy="150" r="7" fill="#4a4a4a" class="pupil"/>
                                <circle cx="167" cy="149" r="3" fill="#000" class="iris"/>
                                <circle cx="166" cy="148" r="1.5" fill="#fff" class="highlight"/>
                                <path d="M 182 145 Q 180 143 178 145" stroke="#333" stroke-width="1.5" fill="none" class="eyelash"/>
                                <path d="M 180 147 Q 178 145 176 147" stroke="#333" stroke-width="1.5" fill="none" class="eyelash"/>
                                <path d="M 178 149 Q 176 147 174 149" stroke="#333" stroke-width="1.5" fill="none" class="eyelash"/>
                            </g>
                            <path d="M 115 140 Q 130 138 145 140" stroke="#8b4513" stroke-width="2" fill="none" stroke-linecap="round" class="eyebrow"/>
                            <path d="M 155 140 Q 170 138 185 140" stroke="#8b4513" stroke-width="2" fill="none" stroke-linecap="round" class="eyebrow"/>
                            <ellipse cx="110" cy="175" rx="10" ry="8" fill="#ffb3ba" opacity="0.5" class="blush"/>
                            <ellipse cx="190" cy="175" rx="10" ry="8" fill="#ffb3ba" opacity="0.5" class="blush"/>
                            <ellipse cx="150" cy="170" rx="3" ry="5" fill="#fdbcb4" opacity="0.5"/>
                            <path d="M 135 190 Q 150 195 165 190" stroke="#d81b60" stroke-width="4" fill="none" stroke-linecap="round" class="lips"/>
                            <path d="M 135 190 Q 150 193 165 190" stroke="#ff69b4" stroke-width="2" fill="none" stroke-linecap="round" class="lips-gloss"/>
                            <g class="makeup-brush">
                                <rect x="220" y="160" width="30" height="5" rx="2.5" fill="#d4af37" transform="rotate(35 235 162.5)" class="brush-handle"/>
                                <rect x="240" y="150" width="10" height="15" rx="3" fill="#8b7355" class="brush-body"/>
                                <circle cx="245" cy="142" r="4" fill="#ffb3ba" class="brush-tip"/>
                                <circle cx="200" cy="175" r="1.5" fill="#ffb3ba" opacity="0.6" class="particle particle-1"/>
                                <circle cx="205" cy="170" r="1" fill="#ffb3ba" opacity="0.5" class="particle particle-2"/>
                                <circle cx="195" cy="180" r="1.2" fill="#ffb3ba" opacity="0.4" class="particle particle-3"/>
                            </g>
                            <g class="hair-brush">
                                <rect x="50" y="120" width="25" height="4" rx="2" fill="#d4af37" transform="rotate(-25 62.5 122)" class="brush-handle"/>
                                <rect x="45" y="110" width="8" height="15" rx="2" fill="#8b7355" class="brush-body"/>
                                <line x1="49" y1="105" x2="49" y2="110" stroke="#8b7355" stroke-width="1.5" class="bristle"/>
                                <line x1="51" y1="105" x2="51" y2="110" stroke="#8b7355" stroke-width="1.5" class="bristle"/>
                                <line x1="53" y1="105" x2="53" y2="110" stroke="#8b7355" stroke-width="1.5" class="bristle"/>
                                <circle cx="70" cy="100" r="1.5" fill="#d4a574" opacity="0.5" class="hair-particle particle-4"/>
                                <circle cx="75" cy="95" r="1" fill="#d4a574" opacity="0.4" class="hair-particle particle-5"/>
                            </g>
                            <g class="eyeliner-brush">
                                <rect x="220" y="130" width="25" height="3" rx="1.5" fill="#d4af37" transform="rotate(-20 232.5 131.5)" class="brush-handle"/>
                                <rect x="235" y="120" width="7" height="12" rx="2" fill="#8b7355" class="brush-body"/>
                                <circle cx="238" cy="115" r="2.5" fill="#4a4a4a" class="brush-tip"/>
                            </g>
                        </svg>
                    </div>
                    <p class="preloader-text">${text}</p>
                    <div class="preloader-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            `;
            document.body.appendChild(preloader);
        }
    } else {
        // Update text if preloader exists
        const textEl = preloader.querySelector('.preloader-text');
        if (textEl) {
            textEl.textContent = text;
        }
        preloader.classList.remove('hidden');
    }
}

/**
 * Hide preloader
 */
function hidePreloader() {
    const preloader = document.getElementById('preloader');
    if (preloader) {
        preloader.classList.add('hidden');
        setTimeout(() => {
            if (preloader.parentNode) {
                preloader.remove();
            }
        }, 500);
    }
}

/**
 * Wait for all images in creator cards to load
 */
function waitForImagesToLoad() {
    return new Promise((resolve) => {
        const images = document.querySelectorAll('.creator-card img[data-role="header"]');
        if (images.length === 0) {
            resolve();
            return;
        }
        
        let loadedCount = 0;
        let errorCount = 0;
        const totalImages = images.length;
        
        const checkComplete = () => {
            if (loadedCount + errorCount >= totalImages) {
                // Wait a bit more for smooth transition
                setTimeout(resolve, 300);
            }
        };
        
        images.forEach(img => {
            if (img.complete) {
                loadedCount++;
                checkComplete();
            } else {
                img.addEventListener('load', () => {
                    loadedCount++;
                    checkComplete();
                });
                img.addEventListener('error', () => {
                    errorCount++;
                    checkComplete();
                });
            }
        });
        
        // Timeout after 10 seconds to prevent infinite waiting
        setTimeout(() => {
            resolve();
        }, 10000);
    });
}

/**
 * Update all creator cards for similarity search mode
 */
async function updateAllCreatorCardsForSimilarity(queryImageFile) {
    try {
        // Show preloader
        showPreloader('מחפש תמונות דומות...');
        
        // Use the new endpoint that finds most similar image per creator in one call
        const { searchByUploadByCreator } = await import('./api.js');
        const matches = await searchByUploadByCreator(queryImageFile);
        
        // Get all creators to merge with similarity results
        const creators = await loadCreatorsWithDisplayImages();
        
        // Create a map of username -> similarity match
        const similarityMap = new Map();
        matches.forEach(match => {
            similarityMap.set(match.creator_username, match);
        });
        
        // Store similarity data globally for persistence through filters
        similarityDataMap.clear();
        matches.forEach(match => {
            let imageUrl = match.image.media_url;
            similarityDataMap.set(match.creator_username, {
                similarity_score: match.similarity_score,
                similar_image_media_id: match.image.media_id,
                similar_image_data: {
                    id: match.image.id,
                    media_id: match.image.media_id,
                    url: imageUrl,
                    caption: match.image.caption,
                    width: match.image.width,
                    height: match.image.height
                },
                sample_image: imageUrl
            });
        });
        
        // Merge similarity data into all creators (not just matches)
        // This allows filtering by price/location while keeping similarity images
        const allCreatorsWithSimilarity = creators.map(creator => {
            const match = similarityMap.get(creator.username);
            if (match) {
                let imageUrl = match.image.media_url;
                return {
                    ...creator,
                    sample_image: imageUrl,
                    similarity_score: match.similarity_score,
                    similar_image_media_id: match.image.media_id,
                    similar_image_data: {
                        id: match.image.id,
                        media_id: match.image.media_id,
                        url: imageUrl,
                        caption: match.image.caption,
                        width: match.image.width,
                        height: match.image.height
                    }
                };
            }
            return creator;
        });
        
        // Sort by similarity score (creators with matches first, then by score)
        const sortedCreators = allCreatorsWithSimilarity.sort((a, b) => {
            // Creators with similarity scores come first
            if (a.similarity_score !== undefined && b.similarity_score === undefined) return -1;
            if (a.similarity_score === undefined && b.similarity_score !== undefined) return 1;
            // If both have scores, sort by score (higher is better)
            if (a.similarity_score !== undefined && b.similarity_score !== undefined) {
                return b.similarity_score - a.similarity_score;
            }
            return 0;
        });
        
        // Update window.allCreators to include similarity data for future filters
        window.allCreators = sortedCreators;
        
        // Update display
        await updateCreatorCardsDisplay(sortedCreators);
        
        // Update preloader text
        showPreloader('מעדכן תמונות...');
        
        // Wait for all images to load
        await waitForImagesToLoad();
        
        // Hide preloader
        hidePreloader();
    } catch (error) {
        console.error('Failed to update creator cards for similarity mode:', error);
        hidePreloader();
    }
}

/**
 * Update the display of creator cards
 */
async function updateCreatorCardsDisplay(creators) {
    // Import createCreatorCard from creators.js
    const { createCreatorCard } = await import('./creators.js');
    
    // Find the container - could be 'creatorsList' or '.creator-cards'
    const creatorCardsContainer = document.querySelector('.creator-cards') || document.getElementById('creatorsList');
    if (!creatorCardsContainer) {
        console.error('Creator cards container not found');
        return;
    }
    
    // Clear existing cards
    creatorCardsContainer.innerHTML = '';
    
    // Create grid container if needed
    let grid = creatorCardsContainer.querySelector('.creators-grid');
    if (!grid) {
        grid = document.createElement('div');
        grid.className = 'creators-grid';
        creatorCardsContainer.appendChild(grid);
    } else {
        grid.innerHTML = '';
    }
    
    // Create new cards
    creators.forEach(creator => {
        const card = createCreatorCard(creator);
        grid.appendChild(card);
    });
    
    // Return promise that resolves when cards are created
    return Promise.resolve();
}


/**
 * Handle similarity search button click
 */
export function handleSimilaritySearch(queryImageFile) {
    setDisplayMode('similarity', queryImageFile);
}

/**
 * Handle clear filters button click
 */
export function handleClearFilters() {
    // Clear similarity data when resetting filters
    similarityDataMap.clear();
    setDisplayMode('default');
}

/**
 * Get similarity data for a creator (if exists)
 */
export function getSimilarityDataForCreator(username) {
    return similarityDataMap.get(username) || null;
}

/**
 * Initialize image display system
 */
export function initializeImageDisplay() {
    // Set up event listeners for similarity search
    const similaritySearchBtn = document.querySelector('.similarity-search-btn');
    if (similaritySearchBtn) {
        similaritySearchBtn.addEventListener('click', () => {
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = 'image/*';
            fileInput.onchange = (e) => {
                const file = e.target.files[0];
                if (file) {
                    handleSimilaritySearch(file);
                }
            };
            fileInput.click();
        });
    }
    
    // Set up event listener for clear filters
    const clearFiltersBtn = document.querySelector('.clear-filters-btn');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', handleClearFilters);
    }
    
    // Load initial creators
    // updateAllCreatorCardsForDefault();
}
