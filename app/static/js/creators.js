// Creator management functions
import { normalizePhone, formatPriceRange } from './utils.js';

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
  card.style.cssText = 'border-radius: 16px; overflow: hidden; background: transparent; box-shadow: none; display: flex; flex-direction: column; width: 100%; max-width: 320px; margin: 0 auto; cursor: pointer;';
  
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
  headerImg.style.cssText = 'width: 100%; aspect-ratio: 4/5; object-fit: cover; background: #f3f4f6; border-radius: 16px 16px 0 0;';
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
  content.style.cssText = 'padding: 16px; background: white; flex: 1; display: flex; flex-direction: column;';
  
  // Avatar and username header
  const header = document.createElement('div');
  header.style.cssText = 'display: flex; align-items: center; gap: 12px; margin-bottom: 12px;';
  
  // Profile picture avatar
  const avatar = document.createElement('img');
  // Use Instagram profile picture URL
  const profilePicUrl = creator.profile_picture || '';
  avatar.src = profilePicUrl;
  avatar.alt = creator.username ? `${creator.username} profile picture` : 'Creator profile picture';
  avatar.style.cssText = 'width: 48px; height: 48px; border-radius: 50%; object-fit: cover; background: #f3f4f6; border: 2px solid #e5e7eb; flex-shrink: 0;';
  avatar.onerror = () => { 
    // Fallback to a default avatar or hide if no image available
    avatar.style.display = 'none';
  };
  header.appendChild(avatar);
  
  // Username and creator info container
  const usernameContainer = document.createElement('div');
  usernameContainer.style.cssText = 'display: flex; flex-direction: column; gap: 2px; flex: 1;';
  
  const usernameLink = document.createElement('a');
  usernameLink.textContent = creator.username ? `@${creator.username}` : 'Unknown';
  usernameLink.href = creator.username ? `https://instagram.com/${creator.username}` : '#';  
  usernameLink.target = '_blank';
  usernameLink.rel = 'noopener';
  usernameLink.setAttribute('data-creator-username', creator.username || '');
  usernameLink.style.cssText = 'font-weight: 700; font-size: 18px; color: #111827; text-decoration: none; line-height: 1.2;';
  usernameContainer.appendChild(usernameLink);
  
  // Optional: Add "Hair creator" label below username
  if (creator.username) {
    const creatorLabel = document.createElement('span');
    creatorLabel.textContent = `Hair creator: ${creator.username}`;
    creatorLabel.style.cssText = 'color: #6b7280; font-size: 12px; line-height: 1.2;';
    usernameContainer.appendChild(creatorLabel);
  }
  
  header.appendChild(usernameContainer);
  content.appendChild(header);
  
  // Bio
  if (creator.bio) {
    const bio = document.createElement('p');
    bio.textContent = creator.bio;
    bio.style.cssText = 'color: #6b7280; font-size: 14px; margin: 0 0 12px 0; line-height: 1.4;';
    content.appendChild(bio);
  }
  
  // Location
  if (creator.location) {
    const location = document.createElement('div');
    location.style.cssText = 'display: flex; align-items: center; gap: 6px; margin-bottom: 8px; color: #6b7280; font-size: 14px;';
    location.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
      </svg>
      ${creator.location}
    `;
    content.appendChild(location);
  }
  
  // Price range
  if (creator.min_price || creator.max_price) {
    const price = document.createElement('div');
    price.style.cssText = 'margin-bottom: 12px; color: #111827; font-weight: 600; font-size: 14px;';
    price.textContent = formatPriceRange(creator.min_price, creator.max_price);
    content.appendChild(price);
  }
  
  // WhatsApp button
  if (creator.phone) {
    const whatsappBtn = document.createElement('a');
    whatsappBtn.href = `https://wa.me/${normalizePhone(creator.phone)}`;
    whatsappBtn.target = '_blank';
    whatsappBtn.rel = 'noopener';
    whatsappBtn.style.cssText = 'display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 8px 16px; background: #25d366; color: white; text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 600; margin-top: auto;';
    whatsappBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893A11.821 11.821 0 0020.885 3.488"/>
      </svg>
      WhatsApp
    `;
    content.appendChild(whatsappBtn);
  }
  
  card.appendChild(content);
  return card;
}

// Filter creators based on criteria
export function filterCreators(creators, filters) {
  return creators.filter(creator => {
    // Location filter
    if (filters.locations && filters.locations.length > 0) {
      const creatorLocations = (creator.location || '').split(',').map(l => l.trim());
      const hasMatchingLocation = filters.locations.some(loc => 
        creatorLocations.some(creatorLoc => creatorLoc.includes(loc))
      );
      if (!hasMatchingLocation) return false;
    }
    
    // Price filter
    if (filters.maxPrice !== undefined) {
      const creatorMinPrice = creator.min_price || 0;
      const creatorMaxPrice = creator.max_price || Infinity;
      
      // Check if creator's price range intersects with [0, maxPrice]
      if (creatorMinPrice > filters.maxPrice) return false;
    }
    
    // Availability filter (placeholder for future implementation)
    if (filters.availability) {
      // TODO: Implement availability filtering
    }
    
    return true;
  });
}

// Sort creators
export function sortCreators(creators, sortBy) {
  const sorted = [...creators];
  
  switch (sortBy) {
    case 'price_low':
      return sorted.sort((a, b) => (a.min_price || 0) - (b.min_price || 0));
    case 'price_high':
      return sorted.sort((a, b) => (b.max_price || 0) - (a.max_price || 0));
    case 'name':
      return sorted.sort((a, b) => (a.username || '').localeCompare(b.username || ''));
    case 'recent':
    default:
      return sorted.sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0));
  }
}
