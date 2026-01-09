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
export function showPreloader(text = 'טוען את המסרקות והמאפרות המובילות...') {
    let preloader = document.getElementById('preloader');
    if (!preloader) {
        console.log("preloader not found");
    } else {
        // Update text if preloader exists
        const textEl = preloader.querySelector('.preloader-text');
        if (textEl) {
            textEl.textContent = text;
        }
        // Make sure preloader is visible
        preloader.classList.remove('hidden');
        preloader.style.display = 'flex';
        preloader.style.opacity = '1';
        preloader.style.visibility = 'visible';
    }
}

/**
 * Hide preloader
 */
export function hidePreloader() {
    const preloader = document.getElementById('preloader');
    if (preloader) {
        // Add the hidden class first
        preloader.classList.add('hidden');
        // Remove any inline styles that might override the CSS class
        preloader.style.removeProperty('display');
        preloader.style.removeProperty('opacity');
        preloader.style.removeProperty('visibility');
        preloader.style.removeProperty('z-index');
        // Force a reflow to ensure CSS is applied
        void preloader.offsetHeight;
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
