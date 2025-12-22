// Filter and search functions
import { searchByUploadByCreator } from './api.js';
import { filterCreators, sortCreators, displayCreators } from './creators.js';
import { showLoading } from './ui.js';
import { handleSimilaritySearch, handleClearFilters } from './image-display.js';

// Setup filter functionality
export function setupFilters() {
  setupRegionDropdown();
  setupPriceSlider();
  setupStyleMatch();
  setupClearFilters();
}

// Region dropdown functionality
function setupRegionDropdown() {
  const btn = document.getElementById('regionDropdownBtn');
  const menu = document.getElementById('regionDropdownMenu');
  const options = document.querySelectorAll('#regionOptionsList input[type="checkbox"]');
  
  if (!btn || !menu) return;
  
  // Toggle dropdown
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    menu.classList.toggle('open');
  });
  
  // Close dropdown when clicking outside
  document.addEventListener('click', (e) => {
    if (!btn.contains(e.target) && !menu.contains(e.target)) {
      menu.classList.remove('open');
    }
  });
  
  // Handle option selection
  options.forEach(option => {
    option.addEventListener('change', updateRegionSelection);
  });
  
  // Update selection display
  updateRegionSelection();
}

function updateRegionSelection() {
  const selected = getSelectedRegions();
  const label = document.getElementById('regionSelectedLabel');
  
  if (!label) return;
  
  if (selected.length === 0) {
    label.textContent = 'בחרו אזורים...';
    label.classList.add('placeholder');
  } else if (selected.length === 1) {
    label.textContent = selected[0];
    label.classList.remove('placeholder');
  } else {
    label.textContent = `${selected.length} אזורים נבחרו`;
    label.classList.remove('placeholder');
  }
  
  // Trigger filtering
  filterCreatorsAndDisplay();
}

function getSelectedRegions() {
  const options = document.querySelectorAll('#regionOptionsList input[type="checkbox"]:checked');
  return Array.from(options).map(option => option.value);
}

// Price slider functionality
function setupPriceSlider() {
  const maxSlider = document.getElementById('maxSlider');
  const maxLabel = document.getElementById('maxLabel');
  
  if (!maxSlider || !maxLabel) return;
  
  // Update display when slider changes
  maxSlider.addEventListener('input', () => {
    const value = parseInt(maxSlider.value);
    maxLabel.textContent = `₪ ${value.toLocaleString()}`;
    filterCreatorsAndDisplay();
  });
  
  // Initialize display
  const initialValue = parseInt(maxSlider.value);
  maxLabel.textContent = `₪ ${initialValue.toLocaleString()}`;
}

// Style match functionality
function setupStyleMatch() {
  const styleMatchBtn = document.getElementById('styleMatchBtn');
  const styleMatchFile = document.getElementById('styleMatchFile');
  
  if (!styleMatchBtn || !styleMatchFile) return;
  
  styleMatchBtn.addEventListener('click', () => {
    styleMatchFile.click();
  });
  
  styleMatchFile.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      const file = e.target.files[0];
      handleSimilaritySearch(file);
    }
  });
}

// Handle style match file upload
async function handleStyleMatchFile(input) {
  const file = input.files[0];
  if (!file) return;
  
  try {
    showLoading('creatorsList', 'מחפש התאמות...');
    
    // Search for similar images
    const matches = await searchByUploadByCreator(file);
    
    if (matches && matches.length > 0) {
      // Update creator cards with best matches
      updateCreatorCardsWithMatches(matches);
      showNotification(`נמצאו ${matches.length} התאמות`, 'success');
    } else {
      showNotification('לא נמצאו התאמות', 'warning');
    }
  } catch (error) {
    console.error('Style match failed:', error);
    showNotification('שגיאה בחיפוש התאמות', 'error');
  } finally {
    // Clear the file input
    input.value = '';
  }
}

// Update creator cards with style match results
function updateCreatorCardsWithMatches(matches) {
  const cards = document.querySelectorAll('.creator-card');
  
  cards.forEach(card => {
    const usernameElement = card.querySelector('[data-creator-username]');
    if (!usernameElement) return;
    
    const username = usernameElement.getAttribute('data-creator-username');
    
    // Find best match for this creator
    const creatorMatches = matches.filter(match => 
      match.caption && match.caption.includes(`@${username}`)
    );
    
    if (creatorMatches.length > 0) {
      const best = creatorMatches[0]; // Assuming first is best
      const headerImg = card.querySelector('img[data-role="header"]');
      if (headerImg && best.url) {
        headerImg.src = best.local_url || best.url;
      }
    }
  });
}

// Clear filters functionality
function setupClearFilters() {
  const clearBtn = document.getElementById('clearFiltersBtn');
  if (!clearBtn) return;
  
  clearBtn.addEventListener('click', () => {
    clearFilters();
    handleClearFilters();
  });
}

function clearFilters() {
  // Reset region selection
  const regionOptions = document.querySelectorAll('#regionOptionsList input[type="checkbox"]');
  regionOptions.forEach(option => {
    option.checked = false;
  });
  updateRegionSelection();
  
  // Reset price slider
  const maxSlider = document.getElementById('maxSlider');
  if (maxSlider) {
    maxSlider.value = maxSlider.max;
    const maxLabel = document.getElementById('maxLabel');
    if (maxLabel) {
      maxLabel.textContent = `₪ ${parseInt(maxSlider.value).toLocaleString()}`;
    }
  }
  
  // Reset availability (if implemented)
  const availabilityInput = document.getElementById('filterDate');
  if (availabilityInput) {
    availabilityInput.value = '';
  }
  
  // Refresh display
  filterCreatorsAndDisplay();
}

// Main filtering function
function filterCreatorsAndDisplay() {
  if (!window.allCreators) return;
  
  const filters = {
    locations: getSelectedRegions(),
    maxPrice: parseInt(document.getElementById('maxSlider')?.value || '10000'),
    availability: document.getElementById('filterDate')?.value
  };
  
  // Filter creators
  const filtered = filterCreators(window.allCreators, filters);
  
  // Sort creators (default: recent)
  const sorted = sortCreators(filtered, 'recent');
  
  // Display results
  displayCreators(sorted);
}

// Export for external use
window.filterCreatorsAndDisplay = filterCreatorsAndDisplay;
