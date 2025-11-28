// UI manipulation functions
import { handleImgError } from './utils.js';

// Display photos in a grid
export function displayPhotos(photos, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  container.innerHTML = '';
  
  photos.forEach(photo => {
    const div = document.createElement('div');
    div.className = 'card';
    
    const img = document.createElement('img');
    img.src = photo.url;
    img.alt = photo.caption || '';
    img.onerror = () => handleImgError(img);
    
    div.appendChild(img);
    
    if (photo.caption) {
      const caption = document.createElement('div');
      caption.className = 'hashtags';
      caption.textContent = photo.caption;
      div.appendChild(caption);
    }
    
    if (photo.similarity) {
      const similarity = document.createElement('div');
      similarity.className = 'similarity';
      similarity.textContent = `Similarity: ${(photo.similarity * 100).toFixed(1)}%`;
      div.appendChild(similarity);
    }
    
    container.appendChild(div);
  });
}

// Display search results
export function displaySearchResults(matches) {
  const container = document.getElementById('searchResults');
  if (!container) return;
  
  container.innerHTML = '<h3>Similar Images</h3>';
  displayPhotos(matches, 'searchResults');
}

// Display hashtag search results
export function displayHashtagResults(matches) {
  const container = document.getElementById('hashtagResults');
  if (!container) return;
  
  container.innerHTML = '<h3>Hashtag Search Results</h3>';
  displayPhotos(matches, 'hashtagResults');
}

// Show loading state
export function showLoading(containerId, message = 'Loading...') {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  container.innerHTML = `<div class="loading">${message}</div>`;
}

// Show error message
export function showError(containerId, message) {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  container.innerHTML = `<div class="error" style="color: red; text-align: center; padding: 20px;">${message}</div>`;
}

// Toggle modal visibility
export function toggleModal(modalId, show) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  
  if (show) {
    modal.classList.add('open');
  } else {
    modal.classList.remove('open');
  }
}

// Update form field value
export function updateFormField(fieldId, value) {
  const field = document.getElementById(fieldId);
  if (field) {
    field.value = value;
  }
}

// Get form field value
export function getFormFieldValue(fieldId) {
  const field = document.getElementById(fieldId);
  return field ? field.value : '';
}

// Get selected values from multi-select
export function getSelectedValues(selectId) {
  const select = document.getElementById(selectId);
  if (!select) return [];
  
  return Array.from(select.selectedOptions).map(option => option.value);
}

// Set selected values in multi-select
export function setSelectedValues(selectId, values) {
  const select = document.getElementById(selectId);
  if (!select) return;
  
  Array.from(select.options).forEach(option => {
    option.selected = values.includes(option.value);
  });
}

// Show notification
export function showNotification(message, type = 'info') {
  // Create notification element
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 20px;
    border-radius: 8px;
    color: white;
    font-weight: 500;
    z-index: 10000;
    max-width: 300px;
    word-wrap: break-word;
  `;
  
  // Set background color based on type
  switch (type) {
    case 'success':
      notification.style.backgroundColor = '#10b981';
      break;
    case 'error':
      notification.style.backgroundColor = '#ef4444';
      break;
    case 'warning':
      notification.style.backgroundColor = '#f59e0b';
      break;
    default:
      notification.style.backgroundColor = '#3b82f6';
  }
  
  notification.textContent = message;
  document.body.appendChild(notification);
  
  // Remove after 3 seconds
  setTimeout(() => {
    if (notification.parentNode) {
      notification.parentNode.removeChild(notification);
    }
  }, 3000);
}
