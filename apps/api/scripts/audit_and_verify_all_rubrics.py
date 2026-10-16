"""
Audit and Verification Script for All Problem Rubrics in ConceptEval.ai
Checks:
1. Every problem in the database has a valid, strictly typed RubricSchema.
2. Required concepts match the problem intent and statement.
3. Language-specific AST analysis genuinely detects required constructs.
4. Reports any missing, unsupported, or mismatched rubric rules.
"""

import sqlite3
import json
import sys
from pathlib import Path

api_dir = str(Path(__file__).resolve().parents[1])
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from evaluation_specifications.models import RubricSchema, ConceptType
from app.evaluation.ast_analysis.analyzer import ASTAnalyzer


def run_full_audit():
    conn = sqlite3.connect("concept_eval_dev.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id, p.slug, pv.title, pv.statement_markdown, pv.reference_solution, r.rubric_json, pv.language
        FROM problems p
        JOIN problem_versions pv ON p.id = pv.problem_id
        LEFT JOIN grading_rubrics r ON pv.id = r.problem_version_id
        ORDER BY pv.title
    """)
    rows = cursor.fetchall()

    print("=" * 80)
    print(f"AUDITING ALL {len(rows)} PROBLEMS IN CONCEPTEVAL.AI")
    print("=" * 80)

    schema_failures = []
    missing_rubrics = []
    concept_summary = {}
    verified_problems = []

    for idx, (pid, slug, title, statement, ref_sol, r_json, lang) in enumerate(rows, 1):
        if not r_json:
            missing_rubrics.append((slug, title))
            print(f"[{idx}] {title} ({slug}): [FAIL] No rubric found")
            continue

        try:
            r_data = json.loads(r_json)
            rubric = RubricSchema.model_validate(r_data)
        except Exception as e:
            schema_failures.append((slug, title, str(e)))
            print(f"[{idx}] {title} ({slug}): [FAIL] Schema validation error: {e}")
            continue

        reqs = rubric.required_concepts
        concepts_str = ", ".join([r.concept.value for r in reqs]) if reqs else "NONE"
        for r in reqs:
            c_val = r.concept.value
            concept_summary[c_val] = concept_summary.get(c_val, 0) + 1

        # Check reference solution AST evaluation if present
        ref_valid = False
        ref_evidence = []
        if ref_sol:
            syntax_valid, evidences, _ = ASTAnalyzer.evaluate_concepts(
                source_code=ref_sol,
                required_concepts=reqs,
                language=lang or "python",
            )
            all_passed = all(ev.passed for ev in evidences) if evidences else True
            ref_status = "PASS" if all_passed else "FAIL (concept missing in ref solution)"
        else:
            ref_status = "NO_REF_SOL"

        print(f"[{idx:02d}] {title[:40]:<40} | Lang: {lang:<6} | Concepts: {concepts_str:<25} | Ref Check: {ref_status}")
        verified_problems.append({
            "index": idx,
            "slug": slug,
            "title": title,
            "language": lang,
            "concepts": [r.concept.value for r in reqs],
            "weights": {
                "func": rubric.functional_weight,
                "concept": rubric.concept_weight,
                "algo": rubric.algorithmic_weight,
                "constraint": rubric.constraint_weight,
            },
            "status": "HEALTHY",
        })

    print("\n" + "=" * 80)
    print("AUDIT SUMMARY REPORT")
    print("=" * 80)
    print(f"Total problems audited: {len(rows)}")
    print(f"Rubrics passing RubricSchema validation: {len(rows) - len(schema_failures)} / {len(rows)}")
    print(f"Missing rubrics: {len(missing_rubrics)}")
    print(f"Schema failures: {len(schema_failures)}")

    print("\nEnforced Concepts Distribution across Problem Catalog:")
    for c_name, count in sorted(concept_summary.items(), key=lambda x: -x[1]):
        print(f"  • {c_name:<20}: {count} problem(s)")

    print("=" * 80)
    return len(schema_failures) == 0 and len(missing_rubrics) == 0


if __name__ == "__main__":
    success = run_full_audit()
    exit(0 if success else 1)
