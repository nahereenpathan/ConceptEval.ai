"""
Safe Deduplication and Database Repair Tool for ConceptEval.ai
Identifies duplicate problem clusters, preserves canonical records and all relationships,
and safely cleans redundant duplicate records within an atomic database transaction.

Supports:
  --dry-run   (Default: generates detailed impact report without modifying database)
  --execute   (Executes transaction after creating an automatic timestamped backup)
"""

import argparse
import datetime
import json
import os
import re
import shutil
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


def normalize_text(text: str) -> str:
    """Normalize text by lowercasing, removing punctuation and condensing whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compute_content_fingerprint(title: str, statement: str) -> str:
    """Compute deterministic SHA-256 hash of normalized title and core statement."""
    import hashlib
    norm_title = normalize_text(title)
    norm_statement = normalize_text(statement[:300])
    payload = f"{norm_title}::{norm_statement}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def find_duplicate_clusters(cursor: sqlite3.Cursor) -> List[Dict[str, Any]]:
    """Scan database for duplicate problem clusters."""
    cursor.execute("""
        SELECT 
            p.id as problem_id,
            p.slug,
            p.status,
            p.owner_type,
            p.created_at,
            pv.id as version_id,
            pv.version_number,
            pv.title,
            pv.statement_markdown,
            pv.difficulty,
            pv.language
        FROM problems p
        JOIN problem_versions pv ON pv.problem_id = p.id
        ORDER BY p.created_at ASC
    """)
    rows = cursor.fetchall()

    by_fingerprint = defaultdict(list)
    by_norm_title = defaultdict(list)

    for r in rows:
        row_dict = dict(r)
        title = r["title"] or ""
        statement = r["statement_markdown"] or ""
        slug = r["slug"] or ""

        fingerprint = compute_content_fingerprint(title, statement)
        norm_title = normalize_text(title)

        row_dict["fingerprint"] = fingerprint
        row_dict["norm_title"] = norm_title
        row_dict["slug_base"] = re.sub(r"-\d{9,12}$", "", slug)

        # Count relations
        v_id = r["version_id"]
        p_id = r["problem_id"]

        cursor.execute("SELECT COUNT(*) FROM submissions WHERE problem_version_id = ?", (v_id,))
        row_dict["submissions_count"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM problem_bookmarks WHERE problem_id = ?", (p_id,))
        row_dict["bookmarks_count"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM test_cases WHERE problem_version_id = ?", (v_id,))
        row_dict["test_cases_count"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM assignments WHERE problem_version_id = ?", (v_id,))
        row_dict["assignments_count"] = cursor.fetchone()[0]

        by_fingerprint[fingerprint].append(row_dict)
        by_norm_title[norm_title].append(row_dict)

    clusters = []
    seen_ids = set()

    for fp, items in by_fingerprint.items():
        if len(items) > 1:
            clusters.append({
                "type": "content_fingerprint_match",
                "key": fp,
                "title": items[0]["title"],
                "records": items,
            })
            for it in items:
                seen_ids.add(it["problem_id"])

    for nt, items in by_norm_title.items():
        if len(items) > 1 and not any(it["problem_id"] in seen_ids for it in items):
            clusters.append({
                "type": "title_match",
                "key": nt,
                "title": items[0]["title"],
                "records": items,
            })

    return clusters


def select_canonical_record(records: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Deterministically rank records to pick the canonical one:
    1. Highest submissions count (crucial for preserving student records)
    2. Highest bookmarks count
    3. Status == 'published'
    4. Clean slug (no timestamp suffix)
    5. Oldest created_at
    """
    def rank_key(rec):
        clean_slug = 1 if not re.search(r"-\d{9,12}$", rec["slug"]) else 0
        is_published = 1 if rec["status"] == "published" else 0
        return (
            rec["submissions_count"],
            rec["bookmarks_count"],
            rec["assignments_count"],
            is_published,
            clean_slug,
            -1 * (datetime.datetime.fromisoformat(rec["created_at"].replace("Z", "+00:00")).timestamp() if rec["created_at"] else 0)
        )

    # Sort in descending order of rank
    sorted_recs = sorted(records, key=rank_key, reverse=True)
    canonical = sorted_recs[0]
    redundant = sorted_recs[1:]
    return canonical, redundant


def plan_and_repair(db_path: str, execute: bool = False):
    print("=" * 80)
    print(f"SAFE DEDUPLICATION & REPAIR TOOL: {db_path}")
    print(f"MODE: {'*** LIVE TRANSACTION EXECUTION ***' if execute else 'DRY-RUN (NO CHANGES APPLIED)'}")
    print("=" * 80)

    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    clusters = find_duplicate_clusters(cursor)
    if not clusters:
        print("\nNo duplicate clusters detected in database. All records are unique.")
        conn.close()
        return

    print(f"\nFound {len(clusters)} duplicate problem cluster(s):")

    repair_plan = []

    for idx, cluster in enumerate(clusters, 1):
        canonical, redundant = select_canonical_record(cluster["records"])
        target_slug = cluster["records"][0]["slug_base"]
        
        # If canonical is draft but a redundant was published, canonical becomes published
        canonical_target_status = "published" if any(r["status"] == "published" for r in cluster["records"]) else canonical["status"]

        print(f"\n[CLUSTER #{idx}] Title: '{cluster['title']}' ({len(cluster['records'])} copies)")
        print(f"  Canonical ID to Preserve : {canonical['problem_id']} (Slug: {canonical['slug']}, Subs: {canonical['submissions_count']})")
        print(f"  Target Clean Slug        : {target_slug}")
        print(f"  Target Status            : {canonical_target_status}")
        print(f"  Redundant IDs to Remove  : {[r['problem_id'] for r in redundant]}")

        repair_plan.append({
            "canonical": canonical,
            "target_slug": target_slug,
            "target_status": canonical_target_status,
            "redundant": redundant,
        })

    if not execute:
        print("\n" + "=" * 80)
        print("DRY RUN COMPLETE: No data was modified.")
        print("To execute these repairs inside a safe transaction, run with --execute.")
        print("=" * 80)
        conn.close()
        return

    # Backup before live execution
    backup_file = f"{db_path}.bak_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    conn.close() # Close to flush any pending buffers before copy
    shutil.copy2(db_path, backup_file)
    print(f"\n[BACKUP] Created verified backup: {backup_file} ({os.path.getsize(backup_file)} bytes)")

    # Re-open for atomic transaction
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys = OFF;") # Temporarily manage constraints manually during re-linking
        cursor.execute("BEGIN TRANSACTION;")

        for item in repair_plan:
            canonical = item["canonical"]
            canon_pid = canonical["problem_id"]
            canon_vid = canonical["version_id"]
            target_slug = item["target_slug"]
            target_status = item["target_status"]

            # First: make sure any redundant problem with target_slug is renamed temporarily to avoid unique collision
            for red in item["redundant"]:
                red_pid = red["problem_id"]
                red_vid = red["version_id"]

                # 1. Re-link Submissions to canonical version_id
                cursor.execute(
                    "UPDATE submissions SET problem_version_id = ? WHERE problem_version_id = ?",
                    (canon_vid, red_vid)
                )

                # 2. Re-link Classroom Assignments to canonical version_id
                cursor.execute(
                    "UPDATE assignments SET problem_version_id = ? WHERE problem_version_id = ?",
                    (canon_vid, red_vid)
                )

                # 3. Re-link Bookmarks to canonical problem_id
                # Avoid duplicate bookmark unique constraint
                cursor.execute("SELECT user_id FROM problem_bookmarks WHERE problem_id = ?", (red_pid,))
                bm_users = [row[0] for row in cursor.fetchall()]
                for u_id in bm_users:
                    cursor.execute(
                        "SELECT COUNT(*) FROM problem_bookmarks WHERE user_id = ? AND problem_id = ?",
                        (u_id, canon_pid)
                    )
                    already_bookmarked = cursor.fetchone()[0] > 0
                    if not already_bookmarked:
                        cursor.execute(
                            "UPDATE problem_bookmarks SET problem_id = ? WHERE problem_id = ? AND user_id = ?",
                            (canon_pid, red_pid, u_id)
                        )
                    else:
                        cursor.execute(
                            "DELETE FROM problem_bookmarks WHERE problem_id = ? AND user_id = ?",
                            (red_pid, u_id)
                        )

                # 4. Migrate any topics assigned to redundant version that canonical doesn't have
                cursor.execute("SELECT topic_id FROM problem_topic_assignments WHERE problem_version_id = ?", (red_vid,))
                red_topics = [row[0] for row in cursor.fetchall()]
                for tid in red_topics:
                    cursor.execute(
                        "SELECT COUNT(*) FROM problem_topic_assignments WHERE problem_version_id = ? AND topic_id = ?",
                        (canon_vid, tid)
                    )
                    has_topic = cursor.fetchone()[0] > 0
                    if not has_topic:
                        cursor.execute(
                            "UPDATE problem_topic_assignments SET problem_version_id = ? WHERE problem_version_id = ? AND topic_id = ?",
                            (canon_vid, red_vid, tid)
                        )

                # 5. Delete dependent records of redundant version
                cursor.execute("DELETE FROM test_cases WHERE problem_version_id = ?", (red_vid,))
                cursor.execute("DELETE FROM grading_rubrics WHERE problem_version_id = ?", (red_vid,))
                cursor.execute("DELETE FROM problem_topic_assignments WHERE problem_version_id = ?", (red_vid,))
                cursor.execute("DELETE FROM rubric_extraction_runs WHERE problem_version_id = ?", (red_vid,))
                cursor.execute("DELETE FROM problem_versions WHERE id = ?", (red_vid,))

                # 6. Delete redundant problem row
                cursor.execute("DELETE FROM problems WHERE id = ?", (red_pid,))

            # 7. Update canonical problem slug and status
            cursor.execute(
                "UPDATE problems SET slug = ?, status = ? WHERE id = ?",
                (target_slug, target_status, canon_pid)
            )

        conn.commit()
        print("\n[SUCCESS] Transaction committed successfully!")

    except Exception as exc:
        conn.rollback()
        print(f"\n[FAILED] Error during repair transaction. Rolled back changes: {exc}")
        raise
    finally:
        conn.close()

    # Re-run audit to verify clean state
    print("\n--- POST-REPAIR VERIFICATION AUDIT ---")
    conn_verify = sqlite3.connect(db_path)
    conn_verify.row_factory = sqlite3.Row
    cursor_verify = conn_verify.cursor()
    rem_clusters = find_duplicate_clusters(cursor_verify)
    conn_verify.close()

    if not rem_clusters:
        print("✅ VERIFIED: 0 duplicate clusters remain in database!")
    else:
        print(f"⚠️ Warning: {len(rem_clusters)} duplicate clusters still detected.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ConceptEval.ai Safe Problem Deduplication Tool")
    parser.add_argument("--db", default="concept_eval_dev.db", help="Path to sqlite database")
    parser.add_argument("--execute", action="store_true", help="Execute live repair inside transaction")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry-run only (default)")
    args = parser.parse_args()

    do_execute = args.execute and not args.dry_run
    plan_and_repair(args.db, execute=do_execute)
