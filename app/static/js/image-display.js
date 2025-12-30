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
        await updateCreatorCardsDisplay(creators);
    } catch (error) {
        console.error('Failed to update creator cards for default mode:', error);
    }
}

/**
 * Update all creator cards for similarity search mode
 */
async function updateAllCreatorCardsForSimilarity(queryImageFile) {
    try {
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
        
        // Only show creators that have matches (top 10 from API)
        // Results are already sorted by similarity score from the API
        // Use Promise.all to handle async URL fetching
        const updatedCreators = await Promise.all(matches.map(async (match) => {
            // Find the creator data
            const creator = creators.find(c => c.username === match.creator_username);
            
            // Get image URLs using get_instagram_media_url
            // match.image.url should be the Instagram post URL (permalink)
            let imageUrl = match.image.media_url;
        
        
            
            if (!creator) {
                // If creator not found, create minimal object
                return {
                    username: match.creator_username,
                    similarity_score: match.similarity_score,
                    similar_image_data: match.image,
                    sample_image: imageUrl
                };
            }
            
            return {
                ...creator,
                // Use the most similar image as the display image
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
        }));
        
        await updateCreatorCardsDisplay(updatedCreators);
    } catch (error) {
        console.error('Failed to update creator cards for similarity mode:', error);
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
    setDisplayMode('default');
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
