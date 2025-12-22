// Main application initialization
import { loadCreators, loadRandomPhotos } from './api.js';
import { setupFilters } from './filters.js';
import { setupAuth } from './auth.js';
import { initializeImageDisplay } from './image-display.js';

// Global variables
let allCreators = [];
let queryEmbedding = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', async () => {
  console.log('🎨 Hair Similarity App Starting...');
  
  try {
    // Load initial data
    // await loadRandomPhotos();
    await loadCreators();
    
    // Setup UI components
    setupFilters();
    setupAuth();
    initializeImageDisplay();
    
    console.log('✅ App initialized successfully');
  } catch (error) {
    console.error('❌ Failed to initialize app:', error);
  }
});

// Export for other modules
window.allCreators = allCreators;
window.queryEmbedding = queryEmbedding;
