// Main application initialization
import { loadCreators } from './api.js';
import { setupFilters } from './filters.js';
import { setupAuth } from './auth.js';
import { initializeImageDisplay } from './image-display.js';
import { setupReviewsForm } from './creators.js';

// Global variables
let allCreators = [];
let queryEmbedding = null;

// Hide preloader function
function hidePreloader() {
  const preloader = document.getElementById('preloader');
  const body = document.body;
  
  if (preloader) {
    preloader.classList.add('hidden');
    // Show body content
    body.classList.add('loaded');
    // Remove preloader from DOM after animation
    setTimeout(() => {
      preloader.remove();
    }, 500);
  } else {
    // If preloader already removed, just show body
    body.classList.add('loaded');
  }
}


// Initialize the application
document.addEventListener('DOMContentLoaded', async () => {
  console.log('🎨 Hair Similarity App Starting...');
  
  // Ensure preloader is visible
  const preloader = document.getElementById('preloader');
  if (preloader) {
    preloader.classList.remove('hidden');
    preloader.style.display = 'flex';
    preloader.style.opacity = '1';
    preloader.style.visibility = 'visible';
  }
  
  try {
    // Load initial data
    await loadCreators();
    
    // Setup UI components
    setupFilters();
    setupAuth();
    initializeImageDisplay();
    setupReviewsForm();
    
    // Hide preloader after everything is loaded
    hidePreloader();
    
    console.log('✅ App initialized successfully');
  } catch (error) {
    console.error('❌ Failed to initialize app:', error);
    // Hide preloader even on error
    hidePreloader();
  }
});

// Export for other modules
window.allCreators = allCreators;
window.queryEmbedding = queryEmbedding;
