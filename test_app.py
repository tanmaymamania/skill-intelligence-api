from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "available_roles" in data


def test_roles_endpoint():
    response = client.get("/roles")
    assert response.status_code == 200
    roles = response.json()
    assert "Data Analyst" in roles
    assert "Data Scientist" in roles


def test_quiz_to_assessment_flow():
    # 1. Generate quiz for Python
    quiz = client.post("/generate-quiz", json={
        "employee_id": "emp-test-01",
        "skill": "Python",
        "question_count": 5
    })
    assert quiz.status_code == 200
    body = quiz.json()
    assert "quiz_id" in body
    assert len(body["questions"]) == 5
    
    # Check that answers are stripped in generated questions (anti-cheat)
    for q in body["questions"]:
        assert "correct_option" not in q
        assert "explanation" not in q

    # 2. Submit quiz with all option 0
    answers = [{"question_id": q["question_id"], "selected_option": 0} for q in body["questions"]]
    result = client.post("/submit-quiz", json={
        "quiz_id": body["quiz_id"],
        "employee_id": "emp-test-01",
        "designation": "Data Analyst",
        "answers": answers
    })
    assert result.status_code == 200
    res_data = result.json()
    
    # Validate fields matching Member 2 and system spec
    expected_keys = {
        "employee_id", "role", "designation", "assessment_source",
        "skill", "score", "current_level", "required_level", "gap",
        "status", "recommended_courses", "feedback"
    }
    assert expected_keys.issubset(res_data.keys())
    assert res_data["assessment_source"] == "quiz"
    assert res_data["status"] in ["Meets Requirement", "Needs Improvement", "High Priority"]


def test_direct_recommendations():
    resp = client.get("/recommendations?skill=Python&current_level=1&required_level=4")
    assert resp.status_code == 200
    data = resp.json()
    assert data["gap"] == 3
    assert data["status"] == "High Priority"
    assert len(data["recommended_courses"]) > 0


if __name__ == "__main__":
    print("[RUNNING TESTS] Starting test suite...")
    test_health_endpoint()
    print("  [PASS] test_health_endpoint")
    test_roles_endpoint()
    print("  [PASS] test_roles_endpoint")
    test_quiz_to_assessment_flow()
    print("  [PASS] test_quiz_to_assessment_flow")
    test_direct_recommendations()
    print("  [PASS] test_direct_recommendations")
    print("\n========================================")
    print("  SUCCESS: ALL TESTS PASSED (4/4)")
    print("========================================")
