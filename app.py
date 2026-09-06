"""Skill Intelligence API - Adaptive AI Quiz Generator & Course Recommender.

Role 3 Module for AI Skill Intelligence & Learning Platform (SIH 2026).
Integrates with Member 2's Skill Extractor & Gap Analysis module
(https://github.com/yash0026-vsf/skill_assessment_).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

# Load environment variables (.env file)
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("skill_intelligence")

app = FastAPI(
    title="AI Skill Intelligence API (Role 3)",
    description="Adaptive AI Quiz Generator and Course Recommendation Engine aligned with SIH 2026 requirements.",
    version="1.1.0",
)

# ---------------------------------------------------------------------------
# Gemini Client Initialization (matching Member 2's SDK)
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = None
MODELS_TO_TRY = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

if GEMINI_API_KEY and GEMINI_API_KEY.strip() and GEMINI_API_KEY != "your_actual_gemini_api_key_here":
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("[AI] Google Gemini client initialized successfully.")
    except Exception as exc:
        logger.warning(f"[AI] Could not initialize Gemini client: {exc}. Falling back to static bank.")
else:
    logger.info("[AI] No GEMINI_API_KEY configured. Running with curated local question bank.")


# ---------------------------------------------------------------------------
# Benchmark Roles Dataset (Member 2 Compatibility)
# ---------------------------------------------------------------------------
def load_role_requirements() -> dict[str, dict[str, int]]:
    """Loads benchmark role requirements from data/employee_requirement.json if available."""
    data_path = Path("data/employee_requirement.json")
    if data_path.exists():
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read {data_path}: {e}")
    # Default benchmark catalog matching Member 2's exact dataset
    return {
        "Data Analyst": {
            "Python": 3, "Data Analysis": 4, "Survey Design": 3,
            "Data Collection": 3, "Statistical Analysis": 4,
        },
        "Data Scientist": {
            "Python": 4, "Machine Learning": 4, "Statistical Analysis": 4,
            "SQL": 3, "Deep Learning": 3,
        },
        "Software Engineer": {
            "Python": 4, "SQL": 3, "Data Structures": 4,
            "System Design": 3, "FastAPI": 3,
        },
    }

ROLE_REQUIREMENTS = load_role_requirements()


# ---------------------------------------------------------------------------
# Course Catalogue (Targeted by Skill & Difficulty Level 1–5)
# ---------------------------------------------------------------------------
COURSES = [
    # Python Tracks
    {"course_id": "py-101", "name": "Python Foundations", "skills": ["Python"], "difficulty_level": 1, "duration_hours": 8, "description": "Syntax, data types, control flow, and basic scripts."},
    {"course_id": "py-201", "name": "Intermediate Python & OOP", "skills": ["Python"], "difficulty_level": 2, "duration_hours": 10, "description": "Functions, object-oriented concepts, exceptions, and packaging."},
    {"course_id": "py-301", "name": "Advanced Python & Modules", "skills": ["Python"], "difficulty_level": 3, "duration_hours": 12, "description": "Iterators, generators, decorators, and context managers."},
    {"course_id": "py-401", "name": "Python for Data Analysis & Pandas", "skills": ["Python", "Data Analysis"], "difficulty_level": 4, "duration_hours": 16, "description": "Pandas, NumPy, vectorization, and data wrangling workflows."},
    {"course_id": "py-501", "name": "High Performance & Concurrent Python", "skills": ["Python"], "difficulty_level": 5, "duration_hours": 20, "description": "AsyncIO, multiprocessing, GIL internals, and C-extensions."},
    # SQL Tracks
    {"course_id": "sql-101", "name": "SQL Essentials", "skills": ["SQL"], "difficulty_level": 1, "duration_hours": 7, "description": "SELECT queries, filtering, joins, and basic aggregation."},
    {"course_id": "sql-201", "name": "Intermediate Relational Database Querying", "skills": ["SQL"], "difficulty_level": 2, "duration_hours": 9, "description": "Grouping, subqueries, and table constraints."},
    {"course_id": "sql-301", "name": "SQL for Analytics & Window Functions", "skills": ["SQL"], "difficulty_level": 3, "duration_hours": 10, "description": "CTEs, RANK(), PARTITION BY, and analytical queries."},
    {"course_id": "sql-401", "name": "Query Optimization & Indexing", "skills": ["SQL"], "difficulty_level": 4, "duration_hours": 14, "description": "Execution plans, B-Tree indices, partitions, and tuning."},
    # Data Analysis & Statistics Tracks
    {"course_id": "da-201", "name": "Exploratory Data Analysis Mastery", "skills": ["Data Analysis"], "difficulty_level": 2, "duration_hours": 10, "description": "Data cleaning, distribution analysis, and anomaly detection."},
    {"course_id": "da-301", "name": "Business Analytics & BI Dashboards", "skills": ["Data Analysis"], "difficulty_level": 3, "duration_hours": 14, "description": "Cohort analysis, KPI trees, and executive dashboards."},
    {"course_id": "da-401", "name": "Advanced Statistical Modeling", "skills": ["Data Analysis", "Statistical Analysis"], "difficulty_level": 4, "duration_hours": 18, "description": "Hypothesis testing, ANOVA, linear regressions, and statistical inference."},
    # Machine Learning Tracks
    {"course_id": "ml-301", "name": "Applied Machine Learning with Scikit-Learn", "skills": ["Machine Learning"], "difficulty_level": 3, "duration_hours": 16, "description": "Classification, regression, cross-validation, and feature engineering."},
    {"course_id": "ml-401", "name": "Advanced ML & Ensemble Architectures", "skills": ["Machine Learning"], "difficulty_level": 4, "duration_hours": 20, "description": "XGBoost, LightGBM, hyperparameter tuning, and pipeline deployment."},
    {"course_id": "dl-301", "name": "Deep Learning Fundamentals & PyTorch", "skills": ["Deep Learning", "Machine Learning"], "difficulty_level": 3, "duration_hours": 22, "description": "Neural nets, backpropagation, and PyTorch tensors."},
    {"course_id": "dl-401", "name": "Computer Vision & NLP with Transformers", "skills": ["Deep Learning"], "difficulty_level": 4, "duration_hours": 24, "description": "CNNs, Attention mechanisms, and HuggingFace transformers."},
]


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Question:
    question_id: str
    skill: str
    difficulty: int
    prompt: str
    options: list[str]
    correct_option: int
    explanation: str

    @property
    def fingerprint(self) -> str:
        """A stable content hash: same wording means same question, even with a new ID."""
        normalized = re.sub(r"\W+", "", self.prompt.lower())
        return hashlib.sha256(f"{self.skill.lower()}:{normalized}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# Curated Question Bank (Levels 1 to 5)
# ---------------------------------------------------------------------------
QUESTION_BANK: list[Question] = [
    # Python
    Question("py-1a", "Python", 1, "Which symbol starts a single-line Python comment?", ["#", "//", "<!--", "*"], 0, "Python comments start with #."),
    Question("py-1b", "Python", 1, "Which built-in type stores whole numbers in Python?", ["str", "int", "list", "bool"], 1, "int stores integer values."),
    Question("py-2a", "Python", 2, "What does len([10, 20, 30]) return?", ["2", "3", "30", "Error"], 1, "The list contains three items."),
    Question("py-2b", "Python", 2, "Which keyword is used to define a function in Python?", ["func", "function", "def", "define"], 2, "Python functions are introduced with def."),
    Question("py-3a", "Python", 3, "What does a Python dictionary store?", ["Only numbers", "Key-value pairs", "Only text", "Sorted files"], 1, "Dictionaries map unique keys to values."),
    Question("py-3b", "Python", 3, "Which block is used to catch exceptions in Python?", ["catch", "except", "error", "handle"], 1, "Python uses try/except blocks."),
    Question("py-4a", "Python", 4, "What is a generator expression mainly useful for?", ["Creating classes", "Memory-efficient lazy iteration", "Writing files", "Installing packages"], 1, "Generators yield items on demand without loading everything in RAM."),
    Question("py-4b", "Python", 4, "What does a context manager guaranteed ensure in Python?", ["A variable is global", "Resources are properly acquired and cleaned up", "Code runs faster", "Lists are sorted"], 1, "With statements ensure __enter__ and __exit__ clean up resources."),
    Question("py-5a", "Python", 5, "Which dual magic methods define the Python Context Manager protocol?", ["__enter__ and __exit__", "__init__ and __str__", "__iter__ and __next__", "__get__ and __set__"], 0, "Context managers must implement __enter__ and __exit__."),
    Question("py-5b", "Python", 5, "What does the Python GIL (Global Interpreter Lock) primarily prevent?", ["Multi-process execution", "True concurrent multi-threaded bytecode execution", "Garbage collection", "File I/O"], 1, "The GIL allows only one thread to hold the Python interpreter at a time."),
    
    # SQL
    Question("sql-1a", "SQL", 1, "Which SQL command is used to read data from a table?", ["GET", "SELECT", "READ", "PULL"], 1, "SELECT retrieves data."),
    Question("sql-2a", "SQL", 2, "Which SQL clause filters records BEFORE grouping?", ["WHERE", "HAVING", "ORDER BY", "LIMIT"], 0, "WHERE filters rows before GROUP BY aggregation."),
    Question("sql-3a", "SQL", 3, "Which JOIN retains all rows from the left table regardless of a match?", ["INNER JOIN", "RIGHT JOIN", "LEFT JOIN", "CROSS JOIN"], 2, "LEFT JOIN preserves left-table rows."),
    Question("sql-4a", "SQL", 4, "Which feature computes ranks or running totals without collapsing rows?", ["GROUP BY", "Window function (OVER)", "DELETE", "DISTINCT"], 1, "Window functions compute across sets of rows while preserving each individual row."),
    Question("sql-5a", "SQL", 5, "What is a Common Table Expression (CTE) defined with?", ["DEFINE TABLE", "WITH", "CREATE CTE", "TEMPORARY"], 1, "A CTE is defined using the WITH statement."),

    # Machine Learning
    Question("ml-1a", "Machine Learning", 1, "What is supervised learning characterized by?", ["Labeled training data", "No target variable", "Agent rewards", "Random noise"], 0, "Supervised learning learns from input-output pairs with known labels."),
    Question("ml-2a", "Machine Learning", 2, "Which metric is best suited for an imbalanced classification problem?", ["Accuracy", "F1-Score / PR-AUC", "Mean Squared Error", "R-squared"], 1, "F1-Score balances precision and recall on skewed target distributions."),
    Question("ml-3a", "Machine Learning", 3, "What problem does L2 regularization (Ridge) primarily mitigate?", ["Overfitting via weight decay", "Underfitting", "Data leakage", "Vanishing gradients"], 0, "L2 penalizes large squared weights, preventing models from overfitting."),
    Question("ml-4a", "Machine Learning", 4, "In Gradient Boosted Trees (e.g. XGBoost), how are new trees trained?", ["Independently in parallel", "Sequentially to predict residual errors of previous trees", "By taking random sub-samples only", "By inverting the covariance matrix"], 1, "Boosting trains subsequent trees sequentially to correct the residual errors."),
    Question("ml-5a", "Machine Learning", 5, "What is the primary motivation for the Scaled Dot-Product Attention in Transformers dividing by sqrt(d_k)?", ["To decrease vocabulary size", "To prevent dot-products from growing excessively large into small gradient regions", "To enforce orthogonality", "To eliminate non-linearities"], 1, "Dividing by sqrt(d_k) prevents the softmax function from saturating into regions with vanishing gradients."),
]

# In-Memory Cache (Can be connected to shared DB)
QUIZ_HISTORY: dict[tuple[str, str], set[str]] = defaultdict(set)
QUIZZES: dict[str, list[Question]] = {}


# ---------------------------------------------------------------------------
# Dynamic AI Question Generation (Gemini 2.5 Flash)
# ---------------------------------------------------------------------------
def generate_questions_with_gemini(skill: str, levels: list[int]) -> list[Question]:
    """Generates novel multiple-choice questions on-the-fly using Google Gemini."""
    if not gemini_client:
        return []

    prompt = f"""You are an expert technical interviewer creating a standardized skill evaluation test for the skill: '{skill}'.
Generate exactly {len(levels)} multiple-choice question(s), one for each difficulty level listed in: {levels}.

Proficiency Level Definitions:
Level 1: Basic awareness and syntax fundamentals.
Level 2: Beginner concepts and simple problem solving.
Level 3: Intermediate practical application, common libraries, debugging.
Level 4: Advanced architectural patterns, performance optimization, best practices.
Level 5: Expert internal workings, edge cases, distributed or complex systems.

Return ONLY a valid JSON array in this exact format:
[
  {{
    "difficulty": 1,
    "prompt": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_option": 0,
    "explanation": "Why this option is correct."
  }}
]

Rules:
- Exactly 4 options per question.
- 'correct_option' must be the 0-indexed integer (0, 1, 2, or 3).
- Output must be strict JSON with no markdown fences or preamble.
"""
    for model_name in MODELS_TO_TRY:
        try:
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            raw_text = response.text.strip()
            # Strip code backticks if model wrapped in ```json ... ```
            clean_json = re.sub(r"^```(?:json)?\s*", "", raw_text)
            clean_json = re.sub(r"\s*```$", "", clean_json).strip()
            
            data = json.loads(clean_json)
            generated: list[Question] = []
            for item in data:
                q_id = f"ai-{skill.lower()[:3]}-{item.get('difficulty', 1)}-{uuid.uuid4().hex[:6]}"
                q = Question(
                    question_id=q_id,
                    skill=skill,
                    difficulty=int(item["difficulty"]),
                    prompt=item["prompt"],
                    options=list(item["options"]),
                    correct_option=int(item["correct_option"]),
                    explanation=item.get("explanation", "Correct choice."),
                )
                generated.append(q)
            logger.info(f"[AI] Successfully generated {len(generated)} questions for {skill} using {model_name}.")
            return generated
        except Exception as exc:
            logger.warning(f"[AI] Generation with {model_name} failed: {exc}. Trying next model...")

    return []


# ---------------------------------------------------------------------------
# Quiz Generation & Recommendation Logic
# ---------------------------------------------------------------------------
def questions_for_new_quiz(employee_id: str, skill: str, count: int) -> list[Question]:
    available = [q for q in QUESTION_BANK if q.skill.lower() == skill.lower()]
    seen = QUIZ_HISTORY[(employee_id, skill.lower())]
    fresh = [q for q in available if q.fingerprint not in seen]

    # If the static bank doesn't have enough unseen questions, generate dynamically with Gemini!
    if len(fresh) < count and gemini_client:
        needed_levels = []
        for level in range(1, 6):
            if not any(q.difficulty == level for q in fresh):
                needed_levels.append(level)
        while len(needed_levels) < (count - len(fresh)):
            needed_levels.append((len(needed_levels) % 5) + 1)

        ai_questions = generate_questions_with_gemini(skill, needed_levels)
        for q in ai_questions:
            if q.fingerprint not in seen:
                QUESTION_BANK.append(q)
                fresh.append(q)

    if not fresh:
        raise HTTPException(
            404,
            f"No questions available for skill '{skill}'. Please check spelling or configure GEMINI_API_KEY in .env for on-the-fly generation."
        )

    # Prioritize 1 question from each difficulty level first
    chosen: list[Question] = []
    for level in range(1, 6):
        match = next((q for q in fresh if q.difficulty == level), None)
        if match and len(chosen) < count:
            chosen.append(match)

    # Fill remaining spots with other fresh questions
    for q in fresh:
        if q not in chosen and len(chosen) < count:
            chosen.append(q)

    if len(chosen) < count and len(fresh) < count:
        # If still short, reuse unused questions or return available
        pass

    return chosen[:count]


def level_from_answers(questions: list[Question], answers: list[Answer]) -> tuple[int, int, int]:
    answer_map = {answer.question_id: answer.selected_option for answer in answers}
    correct_by_level = defaultdict(int)
    asked_by_level = defaultdict(int)
    total_correct = 0

    for question in questions:
        asked_by_level[question.difficulty] += 1
        if answer_map.get(question.question_id) == question.correct_option:
            total_correct += 1
            correct_by_level[question.difficulty] += 1

    # Competency is the highest difficulty level where the candidate achieved >= 60% accuracy
    level = 1
    for difficulty in range(1, 6):
        if asked_by_level[difficulty] and (correct_by_level[difficulty] / asked_by_level[difficulty]) >= 0.60:
            level = difficulty

    return level, total_correct, len(questions)


def recommend(skill: str, current_level: int, required_level: int) -> list[dict]:
    if current_level >= required_level:
        return []
    candidates = [c for c in COURSES if skill.lower() in [s.lower() for s in c["skills"]]]
    useful = [c for c in candidates if current_level < c["difficulty_level"] <= required_level]
    useful.sort(key=lambda c: c["difficulty_level"])
    return [
        {
            **c,
            "reason": f"Bridges gap from Level {current_level} to {required_level} by mastering Level {c['difficulty_level']} concepts."
        }
        for c in useful
    ]


def gap_status(gap: int) -> str:
    """Matches Member 2's gap_analyzer.py status wording exactly."""
    if gap <= 0:
        return "Meets Requirement"
    if gap == 1:
        return "Needs Improvement"
    return "High Priority"


# ---------------------------------------------------------------------------
# API Request / Response Schemas
# ---------------------------------------------------------------------------
class QuizRequest(BaseModel):
    employee_id: str = Field(..., description="Unique employee identifier", min_length=1)
    skill: str = Field(..., description="Skill to test (e.g. Python, SQL, Machine Learning)")
    question_count: int = Field(default=5, ge=1, le=10, description="Number of questions (1-10)")


class Answer(BaseModel):
    question_id: str
    selected_option: int = Field(ge=0, le=3)


class SubmitQuizRequest(BaseModel):
    quiz_id: str
    employee_id: str
    # Compatible with both standard 'role' and Member 2's 'designation'
    role: str | None = None
    designation: str | None = None
    answers: list[Answer]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "service": "Skill Intelligence API (Role 3)",
        "ai_generator_active": gemini_client is not None,
        "available_roles": list(ROLE_REQUIREMENTS.keys()),
    }


@app.get("/roles", tags=["Requirements"])
def get_roles():
    """Returns benchmark role requirements (aligned with Member 2's dataset)."""
    return ROLE_REQUIREMENTS


@app.post("/generate-quiz", tags=["Quiz"])
def generate_quiz(request: QuizRequest):
    """Generates an adaptive quiz across difficulty levels 1 to 5.
    Excludes previously seen questions and invokes Gemini AI if unseen questions run low.
    """
    questions = questions_for_new_quiz(request.employee_id, request.skill, request.question_count)
    quiz_id = str(uuid.uuid4())
    QUIZZES[quiz_id] = questions

    # Record fingerprints in employee's history to avoid repetition on retakes
    QUIZ_HISTORY[(request.employee_id, request.skill.lower())].update(q.fingerprint for q in questions)

    # Return questions with answer keys stripped to prevent cheating
    return {
        "quiz_id": quiz_id,
        "employee_id": request.employee_id,
        "skill": request.skill,
        "question_count": len(questions),
        "questions": [
            {
                "question_id": q.question_id,
                "difficulty": q.difficulty,
                "prompt": q.prompt,
                "options": q.options,
            }
            for q in questions
        ],
    }


@app.post("/submit-quiz", tags=["Quiz"])
def submit_quiz(request: SubmitQuizRequest):
    """Submits candidate answers, computes verified competency level (1-5),
    calculates skill gap against Member 2's benchmarks, and returns personalized course recommendations.
    """
    questions = QUIZZES.get(request.quiz_id)
    if not questions:
        raise HTTPException(404, "Quiz ID not found or session expired. Please generate a new quiz.")

    skill = questions[0].skill
    role_name = request.role or request.designation
    if not role_name:
        raise HTTPException(422, "Please provide 'role' or 'designation' (e.g. 'Data Analyst', 'Data Scientist').")

    required_level = ROLE_REQUIREMENTS.get(role_name, {}).get(skill)
    if required_level is None:
        # If skill not explicitly benchmarked for this role, fallback to default requirement of 3
        required_level = 3

    current_level, correct, total = level_from_answers(questions, request.answers)
    gap = max(0, required_level - current_level)
    status = gap_status(gap)

    answer_map = {a.question_id: a.selected_option for a in request.answers}
    feedback = [
        {
            "question_id": q.question_id,
            "difficulty": q.difficulty,
            "correct": answer_map.get(q.question_id) == q.correct_option,
            "selected_option": answer_map.get(q.question_id),
            "correct_option": q.correct_option,
            "explanation": q.explanation,
        }
        for q in questions
    ]

    return {
        "employee_id": request.employee_id,
        "role": role_name,
        "designation": role_name,
        "assessment_source": "quiz",
        "skill": skill,
        "score": {
            "correct": correct,
            "total": total,
            "percentage": round((correct / total) * 100, 1) if total else 0.0,
        },
        "current_level": current_level,
        "required_level": required_level,
        "gap": gap,
        "status": status,
        "recommended_courses": recommend(skill, current_level, required_level),
        "feedback": feedback,
    }


@app.get("/recommendations", tags=["Recommendations"])
def get_recommendations(
    skill: str = Query(..., description="Target skill"),
    current_level: int = Query(..., ge=1, le=5, description="Candidate's current level (1-5)"),
    required_level: int = Query(..., ge=1, le=5, description="Role benchmark required level (1-5)"),
):
    """Directly fetch recommended courses to bridge a given skill gap."""
    gap = max(0, required_level - current_level)
    return {
        "skill": skill,
        "current_level": current_level,
        "required_level": required_level,
        "gap": gap,
        "status": gap_status(gap),
        "recommended_courses": recommend(skill, current_level, required_level),
    }
