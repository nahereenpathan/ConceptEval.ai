"""
Live End-to-End HTTP Verification Script
Validates running FastAPI server and live dual-track evaluation over real HTTP.
"""

import httpx

def main():
    client = httpx.Client(base_url="http://127.0.0.1:8000/api/v1")

    # 1. Login
    print("1. Authenticating as demo student...")
    login_res = client.post("/auth/login", json={
        "email": "student@codeedu.org",
        "password": "StudentPassword123!"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get problems
    print("2. Fetching published problems...")
    problems_res = client.get("/problems")
    assert problems_res.status_code == 200
    problems = problems_res.json()
    p1 = next(p for p in problems if p["slug"] == "print-hello-world-4-times")
    print(f"   Selected problem: '{p1['title']}' (ID: {p1['id']})")

    # 3. Submit compliant code (with loop)
    print("3. Submitting compliant solution with loop...")
    compliant_code = "for i in range(4):\n    print('Hello World')\n"
    sub1_res = client.post("/submissions", headers=headers, json={
        "problem_id": p1["id"],
        "problem_version_number": 1,
        "language": "python",
        "source_code": compliant_code,
    })
    assert sub1_res.status_code == 201
    sub1 = sub1_res.json()
    print(f"   ✅ Total Score: {sub1['total_score']}/100")
    print(f"   Feedback: {sub1['summary_feedback']}")
    for crit in sub1['criteria_scores']:
        print(f"      - {crit['criterion']}: {crit['awarded_points']}/{crit['max_points']} ({crit['reason_code']})")

    # 4. Submit non-compliant code (repeated print without loop)
    print("\n4. Submitting non-compliant solution (repeated print without loop)...")
    non_compliant_code = "print('Hello World')\nprint('Hello World')\nprint('Hello World')\nprint('Hello World')\n"
    sub2_res = client.post("/submissions", headers=headers, json={
        "problem_id": p1["id"],
        "problem_version_number": 1,
        "language": "python",
        "source_code": non_compliant_code,
    })
    assert sub2_res.status_code == 201
    sub2 = sub2_res.json()
    print(f"   ⚠️ Total Score: {sub2['total_score']}/100")
    print(f"   Feedback: {sub2['summary_feedback']}")
    for crit in sub2['criteria_scores']:
        print(f"      - {crit['criterion']}: {crit['awarded_points']}/{crit['max_points']} ({crit['reason_code']})")
    print(f"   Actionable Suggestions: {sub2['actionable_suggestions']}")

    assert sub1['total_score'] == 100.0, "Compliant solution did not score 100.0"
    assert sub2['total_score'] == 50.0, "Non-compliant solution did not score 50.0"
    print("\n🎉 Live HTTP verification succeeded! Platform is completely operational.")

if __name__ == "__main__":
    main()
