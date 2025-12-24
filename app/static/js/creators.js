// Creator management functions
import { normalizePhone, formatPriceRange } from './utils.js';
import { toggleModal, showNotification } from './ui.js';
import { getReviews, createReview } from './api.js';
import { loadCreators } from './api.js';

// Display creators in grid
export function displayCreators(creators) {
  const container = document.getElementById('creatorsList');
  if (!container) return;
  
  container.innerHTML = '';
  
  if (!creators || creators.length === 0) {
    container.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;">אין יוצרים זמינים</div>';
    return;
  }
  
  const grid = document.createElement('div');
  grid.className = 'creators-grid';
  
  creators.forEach(creator => {
    const card = createCreatorCard(creator);
    grid.appendChild(card);
  });
  
  container.appendChild(grid);
}

// Create individual creator card
export function createCreatorCard(creator) {
  const card = document.createElement('div');
  card.className = 'creator-card';
  card.style.cssText = 'border-radius: 16px; overflow: hidden; background: transparent; box-shadow: none; display: flex; flex-direction: column; width: 100%; height: 100%; margin: 0; cursor: pointer;';
  
  // Make entire card clickable to Instagram
  if (creator.username) {
    card.addEventListener('click', (e) => {
      // Don't trigger if clicking on links/buttons inside the card
      if (e.target.tagName === 'A' || e.target.closest('a')) {
        return;
      }
      window.open(`https://instagram.com/${creator.username}`, '_blank', 'noopener,noreferrer');
    });
  }
  
  // Header image - prioritize: similar_image > recent_image > sample_image > display_image
  const headerImg = document.createElement('img');
  headerImg.setAttribute('data-role', 'header');
  // Use similar image URL if in similarity mode, otherwise use recent image, then fallback to sample
  const imageUrl = creator.similar_image_data?.url || 
                   creator.recent_image || 
                   creator.sample_image  
                    || creator.display_image?.original_url|| 
                   '';
  headerImg.src = imageUrl;
  headerImg.alt = creator.similar_image_data?.caption || creator.bio || '';
  headerImg.style.cssText = 'width: 100%; aspect-ratio: 3/4; object-fit: contain; background: #f3f4f6; border-radius: 16px 16px 0 0; display: block;';
  headerImg.onerror = () => { headerImg.style.display = 'none'; };
  card.appendChild(headerImg);
  
  // Add similarity score indicator if available
  if (creator.similarity_score !== undefined && creator.similarity_score !== null) {
    const similarityBadge = document.createElement('div');
    similarityBadge.style.cssText = 'position: absolute; top: 12px; right: 12px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; z-index: 10;';
    similarityBadge.textContent = `${Math.round(creator.similarity_score * 100)}%`;
    card.style.position = 'relative';
    card.appendChild(similarityBadge);
  }
  
  // Content area
  const content = document.createElement('div');
  content.style.cssText = 'padding: 12px; background: white; flex: 1; display: flex; flex-direction: column;';
  
  // Avatar and username header
  const header = document.createElement('div');
  header.style.cssText = 'display: flex; align-items: center; gap: 8px; margin-bottom: 8px;';
  
  // Profile picture avatar
  const avatar = document.createElement('img');
  // Use Instagram profile picture URL
  const profilePicUrl = creator.profile_picture || '';
  avatar.src = profilePicUrl;
  avatar.alt = creator.username ? `${creator.username} profile picture` : 'Creator profile picture';
  avatar.style.cssText = 'width: 36px; height: 36px; border-radius: 50%; object-fit: cover; background: #f3f4f6; border: 2px solid #e5e7eb; flex-shrink: 0;';
  avatar.onerror = () => { 
    // Fallback to a default avatar or hide if no image available
    avatar.style.display = 'none';
  };
  header.appendChild(avatar);
  
  // Username and creator info container
  const usernameContainer = document.createElement('div');
  usernameContainer.style.cssText = 'display: flex; flex-direction: column; gap: 1px; flex: 1; min-width: 0;';
  
  const usernameLink = document.createElement('a');
  usernameLink.textContent = creator.username ? `@${creator.username}` : 'Unknown';
  usernameLink.href = creator.username ? `https://instagram.com/${creator.username}` : '#';  
  usernameLink.target = '_blank';
  usernameLink.rel = 'noopener';
  usernameLink.setAttribute('data-creator-username', creator.username || '');
  usernameLink.style.cssText = 'font-weight: 700; font-size: 15px; color: #111827; text-decoration: none; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;';
  usernameContainer.appendChild(usernameLink);
  
  header.appendChild(usernameContainer);
  content.appendChild(header);
  
  // Instagram bio - always show a placeholder div to maintain consistent height
  const bioContainer = document.createElement('div');
  bioContainer.style.cssText = 'min-height: 34px; margin-bottom: 8px;';
  if (creator.bio) {
    const bio = document.createElement('p');
    bio.textContent = creator.bio;
    bio.style.cssText = 'color: #6b7280; font-size: 12px; margin: 0; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-overflow: ellipsis;';
    bioContainer.appendChild(bio);
  }
  content.appendChild(bioContainer);
  
  // Location - always show container to maintain consistent height
  const locationContainer = document.createElement('div');
  locationContainer.style.cssText = 'min-height: 20px; margin-bottom: 8px;';
  if (creator.location) {
    // Map English location names to Hebrew
    const locationMap = {
      'North': 'צפון',
      'Haifa': 'חיפה',
      'Center': 'מרכז',
      'Tel Aviv': 'תל אביב',
      'Sharon': 'שרון',
      'Jerusalem': 'ירושלים',
      'South': 'דרום'
    };
    
    // Convert location to Hebrew if it's in English, otherwise use as-is
    let locationDisplay = creator.location;
    if (locationMap[creator.location]) {
      locationDisplay = locationMap[creator.location];
    }
    
    const location = document.createElement('div');
    location.style.cssText = 'display: flex; align-items: center; gap: 4px; color: #6b7280; font-size: 12px;';
    location.innerHTML = `
      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
      </svg>
      ${locationDisplay}
    `;
    locationContainer.appendChild(location);
  }
  content.appendChild(locationContainer);
  
  // Prices - always show container to maintain consistent height (max 3 rows = 6 prices)
  const pricesContainer = document.createElement('div');
  pricesContainer.style.cssText = 'margin-bottom: 8px; min-height: 66px; display: grid; grid-template-columns: 1fr 1fr; gap: 6px 8px;';
  
  const priceLabels = {
    price_hairstyle_bride: 'תסרוקת כלה',
    price_hairstyle_bridesmaid: 'תסרוקת מלווה',
    price_makeup_bride: 'איפור כלה',
    price_makeup_bridesmaid: 'איפור מלווה',
    price_hairstyle_makeup_combo: 'תסרוקת + איפור'
  };
  
  // Collect all valid prices (non-zero, non-null, non-undefined, non-empty)
  const validPrices = [];
  for (const [key, label] of Object.entries(priceLabels)) {
    const priceValue = creator[key];
    const priceNum = parseFloat(priceValue);
    // Only include if it's a valid number and greater than 0
    if (priceValue !== null && priceValue !== undefined && priceValue !== '' && !isNaN(priceNum) && priceNum > 0) {
      validPrices.push({ label, price: priceNum });
    }
  }
  
  // Display prices in grid (2 per row)
  validPrices.forEach(({ label, price }) => {
    const priceItem = document.createElement('div');
    priceItem.style.cssText = 'display: flex; justify-content: space-between; align-items: center; font-size: 11px;';
    
    const priceLabel = document.createElement('span');
    priceLabel.textContent = label;
    priceLabel.style.cssText = 'color: #6b7280; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;';
    
    const priceValueEl = document.createElement('span');
    priceValueEl.textContent = `₪${price.toLocaleString()}`;
    priceValueEl.style.cssText = 'color: #111827; font-weight: 600; flex-shrink: 0; margin-right: 4px;';
    
    priceItem.appendChild(priceLabel);
    priceItem.appendChild(priceValueEl);
    pricesContainer.appendChild(priceItem);
  });
  
  content.appendChild(pricesContainer);
  
  // Action buttons container
  const actionsContainer = document.createElement('div');
  actionsContainer.style.cssText = 'display: flex; gap: 8px; margin-top: auto;';
  
  // Reviews button
  const reviewsBtn = document.createElement('button');
  reviewsBtn.type = 'button';
  const reviewCount = creator.review_count || 0;
  reviewsBtn.textContent = `ביקורות (${reviewCount})`;
  reviewsBtn.style.cssText = 'display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 6px 12px; background: #7c3aed; color: white; text-decoration: none; border-radius: 6px; font-size: 12px; font-weight: 600; border: none; cursor: pointer; flex: 1;';
  reviewsBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    openReviewsModal(creator.username);
  });
  actionsContainer.appendChild(reviewsBtn);
  
  // WhatsApp button
  if (creator.phone) {
    const whatsappBtn = document.createElement('a');
    whatsappBtn.href = `https://wa.me/${normalizePhone(creator.phone)}`;
    whatsappBtn.target = '_blank';
    whatsappBtn.rel = 'noopener';
    whatsappBtn.style.cssText = 'display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 6px 12px; background: #25d366; color: white; text-decoration: none; border-radius: 6px; font-size: 12px; font-weight: 600; flex: 1;';
    whatsappBtn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893A11.821 11.821 0 0020.885 3.488"/>
      </svg>
      WhatsApp
    `;
    actionsContainer.appendChild(whatsappBtn);
  }
  
  content.appendChild(actionsContainer);
  
  card.appendChild(content);
  return card;
}

// Filter creators based on criteria
export function filterCreators(creators, filters) {
  return creators.filter(creator => {
    // Location filter - search based on arrival_location array (where creator can arrive to)
    if (filters.locations && filters.locations.length > 0) {
      // Parse arrival_location (can be string or array)
      let creatorArrivalLocations = [];
      if (creator.arrival_location) {
        if (Array.isArray(creator.arrival_location)) {
          creatorArrivalLocations = creator.arrival_location;
        } else if (typeof creator.arrival_location === 'string') {
          creatorArrivalLocations = creator.arrival_location.split(',').map(l => l.trim());
        }
      }
      
      // Check if any filter location matches any of the creator's arrival locations
      const hasMatchingLocation = filters.locations.some(loc => 
        creatorArrivalLocations.some(creatorLoc => creatorLoc.includes(loc) || loc.includes(creatorLoc))
      );
      if (!hasMatchingLocation) return false;
    }
    
    // Price filter - check all price fields (excluding zero prices)
    if (filters.maxPrice !== undefined) {
      // Collect all price values from the creator, excluding zeros
      const allPrices = [
        creator.price_hairstyle_bride,
        creator.price_hairstyle_bridesmaid,
        creator.price_makeup_bride,
        creator.price_makeup_bridesmaid,
        creator.price_hairstyle_makeup_combo,
        creator.min_price,
        creator.max_price
      ]
      .filter(price => price !== null && price !== undefined && price !== '')
      .map(price => parseFloat(price))
      .filter(price => !isNaN(price) && price > 0); // Only consider prices > 0 (at least 1)
      
      // If creator has no valid prices (all are zero or empty), exclude them
      if (allPrices.length === 0) {
        return false;
      }
      
      // Check if any price is within the filter range (1 to maxPrice)
      const hasPriceInRange = allPrices.some(price => price <= filters.maxPrice);
      
      if (!hasPriceInRange) return false;
    }
    
    // Availability filter (placeholder for future implementation)
    if (filters.availability) {
      // TODO: Implement availability filtering
    }
    
    return true;
  });
}

// Helper function to get minimum price from all price fields (excluding zero)
function getMinPrice(creator) {
  const allPrices = [
    creator.price_hairstyle_bride,
    creator.price_hairstyle_bridesmaid,
    creator.price_makeup_bride,
    creator.price_makeup_bridesmaid,
    creator.price_hairstyle_makeup_combo,
    creator.min_price
  ].filter(price => price !== null && price !== undefined && price !== '')
   .map(price => parseFloat(price))
   .filter(price => !isNaN(price) && price > 0); // Only consider prices > 0
  
  return allPrices.length > 0 ? Math.min(...allPrices) : Infinity;
}

// Helper function to get maximum price from all price fields (excluding zero)
function getMaxPrice(creator) {
  const allPrices = [
    creator.price_hairstyle_bride,
    creator.price_hairstyle_bridesmaid,
    creator.price_makeup_bride,
    creator.price_makeup_bridesmaid,
    creator.price_hairstyle_makeup_combo,
    creator.max_price
  ].filter(price => price !== null && price !== undefined && price !== '')
   .map(price => parseFloat(price))
   .filter(price => !isNaN(price) && price > 0); // Only consider prices > 0
  
  return allPrices.length > 0 ? Math.max(...allPrices) : 0;
}

// Sort creators
export function sortCreators(creators, sortBy) {
  const sorted = [...creators];
  
  switch (sortBy) {
    case 'price_low':
      return sorted.sort((a, b) => getMinPrice(a) - getMinPrice(b));
    case 'price_high':
      return sorted.sort((a, b) => getMaxPrice(b) - getMaxPrice(a));
    case 'name':
      return sorted.sort((a, b) => (a.username || '').localeCompare(b.username || ''));
    case 'recent':
    default:
      return sorted.sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0));
  }
}

// Open reviews modal
export async function openReviewsModal(creatorUsername) {
  const modal = document.getElementById('reviewsModal');
  if (!modal) return;
  
  // Update subtitle
  const subtitle = document.getElementById('reviewsModalSubtitle');
  if (subtitle) {
    subtitle.textContent = `ביקורות על @${creatorUsername}`;
  }
  
  // Store creator username for form submission
  modal.setAttribute('data-creator-username', creatorUsername);
  
  // Load reviews
  await loadReviews(creatorUsername);
  
  // Show modal
  toggleModal('reviewsModal', true);
}

// Load and display reviews
async function loadReviews(creatorUsername) {
  const reviewsList = document.getElementById('reviewsList');
  if (!reviewsList) return;
  
  try {
    reviewsList.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">טוען ביקורות...</div>';
    
    const data = await getReviews(creatorUsername);
    const reviews = data.reviews || [];
    
    if (reviews.length === 0) {
      reviewsList.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">אין ביקורות עדיין. היו הראשונים להוסיף ביקורת!</div>';
      return;
    }
    
    reviewsList.innerHTML = '';
    
    reviews.forEach(review => {
      const reviewDiv = document.createElement('div');
      reviewDiv.style.cssText = 'padding: 16px; margin-bottom: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb;';
      
      const header = document.createElement('div');
      header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;';
      
      const nameAndRating = document.createElement('div');
      nameAndRating.style.cssText = 'display: flex; align-items: center; gap: 8px;';
      
      const reviewerName = document.createElement('strong');
      reviewerName.textContent = review.reviewer_name || 'אנונימי';
      reviewerName.style.cssText = 'color: #111827; font-size: 14px;';
      nameAndRating.appendChild(reviewerName);
      
      if (review.rating) {
        const rating = document.createElement('span');
        rating.textContent = '⭐'.repeat(review.rating);
        rating.style.cssText = 'color: #f59e0b; font-size: 14px;';
        nameAndRating.appendChild(rating);
      }
      
      header.appendChild(nameAndRating);
      
      const date = document.createElement('span');
      if (review.created_at) {
        const reviewDate = new Date(review.created_at);
        date.textContent = reviewDate.toLocaleDateString('he-IL');
      }
      date.style.cssText = 'color: #6b7280; font-size: 12px;';
      header.appendChild(date);
      
      const comment = document.createElement('p');
      comment.textContent = review.comment;
      comment.style.cssText = 'color: #374151; font-size: 14px; line-height: 1.5; margin: 0;';
      
      reviewDiv.appendChild(header);
      reviewDiv.appendChild(comment);
      reviewsList.appendChild(reviewDiv);
    });
  } catch (error) {
    console.error('Failed to load reviews:', error);
    reviewsList.innerHTML = '<div style="text-align: center; padding: 20px; color: #ef4444;">שגיאה בטעינת הביקורות</div>';
  }
}

// Setup reviews form submission
export function setupReviewsForm() {
  const form = document.getElementById('addReviewForm');
  if (!form) return;
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const modal = document.getElementById('reviewsModal');
    if (!modal) return;
    
    const creatorUsername = modal.getAttribute('data-creator-username');
    if (!creatorUsername) {
      showNotification('שגיאה: לא נמצא שם יוצר/ת', 'error');
      return;
    }
    
    const reviewerName = document.getElementById('reviewerName')?.value || '';
    const comment = document.getElementById('reviewComment')?.value || '';
    const rating = document.getElementById('reviewRating')?.value || null;
    
    if (!comment.trim()) {
      showNotification('אנא הזינו תגובה', 'error');
      return;
    }
    
    const token = localStorage.getItem('auth_token');
    if (!token) {
      showNotification('נדרש להתחבר כדי להוסיף ביקורת', 'error');
      return;
    }
    
    try {
      await createReview({
        creator_username: creatorUsername,
        reviewer_name: reviewerName || null,
        comment: comment.trim(),
        rating: rating ? parseInt(rating) : null
      }, token);
      
      // Clear form
      form.reset();
      
      // Reload reviews
      await loadReviews(creatorUsername);
      
      // Refresh creators list to update review count
      await loadCreators();
      
      showNotification('ביקורת נוספה בהצלחה!', 'success');
    } catch (error) {
      console.error('Failed to create review:', error);
      showNotification('שגיאה בהוספת ביקורת', 'error');
    }
  });
}
