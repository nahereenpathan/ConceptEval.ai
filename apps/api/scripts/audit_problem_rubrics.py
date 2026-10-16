"""
Audit script to inspect all existing problems, their statements, and their GradingRubrics in concept_eval_dev.db.
"""
import sqlite3
import json

def audit():
    conn = sqlite3.connect('concept_eval_dev.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT p.id, p.slug, pv.title, pv.statement_markdown, r.rubric_json, r.status
    FROM problems p
    JOIN problem_versions pv ON p.id = pv.problem_id
    LEFT JOIN grading_rubrics r ON pv.id = r.problem_version_id
    ORDER BY pv.title
    ''')
    rows = cursor.fetchall()
    
    with open("rubric_audit_report.txt", "w", encoding="utf-8") as f:
        f.write(f"Total Problem Records Found: {len(rows)}\n\n")

        for idx, row in enumerate(rows, start=1):
            pid, slug, title, statement, rubric_json, r_status = row
            f.write(f"[{idx}] SLUG: {slug} | TITLE: {title}\n")
            f.write(f"    Rubric Status: {r_status}\n")
            f.write(f"    Statement Preview: {statement[:150].strip().replace(chr(10), ' ')}...\n")
            
            if rubric_json:
                try:
                    r_data = json.loads(rubric_json)
                    reqs = r_data.get("required_concepts", [])
                    prohs = r_data.get("prohibited_constructs", [])
                    weights = {
                        "func": r_data.get("functional_weight"),
                        "concept": r_data.get("concept_weight"),
                        "algo": r_data.get("algorithmic_weight"),
                        "constraint": r_data.get("constraint_weight")
                    }
                    f.write(f"    Weights: {weights}\n")
                    f.write(f"    Required Concepts ({len(reqs)}):\n")
                    for req in reqs:
                        c = req.get("concept")
                        constructs = req.get("accepted_constructs", [])
                        min_occ = req.get("min_occurrences")
                        desc = req.get("description")
                        f.write(f"      • {c} (constructs: {constructs}, min: {min_occ}) - {desc}\n")
                    
                    f.write(f"    Prohibitions ({len(prohs)}):\n")
                    for proh in prohs:
                        ptype = proh.get("construct_type")
                        targets = proh.get("forbidden_targets", [])
                        desc = proh.get("description")
                        f.write(f"      • {ptype} (forbidden: {targets}) - {desc}\n")
                except Exception as e:
                    f.write(f"    [!] Error parsing rubric_json: {e}\n")
            else:
                f.write("    [!] MISSING RUBRIC: No grading rubric linked to problem_version!\n")
            f.write("-" * 70 + "\n")

    print(f"Audit report written to rubric_audit_report.txt ({len(rows)} problems audited)")

if __name__ == "__main__":
    audit()
