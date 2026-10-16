"""
Backfill starter_code for existing problems in concept_eval_dev.db
from starter_catalog.json and core templates.
"""
import json
import os
import sqlite3
import sys

def backfill():
    db_path = "concept_eval_dev.db"
    catalog_path = os.path.join(os.path.dirname(__file__), "..", "app", "content_import", "starter_catalog.json")

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    starter_by_slug = {}
    for p in catalog.get("problems", []):
        if p.get("starter_code") and p.get("slug"):
            starter_by_slug[p["slug"]] = p["starter_code"]

    # Hardcoded starters for core seeded problems
    starter_by_slug["print-hello-world-4-times"] = (
        "# Print 'Hello World' exactly 4 times using a loop\n"
        "for i in range(4):\n"
        "    print('Hello World')\n"
    )
    starter_by_slug["recursive-factorial"] = (
        "import sys\n\n"
        "def factorial(n: int) -> int:\n"
        "    # Must use recursion\n"
        "    if n <= 1:\n"
        "        return 1\n"
        "    return n * factorial(n - 1)\n\n"
        "if __name__ == '__main__':\n"
        "    raw = sys.stdin.read().strip()\n"
        "    if raw:\n"
        "        print(factorial(int(raw)))\n"
    )
    starter_by_slug["multiply-array-elements-by-two"] = (
        "import sys\n\n"
        "def multiply_by_two():\n"
        "    raw = sys.stdin.read().strip()\n"
        "    if not raw:\n"
        "        return\n"
        "    nums = [int(x) for x in raw.split()]\n"
        "    res = [str(x * 2) for x in nums]\n"
        "    print(' '.join(res))\n\n"
        "if __name__ == '__main__':\n"
        "    multiply_by_two()\n"
    )
    starter_by_slug["sum-of-first-n-natural-numbers"] = (
        "import sys\n\n"
        "def sum_first_n():\n"
        "    raw = sys.stdin.read().strip()\n"
        "    if not raw:\n"
        "        return\n"
        "    n = int(raw)\n"
        "    total = 0\n"
        "    for i in range(1, n + 1):\n"
        "        total += i\n"
        "    print(total)\n\n"
        "if __name__ == '__main__':\n"
        "    sum_first_n()\n"
    )

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    updated = 0
    for slug, starter in starter_by_slug.items():
        cursor.execute("""
            UPDATE problem_versions
            SET starter_code = ?
            WHERE problem_id IN (SELECT id FROM problems WHERE slug = ?)
        """, (starter, slug))
        if cursor.rowcount > 0:
            updated += cursor.rowcount

    conn.commit()
    conn.close()
    print(f"Backfilled starter_code for {updated} problem versions.")

if __name__ == "__main__":
    backfill()
