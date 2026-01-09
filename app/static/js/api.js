// API communication functions
import { displayPhotos } from './ui.js';
import { displayCreators } from './creators.js';
import { showPreloader, hidePreloader } from './image-display.js';

const API_BASE = '';



// Load creators
export async function loadCreators(showLoading = false) {
  try {
    // Show preloader if requested
    if (showLoading) {
      showPreloader('טוען את המסרקות והמאפרות המובילות...');
    }
    
    // Use with-display-images endpoint to get recent Instagram images
    const res = await fetch(`${API_BASE}/api/creators/with-display-images`);
    const data = await res.json();
    window.allCreators = data.creators;
    displayCreators(data.creators);
    
    // Hide preloader if it was shown
    if (showLoading) {
      hidePreloader();
    }
    
    // Return success
    return true;
  } catch (error) {
    console.error('Failed to load creators:', error);
    // Hide preloader on error
    if (showLoading) {
      hidePreloader();
    }
    throw error;
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
      // Check if response is JSON before parsing
      const contentType = res.headers.get('content-type');
      let errorMessage = `HTTP ${res.status}: ${res.statusText}`;
      
      if (contentType && contentType.includes('application/json')) {
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (parseError) {
          console.error('Failed to parse error response as JSON:', parseError);
          // If JSON parsing fails, try to get text
          const text = await res.text();
          errorMessage = text || errorMessage;
        }
      } else {
        // Response is not JSON, try to get text
        try {
          const text = await res.text();
          errorMessage = text || errorMessage;
        } catch (textError) {
          console.error('Failed to read error response:', textError);
        }
      }
      
      throw new Error(errorMessage);
    }
    
    return await res.json();
  } catch (error) {
    console.error('Registration failed:', error);
    // If it's already an Error with a message, re-throw it
    if (error instanceof Error) {
      throw error;
    }
    // Otherwise, wrap it in an Error
    throw new Error(error.message || 'Registration failed');
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
      // Check if response is JSON before parsing
      const contentType = res.headers.get('content-type');
      let errorMessage = `HTTP ${res.status}: ${res.statusText}`;
      
      if (contentType && contentType.includes('application/json')) {
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (parseError) {
          console.error('Failed to parse error response as JSON:', parseError);
          const text = await res.text();
          errorMessage = text || errorMessage;
        }
      } else {
        try {
          const text = await res.text();
          errorMessage = text || errorMessage;
        } catch (textError) {
          console.error('Failed to read error response:', textError);
        }
      }
      
      throw new Error(errorMessage);
    }
    
    return await res.json();
  } catch (error) {
    console.error('Login failed:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(error.message || 'Login failed');
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
    
    if (!res.ok) {
      // Try to get error message from response
      let errorMessage = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorData = await res.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {
        // If response is not JSON, try text
        try {
          errorMessage = await res.text() || errorMessage;
        } catch (e2) {
          // Use default message
        }
      }
      const error = new Error(errorMessage);
      error.response = res;
      throw error;
    }
    
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
