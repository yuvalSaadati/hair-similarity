// Filter and search functions
import { filterCreators, sortCreators, displayCreators } from './creators.js';
import { handleSimilaritySearch, handleClearFilters, getSimilarityDataForCreator } from './image-display.js';

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
  
  // Merge similarity data if it exists (from image similarity search)
  // This ensures similarity images persist in the background even when filtering by price/location
  const creatorsWithSimilarity = filtered.map(creator => {
    const similarityData = getSimilarityDataForCreator(creator.username);
    if (similarityData) {
      return {
        ...creator,
        ...similarityData
      };
    }
    return creator;
  });
  
  // Sort creators (default: recent)
  const sorted = sortCreators(creatorsWithSimilarity, 'recent');
  
  // Display results
  displayCreators(sorted);
}

// Export for external use
window.filterCreatorsAndDisplay = filterCreatorsAndDisplay;
