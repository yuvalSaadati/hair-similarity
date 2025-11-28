// Utility functions

// Keywords for filtering
export const KEYWORDS = [
  'hair', 'updo', 'half-up', 'ponytail', 'bun', 'braid', 'braids', 
  'waves', 'curls', 'curly', 'straight', 'sleek', 'bob', 'lob', 
  'pixie', 'shag', 'layers', 'fringe', 'bangs', 'wolf cut', 'fade', 
  'skin fade', 'שיער', 'תסרוקת', 'פן', 'עיצוב', 'מעצב', 'אסוף', 
  'חצי-אסוף', 'קוקו', 'קוקס', 'צמה', 'צמות', 'גלים', 'תלתלים', 
  'חלק', 'כלה', 'wedding', 'bridal', 'bride', 'תלתלים'
];

// Check if tags contain hair-related keywords
export function allowByKeywords(tags) {
  if (!tags || !Array.isArray(tags)) return false;
  return tags.some(tag => 
    KEYWORDS.some(keyword => 
      tag.toLowerCase().includes(keyword.toLowerCase())
    )
  );
}

// Handle image loading errors
export function handleImgError(img) {
  img.style.display = 'none';
  const parent = img.parentElement;
  if (parent && parent.classList.contains('card')) {
    parent.style.display = 'none';
  }
}

// Normalize phone number for WhatsApp
export function normalizePhone(phone) {
  if (!phone) return '';
  return phone.replace(/[^\d]/g, '');
}

// Format price range display
export function formatPriceRange(min, max) {
  if (!min && !max) return '';
  if (!min) return `עד ₪${max.toLocaleString()}`;
  if (!max) return `מ-₪${min.toLocaleString()}`;
  return `₪${min.toLocaleString()} - ₪${max.toLocaleString()}`;
}

// Debounce function for performance
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Throttle function for performance
export function throttle(func, limit) {
  let inThrottle;
  return function() {
    const args = arguments;
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// Format date for display
export function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('he-IL', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

// Format time for display
export function formatTime(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleTimeString('he-IL', {
    hour: '2-digit',
    minute: '2-digit'
  });
}

// Validate email format
export function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

// Validate phone number format
export function isValidPhone(phone) {
  const phoneRegex = /^[\d\-\+\(\)\s]+$/;
  return phoneRegex.test(phone) && phone.replace(/[^\d]/g, '').length >= 10;
}

// Generate random ID
export function generateId() {
  return Math.random().toString(36).substr(2, 9);
}

// Deep clone object
export function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') return obj;
  if (obj instanceof Date) return new Date(obj.getTime());
  if (obj instanceof Array) return obj.map(item => deepClone(item));
  if (typeof obj === 'object') {
    const clonedObj = {};
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key]);
      }
    }
    return clonedObj;
  }
}

// Check if element is in viewport
export function isInViewport(element) {
  const rect = element.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

// Smooth scroll to element
export function scrollToElement(element, offset = 0) {
  if (!element) return;
  
  const elementPosition = element.getBoundingClientRect().top;
  const offsetPosition = elementPosition + window.pageYOffset - offset;
  
  window.scrollTo({
    top: offsetPosition,
    behavior: 'smooth'
  });
}

// Get URL parameters
export function getUrlParams() {
  const params = {};
  const urlSearchParams = new URLSearchParams(window.location.search);
  for (const [key, value] of urlSearchParams) {
    params[key] = value;
  }
  return params;
}

// Set URL parameters
export function setUrlParams(params) {
  const url = new URL(window.location);
  Object.keys(params).forEach(key => {
    if (params[key] !== null && params[key] !== undefined) {
      url.searchParams.set(key, params[key]);
    } else {
      url.searchParams.delete(key);
    }
  });
  window.history.replaceState({}, '', url);
}

// Local storage helpers
export const storage = {
  get: (key) => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    } catch (error) {
      console.error('Error reading from localStorage:', error);
      return null;
    }
  },
  
  set: (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error('Error writing to localStorage:', error);
    }
  },
  
  remove: (key) => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Error removing from localStorage:', error);
    }
  }
};

