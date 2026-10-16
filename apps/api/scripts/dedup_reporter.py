"""
Safe Duplicate Detection and Content Fingerprinting Tool for ConceptEval.ai
Audits the problem database for exact and near-duplicate problems, generates
normalized title/statement fingerprints, and inspects related foreign key records.
"""

import hashlib
import json
import re
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
    norm_title = normalize_text(title)
    norm_statement = normalize_text(statement[:300]) # first 300 chars of statement
    payload = f"{norm_title}::{norm_statement}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def audit_problem_database(db_path: str) -> Dict[str, Any]:
    """Inspect database for duplicate problems by title, slug, and content fingerprint."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query all problems and active versions
    cursor.execute("""
        SELECT 
            p.id as problem_id,
            p.slug,
            p.owner_type,
            p.status,
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

    total_problems = len(rows)
    by_fingerprint = defaultdict(list)
    by_norm_title = defaultdict(list)
    by_slug_base = defaultdict(list)

    for r in rows:
        row_dict = dict(r)
        title = r["title"] or ""
        statement = r["statement_markdown"] or ""
        slug = r["slug"] or ""

        # Normalize slug base (remove trailing timestamps like -1792139618)
        slug_base = re.sub(r"-\d{9,12}$", "", slug)

        fingerprint = compute_content_fingerprint(title, statement)
        norm_title = normalize_text(title)

        row_dict["fingerprint"] = fingerprint
        row_dict["norm_title"] = norm_title
        row_dict["slug_base"] = slug_base

        # Query related records counts
        v_id = r["version_id"]
        p_id = r["problem_id"]

        cursor.execute("SELECT COUNT(*) FROM submissions WHERE problem_version_id = ?", (v_id,))
        row_dict["submissions_count"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM problem_bookmarks WHERE problem_id = ?", (p_id,))
        row_dict["bookmarks_count"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM test_cases WHERE problem_version_id = ?", (v_id,))
        row_dict["test_cases_count"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM grading_rubrics WHERE problem_version_id = ?", (v_id,))
        row_dict["rubrics_count"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM problem_topic_assignments WHERE problem_version_id = ?", (v_id,))
        row_dict["topics_count"] = cursor.fetchone()[0]

        by_fingerprint[fingerprint].append(row_dict)
        by_norm_title[norm_title].append(row_dict)
        by_slug_base[slug_base].append(row_dict)

    # Detect duplicate clusters
    duplicate_clusters = []
    seen_ids = set()

    for fp, items in by_fingerprint.items():
        if len(items) > 1:
            duplicate_clusters.append({
                "type": "content_fingerprint_match",
                "key": fp,
                "title": items[0]["title"],
                "records": items,
            })
            for it in items:
                seen_ids.add(it["problem_id"])

    # Check if any norm_title duplicates were missed by fingerprint
    for nt, items in by_norm_title.items():
        if len(items) > 1 and not any(it["problem_id"] in seen_ids for it in items):
            duplicate_clusters.append({
                "type": "title_match",
                "key": nt,
                "title": items[0]["title"],
                "records": items,
            })

    conn.close()

    return {
        "db_path": db_path,
        "total_records": total_problems,
        "unique_fingerprints": len(by_fingerprint),
        "unique_titles": len(by_norm_title),
        "duplicate_clusters_count": len(duplicate_clusters),
        "duplicate_clusters": duplicate_clusters,
    }


def print_audit_report(report: Dict[str, Any]):
    print("=" * 80)
    print(f"DATABASE DUPLICATE AUDIT REPORT: {report['db_path']}")
    print("=" * 80)
    print(f"Total Problem Records Evaluated : {report['total_records']}")
    print(f"Unique Content Fingerprints     : {report['unique_fingerprints']}")
    print(f"Unique Normalized Titles        : {report['unique_titles']}")
    print(f"Duplicate Problem Clusters      : {report['duplicate_clusters_count']}")
    print("=" * 80)

    if not report["duplicate_clusters"]:
        print("\nAll problem records in database are completely unique! No duplicate clusters detected.")
        return

    for idx, cluster in enumerate(report["duplicate_clusters"], 1):
        print(f"\n[CLUSTER #{idx}] Title: '{cluster['title']}' ({len(cluster['records'])} duplicate copies)")
        print(f"  Match Reason: {cluster['type']} ({cluster['key'][:16]}...)")
        
        # Sort records: prioritize one with submissions or oldest created_at
        sorted_records = sorted(
            cluster["records"],
            key=lambda x: (
                -x["submissions_count"], # highest submissions first
                -x["bookmarks_count"],   # highest bookmarks first
                1 if "-" in re.sub(r"-\d+$", "", x["slug"]) else 0, # clean slug
                x["created_at"],         # oldest first
            )
        )

        canonical = sorted_records[0]
        duplicates = sorted_records[1:]

        print(f"  >> CANONICAL RECORD TO PRESERVE:")
        print(f"     Problem ID  : {canonical['problem_id']}")
        print(f"     Version ID  : {canonical['version_id']}")
        print(f"     Slug        : {canonical['slug']}")
        print(f"     Submissions : {canonical['submissions_count']} | Bookmarks: {canonical['bookmarks_count']} | Tests: {canonical['test_cases_count']}")
        print(f"     Created At  : {canonical['created_at']}")

        print(f"  >> REDUNDANT COPIES TO CONSOLIDATE & REMOVE:")
        for dup in duplicates:
            print(f"     - Problem ID : {dup['problem_id']}")
            print(f"       Slug       : {dup['slug']}")
            print(f"       Relations  : Submissions: {dup['submissions_count']}, Bookmarks: {dup['bookmarks_count']}, Tests: {dup['test_cases_count']}")
            print(f"       Created At : {dup['created_at']}")


if __name__ == "__main__":
    db_file = sys.argv[1] if len(sys.argv) > 1 else "concept_eval_dev.db"
    report = audit_problem_database(db_file)
    print_audit_report(report)
