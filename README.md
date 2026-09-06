# AI Skill Intelligence API (Role 3 - SIH 2026)

Adaptive AI Quiz Generator & Course Recommendation Engine for the **AI Skill Intelligence & Learning Platform (PS 26101)**.

This module is designed to seamlessly integrate with [Member 2's Skill Assessment Repository](https://github.com/yash0026-vsf/skill_assessment_).

---

## System Architecture & Team Flow

```
┌───────────────────────────────────────┐
│ Member 2: Resume / Profile Extraction │
│ Uses Gemini to extract baseline level │
└──────────────────┬────────────────────┘
                   │ Baseline Skill & Level (1–5)
                   ▼
┌───────────────────────────────────────┐
│ Member 3 (This Module): AI Quiz & Gap │
│ • Generates adaptive 1–5 level quiz   │
│ • Hybrid AI Engine (Local Bank +      │
│   Gemini 2.5 Flash on-the-fly)        │
│ • Calculates empirical level & gap    │
│ • Recommends targeted courses         │
└──────────────────┬────────────────────┘
                   │ Output payload (gap, status, courses)
                   ▼
┌───────────────────────────────────────┐
│ Members 4 & 5: Backend & UI Dashboard │
│ Unified display for Profile + Quiz    │
└───────────────────────────────────────┘
```

---

## Features

1. **Adaptive Difficulty Levels (1 to 5)**:
   - Evaluates from Level 1 (Basic Awareness) up to Level 5 (Expert / Architecture).
2. **Hybrid AI Engine (Local Bank + Google Gemini Flash)**:
   - Uses a curated local question bank for ultra-fast response.
   - Automatically calls **Google Gemini 2.5 Flash** to generate brand new questions dynamically if an employee retakes the test or requests an unbanked skill.
3. **Anti-Repeat Fingerprinting**:
   - SHA-256 normalized hash guarantees candidates never see duplicate questions on retakes.
4. **Member 2 Schema Alignment**:
   - Directly loads benchmark requirements from `data/employee_requirement.json`.
   - Supports both `role` and Member 2's `designation` parameter.
   - Uses exact matching status strings (`Meets Requirement`, `Needs Improvement`, `High Priority`).
   - Tags results with `"assessment_source": "quiz"`.
5. **Targeted Course Recommendations**:
   - Matches courses whose difficulty level lies strictly within $(current\_level, required\_level]$.
6. **Anti-Cheat Output**:
   - The `/generate-quiz` response strips out the correct answers and explanations so candidates cannot inspect them via browser developer tools.

---

## Quick Start

### 1. Set Up Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure Gemini API Key (Optional for GenAI)

Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Add your Gemini API key in `.env`:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```
*(Note: If no API key is provided, the system seamlessly falls back to the built-in curated question bank!)*

### 4. Run the Server

```powershell
uvicorn app:app --reload
```

Interactive API documentation (Swagger UI) is available at:  
👉 **http://127.0.0.1:8000/docs**

---

## Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/generate-quiz` | Generates a 1–5 level quiz. Body: `{"employee_id":"emp-1","skill":"Python","question_count":5}` |
| `POST` | `/submit-quiz` | Submits answers, computes verified competency level, calculates gap against role, and returns recommendations + feedback. |
| `GET` | `/recommendations` | `?skill=Python&current_level=2&required_level=4`. Returns targeted courses to bridge the gap. |
| `GET` | `/roles` | Returns role requirements loaded from `data/employee_requirement.json`. |
| `GET` | `/health` | Health check probe (`status`, `ai_generator_active`, `available_roles`). |

---

## Run Unit Tests

```powershell
pip install -r requirements-dev.txt
pytest -v
```

---

## How to Push to GitHub

```powershell
git init
git add .
git commit -m "feat: complete Role 3 adaptive quiz generator, course recommendations, and Member 2 integration"
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>.git
git push -u origin main
```
