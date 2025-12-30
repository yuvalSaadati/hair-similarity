// API communication functions
import { displayPhotos } from './ui.js';
import { displayCreators } from './creators.js';

const API_BASE = '';



// Load creators
export async function loadCreators() {
  try {
    // Use with-display-images endpoint to get recent Instagram images
    const res = await fetch(`${API_BASE}/api/creators/with-display-images`);
    const data = await res.json();
    window.allCreators = data.creators;
    displayCreators(data.creators);
  } catch (error) {
    console.error('Failed to load creators:', error);   
  }
}

// Search by uploaded image, grouped by creator (returns best match per creator)
export async function searchByUploadByCreator(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const res = await fetch(`${API_BASE}/search/upload/by-creator`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    const data = await res.json();
    return data.matches; // Array of {creator_username, image, similarity_score}
  } catch (error) {
    console.error('Search by creator failed:', error);
    throw error;
  }
}

// Register user
export async function registerUser(email, password) {
  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    });
    
    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || `HTTP ${res.status}: ${res.statusText}`);
    }
    
    return await res.json();
  } catch (error) {
    console.error('Registration failed:', error);
    throw error;
  }
}

// Login user
export async function loginUser(email, password) {
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    });
    
    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || `HTTP ${res.status}: ${res.statusText}`);
    }
    
    return await res.json();
  } catch (error) {
    console.error('Login failed:', error);
    throw error;
  }
}

// Get current user's creator profile
export async function getMyCreator(token) {
  try {
    const res = await fetch(`${API_BASE}/api/me/creator`, {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    return await res.json();
  } catch (error) {
    console.error('Failed to get creator profile:', error);
    throw error;
  }
}

// Update creator profile
export async function updateCreatorProfile(token, data) {
  const params = new URLSearchParams(data);
  
  try {
    const res = await fetch(`${API_BASE}/api/me/creator?${params.toString()}`, {
      method: 'PUT',
      headers: { 'Authorization': 'Bearer ' + token }
    });
    return await res.json();
  } catch (error) {
    console.error('Failed to update creator profile:', error);
    throw error;
  }
}

// Get creator images
export async function getCreatorImages(username, token) {
  try {
    const res = await fetch(`${API_BASE}/api/creators/${username}/images`, {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    return await res.json();
  } catch (error) {
    console.error('Failed to get creator images:', error);
    throw error;
  }
}

// Set default image for creator
export async function setDefaultImage(username, imageId, token) {
  try {
    const res = await fetch(`${API_BASE}/api/creators/${username}/set-default-image`, {
      method: 'POST',
      headers: { 
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ image_id: imageId })
    });
    return await res.json();
  } catch (error) {
    console.error('Failed to set default image:', error);
    throw error;
  }
}

// Get reviews for a creator
export async function getReviews(creatorUsername) {
  try {
    const res = await fetch(`${API_BASE}/api/reviews/${creatorUsername}`);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    console.error('Failed to get reviews:', error);
    throw error;
  }
}

// Create a new review
export async function createReview(reviewData, token) {
  try {
    const res = await fetch(`${API_BASE}/api/reviews`, {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(reviewData)
    });
    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || `HTTP ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    console.error('Failed to create review:', error);
    throw error;
  }
}
