# Scripts

This directory contains utility scripts for maintaining the application.

## refresh_creator_images.py

Daily script to refresh Instagram images for all creators. This script:

1. Iterates over all creators in the database
2. Deletes existing images for each creator
3. Fetches the latest 20 images from Instagram (configurable)
4. Re-ingests them with fresh `media_url` values
5. Updates the `recent_image` field for each creator

### Why?

Instagram `media_url` fields are temporary and expire after some time. This script ensures all image URLs stay fresh by re-fetching them daily.

### Usage

```bash
# Basic usage (refreshes 20 images per creator)
python scripts/refresh_creator_images.py

# Custom limit (e.g., 30 images per creator)
python scripts/refresh_creator_images.py --limit 30

# Dry run (see what would happen without making changes)
python scripts/refresh_creator_images.py --dry-run
```

### Scheduling

#### Linux/Mac (cron)

Add to crontab to run daily at 2 AM:

```bash
0 2 * * * cd /path/to/hair-similarity && /path/to/venv/bin/python scripts/refresh_creator_images.py >> /var/log/refresh_images.log 2>&1
```

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to "Daily" at desired time
4. Action: Start a program
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `scripts\refresh_creator_images.py`
   - Start in: `C:\path\to\hair-similarity`

#### Docker/Container

Add to your deployment:

```yaml
# docker-compose.yml
services:
  refresh-images:
    build: .
    command: python scripts/refresh_creator_images.py
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - IG_ACCESS_TOKEN=${IG_ACCESS_TOKEN}
      - IG_USER_ID=${IG_USER_ID}
    restart: "no"  # Run once and exit
    profiles:
      - daily-tasks
```

Then run: `docker-compose --profile daily-tasks run --rm refresh-images`

### Requirements

- Database connection configured
- Instagram API credentials (`IG_ACCESS_TOKEN`, `IG_USER_ID`) set in environment
- All app dependencies installed

### Output

The script provides detailed output:
- Progress for each creator
- Number of images deleted/added/skipped
- Error messages if any
- Summary at the end

Example output:
```
============================================================
Refreshing images for all creators (limit: 20 per creator)
============================================================

Found 5 creators

[1/5] Processing creator: @hair_stylist
  ✓ Deleted 15 existing images
  ✓ Added 18 new images, skipped 2
  ✓ Updated recent_image

[2/5] Processing creator: @makeup_artist
  ✓ Deleted 12 existing images
  ✓ Added 20 new images, skipped 0
  ✓ Updated recent_image

...

============================================================
SUMMARY
============================================================
Total images deleted: 67
Total images added: 95
Total images skipped: 5
Total errors: 0

✓ All creators processed successfully!
============================================================
```

