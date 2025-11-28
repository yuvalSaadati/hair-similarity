# Unused Code Analysis

## 🔴 Files/Functions You Can DELETE

### 1. **`app/routers/similarity.py`** - ⚠️ PARTIALLY UNUSED
**Status:** Not used by frontend, but has some useful functions

**What it does:**
- `/api/similarity/search/{username}` - Search similar images for specific creator
- `/api/similarity/creator/{username}/media` - Get all media from creator
- `/api/similarity/search/global` - Global similarity search

**Why it's unused:**
- Frontend uses `/search/upload/by-creator` instead (from `search.py`)
- The global search endpoint duplicates functionality in `search.py`

**Recommendation:** 
- ❌ **DELETE** - The functionality is already in `search.py` and `database.py`
- Remove from `app/main.py`: `app.include_router(similarity.router)`

---

### 2. **`app/routers/display.py`** - ⚠️ MOSTLY UNUSED
**Status:** Only 1 endpoint is used, others are not

**What it does:**
- `/api/display/creator/{username}/image` - ❌ NOT USED
- `/api/display/creator/{username}/similar-image` - ✅ USED (in `image-display.js`)
- `/api/display/creator/{username}/sample-image` - ❌ NOT USED
- `/api/display/creator/{username}/all-images` - ❌ NOT USED
- `/api/display/creator/{username}/reset-sample` - ❌ NOT USED

**Why most are unused:**
- Frontend uses `/api/creators/with-display-images` instead
- The similar-image endpoint is used but could be replaced

**Recommendation:**
- ⚠️ **SIMPLIFY** - Keep only the used endpoint, or remove entirely and use `/search/upload/by-creator` instead
- The `/api/creators/with-display-images` endpoint already handles display images

---

### 3. **`app/creator_media_manager.py`** - ⚠️ REDUNDANT
**Status:** Overlaps with `image_display_manager.py` and `database.py`

**What it does:**
- `find_similar_creator_images()` - Similar to `database.search_similar_images_by_creator()`
- `get_creator_all_media()` - Similar to `image_display_manager.get_creator_all_images_for_search()`
- `update_creator_sample_image()` - Similar to `image_display_manager.update_creator_sample_image()`
- `cleanup_old_media()` - ❌ NOT USED ANYWHERE

**Why it's redundant:**
- `similarity.py` uses it, but `similarity.py` itself is unused
- Functions duplicate functionality in other files

**Recommendation:**
- ❌ **DELETE** - Functionality exists in `database.py` and `image_display_manager.py`
- Only used by `similarity.py` which is also unused

---

### 4. **`app/routers/ingest.py`** - ⚠️ NOT USED BY FRONTEND
**Status:** Endpoint exists but not called from frontend

**What it does:**
- `/ingest/instagram/creators` - Manual Instagram ingestion endpoint

**Why it might be unused:**
- Image ingestion should happen automatically when creator is added
- This is a manual/admin endpoint

**Recommendation:**
- ⚠️ **KEEP FOR NOW** - Might be useful for admin/manual ingestion
- But if you enable auto-ingestion in `creators.py`, this becomes redundant

---

### 5. **Unused Functions in `app/image_display_manager.py`**

**Functions that ARE used:**
- ✅ `get_creator_display_image()` - Used in `creators.py`

**Functions that are NOT used:**
- ❌ `get_creator_all_images_for_search()` - Only used by `display.py` which is mostly unused
- ❌ `update_creator_sample_image()` - Only used by `display.py`
- ❌ `get_creator_sample_image()` - Only used by `display.py`
- ❌ `set_creator_default_sample_image()` - Only used by `display.py`

**Recommendation:**
- ⚠️ **SIMPLIFY** - Keep only `get_creator_display_image()` if you remove `display.py`

---

### 6. **Unused API Endpoints in Frontend**

**In `app/static/js/api.js`:**
- ❌ `searchByUpload()` - Function exists but never called
- ❌ `searchByHashtags()` - Function exists but never called

**Recommendation:**
- ❌ **DELETE** - These functions are not used anywhere

---

## ✅ Files You SHOULD KEEP

### Core Files (All Used):
- ✅ `app/routers/creators.py` - Main creator endpoints
- ✅ `app/routers/search.py` - Image search (used by frontend)
- ✅ `app/routers/auth.py` - Authentication
- ✅ `app/routers/me.py` - User profile management
- ✅ `app/database.py` - Database queries
- ✅ `app/image_processing.py` - CLIP embeddings
- ✅ `app/instagram.py` - Instagram API
- ✅ `app/image_proxy.py` - Image proxy system
- ✅ `app/image_display_manager.py` - At least `get_creator_display_image()` is used

---

## 📋 Cleanup Action Plan

### Phase 1: Safe Deletions (No Breaking Changes)
1. ❌ Delete `app/routers/similarity.py`
2. ❌ Remove `app.include_router(similarity.router)` from `app/main.py`
3. ❌ Delete `app/creator_media_manager.py`
4. ❌ Remove unused functions from `app/static/js/api.js`:
   - `searchByUpload()`
   - `searchByHashtags()`

### Phase 2: Simplify (Requires Testing)
5. ⚠️ Simplify or remove `app/routers/display.py`
   - Option A: Keep only `/api/display/creator/{username}/similar-image` if needed
   - Option B: Remove entirely and use `/search/upload/by-creator` instead
6. ⚠️ Clean up `app/image_display_manager.py`
   - Keep only `get_creator_display_image()`
   - Remove other unused functions

### Phase 3: Optional
7. ⚠️ Consider removing `app/routers/ingest.py` if auto-ingestion works
8. ⚠️ Update `app/static/js/image-display.js` to not use `/api/display/*` if you remove it

---

## 🎯 Summary

**Total files to delete:** 2-3 files
- `app/routers/similarity.py` ✅ DELETE
- `app/creator_media_manager.py` ✅ DELETE
- `app/routers/display.py` ⚠️ SIMPLIFY OR DELETE

**Functions to remove:** ~10-15 unused functions across multiple files

**Impact:** Low risk - these are not used by the frontend

