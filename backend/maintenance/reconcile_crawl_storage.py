import os
import sys
import argparse
import sqlite3

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config.settings import _DB_PATH
from app.config.utils import get_sanitized_domain

def reconcile_storage(dry_run: bool = True):
    print("============================================================", flush=True)
    print(" CRAWL STORAGE RECONCILIATION & SANITATION UTILITY", flush=True)
    print(f" Mode: {'DRY RUN (No data deleted)' if dry_run else 'LIVE EXECUTION'}", flush=True)
    print("============================================================\n", flush=True)

    db_file = os.path.abspath(_DB_PATH)
    if not os.path.exists(db_file):
        print(f"[ERROR] Database file not found at {db_file}", flush=True)
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, url FROM projects;")
    projects = cursor.fetchall()
    conn.close()

    canonical_slugs = set()
    for p in projects:
        url = p[2] or p[1]
        slug = get_sanitized_domain(url)
        canonical_slugs.add(slug)
        print(f"[PROJECT] ID={p[0]}, Name='{p[1]}', Canonical Slug='{slug}'", flush=True)

    websites_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "websites"))
    if not os.path.exists(websites_dir):
        print(f"\n[STORAGE] Websites storage directory '{websites_dir}' does not exist.", flush=True)
        return

    disk_dirs = [d for d in os.listdir(websites_dir) if os.path.isdir(os.path.join(websites_dir, d))]
    print(f"\n[STORAGE] Found {len(disk_dirs)} storage directories on disk.", flush=True)

    orphaned = []
    active = []

    for d in disk_dirs:
        if d in canonical_slugs:
            active.append(d)
        else:
            orphaned.append(d)

    print(f"\n[RESULTS] Active Project Directories ({len(active)}): {', '.join(active)}", flush=True)
    print(f"[RESULTS] Orphaned Storage Directories ({len(orphaned)}): {', '.join(orphaned) if orphaned else 'None'}", flush=True)

    if orphaned:
        if dry_run:
            print("\n[ACTION REQUIRED] Dry-run report complete. To migrate or archive orphaned folders, run with --execute.", flush=True)
        else:
            print("\n[LIVE EXECUTION] Moving orphaned storage folders to data/backups/orphaned_storage/...", flush=True)
            backup_dir = os.path.join(os.path.dirname(websites_dir), "backups", "orphaned_storage")
            os.makedirs(backup_dir, exist_ok=True)
            import shutil
            for o in orphaned:
                src_path = os.path.join(websites_dir, o)
                dst_path = os.path.join(backup_dir, o)
                shutil.move(src_path, dst_path)
                print(f"[MIGRATED] '{o}' -> '{dst_path}'", flush=True)
            print("[SUCCESS] Orphaned storage reconciliation complete.", flush=True)
    else:
        print("\n[SUCCESS] All storage directories on disk match active project records.", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcile crawl storage directories against active project records.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run in dry-run report mode (default)")
    parser.add_argument("--execute", action="store_true", help="Execute safe migration of orphaned storage folders")
    args = parser.parse_args()

    is_dry_run = not args.execute
    reconcile_storage(dry_run=is_dry_run)
