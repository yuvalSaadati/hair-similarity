#!/usr/bin/env python3
"""
Daily script to refresh Instagram images for all creators.

This script:
1. Iterates over all creators in the database
2. Deletes existing images for each creator
3. Fetches the latest 20 images from Instagram
4. Re-ingests them with fresh media_url values

Run this script daily (e.g., via cron or scheduled task) to keep image URLs fresh.
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db import conn
from app.database import get_creators
from app.routers.creators import ingest_instagram_creators
from app.instagram import ig_get_most_recent_image
import traceback

def delete_creator_images(username: str) -> int:
    """Delete all images for a specific creator"""
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM images
            WHERE creator_username = %s
        """, (username,))
        deleted_count = cur.rowcount
        conn.commit()
        return deleted_count

def refresh_all_creators_images(limit_per_creator: int = 30, dry_run: bool = False):
    """
    Refresh images for all creators
    
    Args:
        limit_per_creator: Number of images to fetch per creator (default: 20)
        dry_run: If True, only show what would be done without making changes
    """
    print(f"{'=' * 60}")
    print(f"Refreshing images for all creators (limit: {limit_per_creator} per creator)")
    if dry_run:
        print("DRY RUN MODE - No changes will be made")
    print(f"{'=' * 60}\n")
    
    # Get all creators
    try:
        creators = get_creators()
        print(f"Found {len(creators)} creators\n")
    except Exception as e:
        print(f"Error fetching creators: {e}")
        traceback.print_exc()
        return
    
    if not creators:
        print("No creators found in database.")
        return
    
    total_deleted = 0
    total_added = 0
    total_skipped = 0
    total_errors = 0
    failed_creators = []
    
    for i, creator in enumerate(creators, 1):
        username = creator.username
        if not username:
            print(f"[{i}/{len(creators)}] Skipping creator with no username")
            continue
        
        print(f"[{i}/{len(creators)}] Processing creator: @{username}")
        
        try:
            # Delete existing images for this creator
            if not dry_run:
                deleted = delete_creator_images(username)
                total_deleted += deleted
                print(f"  ✓ Deleted {deleted} existing images")
            else:
                # Count existing images in dry run
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) FROM images WHERE creator_username = %s
                    """, (username,))
                    count = cur.fetchone()[0]
                    print(f"  [DRY RUN] Would delete {count} existing images")
            
            # Re-ingest images for this creator
            if not dry_run:
                result = ingest_instagram_creators([username], limit_per_creator)
                total_added += result.get("added", 0)
                total_skipped += result.get("skipped", 0)
                errors = result.get("errors", [])
                if errors:
                    total_errors += len(errors)
                    print(f"  ⚠ {len(errors)} errors occurred")
                print(f"  ✓ Added {result.get('added', 0)} new images, skipped {result.get('skipped', 0)}")
            else:
                print(f"  [DRY RUN] Would fetch and ingest up to {limit_per_creator} images")
            
            # Update recent_image for the creator
            if not dry_run:
                try:
                    recent_image = ig_get_most_recent_image(username)
                    if recent_image and recent_image.get("media_url"):
                        # Get creator's user_id to update
                        with conn.cursor() as cur:
                            cur.execute("""
                                SELECT user_id FROM creators WHERE username = %s
                            """, (username,))
                            row = cur.fetchone()
                            if row:
                                user_id = row[0]
                                # Update only the recent_image field
                                cur.execute("""
                                    UPDATE creators 
                                    SET recent_image = %s, updated_at = now()
                                    WHERE user_id = %s
                                """, (recent_image["media_url"], user_id))
                                conn.commit()
                                print(f"  ✓ Updated recent_image")
                except Exception as e:
                    print(f"  ⚠ Failed to update recent_image: {e}")
            
            print()
            
        except Exception as e:
            print(f"  ✗ Error processing creator @{username}: {e}")
            traceback.print_exc()
            failed_creators.append(username)
            print()
    
    # Summary
    print(f"{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    if not dry_run:
        print(f"Total images deleted: {total_deleted}")
        print(f"Total images added: {total_added}")
        print(f"Total images skipped: {total_skipped}")
        print(f"Total errors: {total_errors}")
    else:
        print("[DRY RUN] No actual changes made")
    
    if failed_creators:
        print(f"\nFailed creators ({len(failed_creators)}):")
        for username in failed_creators:
            print(f"  - @{username}")
    else:
        print("\n✓ All creators processed successfully!")
    print(f"{'=' * 60}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Refresh Instagram images for all creators",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Refresh images for all creators (20 images per creator)
  python scripts/refresh_creator_images.py
  
  # Refresh with custom limit
  python scripts/refresh_creator_images.py --limit 30
  
  # Dry run to see what would happen
  python scripts/refresh_creator_images.py --dry-run
        """
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=30,
        help='Number of images to fetch per creator (default: 20)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    try:
        refresh_all_creators_images(
            limit_per_creator=args.limit,
            dry_run=args.dry_run
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

