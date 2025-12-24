// Authentication functions
import { registerUser, loginUser, getMyCreator, updateCreatorProfile, getCreatorImages, setDefaultImage } from './api.js';
import { toggleModal, updateFormField, getFormFieldValue, getSelectedValues, setSelectedValues, getSelectedValuesFromCheckboxes, setSelectedValuesInCheckboxes, showNotification } from './ui.js';
import { loadCreators } from './api.js';

// Setup authentication event listeners
export function setupAuth() {
  // Sign up modal
  const signUpBtn = document.getElementById('signUpBtn');
  if (signUpBtn) {
    signUpBtn.addEventListener('click', openSignUpModal);
  }
  
  // Sign in modal
  const signInBtn = document.getElementById('signInBtn');
  if (signInBtn) {
    signInBtn.addEventListener('click', openSignInModal);
  }
  
  // Modal close buttons
  const closeButtons = document.querySelectorAll('.modal-close');
  closeButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const modal = e.target.closest('.modal');
      if (modal) {
        toggleModal(modal.id, false);
      }
    });
  });
  
  // Modal backdrop clicks
  const modals = document.querySelectorAll('.modal');
  modals.forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        toggleModal(modal.id, false);
      }
    });
  });
  
  // Sign up form submission
  const signUpForm = document.getElementById('signUpForm');
  if (signUpForm) {
    signUpForm.addEventListener('submit', handleSignUp);
  }
  
  // Sign in form submission
  const signInForm = document.getElementById('signInForm');
  if (signInForm) {
    signInForm.addEventListener('submit', handleSignIn);
  }
  
  // Creator management form submission
  const creatorMgmtForm = document.getElementById('creatorMgmtForm');
  if (creatorMgmtForm) {
    creatorMgmtForm.addEventListener('submit', handleUpdateCreatorProfile);
  }
  
  // Setup arrival location dropdowns
  setupArrivalLocationDropdowns();
}

// Setup arrival location dropdowns (similar to region dropdown)
function setupArrivalLocationDropdowns() {
  // Sign-up form dropdown
  setupArrivalLocationDropdown('signupArrivalLocationBtn', 'signupArrivalLocationMenu', 'signupArrivalLocationOptionsList', 'signupArrivalLocationLabel');
  
  // Management form dropdown
  setupArrivalLocationDropdown('mgmtArrivalLocationBtn', 'mgmtArrivalLocationMenu', 'mgmtArrivalLocationOptionsList', 'mgmtArrivalLocationLabel');
}

function setupArrivalLocationDropdown(btnId, menuId, optionsListId, labelId) {
  const btn = document.getElementById(btnId);
  const menu = document.getElementById(menuId);
  const options = document.querySelectorAll(`#${optionsListId} input[type="checkbox"]`);
  
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
    option.addEventListener('change', () => updateArrivalLocationSelection(optionsListId, labelId));
  });
  
  // Update selection display
  updateArrivalLocationSelection(optionsListId, labelId);
}

function updateArrivalLocationSelection(optionsListId, labelId) {
  const selected = getSelectedValuesFromCheckboxes(optionsListId);
  const label = document.getElementById(labelId);
  
  if (!label) return;
  
  if (selected.length === 0) {
    label.textContent = 'בחרו מיקומי הגעה...';
    label.classList.add('placeholder');
  } else if (selected.length === 1) {
    label.textContent = selected[0];
    label.classList.remove('placeholder');
  } else {
    label.textContent = `${selected.length} מיקומים נבחרו`;
    label.classList.remove('placeholder');
  }
}

// Open sign up modal
export function openSignUpModal() {
  toggleModal('signUpModal', true);
}

// Open sign in modal
export function openSignInModal() {
  toggleModal('signInModal', true);
}

// Open creator management modal
export async function openCreatorManagementModal() {
  const token = localStorage.getItem('auth_token');
  if (!token) {
    openSignInModal();
    return;
  }
  
  try {
    // Load creator data
    const data = await getMyCreator(token);
    const creator = data.creator || {};
    
    // Prefill form
    updateFormField('mgmt_username', creator.username || '');
    updateFormField('mgmt_phone', creator.phone || '');
    updateFormField('mgmt_price_hairstyle_bride', creator.price_hairstyle_bride || '');
    updateFormField('mgmt_price_hairstyle_bridesmaid', creator.price_hairstyle_bridesmaid || '');
    updateFormField('mgmt_price_makeup_bride', creator.price_makeup_bride || '');
    updateFormField('mgmt_price_makeup_bridesmaid', creator.price_makeup_bridesmaid || '');
    updateFormField('mgmt_price_hairstyle_makeup_combo', creator.price_hairstyle_makeup_combo || '');
    
    // Handle location (single location - where creator is leaving from)
    updateFormField('mgmt_location', creator.location || '');
    
    // Handle arrival location multi-select (array of locations creator can arrive to)
    let arrivalLocationValues = [];
    if (creator.arrival_location) {
      if (Array.isArray(creator.arrival_location)) {
        arrivalLocationValues = creator.arrival_location;
      } else if (typeof creator.arrival_location === 'string') {
        arrivalLocationValues = creator.arrival_location.split(',').map(s => s.trim());
      }
    }
    setSelectedValuesInCheckboxes('mgmtArrivalLocationOptionsList', arrivalLocationValues);
    updateArrivalLocationSelection('mgmtArrivalLocationOptionsList', 'mgmtArrivalLocationLabel');
    
    // Load creator images
    if (creator.username) {
      await loadCreatorImages(creator.username);
    }
    
    toggleModal('creatorManagementModal', true);
  } catch (error) {
    console.error('Failed to load creator data:', error);
    showNotification('שגיאה בטעינת נתוני היוצר/ת', 'error');
  }
}

// Handle sign up
async function handleSignUp(e) {
  e.preventDefault();
  
  const email = getFormFieldValue('signup_email');
  const password = getFormFieldValue('signup_password');
  const username = getFormFieldValue('signup_username');
  const phone = getFormFieldValue('signup_phone');
  const priceHairstyleBride = getFormFieldValue('signup_price_hairstyle_bride');
  const priceHairstyleBridesmaid = getFormFieldValue('signup_price_hairstyle_bridesmaid');
  const priceMakeupBride = getFormFieldValue('signup_price_makeup_bride');
  const priceMakeupBridesmaid = getFormFieldValue('signup_price_makeup_bridesmaid');
  const priceHairstyleMakeupCombo = getFormFieldValue('signup_price_hairstyle_makeup_combo');
  
  if (!email || !password || !username) {
    showNotification('אימייל, סיסמה ושם משתמש באינסטגרם נדרשים', 'error');
    return;
  }
  
  // Validate password length (bcrypt limit is 72 bytes)
  if (password.length > 72) {
    showNotification('הסיסמה ארוכה מדי. אנא בחרו סיסמה של עד 72 תווים', 'error');
    return;
  }
  
  try {
    // Register user
    const registerData = await registerUser(email, password);
    localStorage.setItem('auth_token', registerData.token);
    
    // Create creator profile
    // Location is single value (where creator is leaving from)
    const location = getFormFieldValue('signup_location');
    // Arrival location is array (where creator can arrive to)
    const arrivalLocationValues = getSelectedValuesFromCheckboxes('signupArrivalLocationOptionsList');
    const arrivalLocation = arrivalLocationValues.join(',');
    
    const creatorData = {
      username: username,
      phone: phone,
      location: location,
      arrival_location: arrivalLocation,
      price_hairstyle_bride: priceHairstyleBride || '',
      price_hairstyle_bridesmaid: priceHairstyleBridesmaid || '',
      price_makeup_bride: priceMakeupBride || '',
      price_makeup_bridesmaid: priceMakeupBridesmaid || '',
      price_hairstyle_makeup_combo: priceHairstyleMakeupCombo || '',
      ingest_limit: 100
    };
    
    await updateCreatorProfile(registerData.token, creatorData);
    
    toggleModal('signUpModal', false);
    showNotification('הרשמה הושלמה בהצלחה! התמונות שלכם נטענות ברקע...', 'success');
    loadCreators();
  } catch (error) {
    console.error('Sign up failed:', error);
    showNotification('הרשמה נכשלה', 'error');
  }
}

// Handle sign in
async function handleSignIn(e) {
  e.preventDefault();
  
  const email = getFormFieldValue('signin_email');
  const password = getFormFieldValue('signin_password');
  
  try {
    const data = await loginUser(email, password);
    localStorage.setItem('auth_token', data.token);
    
    toggleModal('signInModal', false);
    openCreatorManagementModal();
  } catch (error) {
    console.error('Sign in failed:', error);
    showNotification('כניסה נכשלה', 'error');
  }
}

// Load creator images for management modal
async function loadCreatorImages(username) {
  if (!username) return;
  
  try {
    const token = localStorage.getItem('auth_token');
    const data = await getCreatorImages(username, token);
    const gallery = document.getElementById('creatorImagesGallery');
    
    if (!gallery) return;
    
    gallery.innerHTML = '';
    
    data.images.forEach(img => {
      const imgDiv = document.createElement('div');
      imgDiv.style.cssText = 'position: relative; cursor: pointer; border-radius: 8px; overflow: hidden;';
      imgDiv.addEventListener('click', () => handleSetDefaultImage(img.id, username));
      
      const imgEl = document.createElement('img');
      imgEl.src = img.local_url || img.url;
      imgEl.style.cssText = 'width: 100%; height: 120px; object-fit: cover;';
      imgEl.onerror = () => { imgDiv.style.display = 'none'; };
      
      const overlay = document.createElement('div');
      overlay.style.cssText = 'position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; opacity: 0; transition: opacity 0.2s;';
      overlay.textContent = 'לחץ לבחירה';
      
      imgDiv.appendChild(imgEl);
      imgDiv.appendChild(overlay);
      
      imgDiv.addEventListener('mouseenter', () => overlay.style.opacity = '1');
      imgDiv.addEventListener('mouseleave', () => overlay.style.opacity = '0');
      
      gallery.appendChild(imgDiv);
    });
  } catch (error) {
    console.error('Failed to load creator images:', error);
    showNotification('שגיאה בטעינת התמונות', 'error');
  }
}

// Handle setting default image
async function handleSetDefaultImage(imageId, username) {
  const token = localStorage.getItem('auth_token');
  if (!token) return;
  
  try {
    await setDefaultImage(username, imageId, token);
    showNotification('תמונה ראשית עודכנה בהצלחה!', 'success');
    loadCreators(); // Refresh the creators list
  } catch (error) {
    console.error('Failed to set default image:', error);
    showNotification('שגיאה בעדכון התמונה הראשית', 'error');
  }
}

// Handle update creator profile
async function handleUpdateCreatorProfile(e) {
  e.preventDefault();
  
  const token = localStorage.getItem('auth_token');
  if (!token) return;
  
  const username = getFormFieldValue('mgmt_username');
  const phone = getFormFieldValue('mgmt_phone');
  const priceHairstyleBride = getFormFieldValue('mgmt_price_hairstyle_bride');
  const priceHairstyleBridesmaid = getFormFieldValue('mgmt_price_hairstyle_bridesmaid');
  const priceMakeupBride = getFormFieldValue('mgmt_price_makeup_bride');
  const priceMakeupBridesmaid = getFormFieldValue('mgmt_price_makeup_bridesmaid');
  const priceHairstyleMakeupCombo = getFormFieldValue('mgmt_price_hairstyle_makeup_combo');
  
  if (!username) {
    showNotification('שם משתמש באינסטגרם נדרש', 'error');
    return;
  }
  
  // Location is single value (where creator is leaving from)
  const location = getFormFieldValue('mgmt_location');
  // Arrival location is array (where creator can arrive to)
  const arrivalLocationValues = getSelectedValuesFromCheckboxes('mgmtArrivalLocationOptionsList');
  const arrivalLocation = arrivalLocationValues.join(',');
  
  const creatorData = {
    username: username,
    phone: phone,
    location: location,
    arrival_location: arrivalLocation,
    price_hairstyle_bride: priceHairstyleBride || '',
    price_hairstyle_bridesmaid: priceHairstyleBridesmaid || '',
    price_makeup_bride: priceMakeupBride || '',
    price_makeup_bridesmaid: priceMakeupBridesmaid || '',
    price_hairstyle_makeup_combo: priceHairstyleMakeupCombo || ''
  };
  
  try {
    await updateCreatorProfile(token, creatorData);
    showNotification('פרופיל היוצר/ת עודכן בהצלחה!', 'success');
    loadCreators(); // Refresh the creators list
  } catch (error) {
    console.error('Failed to update creator profile:', error);
    showNotification('שגיאה בעדכון הפרופיל', 'error');
  }
}

// Check if user is authenticated
export function isAuthenticated() {
  return !!localStorage.getItem('auth_token');
}

// Logout user
export function logout() {
  localStorage.removeItem('auth_token');
  showNotification('התנתקת בהצלחה', 'success');
  // Refresh the page to update UI
  window.location.reload();
}
