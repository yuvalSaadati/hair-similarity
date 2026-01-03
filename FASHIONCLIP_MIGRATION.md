# FashionCLIP Migration Guide

## Changes Made

The codebase has been updated to use **FashionCLIP** instead of the standard CLIP model for better fashion/beauty-specific image similarity.

## Installation

Install FashionCLIP:

```bash
pip install fashion-clip
```

Or update requirements:

```bash
pip install -r app/requirements.txt
```

## What Changed

1. **`app/image_processing.py`**:
   - Replaced `clip.load("ViT-B/32")` with `FashionCLIP('fashion-clip')`
   - Updated `image_to_embedding()` to use FashionCLIP's API
   - Maintains same interface (returns torch.Tensor, 512 dimensions)

2. **`app/requirements.txt`**:
   - Added `fashion-clip` package

## Benefits

- **Better fashion/beauty understanding**: FashionCLIP is fine-tuned on fashion datasets
- **Improved similarity results**: Should perform better for hair/makeup images
- **Same embedding size**: Still 512 dimensions, compatible with existing database

## Important Notes

1. **Existing embeddings**: Existing images in the database were created with standard CLIP. For best results, you should:
   - Re-run the image ingestion script to regenerate embeddings with FashionCLIP
   - Or keep both models and gradually migrate

2. **Model loading**: FashionCLIP will be loaded on first use (lazy loading)

3. **Fallback**: If FashionCLIP installation fails, the code will raise an ImportError. You can temporarily revert to CLIP if needed.

## Testing

After installation, test the model:

```python
from app.image_processing import image_to_embedding
from PIL import Image

# Load a test image
img = Image.open("test_hair_image.jpg")

# Generate embedding
embedding = image_to_embedding(img)
print(f"Embedding shape: {embedding.shape}")  # Should be torch.Size([512])
```

## Re-generating Embeddings

To update all existing images with FashionCLIP embeddings, run:

```bash
python scripts/refresh_creator_images.py
```

This will delete old embeddings and create new ones with FashionCLIP.

## Troubleshooting

**Issue**: `ImportError: FashionCLIP not installed`

**Solution**: 
```bash
pip install fashion-clip
```

**Issue**: Model loading is slow

**Solution**: This is normal on first load. The model is cached after first use.

**Issue**: Different similarity results

**Solution**: This is expected! FashionCLIP may rank images differently than standard CLIP. You may need to re-generate all embeddings for consistency.

